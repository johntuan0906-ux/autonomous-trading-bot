from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    raw: dict
    api_key: str
    api_secret: str
    mode: str
    dry_run: bool

    @property
    def symbols(self): return self.raw["symbols"]


def load_config(path: str | Path) -> Settings:
    load_dotenv()
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Settings(
        raw=raw,
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        mode=os.getenv("MODE", "testnet").lower(),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
    )
