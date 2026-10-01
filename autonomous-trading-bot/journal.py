"""Trade journal: nhat ky moi giao dich (muc 17 tai lieu) — luu JSONL de phan tich sau."""
from __future__ import annotations

import json
import os
import time


def log_trade(path: str = "logs/journal.jsonl", **fields) -> dict:
    rec = {"ts": time.time(), **fields}
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec
