"""Stress-test DUONG TIEN bang du lieu THAT cua chinh bot (26/10).

Y tuong lay tu Kronos (§21 REPO_IDEAS, muc "sinh du lieu tong hop de stress-test harness"):
thay vi tin vao MOT duong equity da xay ra (co the chi la may man), hay **bootstrap tu phan
phoi R that** cua bot roi tra loi 4 cau hoi van hanh:

  1) Lap lai phan phoi do N lan thi **xac suat ket thuc am** la bao nhieu?
  2) **Drawdown toi da** (theo R va % equity) thuong la bao nhieu?
  3) **Xac suat cham tran lo NGAY** la bao nhieu — voi tran **2%** so voi **6%**?
     (kiem chung quyet dinh cua hoi dong 22/10 bang so)
  4) **Suc chiu CHI PHI**: neu slippage tang them X R/lenh thi con lai bao nhieu co hoi?
     (noi truc tiep voi ket qua probe: chi phi hien tai 0.10-0.16R/lenh)

Tat dinh (seed), KHONG can mang, KHONG cham duong tien (chi doc journal).

Chay:
    python tools/stress_harness.py --target testnet
    python tools/stress_harness.py --target live --paths 5000 --cap-pct 6
    python tools/stress_harness.py --json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atr_quality_probe as AQP      # noqa: E402  (dung lai reader journal)


def load_rs(path: Path) -> list:
    """Danh sach R cua cac lenh DA DONG (tu journal that)."""
    _opens, closes = AQP.load_journal(Path(path))
    out: list = []
    for c in closes:
        try:
            out.append(float(c.get("r") or 0.0))
        except (TypeError, ValueError):
            continue
    return out


def bootstrap(rs: list, *, n_paths: int = 2000, n_trades: int = 200,
              seed: int = 7) -> list:
    """Bootstrap (lay co hoan lai) thanh `n_paths` duong luy ke R — tat dinh theo seed."""
    rnd = random.Random(int(seed))
    pool = list(rs or [])
    if not pool:
        return []
    paths: list = []
    for _ in range(int(n_paths)):
        acc = 0.0
        p: list = []
        for _ in range(int(n_trades)):
            acc += pool[rnd.randrange(len(pool))]
            p.append(acc)
        paths.append(p)
    return paths


def max_drawdown(path: list) -> float:
    """Drawdown toi da (theo R, so duong) cua 1 duong luy ke."""
    peak = 0.0
    worst = 0.0
    for x in path or []:
        peak = max(peak, float(x))
        worst = max(worst, peak - float(x))
    return round(worst, 4)


def pct(vals: list, q: float) -> float:
    xs = sorted(float(v) for v in (vals or []) if v is not None)
    if not xs:
        return 0.0
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return round(xs[i], 4)


def summarize_paths(paths: list) -> dict:
    """Thong ke tren tap duong bootstrap: xac suat am, R cuoi, drawdown."""
    if not paths:
        return {"paths": 0}
    finals = [p[-1] for p in paths if p]
    dds = [max_drawdown(p) for p in paths]
    n = len(finals)
    return {
        "paths": n,
        "p_final_neg": round(sum(1 for f in finals if f < 0) / n, 4) if n else 0.0,
        "final_r_med": pct(finals, 0.5), "final_r_p10": pct(finals, 0.1),
        "final_r_p90": pct(finals, 0.9),
        "dd_r_med": pct(dds, 0.5), "dd_r_p90": pct(dds, 0.9),
    }


def daily_trip_prob(rs: list, *, risk_pct: float = 1.2, cap_pct: float = 6.0,
                    trades_per_day: int = 8, n_paths: int = 2000, seed: int = 7,
                    cost_r: float = 0.0) -> float:
    """Xac suat cham tran lo NGAY trong 1 ngay gia lap.

    Moi lenh rui ro `risk_pct`% equity; lenh co R = r thi PnL = r x risk_pct (%) equity.
    Ngay bi "trip" khi tong PnL ngay <= -cap_pct.
    """
    pool = [float(r) - float(cost_r) for r in (rs or [])]
    if not pool:
        return 0.0
    rnd = random.Random(int(seed) + 991)
    hits = 0
    for _ in range(int(n_paths)):
        day = 0.0
        for _ in range(max(1, int(trades_per_day))):
            day += pool[rnd.randrange(len(pool))] * float(risk_pct)
        if day <= -abs(float(cap_pct)):
            hits += 1
    return round(hits / max(1, int(n_paths)), 4)


def cost_shock(rs: list, shock_r: float) -> list:
    """Tru them `shock_r` R moi lenh (mo phong slippage/phi tang)."""
    return [float(r) - float(shock_r) for r in (rs or [])]


def stress(rs: list, *, n_paths: int = 2000, n_trades: int = 200,
           risk_pct: float = 1.2, cap_pct: float = 6.0, trades_per_day: int = 8,
           seed: int = 7, shocks=(0.0, 0.05, 0.10, 0.20)) -> dict:
    """Bao cao day du: co so + suc chiu chi phi + xac suat trip voi 2 tran."""
    base = summarize_paths(bootstrap(rs, n_paths=n_paths, n_trades=n_trades, seed=seed))
    base.update({
        "n_rs": len(rs or []),
        "mean_r": round(sum(rs) / len(rs), 4) if rs else 0.0,
        "win_rate": round(sum(1 for r in rs if r > 0) / len(rs), 4) if rs else 0.0,
        "risk_pct": risk_pct, "cap_pct": cap_pct, "trades_per_day": trades_per_day,
        "seed": seed,
    })
    by_shock: dict = {}
    for s in shocks:
        sm = summarize_paths(bootstrap(cost_shock(rs, s), n_paths=n_paths,
                                       n_trades=n_trades, seed=seed))
        by_shock["%.2fR" % s] = {"p_final_neg": sm.get("p_final_neg", 0.0),
                                 "final_r_med": sm.get("final_r_med", 0.0)}
    base["by_cost_shock"] = by_shock
    base["trip_prob_cap_2"] = daily_trip_prob(rs, risk_pct=risk_pct, cap_pct=2.0,
                                              trades_per_day=trades_per_day,
                                              n_paths=n_paths, seed=seed)
    base["trip_prob_cap_6"] = daily_trip_prob(rs, risk_pct=risk_pct, cap_pct=6.0,
                                              trades_per_day=trades_per_day,
                                              n_paths=n_paths, seed=seed)
    return base


def verdict(s: dict) -> str:
    if not s.get("paths"):
        return "chua du du lieu"
    parts = []
    pneg = float(s.get("p_final_neg") or 0.0)
    parts.append("P(ket thuc am)=%.0f%% (R trung vi %.1f, p10 %.1f)"
                 % (pneg * 100, float(s.get("final_r_med") or 0),
                    float(s.get("final_r_p10") or 0)))
    ddp90 = float(s.get("dd_r_p90") or 0.0)
    parts.append("drawdown p90 = %.1fR (~%.1f%% equity o risk %.1f%%/lenh)"
                 % (ddp90, ddp90 * float(s.get("risk_pct") or 0.0), s.get("risk_pct")))
    t2, t6 = float(s.get("trip_prob_cap_2") or 0), float(s.get("trip_prob_cap_6") or 0)
    parts.append("P(cham tran ngay) = %.0f%% voi tran 2%% vs %.0f%% voi tran 6%%"
                 % (t2 * 100, t6 * 100))
    bs = s.get("by_cost_shock") or {}
    if "0.10R" in bs and "0.00R" in bs:
        parts.append("chi phi tang 0.10R/lenh: P(am) %.0f%% -> %.0f%%"
                     % (float(bs["0.00R"]["p_final_neg"]) * 100,
                        float(bs["0.10R"]["p_final_neg"]) * 100))
    return " | ".join(parts)


def report_text(s: dict, label: str) -> str:
    lines = [
        "=== STRESS-TEST DUONG TIEN | %s | n_R=%d (WR %.0f%%, E(R) %.3f) ==="
        % (label, int(s.get("n_rs") or 0), float(s.get("win_rate") or 0) * 100,
           float(s.get("mean_r") or 0)),
        "  bootstrap %d duong x 200 lenh (seed %s):"
        % (int(s.get("paths") or 0), s.get("seed")),
        "    P(ket thuc am) = %.0f%% | R cuoi: p10 %.1f, trung vi %.1f, p90 %.1f"
        % (float(s.get("p_final_neg") or 0) * 100, s.get("final_r_p10"),
           s.get("final_r_med"), s.get("final_r_p90")),
        "    drawdown: trung vi %.1fR | p90 %.1fR"
        % (s.get("dd_r_med"), s.get("dd_r_p90")),
        "  xac suat CHAM TRAN NGAY: tran 2%% -> %.1f%% | tran 6%% -> %.1f%% "
        "(risk %.1f%%/lenh, %s lenh/ngay)"
        % (float(s.get("trip_prob_cap_2") or 0) * 100,
           float(s.get("trip_prob_cap_6") or 0) * 100,
           s.get("risk_pct"), s.get("trades_per_day")),
    ]
    bs = s.get("by_cost_shock") or {}
    if bs:
        lines.append("  suc chiu CHI PHI (them X R/lenh):")
        for k in sorted(bs):
            lines.append("    +%s -> P(ket thuc am) %.0f%%, R trung vi %.1f"
                         % (k, float(bs[k]["p_final_neg"]) * 100,
                            float(bs[k]["final_r_med"])))
    lines.append("  KET LUAN: %s" % verdict(s))
    return "\n".join(lines)


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="Stress-test duong tien bang bootstrap tu R that (chi doc)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--journal", default="")
    ap.add_argument("--paths", type=int, default=2000, help="so duong bootstrap")
    ap.add_argument("--trades", type=int, default=200, help="so lenh moi duong")
    ap.add_argument("--risk-pct", type=float, default=1.2, help="risk moi lenh (% equity)")
    ap.add_argument("--cap-pct", type=float, default=6.0, help="tran lo ngay (%)")
    ap.add_argument("--per-day", type=int, default=8, help="so lenh/ngay (gia lap tran ngay)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    base = ROOT if args.target == "testnet" else LIVE_DIR
    jp = Path(args.journal) if args.journal else (base / "logs" / "journal.jsonl")
    rs = load_rs(jp)
    s = stress(rs, n_paths=args.paths, n_trades=args.trades, risk_pct=args.risk_pct,
               cap_pct=args.cap_pct, trades_per_day=args.per_day, seed=args.seed)
    s.update({"target": args.target, "journal": str(jp)})
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        print(report_text(s, "%s | %s" % (args.target.upper(), jp.name)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
