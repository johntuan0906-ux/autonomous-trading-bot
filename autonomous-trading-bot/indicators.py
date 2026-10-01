"""Pure pandas/numpy technical indicators + technical momentum score in [-1, +1]."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.fillna(50.0)
    # flat market (no loss and no gain) -> 50
    flat = (avg_gain == 0) & (avg_loss == 0)
    out[flat] = 50.0
    return out


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """df must have columns high/low/close."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(close: pd.Series, period: int = 20, mult: float = 2.0) -> tuple:
    """Tra (upper, mid, lower, bandwidth, pct_b). pct_b: vi tri gia trong band 0..1."""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    bw = (upper - lower) / mid.replace(0.0, np.nan)
    pct_b = (close - lower) / (upper - lower).replace(0.0, np.nan)
    return upper, mid, lower, bw, pct_b


def support_resistance(df: pd.DataFrame, lookback: int = 50, tol_pct: float = 0.003) -> dict:
    """S/R: dinh/day cuc bo bi tu choi nhieu lan. Tra {support, resistance, near, dist_pct}."""
    try:
        hi = df["high"].tail(lookback)
        lo = df["low"].tail(lookback)
        close = float(df["close"].iloc[-1])
        h = hi.values
        l = lo.values
        piv_h = [h[i] for i in range(2, len(h) - 2) if h[i] == max(h[i-2:i+3])]
        piv_l = [l[i] for i in range(2, len(l) - 2) if l[i] == min(l[i-2:i+3])]
        res = max(piv_h) if piv_h else float(hi.max())
        sup = min(piv_l) if piv_l else float(lo.min())
        d_res = abs(close - res) / max(res, 1e-9)
        d_sup = abs(close - sup) / max(sup, 1e-9)
        near = "R" if d_res <= tol_pct and d_res <= d_sup else ("S" if d_sup <= tol_pct else None)
        return {"support": round(float(sup), 6), "resistance": round(float(res), 6),
                "near": near, "dist_pct": round(float(min(d_res, d_sup)), 6)}
    except Exception:
        return {"support": 0.0, "resistance": 0.0, "near": None, "dist_pct": 1.0}


def _body(o: float, c: float) -> float:
    return abs(c - o)


def candle_signal(df: pd.DataFrame) -> dict:
    """Nhan dien mau nen Nhat cuoi. Tra {pattern, bias in [-1,+1]}.
    Tin cay tang khi o vung S/R + volume — bot ket hop o technical_score."""
    try:
        o = df["open"].tail(3).values
        h = df["high"].tail(3).values
        l = df["low"].tail(3).values
        c = df["close"].tail(3).values
        o0, h0, l0, c0 = o[-1], h[-1], l[-1], c[-1]
        rng = max(h0 - l0, 1e-9)
        body = _body(o0, c0)
        upper_w = h0 - max(o0, c0)
        lower_w = min(o0, c0) - l0
        bull = c0 > o0
        if body / rng < 0.1:
            return {"pattern": "DOJI", "bias": 0.0}
        if lower_w / rng > 0.6 and body / rng < 0.35:
            return {"pattern": "HAMMER", "bias": 0.6}
        if upper_w / rng > 0.6 and body / rng < 0.35:
            return {"pattern": "SHOOTING_STAR", "bias": -0.6}
        if body / rng > 0.85:
            return {"pattern": "MARUBOZU_BULL" if bull else "MARUBOZU_BEAR",
                    "bias": 0.5 if bull else -0.5}
        if len(c) >= 2:
            o1, c1 = o[-2], c[-2]
            if c1 < o1 and bull and c0 >= o1 and o0 <= c1:
                return {"pattern": "BULL_ENGULFING", "bias": 0.7}
            if c1 > o1 and not bull and c0 <= o1 and o0 >= c1:
                return {"pattern": "BEAR_ENGULFING", "bias": -0.7}
        if len(c) >= 3:
            oo = df["open"].tail(3).values
            cc = df["close"].tail(3).values
            if all(cc[i] > oo[i] for i in range(3)):
                return {"pattern": "THREE_WHITE", "bias": 0.7}
            if all(cc[i] < oo[i] for i in range(3)):
                return {"pattern": "THREE_BLACK", "bias": -0.7}
            b1 = _body(o[-2], c[-2]) / max(h[-2] - l[-2], 1e-9)
            if c[-3] < o[-3] and b1 < 0.3 and bull and body / rng > 0.5:
                return {"pattern": "MORNING_STAR", "bias": 0.7}
            if c[-3] > o[-3] and b1 < 0.3 and not bull and body / rng > 0.5:
                return {"pattern": "EVENING_STAR", "bias": -0.7}
        return {"pattern": "NONE", "bias": 0.0}
    except Exception:
        return {"pattern": "NONE", "bias": 0.0}


