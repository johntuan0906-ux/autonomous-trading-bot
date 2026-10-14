"""Xem cac ban ghi AGENT cuoi trong journal — tra loi "model nao treo, vi sao".

    python tools/journal_tail.py            # 16 ban ghi cuoi
    python tools/journal_tail.py 40         # 40 ban ghi cuoi
    python tools/journal_tail.py 40 live    # doc journal cua instance LIVE (../atb-live)

Vi sao can: `agents.py --council-health` cho biet TY LE treo theo model, con cong cu
nay cho biet LY DO that (`note=treo/loi/het gio`, `loi provider: ... quota`, ...).
13/10: nho no moi thay `cline-pass/deepseek-v4.1-flash` treo lien tuc trong san xuat.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = ("model", "provider", "status", "action", "reason", "why", "note", "round")


def tail_agents(path, n: int = 16) -> list:
    """N ban ghi event=AGENT cuoi cung trong file journal (ham thuan, test duoc)."""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("event") == "AGENT":
            rows.append(r)
    return rows[-max(1, int(n)):]


def format_row(r: dict) -> str:
    """1 dong de doc: chi lay cac truong co nghia, cat bot cho vua man hinh."""
    return " | ".join("%s=%s" % (k, str(r[k])[:80]) for k in KEEP if r.get(k))


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    args = list(argv if argv is not None else sys.argv[1:])
    n = int(args[0]) if args and args[0].isdigit() else 16
    target = args[1].lower() if len(args) > 1 else "testnet"
    path = (ROOT / "logs" / "journal.jsonl" if target == "testnet"
            else ROOT.parent / "atb-live" / "logs" / "journal.jsonl")
    rows = tail_agents(path, n)
    print("journal=%s | %d ban ghi AGENT cuoi" % (path, len(rows)))
    for r in rows:
        print(format_row(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
