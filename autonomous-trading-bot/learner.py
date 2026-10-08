"""Online adaptive learner: hoc online tu ket qua that (logistic TUYEN TINH).

KHONG phai deep learning: khong co mang no-ron, khong backprop. Chi la 1 mo hinh
logistic tren 20 feature thu cong (learner.FEATURES), cap nhat trong so theo tung
ket qua (thang -> tang w, thua -> giam w) va luu JSON (logs/learner.json).

Bo kien thuc Futures v2 (theo tai lieu user):
- NEWS -> MACRO -> BTC REGIME -> ALT REGIME -> STRUCTURE -> CANDLE -> VOLUME
  -> OI -> FUNDING -> LIQUIDATION -> RISK -> ENTRY -> SL/TP -> MONITOR -> EXIT.
- Signal score 100 diem: regime 20 + htf 15 + structure 20 + S/R 10 + candle 10
  + volume 10 + OI 5 + funding 5, tru news-risk 20 + volatility 15.
- Hoc online logistic: TP=thang tang w, SL=thua giam w. Luu JSON.
"""
from __future__ import annotations

import json
import math
import os
import time

# 10 nhom tin macro/crypto can theo doi (muc 2B/3 tai lieu)
MACRO_KEYS = ["fed", "fomc", "rate", "cpi", "ppi", "nfp", "nonfarm",
              "unemploy", "gdp", "retail", "ism", "jobless"]
CRYPTO_KEYS = ["etf", "sec", "hack", "exploit", "stablecoin", "unlock",
               "upgrade", "listing", "delist", "whale", "stimulus",
               "regulation", "lawsuit"]

FEATURES = ["tech", "sent", "rsi_bias", "trend", "macd", "vol_norm",
            "vol_conf", "candle", "sr", "bb",
            "regime", "htf", "struct", "oi", "fund", "liq",
            "vwap", "sweep", "retest", "liqdom"]


def news_features(headlines: list | None) -> dict:
    """Bien tin thanh features: macro_risk, crypto_risk, etf_flow, econ_event.
    Tra moi gia tri trong [-1,+1] (am = rui ro giam gia)."""
    heads = [str(h or "").lower() for h in (headlines or [])]
    txt = " ".join(heads)
    def cnt(keys):
        return sum(1 for k in keys if k in txt)
    macro_n = cnt(MACRO_KEYS)
    crypto_n = cnt(CRYPTO_KEYS)
    etf_bull = ("inflow" in txt or "etf approval" in txt) and "etf" in txt
    etf_bear = ("outflow" in txt) and "etf" in txt
    econ_event = any(k in txt for k in ("fomc", "cpi", "nfp", "nonfarm",
                                        "rate decision", "opec", "fed"))
    macro_risk = max(-1.0, min(0.0, -0.25 * macro_n))
    crypto_risk = max(-1.0, min(0.0, -0.25 * crypto_n))
    etf_flow = 0.5 if etf_bull else (-0.5 if etf_bear else 0.0)
    return {"macro_risk": macro_risk, "crypto_risk": crypto_risk,
            "etf_flow": etf_flow, "econ_event": bool(econ_event)}


def extract_features(tech_score: float, sent: float, rsi: float = 50.0,
                     ema50: float = 0.0, ema200: float = 1.0,
                     macd_hist: float = 0.0, atr_pct: float = 0.005,
                     vol_ratio: float = 1.0, vol_confirm: bool = False,
                     pattern_bias: float = 0.0, near_sr=None,
                     bb_pctb: float | None = None,
                     regime: float = 0.0, htf: int = 0,
                     struct: float = 0.0,
                     oi_chg: float = 0.0, fund: float = 0.0,
                     liq: float = 0.0,
                     above_vwap: bool = False, sweep_bias: float = 0.0,
                     retest: bool = False, liq_dominance: float = 0.0) -> dict:
    bb_sig = 0.0
    try:
        if bb_pctb is not None:
            bb_sig = 1.0 if bb_pctb > 1.0 else (-1.0 if bb_pctb < 0.0 else 0.0)
    except Exception:
        bb_sig = 0.0
    return {
        "tech": max(-1.0, min(1.0, tech_score)),
        "sent": max(-1.0, min(1.0, sent)),
        "rsi_bias": max(-1.0, min(1.0, (rsi - 50.0) / 50.0)),
        "trend": 1.0 if ema50 > ema200 else -1.0,
        "macd": 1.0 if macd_hist > 0 else -1.0,
        "vol_norm": max(-1.0, min(1.0, (atr_pct - 0.005) / 0.005)),
        "vol_conf": 1.0 if vol_confirm else (0.3 if (vol_ratio or 0) >= 1.2 else -0.3),
        "candle": max(-1.0, min(1.0, pattern_bias or 0.0)),
        "sr": 1.0 if near_sr == "S" else (-1.0 if near_sr == "R" else 0.0),
        "bb": bb_sig,
        "regime": max(-1.0, min(1.0, regime)),
        "htf": 1.0 if htf > 0 else (-1.0 if htf < 0 else 0.0),
        "struct": max(-1.0, min(1.0, struct)),
        "oi": max(-1.0, min(1.0, oi_chg)),
        "fund": max(-1.0, min(1.0, -fund * 50.0)),
        "liq": max(-1.0, min(1.0, liq)),
        "vwap": 1.0 if above_vwap else -1.0,
        "sweep": max(-1.0, min(1.0, sweep_bias or 0.0)),
        "retest": 1.0 if retest else -0.2,
        "liqdom": max(-1.0, min(1.0, liq_dominance)),
    }


