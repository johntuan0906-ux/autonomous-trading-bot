"""Rut kinh nghiem tu journal: in bai hoc + ghi `logs/lessons.json` + `LESSONS.md`.

    python tools/learn_review.py                  # instance hien tai (TESTNET)
    python tools/learn_review.py --target live     # LIVE (../atb-live)
    python tools/learn_review.py --min-n 10 --max-avg-r -0.2
    python tools/learn_review.py --dry             # chi in, khong ghi file

Vi sao: nguoi van hanh yeu cau "luon hoc hoi qua tung lan vao lenh, ghi chu, rut kinh
nghiem de PnL cao hon". Cong cu nay ghep OPEN (feature luc vao lenh) voi CLOSE (ket qua
that) roi gom theo TO HOP dieu kien -> cau tra loi co so lieu: nen tranh gi, nen uu tien gi.

Bot doc `logs/lessons.json` de chan som (xem `LESSONS_ENFORCE` trong `.env`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
sys.path.insert(0, str(ROOT))

import lessons as LES      # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Rut kinh nghiem tu journal")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--min-n", type=int, default=None,
                    help="so mau toi thieu de chan (mac dinh: LESSONS_MIN_N trong .env)")
    ap.add_argument("--max-avg-r", type=float, default=None,
                    help="nguong avgR de chan (mac dinh: LESSONS_MAX_AVG_R trong .env)")
    ap.add_argument("--cap", type=int, default=60, help="tran so to hop giu lai")
    ap.add_argument("--dry", action="store_true", help="chi in, khong ghi file")
    ap.add_argument("--impact", action="store_true",
                    help="bao cao TAC DONG: cong tiet kiem bao nhieu / bo lo bao nhieu")
    ap.add_argument("--sweep", action="store_true",
                    help="quet nhieu nguong avgR -> chon nguong tot nhat bang so lieu")
    ap.add_argument("--prune", action="store_true",
                    help="/prune: truc xuat to hop CU (khong con lenh trong --stale-days)")
    ap.add_argument("--stale-days", type=float, default=30.0,
                    help="so ngay khong co lenh nao thi coi la CU (mac dinh 30, dung voi --prune)")
    ap.add_argument("--evolve", action="store_true",
                    help="/evolve: in KY NANG rut ra tu cac to hop (co ten, doc duoc)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    base = ROOT if args.target == "testnet" else LIVE_DIR
    journal = base / "logs" / "journal.jsonl"
    # Nguong lay tu `.env` cua chinh instance (cung nguon voi bot dung) — de file
    # sinh ra va bot chan theo CUNG mot nguong, khong lech.
    import harness_audit as HA
    env = HA.read_env(base / ".env")
    min_n = int(args.min_n if args.min_n is not None else env.get("LESSONS_MIN_N", 20) or 20)
    max_avg_r = float(args.max_avg_r if args.max_avg_r is not None
                      else env.get("LESSONS_MAX_AVG_R", -0.20) or -0.20)
    enforce = str(env.get("LESSONS_ENFORCE", "false")).lower() in ("1", "true", "yes")
    les = LES.build(journal, cap=args.cap, min_n=min_n, max_avg_r=max_avg_r,
                    stale_days=(args.stale_days if args.prune else 0.0))

    if args.json:
        import json
        print(json.dumps(les, ensure_ascii=False, indent=2))
    else:
        print("=== BAI HOC: %s (%s) ===" % (args.target.upper(), journal))
        print("  lenh da dong doc duoc : %d" % les["trades"])
        print("  to hop theo doi        : %d" % len(les["buckets"]))
        print("  nguong (.env)          : n>=%d, avgR<=%.2f | LESSONS_ENFORCE=%s"
              % (min_n, max_avg_r, enforce))
        print("  to hop DANG CHAN       : %d" % len(les["gates"]))
        if args.prune:
            st = les.get("stale") or {}
            print("  /prune (CU > %.0f ngay)  : truc xuat %d to hop" % (args.stale_days, len(st)))
            for k, why in list(st.items())[:5]:
                print("     - %s (%s)" % (k, why))
        if args.evolve or args.prune:
            sk = les.get("skills") or []
            print("  --- KY NANG (/evolve): %d ---" % len(sk))
            for s in sk:
                print("    [%-8s] %-46s n=%-3d avgR=%+.3f WR=%.0f%% PnL=%+.2f"
                      % (s["kind"], s["name"], s["n"], s["avg_r"], s["wr"], s["pnl"]))
        for s in les["notes"]:
            print("  %s" % s)
        if args.sweep:
            rows = LES.sweep(les["buckets"], min_n=min_n)
            best = LES.best_threshold(rows)
            print("  --- QUET NGUONG avgR (n>=%d) ---" % min_n)
            print("  %-9s %8s %12s %12s %10s" % ("nguong", "so chan", "tiet kiem", "bo lo", "NET"))
            for r in rows:
                mark = "  <-- tot nhat" if best and r["max_avg_r"] == best["max_avg_r"] else ""
                print("  %-9.2f %8d %12.2f %12.2f %10.2f%s"
                      % (r["max_avg_r"], r["n_blocked"], r["saved_pnl"],
                         r["missed_pnl"], r["net"], mark))
            if best:
                print("  => nen dat LESSONS_MAX_AVG_R=%.2f (NET %.2f USDT, chan %d to hop)"
                      % (best["max_avg_r"], best["net"], best["n_blocked"]))
                for k in best["keys"]:
                    print("     - %s" % k)
        if args.impact:
            imp = LES.impact(les["buckets"], min_n=min_n, max_avg_r=max_avg_r)
            print("  --- TAC DONG CUA CONG (uoc tinh tu journal) ---")
            print("  tiet kiem duoc (PnL am bi chan) : %+.2f USDT" % imp["saved_pnl"])
            print("  bo lo (PnL duong sat nguong)    : %+.2f USDT" % imp["missed_pnl"])
            print("  NET                             : %+.2f USDT" % imp["net"])
            for r in imp["blocked"]:
                print("    [CHAN ] %s n=%d avgR=%+.3f PnL=%+.2f"
                      % (r["key"], r["n"], r["avg_r"], r["pnl"]))
            for r in imp["missed"]:
                print("    [BI CHAN NHAM, mat lai] %s n=%d avgR=%+.3f PnL=%+.2f"
                      % (r["key"], r["n"], r["avg_r"], r["pnl"]))
            for r in imp.get("near") or []:
                print("    [SAP bi chan, theo doi] %s n=%d avgR=%+.3f PnL=%+.2f"
                      % (r["key"], r["n"], r["avg_r"], r["pnl"]))

    if not args.dry:
        rep = LES.write_files(les, json_path=base / "logs" / "lessons.json",
                              md_path=base / "LESSONS.md",
                              archive_path=base / "logs" / LES.ARCHIVE_NAME)
        print("  -> %s\n  -> %s (giu phan nguoi viet: %s, truc xuat: %d)"
              % (rep["json"], rep["md"], rep["human_kept"], rep["archived"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
