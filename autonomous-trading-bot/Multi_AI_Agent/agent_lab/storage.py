import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_json_atomic(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


class RunStore:
    def __init__(self, path: Path, quiet: bool = False):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=False)
        self.quiet = quiet

    def event(self, event: str, **data) -> None:
        row = {"timestamp": now(), "event": event, **data}
        with (self.path / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        if not self.quiet and event in ("call_start", "call_done", "retry", "call_error", "handoff", "finished"):
            print(f"[{row['timestamp'][11:19]} UTC] {event}: "
                  + ", ".join(f"{k}={v}" for k, v in data.items()), flush=True)

    def checkpoint(self, state: dict) -> None:
        write_json_atomic(self.path / "transcript.json", state)

    def report(self, state: dict) -> None:
        final = state.get("final")
        body = final["answer_markdown"] if final else "Chưa có bản tổng hợp hoàn chỉnh. Xem các đóng góp bên dưới."
        note = "MÔ PHỎNG — không gọi AI" if state["provider"] == "mock" else "OpenAI API"
        sections = ["# Kết quả multi-agent", f"Chế độ: {state['mode']} | Provider: {note}",
                    f"Trạng thái luồng: `{state['status']}` (không phải chứng nhận chất lượng).",
                    "## Yêu cầu", state["task"], "## Kết quả", body]
        limitations = (final or {}).get("limitations", []) + state["warnings"]
        if limitations:
            sections.extend(["## Giới hạn / việc cần kiểm tra", "\n".join("- " + x for x in limitations)])
        if state["errors"]:
            sections.extend(["## Lỗi", "\n".join("- " + x for x in state["errors"])])
        sections.append("## Đóng góp của từng agent")
        for row in state["transcript"]:
            sections.extend([f"### {row['agent']}", row["content"], "Bàn giao: " + row["handoff_note"]])
        usage = state["usage"]
        sections.extend(["## Thống kê", f"Lượt gọi thử: {usage['calls_attempted']}; "
                         f"input tokens: {usage['input_tokens']}; output tokens: {usage['output_tokens']}.",
                         "Token là số API trả về cho các phản hồi nhận được, không thay thế hóa đơn nhà cung cấp."])
        (self.path / "report.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
