"""Dieu tra 8 OPEN 'mo coi' trong journal LIVE (chi doc, khong ghi gi).

Chay:  python logs\\_diag_journal.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "atb-live"
sys.path.insert(0, str(ROOT))

import reconcile as R  # noqa: E402

JOURNAL = ROOT / "logs" / "journal.jsonl"


def main() -> int:
    opens, closes = R.journal_records(str(JOURNAL))
    # FIFO theo (pair, side) — cung quy uoc voi positions.py
    from collections import defaultdict
    by_key: dict = defaultdict(list)
    for o in opens:
        key = (str(o.get("pair") or o.get("symbol")), str(o.get("side") or "").upper())
        by_key[key].append(o)
    still = R.orphan_opens(str(JOURNAL))
    print("OPEN=%d CLOSE=%d  mo coi(FIFO)=%d" % (len(opens), len(closes), len(still)))
    for o in still:
        sym = str(o.get("pair") or o.get("symbol"))
        side = str(o.get("side") or "").upper()
        ts = float(o.get("ts") or 0)
        n_open = sum(1 for x in by_key[(sym, side)])
        n_close = sum(1 for c in closes
                      if str(c.get("pair") or c.get("symbol")) == sym
                      and str(c.get("side") or "").upper() == side)
        print("\n--- %s %s qty=%s entry=%s ts=%s" %
              (sym, side, o.get("qty"), o.get("price") or o.get("entry"), o.get("ts")))
        print("    strategy=%s adopted=%s reason=%s" %
              (o.get("strategy"), o.get("adopted"), o.get("reason")))
        print("    tong OPEN cung cap/huong=%d | tong CLOSE=%d" % (n_open, n_close))
        same = [x for x in by_key[(sym, side)]
                if abs(float(x.get("ts") or 0) - ts) <= 900]
        print("    OPEN khac trong +-15 phut: %d" % max(0, len(same) - 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
