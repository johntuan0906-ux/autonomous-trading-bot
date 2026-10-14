"""Cham diem TUNG MODEL hoi dong bang ket qua THAT trong journal (offline, chi doc).

    python tools/council_eval.py                     # TESTNET, 30 ngay gan nhat
    python tools/council_eval.py --target live --hours 336
    python tools/council_eval.py --min-n 5 --json    # JSON de dua vao bao cao khac

Vi sao can (14/10): `agents.py --council-health` chi dem model TREO (khong tra loi).
No khong tra loi duoc cau hoi quan trong hon: **model nao bo phieu DUNG** — phieu ALLOW
cua no co cho ra lenh thang, va phieu VETO cua no co chan dung lenh thua? Cong cu nay
ghep moi phieu voi lenh CLOSE dau tien cung symbol/huong (cua so 1 gio) roi tinh:

  value_r = avgR(lenh duoc PHEP) - avgR(lenh bi CHAN)   -> >0 moi dang giu
  veto_precision = ty le VETO dung (lenh do thua)
  brier = calibration cua `confidence` (0 = hoan hao, 0.25 = doan bua)

Y tuong lay tu `rohitg00/ai-engineering-from-scratch` phase G (eval framework:
classical metrics + calibration + leaderboard) — xem REPO_IDEAS.md §12.1.
Chi DOC journal; khong doi hanh vi trading; de xuat bo model phai do nguoi van hanh dien
vao `.env` (cung khuon voi `council_health`).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import council_evals as CE                                                     # noqa: E402

TARGETS = {"testnet": ROOT / "logs" / "journal.jsonl",
           "live": ROOT.parent / "atb-live" / "logs" / "journal.jsonl"}


def _fmt(v, dash: str = "-") -> str:
    if v is None:
        return dash
    if isinstance(v, float):
        return "%+.3f" % v
    return str(v)


def render(rep: dict, min_n: int) -> str:
    lines = ["=== EVAL HOI DONG (theo KET QUA that) | %s gio | %d phieu ghep duoc ==="
             % (rep.get("window_h") or "toan bo", rep.get("cases") or 0)]
    rows = sorted((rep.get("per_model") or {}).items(),
                  key=lambda kv: (-(kv[1].get("matched") or 0), kv[0]))
    lines.append("%-34s %5s %5s %9s %9s %8s %6s %6s"
                 % ("MODEL", "phieu", "ghep", "ALLOW R", "VETO R", "value", "prec", "brier"))
    for m, b in rows:
        lines.append("%-34s %5d %5d %9s %9s %8s %6s %6s"
                     % (m, b["votes"], b["matched"], _fmt(b["allow_avg_r"]),
                        _fmt(b["veto_avg_r"]), _fmt(b["value_r"]),
                        _fmt(b["veto_precision"]), _fmt(b["brier"])))
    cal = rep.get("calibration") or {}
    if cal.get("brier") is not None:
        lines.append("")
        lines.append("Calibration (n=%d, brier=%.3f — cang thap cang tot):"
                     % (cal.get("n") or 0, cal["brier"]))
        for b in cal.get("bins") or []:
            lines.append("  conf %.1f-%.1f: n=%-3d thang that %.0f%% (khai bao %.0f%%)"
                         % (b["lo"], b["hi"], b["n"], 100 * b["win_rate"],
                            100 * b["conf_avg"]))
    lines.append("")
    if rep.get("keep"):
        lines.append("GIU (value_r > 0): " + ", ".join(rep["keep"]))
    if rep.get("drop"):
        lines.append("NEN BO (value_r <= 0, n_ghep >= %d): %s" % (min_n, ", ".join(rep["drop"])))
    if rep.get("thin"):
        lines.append("CHUA DU MAU (n_ghep < %d, KHONG ket luan): %s"
                     % (min_n, ", ".join(rep["thin"])))
    for ln in rep.get("skip_lines") or []:
        lines.append("  -> dien vao .env:  " + ln)
    if not (rep.get("keep") or rep.get("drop")):
        lines.append("Chua du bang chung de xep hang model (can nhieu phieu + lenh CLOSE hon).")
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Cham diem tung model hoi dong (offline)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--hours", type=float, default=720.0,
                    help="cua so gio (mac dinh 720 = 30 ngay)")
    ap.add_argument("--min-n", type=int, default=8,
                    help="so phieu PHAI ghep duoc lenh moi ket luan (mac dinh 8)")
    ap.add_argument("--window-sec", type=float, default=3600.0,
                    help="cua so ghep phieu -> lenh CLOSE (giay)")
    ap.add_argument("--json", action="store_true", help="in JSON (cho bao cao khac)")
    args = ap.parse_args(argv)
    jp = TARGETS[args.target]
    rep = CE.model_leaderboard(str(jp), window_sec=args.window_sec, hours=args.hours,
                               min_n=args.min_n)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(render(rep, args.min_n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
