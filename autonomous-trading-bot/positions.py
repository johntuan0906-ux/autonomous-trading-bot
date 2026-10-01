"""Chan doan VI THE: "vi the THAT tren san" vs "lich su journal" vs "state cua bot".

Chay:
    python positions.py            # tat ca
    python positions.py --pair BTC # loc 1 cap

Vi sao can: sau khi dong lenh tay, rat de hieu nham la "bot van bao con vi the BTC".
Ba nguon du lieu KHAC NHAU hoan toan:
  1. fetch_positions() tren san  -> SU THAT DUY NHAT ve vi the dang mo
  2. journal.jsonl (OPEN chua co CLOSE) -> CHI LA LICH SU ghi chep, khong phai
     vi the dang mo (lenh dong co the do SL/TP hoac do tay ngoai bot)
  3. logs/managed_state.json -> state bot dung de quan ly SL/partial/trail

CANH BAO: vi the co tren san nhung KHONG nam trong managed_state = vi the MO TAY
(bot khong quan ly, khong dat SL/TP cho no). CHI DOC — khong dat/huy lenh, khong sua file.
"""
from __future__ import annotations

import argparse
import json
import time

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from monitor_report import load_journal, match_pairs  # noqa: E402


def journal_orphans(path: str) -> list:
    """OPEN chua ghep duoc CLOSE nao (FIFO) — lich su, khong phai vi the dang mo."""
    opens, closes = load_journal(path)
    _pairs, still = match_pairs(opens, closes)
    rows = []
    for o in sorted(still, key=lambda x: float(x.get("ts") or 0)):
        rows.append({"pair": o.get("pair") or o.get("symbol"),
                     "direction": o.get("direction"), "entry": o.get("entry"),
                     "qty": o.get("qty"), "ts": float(o.get("ts") or 0),
                     "strategy": o.get("strategy")})
    return rows


def managed_trades(path: str) -> dict:
    """Danh sach trade bot dang quan ly (managed_state.json)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("trades") or {}
    except Exception:  # noqa: BLE001
        return {}


def kill_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            rs = json.load(f) or {}
        return {"tripped": bool(rs.get("tripped")), "reason": rs.get("reason") or ""}
    except Exception:  # noqa: BLE001
        return {"tripped": False, "reason": ""}


def collect(cfg, ex=None, pair_filter: str | None = None,
            journal_path: str = "logs/journal.jsonl") -> dict:
    """Gom 3 nguon (san / journal / state). ex=None -> bo qua phan san.

    `journal_path` de truyen vao (test/multi-journal); mac dinh logs/journal.jsonl
    — cung duong dan voi turbo_demo/reconcile.
    """
    sym_filter = (pair_filter or "").upper().replace("/USDT:USDT", "").strip() or None

    def _match(sym: str) -> bool:
        s = str(sym or "").upper()
        return not sym_filter or sym_filter in s

    positions, perr = [], ""
    if ex is not None:
        try:
            for p in (ex.fetch_positions() or []):
                if not _match(p.get("symbol")):
                    continue
                pos = {"symbol": p.get("symbol"), "side": p.get("side"),
                       "qty": float(p.get("contracts") or 0),
                       "entry": p.get("entryPrice"), "mark": p.get("markPrice"),
                       "upnl": float(p.get("unrealizedPnl") or 0.0),
                       "lev": p.get("leverage")}
                if abs(pos["qty"]) > 0:
                    positions.append(pos)
        except Exception as e:  # noqa: BLE001
            perr = str(e)[:200]

    ms_path = str(getattr(cfg, "managed_state_path", "logs/managed_state.json"))
    mtr = managed_trades(ms_path)
    ms_syms = {str(k).upper() for k in mtr}
    orphans = [r for r in journal_orphans(journal_path) if _match(r["pair"])]
    managed = {k: v for k, v in mtr.items() if _match(k)}
    unmanaged = [p for p in positions
                 if not any(s in p["symbol"].upper() for s in ms_syms)]
    return {"positions": positions, "pos_error": perr, "orphans": orphans,
            "managed": managed, "unmanaged": unmanaged,
            "kill": kill_state(str(getattr(cfg, "risk_state_path",
                                           "logs/risk_state.json")))}


def _fmt_px(v) -> str:
    try:
        return f"{float(v):g}"
    except Exception:  # noqa: BLE001
        return str(v)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chan doan vi the that vs lich su journal")
    ap.add_argument("--pair", default=None, help="loc 1 cap, vd BTC hoac ETH")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--no-api", action="store_true", help="bo qua goi san (offline)")
    args = ap.parse_args(argv)
    from config import Settings
    cfg = Settings()
    ex = None
    if not args.no_api:
        try:
            from exchange import BinanceFutures
            ex = BinanceFutures(cfg.api_key, cfg.api_secret, cfg.testnet, dry_run=False)
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] khong tao duoc client san: {e}")
    rep = collect(cfg, ex=ex, pair_filter=args.pair, journal_path=args.journal)

    print("=" * 92)
    print(f"POSITIONS DIAGNOSTIC | testnet={cfg.testnet} dry_run={cfg.dry_run} "
          f"pair={args.pair or 'ALL'}")
    print("=" * 92)
    print("\n[1] VI THE THAT TREN SAN (nguon su that DUY NHAT)")
    if rep["pos_error"]:
        print(f"    [LOI] khong doc duoc san: {rep['pos_error']}")
    elif not rep["positions"]:
        print("    (khong co vi the nao dang mo)")
    for p in rep["positions"]:
        tag = ("MO TAY - bot KHONG quan ly" if any(p["symbol"] == q["symbol"]
                                                   for q in rep["unmanaged"])
               else "bot dang quan ly")
        print("    %-16s %-5s qty=%-10s entry=%-12s mark=%-12s uPnL=%+.2f$  [%s]"
              % (p["symbol"], p["side"], p["qty"], _fmt_px(p["entry"]),
                 _fmt_px(p["mark"]), p["upnl"], tag))
    print("\n[2] JOURNAL: OPEN chua ghep CLOSE  (LICH SU, khong phai vi the dang mo)")
    if not rep["orphans"]:
        print("    (khong co)")
    for r in rep["orphans"]:
        when = time.strftime("%m-%d %H:%M", time.gmtime(r["ts"]))
        print("    %s  %-16s %-5s entry=%-12s qty=%s"
              % (when, r["pair"], r["direction"], _fmt_px(r["entry"]), r["qty"]))
    if rep["orphans"]:
        print("    ^ ghi chep lich su (lenh cu). Doi chieu voi fill that: "
              "python reconcile.py")
    print("\n[3] managed_state.json (bot dang giu state cho cac lenh)")
    if not rep["managed"]:
        print("    (rong - bot khong quan ly lenh nao)")
    for sym, t in rep["managed"].items():
        print("    %-16s %-5s entry=%-12s qty=%-10s sl=%-12s partial=%s be=%s"
              % (sym, t.get("direction"), _fmt_px(t.get("entry")), t.get("qty"),
                 _fmt_px(t.get("sl")), t.get("partial_done"), t.get("be_done")))
    k = rep["kill"]
    print("\n[4] KILL-SWITCH: %s" % (f"TRIPPED — {k['reason']}" if k["tripped"]
                                     else "binh thuong"))
    if rep["unmanaged"]:
        print("\n[!] %d vi the MO TAY (co tren san, khong co trong managed_state): "
              "bot BO QUA (khong SL/TP, khong trailing)." % len(rep["unmanaged"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
