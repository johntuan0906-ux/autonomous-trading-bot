import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    provider: str = "mock"
    api_key: str = field(default="", repr=False)
    model: str = "gpt-4.1-mini"
    role_models: dict[str, str] = field(default_factory=dict)
    max_turns: int = 6
    max_calls: int = 16
    max_output_tokens: int = 2200
    max_concurrency: int = 3
    max_retries: int = 2
    request_timeout: float = 90
    run_timeout: float = 600
    max_context_chars: int = 20000

    def validate(self) -> "Settings":
        if self.provider not in ("mock", "openai"):
            raise ConfigurationError("PROVIDER chi nhan mock hoac openai")
        limits = {
            "max_turns": (1, 20), "max_calls": (1, 100),
            "max_output_tokens": (256, 16000), "max_concurrency": (1, 8),
            "max_retries": (0, 4), "request_timeout": (1, 600),
            "run_timeout": (1, 3600), "max_context_chars": (100, 100000),
        }
        for key, (lo, hi) in limits.items():
            if not lo <= getattr(self, key) <= hi:
                raise ConfigurationError(f"{key} phai trong khoang {lo}..{hi}")
        if not self.model.strip():
            raise ConfigurationError("OPENAI_MODEL khong duoc de trong")
        return self

    def model_for(self, role: str) -> str:
        return self.role_models.get(role) or self.model

    @classmethod
    def from_env(cls, root: Path, provider: str | None = None) -> "Settings":
        # Chi doc .env canh main.py. Khong tu tim .env cua thu muc cha.
        # Bien da export trong terminal co uu tien hon .env.
        load_dotenv(root / ".env", override=False, encoding="utf-8-sig")
        try:
            return cls(
                provider=provider or os.getenv("PROVIDER", "mock").strip(),
                api_key=os.getenv("OPENAI_API_KEY", "").strip(),
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
                role_models={r: os.getenv(f"MODEL_{r.upper()}", "").strip()
                             for r in ("manager", "planner", "builder", "reviewer", "finalizer")},
                max_turns=int(os.getenv("MAX_TURNS", "6")),
                max_calls=int(os.getenv("MAX_CALLS", "16")),
                max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "2200")),
                max_concurrency=int(os.getenv("MAX_CONCURRENCY", "3")),
                max_retries=int(os.getenv("MAX_RETRIES", "2")),
                request_timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90")),
                run_timeout=float(os.getenv("RUN_TIMEOUT_SECONDS", "600")),
                max_context_chars=int(os.getenv("MAX_CONTEXT_CHARS", "20000")),
            ).validate()
        except ValueError as exc:
            if isinstance(exc, ConfigurationError):
                raise
            raise ConfigurationError("Cau hinh so trong .env khong hop le; doi chieu .env.example") from None
