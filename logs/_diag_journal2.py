"""Dieu tra sau: 8 OPEN 'mo coi' trong journal LIVE — doi chieu FILL THAT.

Chay:  python logs\\_diag_journal2.py
Chi DOC: khong ghi journal, khong gui lenh.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "atb-live"
sys.path.insert(0, str(ROOT))

import reconcile as R  # noqa: E402

JOURNAL = str(ROOT / "logs" / "journal.jsonl")
DAYS = 45


def _t(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def main() -> int:
    opens, closes = R.journal_records(JOURNAL)
    still = R.orphan_opens(JOURNAL)
    print("OPEN=%d CLOSE=%d orphans(FIFO)=%d" % (len(opens), len(closes), len(still)))

    from config import Settings
    from exchange import BinanceFutures
    cfg = Settings()
    ex = BinanceFutures(cfg.api_key, cfg.api_secret, cfg.testnet, dry_run=False)

    syms = sorted({str(o.get("pair") or o.get("symbol")) for o in still})
    print("symbol can doi chieu: %s (days=%d)" % (", ".join(syms), DAYS))
    fills = R.fetch_fills(ex, syms, days=DAYS)
    eps, open_pos = R.build_episodes(fills, symbols=set(syms))
    print("fill=%d | vong lenh tai tao=%d | con mo tren san=%d"
          % (len(fills), len(eps), len(open_pos)))
    for p in open_pos:
        print("  [MO] %s %s qty=%.6g entry=%.6g %s"
              % (p["symbol"], p["direction"], p["qty"], p["entry_px"], _t(p["open_ts"] / 1000)))

    for i, o in enumerate(still, 1):
        sym = str(o.get("pair") or o.get("symbol"))
        d = str(o.get("direction") or "").upper()
        ts = float(o.get("ts") or 0)
        print("\n" + "=" * 90)
        print("#%d %s" % (i, _t(ts)))
        print("   OPEN %s %s qty=%.6g entry=%.6g sl=%.6g tp=%.6g strategy=%s adopted=%s"
              % (sym, d, R._f(o.get("qty")), R._f(o.get("entry")), R._f(o.get("sl")),
                 R._f(o.get("tp")), o.get("strategy"), o.get("adopted")))
        twins = [x for x in opens if i - 1 >= 0
                 and str(x.get("pair") or x.get("symbol")) == sym
                 and str(x.get("direction") or "").upper() == d
                 and x is not o and abs(float(x.get("ts") or 0) - ts) <= 7200]
        for x in twins:
            print("   OPEN khac (+-2h) %s qty=%.6g entry=%.6g strategy=%s adopted=%s"
                  % (_t(float(x.get("ts") or 0)), R._f(x.get("qty")),
                     R._f(x.get("entry")), x.get("strategy"), x.get("adopted")))
        cls = [c for c in closes
               if str(c.get("pair") or c.get("symbol")) == sym
               and str(c.get("direction") or "").upper() == d
               and abs(float(c.get("ts") or 0) - ts) <= 7 * 86400]
        for c in cls:
            print("   CLOSE gan (%+.1f ngay) %s qty=%.6g entry=%.6g exit=%.6g pnl=%+.4f %s %s"
                  % ((float(c.get("ts") or 0) - ts) / 86400.0, _t(float(c.get("ts") or 0)),
                     R._f(c.get("qty")), R._f(c.get("entry")), R._f(c.get("exit_price")),
                     R._f(c.get("pnl")), c.get("reason"),
                     "ghi-bu" if c.get("reconciled") else ""))
        near = [e for e in eps
                if e["symbol"] == sym and abs(e["open_ts"] / 1000.0 - ts) <= 2 * 86400]
        for e in near:
            print("   VONG LENH %s->%s %s qty=%.6g entry=%.6g exit=%.6g pnlSan=%+.4f"
                  % (_t(e["open_ts"] / 1000), _t(e["close_ts"] / 1000), e["direction"],
                     e["qty"], e["entry_px"], e["exit_px"], e["realized_pnl"]))
        if not near:
            print("   VONG LENH: khong co (fill ngoai cua so %d ngay hoac lenh tay khong co fill)"
                  % DAYS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
