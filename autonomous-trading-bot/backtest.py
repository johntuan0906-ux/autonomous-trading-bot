"""Backtest nhanh (muc 20/26 tai lieu): replay nen lich su 4 cap, so bien the
quan ly lenh (baseline / break-even / partial+trail / wide-stop) va in
WR - Net PF - expectancy - Max DD trong vai phut thay vi cho demo vai ngay.

Chay:  python backtest.py --days 30 --tf 5m --min-alpha 0.05 [--score 60]

Trung thuc ve gioi han:
- Khong co du lieu tin tuc / OI / funding lich su -> cac phan do de 0 (chi cham
  phan ky thuat + quan ly lenh). Ket qua KHONG phai bang chung cho phan sentiment.
- Khop lenh bi quan: neu 1 nen cham ca SL lan TP thi tinh SL truoc.
- Phi 0.05% x 2 chieu (taker) da tru trong PnL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

from indicators import market_regime, technical_score
from learner import signal_score_100, structure_score
from strategy import classify_strategy
from trade_mgmt import FEE_ROUNDTRIP_PCT, manage, new_trade, trade_result

SYMBOLS = ("BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT")

VARIANTS: dict[str, dict] = {
    "V0_baseline_1.5_3": dict(sl_mult=1.5, tp_mult=3.0, partial_at_r=0.0,
                              partial_pct=0.5, be_at_r=0.0, trail_atr_mult=0.0),
    "V1_breakeven_1R": dict(sl_mult=1.5, tp_mult=3.0, partial_at_r=0.0,
                            partial_pct=0.5, be_at_r=1.0, trail_atr_mult=0.0),
    "V2_partial_be_trail": dict(sl_mult=1.5, tp_mult=3.0, partial_at_r=1.0,
                                partial_pct=0.5, be_at_r=1.0, trail_atr_mult=1.0),
    "V3_wide_partial_trail": dict(sl_mult=2.0, tp_mult=4.0, partial_at_r=1.0,
                                  partial_pct=0.5, be_at_r=1.0, trail_atr_mult=1.5),
}


def fetch_klines(symbol: str, timeframe: str = "5m", days: int = 30,
                 exchange=None) -> pd.DataFrame:
    """Lay nen lich su tu Binance Futures public (phan trang, khong can key)."""
    if exchange is None:
        import ccxt  # type: ignore
        exchange = ccxt.binance({"options": {"defaultType": "future"},
                                 "enableRateLimit": True})
    tf_ms = exchange.parse_timeframe(timeframe) * 1000
    now = exchange.milliseconds()
    since = now - days * 24 * 60 * 60 * 1000
    rows: list = []
    while since < now:
        batch = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not batch:
            break
        rows += batch
        since = batch[-1][0] + tf_ms
        if len(batch) < 1000:
            break
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset=["ts"]).reset_index(drop=True)
    df["ts"] = pd.to_datetime(df["ts"], unit="ms")
    return df



def build_signals(df: pd.DataFrame, atr_period: int = 14, min_alpha: float = 0.05,
                  min_score100: float = 0.0, warmup: int = 210,
                  window: int = 220) -> list[dict]:
    """Duyet tung nen: technical_score tren cua so truot -> tin hieu.

    Entry = open cua nen ke tiep (tranh look-ahead).
    """
    out: list[dict] = []
    n = len(df)
    for i in range(warmup, n - 1):
        sub = df.iloc[max(0, i - window + 1):i + 1]
        try:
            t = technical_score(sub, atr_period)
        except Exception:
            continue
        alpha = float(t.get("score", 0.0))
        if abs(alpha) < min_alpha:
            continue
        direction = "LONG" if alpha > 0 else "SHORT"
        d = 1.0 if direction == "LONG" else -1.0
        try:
            st = structure_score(sub)
        except Exception:
            st = {"struct": 0.0, "bos": "NONE"}
        try:
            reg = market_regime(sub)
        except Exception:
            reg = {"regime": "UNKNOWN"}
        reg_name = str(reg.get("regime", "UNKNOWN"))
        ru = reg_name.upper()
        reg_b = 1.0 if "UP" in ru else (-1.0 if "DOWN" in ru else 0.0)
        sc = signal_score_100(
            regime=reg_b * d, htf=0, struct=float(st.get("struct", 0.0)) * d,
            near_sr=t.get("near_sr"),
            pattern_bias=float(t.get("pattern_bias") or 0.0) * d,
            vol_confirm=bool(t.get("vol_confirm")),
            oi=0.0, fund=0.0, news_risk=0.0,
            atr_pct=float(t.get("atr_pct") or 0.005),
            liq_zone=bool(t.get("eq_high") or t.get("eq_low")),
            btc_align=True)
        if min_score100 > 0 and sc["total"] < min_score100:
            continue
        strat = classify_strategy(
            direction, regime=reg_name, struct=float(st.get("struct", 0.0)),
            bos=str(st.get("bos", "NONE")), retest=False,
            sweep=bool(t.get("sweep")), sweep_bias=float(t.get("sweep_bias") or 0.0),
            near_sr=t.get("near_sr"),
            pattern_bias=float(t.get("pattern_bias") or 0.0),
            vol_confirm=bool(t.get("vol_confirm")), htf=0,
            rsi=float(t.get("rsi") or 50.0))
        out.append({"i": i, "direction": direction, "alpha": round(alpha, 4),
                    "atr": float(t.get("atr") or 0.0),
                    "entry": float(df["open"].iloc[i + 1]),
                    "score100": sc["total"], "strategy": strat,
                    "regime": reg_name, "rsi": float(t.get("rsi") or 50.0)})
    return out


def _group(trades: list[dict], key: str) -> dict:
    """Thong ke rieng theo nhom (pair/direction/strategy/regime) — muc 15/19."""
    out: dict = {}
    for t in trades:
        g = out.setdefault(str(t.get(key) or "?"),
                           {"n": 0, "wins": 0, "net": 0.0, "sum_r": 0.0})
        g["n"] += 1
        g["wins"] += 1 if (t.get("won") or float(t.get("pnl", 0.0)) > 0) else 0
        g["net"] = round(g["net"] + float(t.get("pnl", 0.0)), 4)
        g["sum_r"] = round(g["sum_r"] + float(t.get("r", 0.0)), 4)
    for g in out.values():
        n = max(g["n"], 1)
        g["wr"] = round(g["wins"] / n, 3)
        g["avgR"] = round(g["sum_r"] / n, 3)
    return out


def stats(trades: list[dict], equity: list[float], balance0: float = 1000.0) -> dict:
    """Chi tieu muc 19/25: WR, PF, expectancy R, Max DD, streak, breakdown.

    PnL da tru phi (trade_result) -> net_pf chinh la PF sau chi phi.
    """
    n = len(trades)
    if n == 0:
        return {"n": 0, "wins": 0, "wr": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "gross_pf": 0.0, "net_pf": 0.0, "net": 0.0, "net_pnl": 0.0,
                "exp_r": 0.0, "max_dd_pct": 0.0, "streak_loss": 0,
                "top3_share": 0.0, "fees": 0.0, "exit_mix": {}, "by_symbol": {},
                "by_direction": {}, "by_strategy": {}, "by_regime": {}}
    pnls = [float(t.get("pnl", 0.0)) for t in trades]
    rs = [float(t.get("r", 0.0)) for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gp, gl = sum(wins), abs(sum(losses))
    eq = [float(x) for x in equity] or [balance0]
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak * 100.0)
    streak = cur = 0
    for x in pnls:
        cur = cur + 1 if x < 0 else 0
        streak = max(streak, cur)
    top3 = sum(sorted(wins, reverse=True)[:3])
    pf = round(gp / gl, 3) if gl > 0 else (99.0 if gp > 0 else 0.0)
    return {
        "n": n, "wins": len(wins), "losses": len(losses),
        "wr": round(len(wins) / n, 4),
        "avg_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "avg_loss": round(gl / len(losses), 4) if losses else 0.0,
        "gross_pf": pf, "net_pf": pf,
        "net": round(sum(pnls), 2), "net_pnl": round(sum(pnls), 2),
        "exp_r": round(sum(rs) / n, 4),
        "avg_win_r": round(sum(r for r in rs if r > 0) / max(len(wins), 1), 3),
        "avg_loss_r": round(abs(sum(r for r in rs if r < 0)) / max(len(losses), 1), 3),
        "max_dd_pct": round(mdd, 2),
        "streak_loss": streak,
        "top3_share": round(top3 / gp, 3) if gp > 0 else 0.0,
        "fees": round(sum(float(t.get("fee", 0.0)) for t in trades), 2),
        "exit_mix": {k: sum(1 for t in trades if str(t.get("exit_reason")) == k)
                     for k in sorted({str(t.get("exit_reason")) for t in trades})},
        "by_symbol": _group(trades, "symbol"),
        "by_direction": _group(trades, "direction"),
        "by_side": _group(trades, "direction"),
        "by_strategy": _group(trades, "strategy"),
        "by_regime": _group(trades, "regime"),
    }


def verdict(st: dict) -> str:
    """Tieu chi 'DAT' muc 26: WR>=35%, Net PF>=1.05, E>0, DD<10%, streak<8, n>=30."""
    if int(st.get("n", 0)) < 30:
        return "REVIEW (<30 lenh)"
    ok = (float(st.get("wr", 0)) >= 0.35 and float(st.get("net_pf", 0)) >= 1.05
          and float(st.get("exp_r", 0)) > 0 and float(st.get("max_dd_pct", 99)) < 10.0
          and int(st.get("streak_loss", 99)) < 8 and float(st.get("top3_share", 1)) < 0.5)
    return "PASS" if ok else "FAIL"



def simulate(df: pd.DataFrame, sigs: list[dict], cfg: dict, *,
             balance0: float = 1000.0, risk_pct: float = 0.005,
             cooldown_bars: int = 5, max_bars: int = 400,
             max_leverage: float = 5.0) -> dict:
    """Replay 1 bien the quan ly lenh: toi da 1 vi the tai 1 thoi diem.

    cfg: sl_mult, tp_mult, partial_at_r, partial_pct, be_at_r, trail_atr_mult.
    """
    by_bar: dict[int, dict] = {}
    for s in sigs:
        by_bar.setdefault(int(s["i"]), s)
    trades: list[dict] = []
    equity = [balance0]
    balance = balance0
    t = None
    ref: dict = {}
    bars_open = 0
    last_exit = -10 ** 9
    n = len(df)
    start = max(0, (min(by_bar) if by_bar else 1) - 1)

    for i in range(start, n):
        row = df.iloc[i]
        hi, lo = float(row["high"]), float(row["low"])

        if t is not None:
            bars_open += 1
            reason, px = None, None
            if t.direction == "LONG":
                if lo <= t.sl:
                    reason, px = "SL", t.sl
                elif hi >= t.tp:
                    reason, px = "TP", t.tp
            else:
                if hi >= t.sl:
                    reason, px = "SL", t.sl
                elif lo <= t.tp:
                    reason, px = "TP", t.tp
            if reason is None and bars_open >= max_bars:
                reason, px = "TIME", float(row["close"])
            if reason is None:
                mgkw = {k: cfg[k] for k in ("partial_at_r", "partial_pct",
                                            "be_at_r", "trail_atr_mult") if k in cfg}
                mg = manage(t, float(row["close"]), float(t.atr), **mgkw)
                if mg["action"] in ("EXIT_SL", "EXIT_TP"):
                    reason = "SL" if mg["action"] == "EXIT_SL" else "TP"
                    px = t.sl if reason == "SL" else t.tp
            if reason is not None:
                res = trade_result(t, reason, float(px))
                balance += float(res["pnl"])
                rec = dict(ref)
                rec.update({"pnl": float(res["pnl"]), "r": float(res["r"]),
                            "won": bool(res["won"]),
                            "exit_reason": res["exit_reason"],
                            "partial_done": res["partial_done"],
                            "mfe_r": res["mfe_r"], "qty": t.init_qty,
                            "entry": t.entry, "bars": bars_open,
                            "fee": round(t.init_qty * t.entry * FEE_ROUNDTRIP_PCT, 6)})
                trades.append(rec)
                equity.append(balance)
                last_exit = i
                t, bars_open, ref = None, 0, {}
            continue

        sig = by_bar.get(i)
        if sig is None or (i - last_exit) < cooldown_bars or i + 1 >= n:
            continue
        atr = float(sig.get("atr") or 0.0)
        d = 1.0 if sig["direction"] == "LONG" else -1.0
        entry = float(df["open"].iloc[i + 1])
        dist = float(cfg["sl_mult"]) * atr
        if atr <= 0 or dist <= 0 or entry <= 0:
            continue
        sl = entry - d * dist
        tp = entry + d * float(cfg["tp_mult"]) * atr
        qty = min((balance * risk_pct) / dist, (balance * max_leverage) / entry)
        if qty <= 0:
            continue
        t = new_trade(str(sig.get("symbol", "?")), sig["direction"], entry, qty, sl, tp)
        t.atr = atr
        ref = {"symbol": sig.get("symbol", "?"), "direction": sig["direction"],
               "strategy": sig.get("strategy", "NONE"),
               "regime": sig.get("regime", "?"), "alpha": sig.get("alpha"),
               "score100": sig.get("score100"), "i": i}

    return {"trades": trades, "equity": equity,
            "stats": stats(trades, equity, balance0)}


def _simulate_multi(df: pd.DataFrame, sigs: list[dict], cfg: dict, *,
                    balance0: float = 1000.0, risk_pct: float = 0.005,
                    max_bars: int = 400) -> dict:
    """Nhu simulate() nhung cho phep nhieu tin hieu cung luc (moi tin hieu 1 'slot').

    Tao ra nhieu lenh hon de co mau thong ke (mo phong che do turbo demo).
    """
    syms = sorted({str(s.get("symbol")) for s in sigs})
    seen: list[dict] = []
    for sym in syms:
        sub = [s for s in sigs if str(s.get("symbol")) == sym]
        seen.extend(sub)
    return simulate(df, seen, cfg, balance0=balance0, risk_pct=risk_pct,
                    cooldown_bars=0, max_bars=max_bars)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backtest nhanh 4 cap Binance Futures")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--min-alpha", type=float, default=0.05)
    ap.add_argument("--score", type=float, default=0.0, help="nguong score100 toi thieu")
    ap.add_argument("--symbols", default=",".join(SYMBOLS))
    ap.add_argument("--risk", type=float, default=0.005, help="risk/lệnh (0.005 = 0.5%)")
    ap.add_argument("--balance", type=float, default=1000.0)
    ap.add_argument("--out", default="logs/backtest_result.json")
    args = ap.parse_args(argv)

    try:
        import ccxt  # type: ignore
        ex = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] khong import duoc ccxt: {exc}")
        return 2

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    frames: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            df = fetch_klines(sym, args.tf, args.days, exchange=ex)
            if len(df) > 300:
                frames[sym] = df
                print(f"[OK] {sym}: {len(df)} nen ({args.tf}, {args.days} ngay)")
            else:
                print(f"[SKIP] {sym}: chi {len(df)} nen")
        except Exception as exc:
            print(f"[FAIL] {sym}: {exc}")

    if not frames:
        print("[FAIL] khong co du lieu")
        return 2

    rows = []
    full: dict = {}
    sig_cache: dict[str, list[dict]] = {}
    for sym, df in frames.items():
        sigs = build_signals(df, min_alpha=args.min_alpha, min_score100=args.score)
        for s in sigs:
            s["symbol"] = sym
        sig_cache[sym] = sigs
        print(f"    {sym}: {len(sigs)} tin hieu (alpha>={args.min_alpha})")

    for name, cfg in VARIANTS.items():
        all_trades: list[dict] = []
        eq = [args.balance]
        bal = args.balance
        per_sym: dict = {}
        for sym, df in frames.items():
            res = simulate(df, sig_cache[sym], cfg, balance0=bal, risk_pct=args.risk)
            per_sym[sym] = res["stats"]
            all_trades += res["trades"]
            bal = max(0.0, bal + sum(t["pnl"] for t in res["trades"]))
            eq += res["equity"][1:]
        st = stats(all_trades, eq, args.balance)
        v = verdict(st)
        rows.append((name, st, v, per_sym))
        full[name] = {"stats": st, "verdict": v, "by_pair": per_sym}

    print("\n" + "=" * 96)
    print(f"BACKTEST {args.tf} | {args.days} ngay | min_alpha={args.min_alpha} "
          f"| score>={args.score} | risk={args.risk:.2%}")
    print("=" * 96)
    hdr = (f"{'variant':24} {'n':>5} {'WR%':>6} {'PF':>6} {'E(R)':>7} "
           f"{'net$':>9} {'DD%':>6} {'streak':>6} {'verdict':>17}")
    print(hdr)
    print("-" * 96)
    for name, st, v, _ in rows:
        print(f"{name:24} {st['n']:>5} {st['wr'] * 100:>6.1f} {st['net_pf']:>6.2f} "
              f"{st['exp_r']:>7.3f} {st['net']:>9.2f} {st['max_dd_pct']:>6.2f} "
              f"{st['streak_loss']:>6} {v:>17}")
    print("-" * 96)
    best = max(rows, key=lambda r: (r[1]["net_pf"], r[1]["exp_r"]))
    print(f"BEST: {best[0]}  WR={best[1]['wr'] * 100:.1f}%  PF={best[1]['net_pf']} "
          f"E={best[1]['exp_r']}R  verdict={best[2]}")
    bs = best[1]
    for key in ("by_symbol", "by_direction", "by_strategy", "by_regime"):
        if bs.get(key):
            print(f"  {key}: " + " | ".join(
                f"{k}: n={v['n']} WR={v['wr'] * 100:.0f}% avgR={v['avgR']}"
                for k, v in sorted(bs[key].items())))
    print(f"  exit_mix: {bs.get('exit_mix')}")

    try:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"args": vars(args), "results": full}, f,
                      ensure_ascii=False, indent=1)
        print(f"[OK] da luu {args.out}")
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] khong luu duoc {args.out}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


