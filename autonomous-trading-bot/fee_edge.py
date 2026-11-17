"""fee_edge.py — PHI vs EDGE: voi so du HIEN CO thi co nen vao lenh khong?

Cau hoi cua nguoi van hanh (15/11): *"giam nhu cau >150 USDT, tu dieu phoi phi/don bay theo so du"*.
Toan hoc cho thay **ti le phi/ky vong KHONG phu thuoc vao von**:

    notional = risk_usdt / stop_pct          (SL cang xa thi notional cang nho)
    phi_2_chieu = 2 * fee_rate * notional
    ky_vong    = exp_r * risk_usdt
    ti_le      = phi / ky_vong = 2 * fee_rate / (exp_r * stop_pct)      <-- KHONG co `equity`

⇒ Voi 38 USDT hay 3.800 USDT, ti le nay y het nhau. Cai *co* phu thuoc von la:
  (a) notional co duoi **minNotional 5 USDT** khong (duoi thi san tu choi);
  (b) margin kha dung (don bay chi doi margin, khong doi phi).
⇒ Vi vay: KHONG can >150 USDT. Cai can la **SL du rong** (hoac `exp_r` cao) de phi <= 35% ky vong.
Ham `plan()` tra "can SL rong bao nhieu %" de bot/nguoi van hanh chinh `SL_ATR_MULT` thay vi doan.
"""
from __future__ import annotations

import os

DEFAULT_FEE = 0.0005        # 0,05% taker USD-M (vao + ra = 2 lan)
DEFAULT_MAX_RATIO = 0.35    # phi 2 chieu <= 35% ky vong moi lenh
DEFAULT_MIN_NOTIONAL = 5.0


def fee_rate(cfg=None) -> float:
    """Phi 1 chieu (ti le). Uu tien `cfg.fee_taker_pct` (%) roi den env `FEE_TAKER_PCT`, mac dinh 0,05%."""
    v = getattr(cfg, "fee_taker_pct", None)
    if v is None:
        try:
            v = float(os.getenv("FEE_TAKER_PCT", DEFAULT_FEE * 100.0))
        except (TypeError, ValueError):
            v = DEFAULT_FEE * 100.0
    try:
        return max(0.0, float(v)) / 100.0
    except (TypeError, ValueError):
        return DEFAULT_FEE


def max_ratio(cfg=None) -> float:
    v = getattr(cfg, "max_fee_ratio", None)
    if v is None:
        try:
            v = float(os.getenv("MAX_FEE_RATIO", DEFAULT_MAX_RATIO))
        except (TypeError, ValueError):
            v = DEFAULT_MAX_RATIO
    try:
        return max(0.01, float(v))
    except (TypeError, ValueError):
        return DEFAULT_MAX_RATIO


def roundtrip_fee(notional: float, rate: float = DEFAULT_FEE) -> float:
    """Phi ca vong (vao + ra) tren notional."""
    return 2.0 * max(0.0, float(notional)) * float(rate)


def expected_edge(risk_usdt: float, exp_r: float) -> float:
    """Ky vong lai moi lenh (USDT) = risk * exp_r."""
    return max(0.0, float(risk_usdt)) * max(0.0, float(exp_r))


def fee_ratio(notional: float, risk_usdt: float, exp_r: float,
              rate: float = DEFAULT_FEE) -> float:
    """phi / ky vong (0..∞). `inf` neu ky vong = 0."""
    edge = expected_edge(risk_usdt, exp_r)
    if edge <= 0:
        return float("inf")
    return roundtrip_fee(notional, rate) / edge


def need_stop_pct(exp_r: float, rate: float = DEFAULT_FEE,
                  max_ratio_: float = DEFAULT_MAX_RATIO) -> float:
    """SL phai RONG it nhat bao nhieu % de phi <= `max_ratio_` x ky vong (0 = khong dat duoc)."""
    e = max(0.0, float(exp_r))
    if e <= 0:
        return 0.0
    return 2.0 * float(rate) / (e * float(max_ratio_))


def plan(*, equity: float, risk_usdt: float, stop_pct: float, exp_r: float,
         notional: float = None, min_notional: float = DEFAULT_MIN_NOTIONAL,
         cfg=None) -> dict:
    """Quyet dinh cho 1 lenh. Tra dict(ok, why, fee, edge, fee_ratio, need_stop_pct, notional...).

    - `risk_usdt`: rui ro that cua lenh (USDT) — da tinh tu qty & khoang SL.
    - `stop_pct` : khoang SL / gia (0,03 = 3%).
    - `notional` : gia tri lenh; bo trong thi suy ra = risk_usdt / stop_pct.
    - `exp_r`    : ky vong R moi lenh (lay tu `perf_report` bot-only; mac dinh `EXP_R_ASSUMED`).
    """
    rate = fee_rate(cfg)
    mr = max_ratio(cfg)
    stop = max(1e-9, float(stop_pct or 0.0))
    risk = max(0.0, float(risk_usdt or 0.0))
    not_ = float(notional) if notional is not None else (risk / stop if risk > 0 else 0.0)
    fee = roundtrip_fee(not_, rate)
    edge = expected_edge(risk, exp_r)
    ratio = fee_ratio(not_, risk, exp_r, rate)
    need = need_stop_pct(exp_r, rate, mr)
    out = {"ok": False, "why": "", "notional": round(not_, 4), "fee": round(fee, 6),
           "edge": round(edge, 6), "fee_ratio": ratio, "need_stop_pct": round(need, 5),
           "stop_pct": round(stop, 5), "exp_r": float(exp_r or 0.0),
           "equity": float(equity or 0.0), "min_notional": float(min_notional)}
    if edge <= 0:
        out["why"] = "ky vong = 0 (exp_r <= 0) — khong co ly do tra phi"
        return out
    if not_ < float(min_notional):
        out["why"] = ("notional %.2f < %.2f USDT (san se tu choi -4164) — can tang risk hoac giam SL"
                      % (not_, float(min_notional)))
        return out
    if ratio > mr:
        out["why"] = ("phi %.4f USDT = %.0f%% ky vong (<%s) — can SL rong >= %.1f%% (dang %.1f%%)"
                      " hoac exp_r cao hon"
                      % (fee, 100.0 * ratio, ("%.0f%%" % (100 * mr)), 100.0 * need, 100.0 * stop))
        return out
    out["ok"] = True
    out["why"] = ("phi %.4f = %.0f%% ky vong — dat (SL %.1f%%, notional %.2f)"
                  % (fee, 100.0 * ratio, 100.0 * stop, not_))
    return out

