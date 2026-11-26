"""Don journal: danh dau OPEN bi ghi TRUNG (B-073) bang `void: true`.

Van de: sau khi bot restart / arm lai, buoc ADOPT ghi OPEN lan 2 cho CUNG mot vi
the (B-050) -> journal co 2 OPEN nhung chi co 1 CLOSE -> moi bao cao deu hien
"N OPEN chua co CLOSE" va `live_ready`/`live_guard` canh bao mai.

Cach xu ly: KHONG xoa lich su, chi them `void: true` vao ban ghi OPEN thua;
`monitor_report.load_journal` bo qua ban ghi `void` nen moi bo dem (positions,
live_ready, live_guard, loss_report, telegram_report, dashboard) sach theo.

Dieu kien danh dau (journal.find_duplicate_opens): cung cap + huong + khoi luong,
gia vao lech <= 0.3%, va trong nhom DA co mot OPEN khac duoc CLOSE gan dung.
OPEN khong tim duoc "ban sao" nhu vay -> vao muc CANH BAO, KHONG dung toi
(co the la vi the con mo hoac thieu du lieu).

Chay:
    python tools/journal_fix.py                 # xem truoc (mac dinh)
    python tools/journal_fix.py --apply         # ghi that (co backup)
    python tools/journal_fix.py --journal logs/journal.jsonl --json logs/journal_fix.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:  # noqa: BLE001
    pass

import journal  # noqa: E402
from monitor_report import load_journal, match_pairs  # noqa: E402


def _t(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def _row(rec: dict) -> str:
    return ("%s %-22s %-5s qty=%-10.6g entry=%-12.6g %s"
            % (_t(float(rec.get("ts") or 0)), rec.get("pair") or rec.get("symbol"),
               str(rec.get("direction") or "").upper(),
               float(rec.get("qty") or 0), float(rec.get("entry") or 0),
               "adopted" if rec.get("adopted") else ""))


def _live_keys() -> tuple:
    """Key cac vi the DANG MO tren san (doc quyen) + so vi the — (set, n).

    `n = 0` KHONG co nghia la "khong con vi the nao": co the do loi doc/quyen API.
    Nguoi goi phai coi `n == 0` la KHONG TIN DUOC va khong duoc void gi.
    """
    try:
        from config import Settings
        from exchange import BinanceFutures
        cfg = Settings()
        ex = BinanceFutures(cfg.api_key, cfg.api_secret, cfg.testnet, dry_run=False)
        rows = ex.fetch_positions()
    except Exception as e:  # noqa: BLE001
        print("  [!] khong doc duoc vi the tren san: %s" % str(e)[:120])
        return set(), 0
    keys: set = set()
    n = 0
    for p in rows or []:
        try:
            qty = abs(float(p.get("contracts") or p.get("amount") or 0))
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            continue
        n += 1
        try:
            entry = float(p.get("entryPrice") or 0)
        except (TypeError, ValueError):
            entry = 0.0
        keys.add((str(p.get("symbol") or ""), qty, entry))
    return keys, n


def _held(rec: dict, live: set) -> bool:
    """OPEN nay co con la vi the dang mo tren san khong (khop cap + qty 2% + gia vao 0.5%).

    So ca GIA VAO vi mot cap co the co nhieu vi the cung khoi luong
    (do that: MOG 64.2 @0.08004 cu vs 64.7 @0.07963 dang mo).
    """
    sym = str(rec.get("pair") or rec.get("symbol") or "")
    try:
        q = float(rec.get("qty") or 0)
        e = float(rec.get("entry") or 0)
    except (TypeError, ValueError):
        return False
    for s, lq, le in live:
        if s != sym or lq <= 0 or abs(q - lq) / lq > 0.02:
            continue
        if le > 0 and e > 0 and abs(e - le) / le > 0.005:
            continue
        return True
    return False


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Danh dau OPEN trung trong journal (void)")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--apply", action="store_true",
                    help="ghi that (backup journal truoc khi sua)")
    ap.add_argument("--void-stale", action="store_true",
                    help="danh dau cac OPEN CU khong con vi the tren san va khong co "
                         "CLOSE (reconcile khong ghi bu duoc) — `void_reason=NO_FILL_EVIDENCE`")
    ap.add_argument("--stale-days", type=float, default=1.0,
                    help="chi void OPEN cu hon N ngay (mac dinh 1)")
    ap.add_argument("--json", default="", help="ghi bao cao JSON ra file")
    args = ap.parse_args(argv)

    opens, closes = load_journal(args.journal)
    res = journal.find_duplicate_opens(opens, closes)
    dupes, review = res["dupes"], res["review"]
    _pairs, still = match_pairs(opens, closes)

    print("=" * 92)
    print("JOURNAL FIX | %s | OPEN=%d CLOSE=%d | OPEN chua CLOSE (FIFO)=%d | apply=%s"
          % (args.journal, len(opens), len(closes), len(still), args.apply))
    print("=" * 92)
    if not dupes:
        print("Khong co OPEN trung dang danh dau duoc.")
    for d in dupes:
        o, tw = d["open"], d["twin"] or {}
        print("  x TRUNG  " + _row(o))
        print("           ban sao da co CLOSE: " + _row(tw))
    for o in review:
        op = o["open"] if isinstance(o, dict) and "open" in o else o
        print("  ? XEM TAY " + _row(op) + "  (khong co OPEN nao cung gia da duoc CLOSE)")
    rep = journal.void_records(args.journal, [d["open"] for d in dupes],
                               reason="DUP_OPEN", apply=args.apply)
    stale_rep = None
    if args.void_stale:
        live, n_live = _live_keys()
        print("\nVi the DANG MO tren san: %d" % n_live)
        if n_live <= 0:
            # Khong tin duoc (loi API/quyen/khong ket noi) ⇒ KHONG void gi, neu khong
            # se danh dau ca OPEN cua vi the dang mo (roi khi dong lai sinh CLOSE mo coi).
            print("  [!] khong doc duoc vi the nao ⇒ BO QUA --void-stale (an toan)")
            stale_rep = {"matched": 0, "unmatched": 0, "backup": None, "applied": False}
        else:
            cut = time.time() - float(args.stale_days) * 86400.0
            stale = [o for o in still
                     if float(o.get("ts") or 0) <= cut and not _held(o, live)]
            for o in stale:
                print("  x CU     " + _row(o) + "  (khong con vi the tren san)")
            stale_rep = journal.void_records(
                args.journal, stale,
                reason="NO_FILL_EVIDENCE", apply=args.apply)
            if args.apply:
                print("DA DANH DAU %d OPEN cu (backup: %s)"
                      % (stale_rep["matched"], stale_rep["backup"]))
            else:
                print("(se danh dau %d OPEN cu — them --apply)" % stale_rep["matched"])
    if args.apply:
        print("\nDA DANH DAU %d ban ghi OPEN trung (backup: %s)"
              % (rep["matched"], rep["backup"]))
        o2, c2 = load_journal(args.journal)
        _p2, still2 = match_pairs(o2, c2)
        print("Sau khi sua: OPEN=%d CLOSE=%d -> OPEN chua CLOSE (FIFO)=%d"
              % (len(o2), len(c2), len(still2)))
    else:
        print("\n(chua ghi gi — them --apply de danh dau that; %d ban ghi se duoc void)"
              % rep["matched"])
    if review:
        print("Con %d OPEN can xem tay (khong tu dong void)." % len(review))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"dupes": [{"open": d["open"], "twin": d["twin"]} for d in dupes],
                       "review": review, "result": rep, "stale": stale_rep,
                       "still_before": len(still)}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