def structure_score(df) -> dict:
    """Cau truc HH/HL/LH/LL + BOS (muc 5 tai lieu). Tra {struct in [-1,+1], bos: str}."""
    try:
        h = df["high"].tail(30).values
        l = df["low"].tail(30).values
        c = df["close"].tail(30).values
        piv_h = [h[i] for i in range(2, len(h) - 2) if h[i] == max(h[i-2:i+3])]
        piv_l = [l[i] for i in range(2, len(l) - 2) if l[i] == min(l[i-2:i+3])]
        s = 0.0
        if len(piv_h) >= 2:
            s += 0.5 if piv_h[-1] > piv_h[-2] else -0.5  # HH vs LH
        if len(piv_l) >= 2:
            s += 0.5 if piv_l[-1] > piv_l[-2] else -0.5  # HL vs LL
        bos = "NONE"
        if piv_h and c[-1] > piv_h[-1]:
            bos = "BOS_UP"
        elif piv_l and c[-1] < piv_l[-1]:
            bos = "BOS_DOWN"
        return {"struct": max(-1.0, min(1.0, s)), "bos": bos}
    except Exception:
        return {"struct": 0.0, "bos": "NONE"}


def signal_score_100(regime: float = 0.0, htf: int = 0, struct: float = 0.0,
                     near_sr=None, pattern_bias: float = 0.0,
                     vol_confirm: bool = False, oi: float = 0.0,
                     fund: float = 0.0, news_risk: float = 0.0,
                     atr_pct: float = 0.005,
                     liq_zone: bool = False, btc_align: bool = True) -> dict:
    """Signal score 100 diem — khung moi (muc 14 tai lieu moi):
    regime 20 + htf 15 + struct 15 + S/R 10 + liquidity 10 + candle 5 +
    volume 10 + OI 5 + funding 5 + BTC align 5.
    >=80 A+ | 70-79 A | 60-69 B | <60 NO-TRADE.
    KHONG phai xac suat thang, phai kiem dinh."""
    parts = {
        "regime": 20.0 * max(-1.0, min(1.0, regime)),
        "htf": 15.0 * (1.0 if htf > 0 else (-1.0 if htf < 0 else 0.0)),
        "struct": 15.0 * max(-1.0, min(1.0, struct)),
        "sr": 10.0 if near_sr in ("S", "R") else 0.0,
        "liquidity": 10.0 if liq_zone else 0.0,
        "candle": 5.0 * max(-1.0, min(1.0, pattern_bias or 0.0)),
        "volume": 10.0 if vol_confirm else 0.0,
        "oi": 5.0 * max(-1.0, min(1.0, oi)),
        "fund": 5.0 * max(-1.0, min(1.0, -fund * 50.0)),
        "btc_align": 5.0 if btc_align else -5.0,
        "news_risk": -20.0 * max(0.0, min(1.0, abs(news_risk))),
        "volatility": -15.0 if atr_pct > 0.02 else 0.0,
    }
    total = sum(parts.values())
    grade = "A+" if total >= 80 else ("A" if total >= 70 else ("B" if total >= 60 else "NO"))
    return {"total": round(total, 2), "grade": grade,
            "parts": {k: round(v, 2) for k, v in parts.items()}}


def expectancy(wr: float, avg_win: float, avg_loss: float) -> float:
    """Expectancy R: E = WR*avgW - (1-WR)*avgL. Phai > 0 sau chi phi (muc 1, 26)."""
    return wr * avg_win - (1.0 - wr) * avg_loss