def mtf_trend(exchange, symbol: str, tf_big: str = "1h", limit: int = 60) -> dict:
    """Xu huong khung lon (boi canh) truoc khung nho: EMA50 vs EMA200.
    Tra {bias: +1/-1/0, ema50, ema200, close}. Loi -> bias 0."""
    try:
        df = exchange.fetch_ohlcv(symbol, tf_big, limit)
        if len(df) < 10:
            return {"bias": 0, "ema50": 0.0, "ema200": 0.0, "close": 0.0}
        close = df["close"].astype(float)
        e50 = float(ema(close, 50).iloc[-1])
        e200 = float(ema(close, min(200, len(df))).iloc[-1])
        px = float(close.iloc[-1])
        return {"bias": 1 if e50 > e200 else -1, "ema50": e50, "ema200": e200, "close": px}
    except Exception:
        return {"bias": 0, "ema50": 0.0, "ema200": 0.0, "close": 0.0}


def vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP intraday (muc 9.4): gia TB theo volume. Tra Series; tren VWAP = phe mua manh."""
    try:
        tp = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"].astype(float).replace(0.0, float("nan"))
        return (tp * vol).cumsum() / vol.cumsum()
    except Exception:
        return df["close"].rolling(20).mean()


def liquidity_zones(df: pd.DataFrame, lookback: int = 50, tol_pct: float = 0.0015) -> dict:
    """Equal High/Low — vung tap trung stop orders (muc 6.3). Tra {eq_high, eq_low}."""
    try:
        h = df["high"].tail(lookback).values
        l = df["low"].tail(lookback).values
        piv_h = sorted([h[i] for i in range(2, len(h) - 2) if h[i] == max(h[i-2:i+3])], reverse=True)
        piv_l = sorted([l[i] for i in range(2, len(l) - 2) if l[i] == min(l[i-2:i+3])])
        eq_h = None
        for i in range(len(piv_h) - 1):
            if abs(piv_h[i] - piv_h[i+1]) / max(piv_h[i], 1e-9) <= tol_pct:
                eq_h = float((piv_h[i] + piv_h[i+1]) / 2.0)
                break
        eq_l = None
        for i in range(len(piv_l) - 1):
            if abs(piv_l[i] - piv_l[i+1]) / max(piv_l[i], 1e-9) <= tol_pct:
                eq_l = float((piv_l[i] + piv_l[i+1]) / 2.0)
                break
        return {"eq_high": eq_h, "eq_low": eq_l}
    except Exception:
        return {"eq_high": None, "eq_low": None}


def liquidity_sweep(df: pd.DataFrame) -> dict:
    """Sweep (muc 6.4): nen xuyen high/low 20 nen roi dong quay nguoc trong 1-2 nen.
    Tra {swept: 'HIGH'/'LOW'/None, bias: +1 thu gom buy-side de giam, -1 nguoc lai}."""
    try:
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values
        if len(c) < 22:
            return {"swept": None, "bias": 0.0}
        prev_h = float(max(h[-21:-1]))
        prev_l = float(min(l[-21:-1]))
        swept_h = bool(h[-2] > prev_h and c[-1] < prev_h)  # quet buy-side roi quay dau
        swept_l = bool(l[-2] < prev_l and c[-1] > prev_l)
        if swept_h and not swept_l:
            return {"swept": "HIGH", "bias": -0.6}
        if swept_l and not swept_h:
            return {"swept": "LOW", "bias": 0.6}
        return {"swept": None, "bias": 0.0}
    except Exception:
        return {"swept": None, "bias": 0.0}


def retest_ok(df: pd.DataFrame, direction: str) -> dict:
    """Retest (muc 5.5/7): sau BOS, gia quay lai vung pha vo + giu duoc (wick cham, than dong ve huong cu).
    Tra {ok: bool}."""
    try:
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values
        if len(c) < 25:
            return {"ok": False}
        if direction == "LONG":
            lvl = float(max(h[-25:-5]))
            touched = bool(min(l[-5:]) <= lvl * 1.002)
            held = bool(c[-1] > lvl * 0.998)
            return {"ok": touched and held}
        lvl = float(min(l[-25:-5]))
        touched = bool(max(h[-5:]) >= lvl * 0.998)
        held = bool(c[-1] < lvl * 1.002)
        return {"ok": touched and held}
    except Exception:
        return {"ok": False}


def market_regime(df: pd.DataFrame) -> dict:
    """Regime 7 trang thai (muc 4): uptrend/downtrend/sideway/breakout/breakdown/compression/high-vol."""
    try:
        c = df["close"].astype(float)
        px = float(c.iloc[-1])
        e50 = float(ema(c, 50).iloc[-1])
        e200 = float(ema(c, min(200, len(c))).iloc[-1])
        hi20 = float(c.tail(20).max())
        lo20 = float(c.tail(20).min())
        rng20 = (hi20 - lo20) / max(px, 1e-9)
        bw_now = None
        try:
            _, _, _, bw, _ = bollinger(c)
            bw_now = float(bw.iloc[-1])
        except Exception:
            pass
        a = float(atr(df).iloc[-1]) / max(px, 1e-9)
        if a > 0.02:
            reg = "HIGH_VOL"
        elif bw_now is not None and bw_now < 0.02 and rng20 < 0.02:
            reg = "COMPRESSION"
        elif px >= hi20 and e50 > e200:
            reg = "BREAKOUT"
        elif px <= lo20 and e50 < e200:
            reg = "BREAKDOWN"
        elif e50 > e200 and rng20 < 0.06:
            reg = "UPTREND"
        elif e50 < e200 and rng20 < 0.06:
            reg = "DOWNTREND"
        else:
            reg = "SIDEWAY"
        bias = 1.0 if reg in ("UPTREND", "BREAKOUT") else (-1.0 if reg in ("DOWNTREND", "BREAKDOWN") else 0.0)
        return {"regime": reg, "bias": bias, "atr_pct": round(a, 6)}
    except Exception:
        return {"regime": "SIDEWAY", "bias": 0.0, "atr_pct": 0.0}


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def technical_score(df: pd.DataFrame, atr_period: int = 14) -> dict:
    """Return dict(score, rsi, ema_fast, ema_slow, macd_hist, atr, atr_pct, close).

    score in [-1, +1]: >0 bullish (Long bias), <0 bearish (Short bias).
    Components:
      trend (EMA50 vs EMA200):            +/- 0.40
      momentum (RSI distance from 50):    +/- up to 0.30
      macd histogram sign:                +/- 0.20
      20-bar breakout:                    +/- 0.10
    """
    if len(df) < 60:
        raise ValueError("Need >= 60 candles for technical_score")
    close = df["close"].astype(float)
    ema50 = ema(close, 50).iloc[-1]
    ema200 = ema(close, 200).iloc[-1] if len(df) >= 200 else ema(close, len(df)).iloc[-1]
    rsi_v = float(rsi(close).iloc[-1])
    _, _, hist = macd(close)
    hist_v = float(hist.iloc[-1])
    atr_v = float(atr(df, atr_period).iloc[-1])
    price = float(close.iloc[-1])
    atr_pct = atr_v / price if price else 0.0

    trend = 0.40 if ema50 > ema200 else -0.40
    momentum = _clamp((rsi_v - 50.0) / 50.0, -1.0, 1.0) * 0.30
    macd_c = 0.20 if hist_v > 0 else -0.20
    hi20 = float(close.tail(20).max())
    lo20 = float(close.tail(20).min())
    if price >= hi20:
        brk = 0.10
    elif price <= lo20:
        brk = -0.10
    else:
        brk = 0.0

    score = _clamp(trend + momentum + macd_c + brk)
    # --- v2 boost: Bollinger + volume-breakout + nen Nhat tai S/R ---
    rsi_overbought = rsi_v > 70
    rsi_oversold = rsi_v < 30
    vol_ratio = 1.0
    vol_confirm = False
    try:
        vol = df["volume"].astype(float) if "volume" in df.columns else None
        if vol is not None and len(vol) >= 20:
            vol_ratio = float(vol.iloc[-1] / max(vol.tail(20).mean(), 1e-9))
            vol_confirm = bool(vol_ratio >= 1.5 and abs(brk) > 0)
    except Exception:
        pass
    bb_bw = bb_pctb = None
    bb_break = 0.0
    try:
        _, _, _, bw, pctb = bollinger(close)
        bb_bw = float(bw.iloc[-1]) if bw is not None else None
        bb_pctb = float(pctb.iloc[-1]) if pctb is not None else None
        if bb_pctb is not None:
            if bb_pctb > 1.0:
                bb_break = 0.10 if vol_confirm else -0.05  # pha band khong volume = bay
            elif bb_pctb < 0.0:
                bb_break = -0.10 if vol_confirm else 0.05
    except Exception:
        pass
    sr = support_resistance(df)
    cs = candle_signal(df)
    # mau nen chi co nghia tai S/R + volume (theo checklist cua user)
    candle_c = 0.0
    if cs["bias"] != 0.0 and sr.get("near") is not None:
        candle_c = float(cs["bias"]) * (0.15 if vol_confirm or vol_ratio >= 1.2 else 0.07)
    # qua mua tai khang cu / qua ban tai ho tro = dao chieu manh hon
    sr_c = 0.0
    if rsi_overbought and sr.get("near") == "R":
        sr_c = -0.10
    elif rsi_oversold and sr.get("near") == "S":
        sr_c = 0.10
    score = _clamp(score + bb_break + candle_c + sr_c)
    # --- v2.2: VWAP + sweep + retest (muc 6/7/9.4) ---
    vwap_bias = 0.0
    try:
        vw = float(vwap(df).iloc[-1])
        vwap_bias = 0.05 if price > vw else (-0.05 if price < vw else 0.0)
        score = _clamp(score + vwap_bias)
    except Exception:
        vw = None
    sw = liquidity_sweep(df)
    sweep_c = 0.0
    # sweep nguoc huong ky thuat = dung lai (fake BOS); thuan huong = cong them
    if sw.get("swept"):
        sb = float(sw.get("bias", 0.0))
        sweep_c = 0.08 if (sb > 0) == (score > 0) else -0.08
        score = _clamp(score + sweep_c)
    lz = liquidity_zones(df)
    return {
        "score": round(score, 4),
        "rsi": round(rsi_v, 2),
        "ema50": round(float(ema50), 6),
        "ema200": round(float(ema200), 6),
        "macd_hist": round(hist_v, 6),
        "atr": round(atr_v, 6),
        "atr_pct": round(atr_pct, 6),
        "close": price,
        "rsi_overbought": bool(rsi_overbought),
        "rsi_oversold": bool(rsi_oversold),
        "vol_ratio": round(float(vol_ratio), 3),
        "vol_confirm": bool(vol_confirm),
        "bb_bandwidth": None if bb_bw is None or bb_bw != bb_bw else round(float(bb_bw), 6),
        "bb_pctb": None if bb_pctb is None or bb_pctb != bb_pctb else round(float(bb_pctb), 4),
        "support": sr.get("support"), "resistance": sr.get("resistance"),
        "near_sr": sr.get("near"),
        "pattern": cs.get("pattern"),
        "pattern_bias": cs.get("bias"),
        "vwap": None if vw is None or vw != vw else round(float(vw), 6),
        "above_vwap": bool(vw is not None and vw == vw and price > vw),
        "sweep": sw.get("swept"), "sweep_bias": sw.get("bias"),
        "eq_high": lz.get("eq_high"), "eq_low": lz.get("eq_low"),
    }
