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
    mt = rep.get("match") or {}
    if mt.get("n"):
        # (09/11) Tach "ghep CHINH XAC" (cung decision_id) khoi "ghep doan" (cua so thoi gian):
        # neu ty le chinh xac thap thi bang diem ben duoi KHONG dang tin, du no dep.
        lines.append("Ghep phieu->lenh: %d/%d (%.0f%%) | chinh xac (decision_id) %d"
                     " | doan theo thoi gian %d | noi duoc theo id %d"
                     % (mt.get("matched") or 0, mt.get("n") or 0,
                        100.0 * float(mt.get("rate") or 0.0),
                        mt.get("via_decision_id") or 0, mt.get("via_heuristic") or 0,
                        mt.get("joined_by_id") or 0))
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


#: (01/11) Dieu kien de NANG hoi dong tu SHADOW len VETO THAT — quyet dinh nguoi van hanh
#: 01/11: "**khi nao du dieu kien hay lam that**". Do bang SO DO THAT (khong doan):
#:   - co >= `min_n` phieu ghep duoc lenh; moi model duoc GIU phai `value_r > 0`;
#:   - calibration `brier <= 0.25` (0.25 = doan bua);
#:   - co it nhat 1 model dat (neu khong thi "hoi dong quyet" chi la trang tri).
MIN_N_GATE = 30
MAX_BRIER_GATE = 0.25


def readiness(rep: dict, *, min_n: int = MIN_N_GATE,
              max_brier: float = MAX_BRIER_GATE) -> dict:
    """Hoi dong da DU DIEU KIEN de quyet dinh TIEN THAT chua? (ham THUAN TUY -> test duoc)

    Tra `{ready, reasons, models_ok, cases}`. `ready=False` kem LY DO cu the de biet can do gi.
    """
    reasons: list = []
    rows = rep.get("per_model") or {}
    ok_models: list = []
    for m, b in sorted(rows.items()):
        if int(b.get("matched") or 0) < int(min_n):
            continue
        v = b.get("value_r")
        if v is None or float(v) <= 0:
            reasons.append("model %s: value_r=%s <= 0 (n=%s)"
                           % (m, v, b.get("matched")))
            continue
        ok_models.append(m)
    cal = rep.get("calibration") or {}
    br = cal.get("brier")
    if br is None:
        reasons.append("chua do duoc calibration (brier)")
    elif float(br) > float(max_brier):
        reasons.append("brier %.3f > %.2f (hoi dong qua TU TIN)" % (float(br), max_brier))
    cases = int(rep.get("cases") or 0)
    if cases < int(min_n):
        reasons.append("chi %d phieu ghep duoc < %d" % (cases, min_n))
    if not ok_models:
        reasons.append("khong model nao co value_r > 0 voi n >= %d" % min_n)
    return {"ready": not reasons, "reasons": reasons, "models_ok": ok_models, "cases": cases}


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
    ap.add_argument("--ready", action="store_true",
                    help="chi kiem CONG nang hoi dong SHADOW -> VETO THAT (exit 0 = du dieu kien)")
    ap.add_argument("--gate-n", type=int, default=MIN_N_GATE,
                    help="so phieu ghep toi thieu cho cong nang (mac dinh %d)" % MIN_N_GATE)
    args = ap.parse_args(argv)
    jp = TARGETS[args.target]
    rep = CE.model_leaderboard(str(jp), window_sec=args.window_sec, hours=args.hours,
                               min_n=args.min_n)
    if args.ready:
        g = readiness(rep, min_n=args.gate_n)
        print("=== CONG NANG HOI DONG (SHADOW -> VETO THAT) | %s ===" % args.target)
        print("  phieu ghep duoc : %d (can >= %d)" % (g["cases"], args.gate_n))
        print("  model dat cong  : %s" % (", ".join(g["models_ok"]) or "khong"))
        if g["ready"]:
            print("  KET LUAN: DU DIEU KIEN — co the nang (van can nguoi van hanh xac nhan)")
            return 0
        print("  KET LUAN: CHUA DU — ly do:")
        for r in g["reasons"]:
            print("    - %s" % r)
        return 1
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(render(rep, args.min_n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