def pf_from_trades(wr: float, avg_win: float, avg_loss: float) -> float:
    """PF = GP/GL = WR*avgW / ((1-WR)*avgL)."""
    gl = (1.0 - wr) * avg_loss
    return (wr * avg_win / gl) if gl > 0 else 0.0


def dynamic_risk_pct(drawdown_pct: float, base: float = 0.5) -> float:
    """Dynamic risk theo DD (muc 16): normal 0.5 -> DD5% 0.35 -> DD8% 0.2 -> DD10% STOP(0)."""
    if drawdown_pct >= 10.0:
        return 0.0
    if drawdown_pct >= 8.0:
        return min(base, 0.20)
    if drawdown_pct >= 5.0:
        return min(base, 0.35)
    return base


class OnlineLearner:
    """Logistic online: p = sigmoid(w.f + b). Update sau moi close."""

    def __init__(self, path: str = "logs/learner.json", lr: float = 0.1):
        self.path = path
        self.lr = lr
        _defaults = {"tech": 0.5, "sent": 0.5, "rsi_bias": 0.1, "trend": 0.1,
                     "macd": 0.1, "vol_norm": 0.1, "vol_conf": 0.1,
                     "candle": 0.1, "sr": 0.1, "bb": 0.1,
                     "regime": 0.3, "htf": 0.2, "struct": 0.3,
                     "oi": 0.1, "fund": 0.1, "liq": 0.1,
                     "vwap": 0.1, "sweep": 0.2, "retest": 0.2, "liqdom": 0.1}
        self.w: dict[str, float] = {f: _defaults.get(f, 0.1) for f in FEATURES}
        self.b = 0.0
        self.n_updates = 0
        self.load()

    def predict(self, feats: dict) -> float:
        z = self.b + sum(self.w.get(f, 0.0) * feats.get(f, 0.0) for f in FEATURES)
        return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))

    def edge(self, feats: dict, direction: str) -> float:
        """Loi the ky vong (-1..+1) theo huong lenh: duong = ung ho vao lenh.

        P0-7: phai dung CUNG quy uoc voi `update()` — SHORT thi dao dau FEATURES
        (chu khong phai dao dau ket qua). Ban cu dao ket qua: `1 - 2p`, chi tuong
        duong khi bias b = 0. Khi b != 0 thi bias tro thanh thien lech LONG/SHORT
        co dinh (thuc te: b = -0.137 va 30 lenh SHORT / 3 lenh LONG).
        """
        f = dict(feats) if direction == "LONG" else {k: -v for k, v in feats.items()}
        return (self.predict(f) - 0.5) * 2.0

    def update(self, feats: dict, direction: str, won: bool) -> dict:
        """Hoc sau khi close: won=True neu TP, False neu SL.

        P0-7 (bug nghiem trong da sua): features da duoc DOI DAU ve huong lenh cua
        chinh no (dong duoi), nen nhan chi la "lenh nay co thang khong" — KHONG phu
        thuoc LONG/SHORT. Ban cu ghi `y = (direction == "LONG") == won`:
            SHORT THANG  -> y = 0  (day la THUA)
            SHORT THUA   -> y = 1  (day la THANG)
        => learner hoc NGUOC hoan toan voi moi lenh SHORT. Vi demo co 30/33 lenh la
        SHORT, toan bo 103 lan hoc bi dao => `edge` am cho setup dang thang =>
        BLOCKED_LEARN=520. Neu chi nới nguong de co them lenh thi se trade theo
        NGHICH DAO cua cai da thang -> mau so lieu cho gate "50 lenh" vo nghia.
        """
        y = 1.0 if won else 0.0
        # Voi SHORT: dao dau features de ca 2 huong dung cung mot khung "huong lenh".
        f = dict(feats) if direction == "LONG" else {k: -v for k, v in feats.items()}
        p = self.predict(f)
        err = y - p
        for k in FEATURES:
            self.w[k] += self.lr * err * f.get(k, 0.0)
        self.b += self.lr * err
        self.n_updates += 1
        self.save()
        return {"p": round(p, 4), "err": round(err, 4), "n": self.n_updates,
                "w": {k: round(v, 4) for k, v in self.w.items()}}

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w") as f:
                json.dump({"w": self.w, "b": self.b, "n": self.n_updates,
                           "ts": time.time()}, f)
        except Exception:
            pass

    def load(self) -> None:
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.w.update(d.get("w", {}))
            self.b = float(d.get("b", 0.0))
            self.n_updates = int(d.get("n", 0))
        except Exception:
            pass
