"""Phan loai strategy (muc 15 tai lieu) + thong ke rieng tung strategy.

Tai lieu: "Mot he thong tong hop PF tot co the che giau mot strategy dang keo
hieu suat xuong" -> phai do rieng tung nhom setup.

A TREND_PULLBACK       : trend ro + hoi ve EMA/RSI trung tinh -> tiep dien trend.
B BREAKOUT_RETEST      : pha vung (20 nen / band) + quay lai test thanh cong.
C LIQ_SWEEP_RECLAIM    : quet thanh khoan (sweep) roi reclaimed theo huong nguoc.
D RANGE_REVERSAL       : thi truong sideway + phan ung tai S/R (dao chieu trong range).
"""
from __future__ import annotations

import json
import os
import time

STRATEGIES = ("A_TREND_PULLBACK", "B_BREAKOUT_RETEST",
              "C_LIQ_SWEEP_RECLAIM", "D_RANGE_REVERSAL", "NONE")


def classify_strategy(direction: str, *, regime: str = "", struct: float = 0.0,
                      bos: str = "NONE", retest: bool = False,
                      sweep: bool = False, sweep_bias: float = 0.0,
                      near_sr: str | None = None, pattern_bias: float = 0.0,
                      vol_confirm: bool = False, htf: int = 0,
                      rsi: float = 50.0) -> str:
    """Tra ma strategy (A/B/C/D/NONE) cho setup hien tai."""
    d = 1.0 if str(direction).upper() == "LONG" else -1.0
    reg = str(regime or "").upper()

    # D: range reversal — sideway/range + phan ung tai S/R + nen xac nhan
    if "RANGE" in reg or "SIDEWAY" in reg or "COMPRESS" in reg:
        at_sr = (near_sr == "S" and d > 0) or (near_sr == "R" and d < 0)
        if at_sr and (pattern_bias * d > 0 or (d > 0 and rsi < 45) or (d < 0 and rsi > 55)):
            return "D_RANGE_REVERSAL"

    # C: liquidity sweep + reclaim — sweep nguoc huong roi quay lai theo lenh
    if sweep and (sweep_bias * d > 0) and (struct * d >= 0 or retest):
        return "C_LIQ_SWEEP_RECLAIM"

    # B: breakout + retest
    bos_ok = ("UP" in str(bos).upper() and d > 0) or ("DOWN" in str(bos).upper() and d < 0)
    if bos_ok and (retest or vol_confirm):
        return "B_BREAKOUT_RETEST"

    # A: trend pullback — trend ro + htf thuan + pullback nhe (RSI chua cuc tri)
    trend_ok = (struct * d > 0) or ("TREND_UP" in reg and d > 0) or ("TREND_DOWN" in reg and d < 0)
    htf_ok = (htf == 0) or ((htf > 0) == (d > 0))
    pullback = (40.0 <= rsi <= 68.0) if d > 0 else (32.0 <= rsi <= 60.0)
    if trend_ok and htf_ok and pullback:
        return "A_TREND_PULLBACK"

    return "NONE"


def bump(code: str, won: bool, r: float = 0.0,
         path: str = "logs/strategy_stats.json") -> dict:
    """Ghi nhan 1 ket qua vao thong ke strategy (n/wins/sum_r)."""
    data: dict = {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    cur = data.get(code) or {"n": 0, "wins": 0, "sum_r": 0.0}
    cur["n"] = int(cur.get("n", 0)) + 1
    cur["wins"] = int(cur.get("wins", 0)) + (1 if won else 0)
    cur["sum_r"] = round(float(cur.get("sum_r", 0.0)) + float(r), 4)
    cur["ts"] = time.time()
    data[code] = cur
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return cur


def report(path: str = "logs/strategy_stats.json") -> dict:
    """Bang thong ke: WR, avg R, tong R tung strategy."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    out = {}
    for k, v in (data or {}).items():
        n = max(int(v.get("n", 0)), 1)
        out[k] = {"n": v.get("n", 0),
                  "wr": round(int(v.get("wins", 0)) / n, 3),
                  "avgR": round(float(v.get("sum_r", 0.0)) / n, 3),
                  "sumR": round(float(v.get("sum_r", 0.0)), 2)}
    return out


def gate_check(code: str, *, min_n: int = 10, avg_r: float = 0.10,
               stats: dict | None = None,
               path: str = "logs/strategy_stats.json",
               blocklist: tuple = ()) -> dict:
    """Strategy gate: co nen CHAN setup thuoc `code` khong (khong ha nguong entry)?

    1) BLOCKLIST (env STRATEGY_BLOCK): chan TRUOC khi do mau — dung khi da co bang
       chung tu ngoai (vi du backtest 30 ngay: A_TREND_PULLBACK n=394 avgR -0.056
       am ben ca 2 cua so) ma mau journal du ban (moi n=3).
    2) AUTO: chan khi BOTH du mau (n >= min_n) VA avgR am ro (avgR <= -avg_r).
    NONE luon cho qua (khong du thong tin de ket luan). Loi doc file -> chi tra
    ket qua blocklist (fail-open cho luong vao lenh; he thong van duoc bao ve boi
    PF ngay + kill-switch). Tra {"blocked": bool, "reason": str, "n", "avg_r"}.
    """
    name = str(code or "NONE")
    if name == "NONE":
        return {"blocked": False, "reason": "", "n": 0, "avg_r": 0.0}
    if name in tuple(blocklist or ()):
        return {"blocked": True,
                "reason": f"strategy {name} trong STRATEGY_BLOCK (bang chung am tu backtest)",
                "n": 0, "avg_r": 0.0}
    data = stats
    if data is None:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:  # noqa: BLE001
            data = {}
    if not isinstance(data, dict):
        data = {}
    cur = data.get(name) or {}
    n = int(cur.get("n", 0) or 0)
    avg = float(cur.get("sum_r", 0.0) or 0.0) / max(n, 1)
    if n >= max(int(min_n), 1) and avg <= -abs(float(avg_r)):
        return {"blocked": True,
                "reason": f"strategy {name} dang am (n={n}, avgR={avg:+.2f})",
                "n": n, "avg_r": round(avg, 3)}
    return {"blocked": False, "reason": "", "n": n, "avg_r": round(avg, 3)}
