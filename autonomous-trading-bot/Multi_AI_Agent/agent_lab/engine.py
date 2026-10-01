import asyncio
import copy
import random
import time

from .config import Settings
from .prompts import instructions
from .providers import ModelRequest, Provider, ProviderError
from .schemas import ConsensusTurn, Contribution, Decision, FinalAnswer
from .storage import RunStore, now

AGENTS = ("planner", "builder", "reviewer")
HANDOFFS = {
    "planner": {"builder"},
    "builder": {"planner", "reviewer"},
    "reviewer": {"planner", "builder", "finish"},
}


class BudgetExceeded(RuntimeError):
    pass


class WorkflowError(RuntimeError):
    pass


class Engine:
    def __init__(self, settings: Settings, provider: Provider, store: RunStore,
                 task: str, context: list[dict], context_metadata: list[dict], mode: str):
        self.settings = settings.validate()
        self.provider, self.store, self.context = provider, store, context
        self.semaphore = asyncio.Semaphore(settings.max_concurrency)
        self.budget_lock = asyncio.Lock()
        self.state = {
            "started_at": now(), "mode": mode, "provider": settings.provider,
            "model": settings.model, "role_models": settings.role_models,
            "task": task, "context_files": context_metadata, "status": "running",
            "transcript": [], "decisions": [], "warnings": [], "errors": [], "final": None,
            "usage": {"calls_attempted": 0, "input_tokens": 0, "output_tokens": 0},
        }

    def snapshot(self) -> None:
        self.store.checkpoint(self.state)

    def payload(self, instruction: str = "", *, independent: bool = False) -> dict:
        return {
            "task": self.state["task"], "mode": self.state["mode"],
            "instruction": instruction, "context": copy.deepcopy(self.context),
            "transcript": [] if independent else copy.deepcopy(self.state["transcript"]),
            "warnings": list(self.state["warnings"]), "errors": list(self.state["errors"]),
        }

    def add_usage(self, result) -> None:
        self.state["usage"]["input_tokens"] += result.input_tokens
        self.state["usage"]["output_tokens"] += result.output_tokens

    async def call(self, role: str, schema, payload: dict):
        request = ModelRequest(role, instructions(role), payload, schema,
                               min(500, self.settings.max_output_tokens) if role == "manager"
                               else self.settings.max_output_tokens)
        for attempt in range(self.settings.max_retries + 1):
            async with self.semaphore:
                async with self.budget_lock:
                    if self.state["usage"]["calls_attempted"] >= self.settings.max_calls:
                        raise BudgetExceeded("Da cham MAX_CALLS; bao gom ca cac lan goi thu lai.")
                    self.state["usage"]["calls_attempted"] += 1
                    call_id = self.state["usage"]["calls_attempted"]
                self.store.event("call_start", call=call_id, agent=role, attempt=attempt + 1)
                started = time.monotonic()
                try:
                    async with asyncio.timeout(self.settings.request_timeout):
                        result = await self.provider.generate(request)
                    self.add_usage(result)
                    self.store.event("call_done", call=call_id, agent=role,
                                     seconds=round(time.monotonic() - started, 2))
                    self.snapshot()
                    return result.parsed
                except asyncio.CancelledError:
                    self.store.event("call_cancelled", call=call_id, agent=role)
                    raise
                except (ProviderError, TimeoutError) as exc:
                    if isinstance(exc, TimeoutError):
                        error = ProviderError("Vuot REQUEST_TIMEOUT_SECONDS.", retryable=True)
                    else:
                        error = exc
                        self.add_usage(error)
                    self.store.event("call_error", call=call_id, agent=role, error=str(error))
                    self.snapshot()
                    if not error.retryable or attempt == self.settings.max_retries:
                        raise error
            delay = min(8, 2 ** attempt) + random.uniform(0, 0.25)
            self.store.event("retry", agent=role, wait_seconds=round(delay, 2))
            await asyncio.sleep(delay)
        raise WorkflowError("Khong nhan duoc phan hoi")

    def append(self, agent: str, result: Contribution) -> None:
        self.state["transcript"].append({"agent": agent, "timestamp": now(), **result.model_dump()})
        self.snapshot()

    def limited(self, message: str) -> None:
        self.state["status"] = "limit_reached"
        self.state["warnings"].append(message)

    async def group(self) -> None:
        for turn in range(self.settings.max_turns):
            decision = await self.call("manager", Decision, self.payload(
                f"Lượt chuyên gia tiếp theo {turn + 1}/{self.settings.max_turns}. "
                "Chọn người tiếp theo hoặc finish khi đủ đóng góp và đã có review cuối."
            ))
            requested, selected = decision.next_speaker, decision.next_speaker
            history = self.state["transcript"]
            missing = [r for r in AGENTS if r not in {m["agent"] for m in history}]
            if selected == "finish":
                if missing:
                    selected = missing[0]
                elif history[-1]["agent"] != "reviewer":
                    selected = "reviewer"
            self.state["decisions"].append({"requested": requested, "selected": selected,
                                           "instruction": decision.instruction})
            self.store.event("manager_decision", requested=requested, selected=selected)
            self.snapshot()
            if selected == "finish":
                return
            instruction = decision.instruction if selected == requested else "Bổ sung phần việc còn thiếu theo vai trò của bạn."
            result = await self.call(selected, Contribution, self.payload(instruction))
            self.append(selected, result)
        self.limited("Group chat hết MAX_TURNS trước quyết định kết thúc của manager; cần xem lại kết quả.")

    async def handoff(self) -> None:
        current = "planner"
        for turn in range(self.settings.max_turns):
            allowed = sorted(HANDOFFS[current])
            result = await self.call(current, Contribution, self.payload(
                f"Lượt {turn + 1}/{self.settings.max_turns}. Hoàn thành phần việc và chọn next_agent "
                f"trong {allowed}. handoff_note ghi việc cụ thể cần người sau xử lý."
            ))
            self.append(current, result)
            if result.next_agent not in HANDOFFS[current]:
                raise WorkflowError(f"Ban giao khong hop le: {current} -> {result.next_agent}.")
            self.store.event("handoff", source=current, target=result.next_agent)
            if result.next_agent == "finish":
                return
            current = result.next_agent
        self.limited("Hand-off hết MAX_TURNS; vẫn còn bước cần làm. Xem transcript trước khi chạy lại.")

    async def parallel(self) -> None:
        # Freeze one input snapshot before starting any worker. No worker sees peer results.
        common = self.payload("Đánh giá độc lập từ góc nhìn vai trò của bạn. Đề xuất ý tưởng nên giữ/loại "
                              "kèm tiêu chí và bằng chứng. next_agent/handoff_note không điều khiển chế độ này.",
                              independent=True)

        async def worker(role: str):
            result = await self.call(role, Contribution, copy.deepcopy(common))
            self.append(role, result)

        results = await asyncio.gather(*(worker(role) for role in AGENTS), return_exceptions=True)
        for role, result in zip(AGENTS, results):
            if isinstance(result, BaseException):
                if isinstance(result, asyncio.CancelledError):
                    raise result
                if not isinstance(result, (ProviderError, BudgetExceeded, WorkflowError)):
                    raise result
                self.state["errors"].append(f"{role}: {result}")
        if not self.state["transcript"]:
            raise WorkflowError("Ca ba agent deu that bai; khong co du lieu de tong hop.")
        if self.state["errors"]:
            self.state["status"] = "partial"
            self.state["warnings"].append("Thiếu báo cáo của ít nhất một chuyên gia; bản tổng hợp có giới hạn.")

    def _consensus_final(self, turns: dict, *, converged: bool) -> None:
        """Ghep cau tra loi bang code tu chinh cac agent — khong qua model nao chon/dien giai lai."""
        heading = ("## Đồng thuận giữa planner/builder/reviewer" if converged
                  else "## Chưa đạt đồng thuận — các vai trò còn khác biệt")
        lines = [heading]
        for role in AGENTS:
            turn = turns.get(role)
            if turn is not None:
                lines.append(f"**{role}**: {turn.recommendation}")
        disagreements = sorted({d for t in turns.values() for d in t.open_disagreements})
        if not converged and not disagreements:
            disagreements = ["Het so vong cho phep (MAX_TURNS) ma chua ca ba xac nhan dong y."]
        self.state["final"] = {"answer_markdown": "\n\n".join(lines), "limitations": disagreements}

    async def consensus(self) -> None:
        """Khong co nguoi chon cau tra loi: dung khi CA BA agent TU xac nhan dong y
        (agrees_with_all), khong thi bao ro con bat dong thay vi an di bang 1 ban tong
        hop nghe tron tru. Vong 1 doc lap; tu vong 2 moi agent doc recommendation/
        open_disagreements vong truoc cua CA BA roi tu quyet dinh co con phan doi khong.
        """
        last: dict[str, ConsensusTurn] = {}
        for turn in range(self.settings.max_turns):
            independent = turn == 0
            instruction = (
                "Vòng 1: đánh giá độc lập, đề xuất recommendation cụ thể và nêu điểm còn cần kiểm tra."
                if independent else
                f"Vòng {turn + 1}: đọc recommendation/open_disagreements vòng trước của CẢ BA vai trò. "
                "Nếu không còn phản đối, đặt agrees_with_all=true và open_disagreements rỗng. "
                "Nếu còn, giữ agrees_with_all=false và nêu cụ thể trong open_disagreements."
            )
            common = self.payload(instruction, independent=independent)
            round_turns: dict[str, ConsensusTurn] = {}

            async def worker(role: str) -> None:
                result = await self.call(role, ConsensusTurn, copy.deepcopy(common))
                self.append(role, result)
                round_turns[role] = result

            results = await asyncio.gather(*(worker(role) for role in AGENTS), return_exceptions=True)
            for role, outcome in zip(AGENTS, results):
                if isinstance(outcome, BaseException):
                    if isinstance(outcome, asyncio.CancelledError):
                        raise outcome
                    if not isinstance(outcome, (ProviderError, BudgetExceeded, WorkflowError)):
                        raise outcome
                    self.state["errors"].append(f"{role}: {outcome}")
            last.update(round_turns)
            if len(round_turns) < len(AGENTS):
                self.state["status"] = "partial"
                self.state["warnings"].append("Thiếu phản hồi ít nhất một agent trong vòng đồng thuận; dừng sớm.")
                self._consensus_final(last, converged=False)
                return
            if all(t.agrees_with_all for t in round_turns.values()):
                self._consensus_final(last, converged=True)
                return
        self._consensus_final(last, converged=False)
        self.limited(f"Không đồng thuận sau {self.settings.max_turns} vòng; xem các bất đồng còn lại.")

    async def run(self) -> dict:
        self.snapshot()
        try:
            async with asyncio.timeout(self.settings.run_timeout):
                mode = self.state["mode"]
                if mode not in ("group", "handoff", "parallel", "consensus"):
                    raise WorkflowError("Mode khong hop le")
                await {"group": self.group, "handoff": self.handoff, "parallel": self.parallel,
                      "consensus": self.consensus}[mode]()
                if self.state["final"] is None:
                    final = await self.call("finalizer", FinalAnswer, self.payload("Tổng hợp kết quả có thể áp dụng."))
                    self.state["final"] = final.model_dump()
                if self.state["status"] == "running":
                    self.state["status"] = "completed"
        except BudgetExceeded as exc:
            self.limited(str(exc))
        except TimeoutError:
            self.limited("Vuot RUN_TIMEOUT_SECONDS; da huy cac tac vu dang cho.")
        except (ProviderError, WorkflowError) as exc:
            self.state["status"] = "failed"
            self.state["errors"].append(str(exc))
        except asyncio.CancelledError:
            self.state["status"] = "interrupted"
            self.state["warnings"].append("Người dùng dừng hoặc tiến trình bị hủy. Giữ các đóng góp đã nhận.")
            raise
        except Exception:
            self.state["status"] = "failed"
            self.state["errors"].append("Lỗi nội bộ chưa xử lý; kiểm tra mã bằng VS Code debugger.")
            raise
        finally:
            self.state["finished_at"] = now()
            self.snapshot()
            self.store.report(self.state)
            self.store.event("finished", status=self.state["status"])
        return self.state
