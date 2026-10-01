import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from .config import ConfigurationError, Settings
from .schemas import Contribution, Decision, FinalAnswer


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False,
                 input_tokens: int = 0, output_tokens: int = 0):
        super().__init__(message)
        self.retryable = retryable
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


@dataclass(frozen=True)
class ModelRequest:
    role: str
    instructions: str
    payload: dict[str, Any]
    schema: type[BaseModel]
    max_output_tokens: int


@dataclass(frozen=True)
class ModelResult:
    parsed: BaseModel
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResult: ...
    async def close(self) -> None: ...


class OpenAIProvider:
    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        if client is not None:  # Dependency injection for HTTP contract tests.
            self.client = client
            return
        if not settings.api_key or settings.api_key in ("YOUR_API_KEY", "dien_key_o_day"):
            raise ConfigurationError("Thieu OPENAI_API_KEY. Dien key trong .env hoac chay --provider mock.")
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.api_key, base_url="https://api.openai.com/v1",
            timeout=settings.request_timeout, max_retries=0,
        )

    async def generate(self, request: ModelRequest) -> ModelResult:
        from openai import APIConnectionError, APIStatusError
        try:
            response = await self.client.responses.create(
                model=self.settings.model_for(request.role),
                instructions=request.instructions,
                input=[{"role": "user", "content": json.dumps(request.payload, ensure_ascii=False)}],
                text={"format": {
                    "type": "json_schema", "name": request.schema.__name__,
                    "strict": True, "schema": request.schema.model_json_schema(),
                }},
                max_output_tokens=request.max_output_tokens,
                store=False,
            )
        except APIConnectionError:
            raise ProviderError("Khong ket noi duoc API/het thoi gian. Kiem tra Internet, proxy va TLS.",
                                retryable=True) from None
        except APIStatusError as exc:
            # Do not echo raw server messages: they may contain credentials or submitted text.
            status, code = exc.status_code, getattr(exc, "code", None)
            if status == 401:
                message = "HTTP 401: API key khong hop le/da thu hoi. Tao key cho dung project."
            elif status == 403:
                message = "HTTP 403: tai khoan/project khong co quyen truy cap."
            elif status == 404:
                message = "HTTP 404: model khong ton tai hoac tai khoan khong co quyen dung. Kiem tra OPENAI_MODEL."
            elif status == 429 and code == "insufficient_quota":
                message = "HTTP 429 insufficient_quota: kiem tra so du va han muc API."
            elif status == 429:
                message = "HTTP 429: vuot toc do goi API. Giam MAX_CONCURRENCY."
            elif status >= 500:
                message = f"HTTP {status}: dich vu API tam loi."
            else:
                message = f"HTTP {status}: yeu cau bi tu choi. Kiem tra model ho tro Responses va Structured Outputs."
            retryable = (status in (408, 409, 429) or status >= 500) and code != "insufficient_quota"
            raise ProviderError(message, retryable=retryable) from None

        usage = response.usage
        counts = {"input_tokens": usage.input_tokens if usage else 0,
                  "output_tokens": usage.output_tokens if usage else 0}
        if response.status != "completed":
            raise ProviderError("Phan hoi chua hoan tat. Neu cham gioi han, tang MAX_OUTPUT_TOKENS hoac rut gon nhiem vu.", **counts)
        for output in response.output:
            for part in getattr(output, "content", []):
                if getattr(part, "type", None) == "refusal":
                    raise ProviderError("Model tu choi yeu cau; khong tao ket qua gia de thay the.", **counts)
        try:
            parsed = request.schema.model_validate_json(response.output_text)
        except (ValidationError, ValueError):
            raise ProviderError("Phan hoi khong dat schema JSON/kiem tra noi dung. Xem lai model va prompt.", **counts) from None
        return ModelResult(parsed, **counts)

    async def close(self) -> None:
        await self.client.close()


class MockProvider:
    """Fixed sample responses. Exercises control flow, never claims AI inference."""
    async def generate(self, request: ModelRequest) -> ModelResult:
        await asyncio.sleep(0.02)
        history = request.payload.get("transcript", [])
        if request.schema is Decision:
            spoken = {entry["agent"] for entry in history}
            next_role = next((r for r in ("planner", "builder", "reviewer") if r not in spoken), "finish")
            return ModelResult(Decision(next_speaker=next_role, instruction="Mô phỏng: thực hiện phần việc theo vai trò."))
        if request.schema is FinalAnswer:
            agents = ", ".join(entry["agent"] for entry in history) or "chưa có"
            return ModelResult(FinalAnswer(
                answer_markdown=("## MÔ PHỎNG — chưa gọi AI\n\n"
                                 f"Luồng đã thu đóng góp từ: {agents}.\n\n"
                                 "Bản demo dùng câu trả lời cố định để kiểm tra cấu hình, "
                                 "chuyển việc, chạy song song và lưu log. "
                                 "Để AI giải quyết yêu cầu, cấu hình API key rồi chạy --provider openai."),
                limitations=["Nội dung mô phỏng không chứng minh chất lượng AI hay kết nối API thật."],
            ))
        next_role = {"planner": "builder", "builder": "reviewer", "reviewer": "finish"}[request.role]
        texts = {
            "planner": "[MÔ PHỎNG] Tách mục tiêu thành yêu cầu, sản phẩm và tiêu chí kiểm tra.",
            "builder": "[MÔ PHỎNG] Đề xuất triển khai theo kế hoạch; chưa tạo mã cho mục tiêu cụ thể.",
            "reviewer": "[MÔ PHỎNG] Kiểm tra đủ bước điều phối; chưa kiểm thử sản phẩm do AI tạo.",
        }
        return ModelResult(Contribution(content=texts[request.role], next_agent=next_role,
                                        handoff_note="Bàn giao mô phỏng, dùng để quan sát luồng."))

    async def close(self) -> None:
        pass
