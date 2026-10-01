"""Sweep tham so SL/TP/quan ly lenh tren du lieu that -> tim cau hinh WR/PF tot nhat.

Chay: python sweep.py --days 10 --tf 15m
"""
from __future__ import annotations

import argparse
import itertools
import json
import os

import backtest as bt


def grid(quick: bool = True) -> list[dict]:
    sls = (1.5, 2.0) if quick else (1.2, 1.5, 2.0, 2.5)
    tps = (2.5, 3.0, 4.0) if quick else (2.0, 3.0, 4.0, 5.0)
    parts = ((0.0, 0.5, 1.0) if quick else (0.0, 0.3, 0.5, 1.0))
    out = []
    for sl, tp, pa in itertools.product(sls, tps, parts):
        if tp / sl < 1.66:
            continue
        out.append({"sl_mult": sl, "tp_mult": tp, "partial_at_r": pa,
                    "partial_pct": 0.5, "be_at_r": 1.0,
                    "trail_atr_mult": 1.0 if pa > 0 else 0.0})
    return out


def name_of(c: dict) -> str:
    return (f"SL{c['sl_mult']}_TP{c['tp_mult']}_P{c['partial_at_r']}"
            f"_BE{c['be_at_r']}_T{c['trail_atr_mult']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--tf", default="15m")
    ap.add_argument("--min-alpha", type=float, default=0.05)
    ap.add_argument("--score", type=float, default=0.0)
    ap.add_argument("--risk", type=float, default=0.005)
    ap.add_argument("--out", default="logs/sweep_result.json")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args(argv)

    import ccxt  # type: ignore
    ex = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})
    frames: dict = {}
    sig_cache: dict = {}
    for sym in bt.SYMBOLS:
        df = bt.fetch_klines(sym, args.tf, args.days, exchange=ex)
        frames[sym] = df
        sigs = bt.build_signals(df, min_alpha=args.min_alpha, min_score100=args.score)
        for s in sigs:
            s["symbol"] = sym
        sig_cache[sym] = sigs
        print(f"[OK] {sym}: {len(df)} nen, {len(sigs)} tin hieu")

    rows = []
    for cfg in grid(quick=not args.full):
        trades: list[dict] = []
        eq = [1000.0]
        bal = 1000.0
        for sym, df in frames.items():
            res = bt.simulate(df, sig_cache[sym], cfg, balance0=bal, risk_pct=args.risk)
            trades += res["trades"]
            bal = max(0.0, bal + sum(t["pnl"] for t in res["trades"]))
            eq += res["equity"][1:]
        st = bt.stats(trades, eq, 1000.0)
        rows.append({"cfg": cfg, "name": name_of(cfg), "stats": st,
                     "verdict": bt.verdict(st)})

    rows.sort(key=lambda r: (-r["stats"]["exp_r"], -r["stats"]["net_pf"]))
    print("\n" + "=" * 100)
    print(f"SWEEP {args.tf} | {args.days} ngay | min_alpha={args.min_alpha} | "
          f"risk={args.risk:.2%} | {len(rows)} cau hinh")
    print("=" * 100)
    print(f"{'config':34} {'n':>5} {'WR%':>6} {'PF':>6} {'E(R)':>8} {'net$':>9} "
          f"{'DD%':>6} {'streak':>6} {'verdict':>17}")
    print("-" * 100)
    for r in rows[:15]:
        st = r["stats"]
        print(f"{r['name']:34} {st['n']:>5} {st['wr'] * 100:>6.1f} {st['net_pf']:>6.3f} "
              f"{st['exp_r']:>8.4f} {st['net']:>9.2f} {st['max_dd_pct']:>6.2f} "
              f"{st['streak_loss']:>6} {r['verdict']:>17}")
    print("-" * 100)
    best = rows[0]
    st = best["stats"]
    print(f"BEST: {best['name']}  WR={st['wr'] * 100:.1f}%  PF={st['net_pf']:.3f} "
          f"E={st['exp_r']:+.4f}R  n={st['n']}  {best['verdict']}")
    for key in ("by_symbol", "by_direction", "by_strategy", "by_regime"):
        if st.get(key):
            print(f"  {key}: " + " | ".join(
                f"{k}: n={v['n']} WR={v['wr'] * 100:.0f}% avgR={v['avgR']:+.3f}"
                for k, v in sorted(st[key].items())))
    print(f"  exit_mix: {st.get('exit_mix')}")
    try:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"args": vars(args), "rows": rows}, f, ensure_ascii=False, indent=1)
        print(f"[OK] da luu {args.out}")
    except Exception as exc:
        print(f"[WARN] {exc}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
