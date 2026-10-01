"""Derivatives data: OI / funding / liquidation / long-short (muc 10-11 tai lieu).

Nguon: Binance Futures public API (khong can key) + Coinglass RSS (mo ta).
OI/funding la boi canh, KHONG phai tin hieu vao lenh doc lap.
"""
from __future__ import annotations

import requests


def fetch_oi_funding(symbol_ccxt: str) -> dict:
    """symbol_ccxt dang 'BTC/USDT:USDT' -> OI hien tai + funding hien tai tu Binance.
    Tra {oi, oi_chg_24h, funding, fund_annual, ls_ratio}. Loi -> gia tri 0."""
    out = {"oi": 0.0, "oi_chg_24h": 0.0, "funding": 0.0, "fund_annual": 0.0, "ls_ratio": 0.0}
    try:
        base = symbol_ccxt.split("/")[0]
        sym = f"{base}USDT"
        r = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                         params={"symbol": sym}, timeout=10)
        if r.ok:
            out["oi"] = float(r.json().get("openInterest") or 0.0)
        r = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                         params={"symbol": sym}, timeout=10)
        if r.ok:
            d = r.json()
            out["funding"] = float(d.get("lastFundingRate") or 0.0)
            out["fund_annual"] = round(out["funding"] * 3 * 365 * 100, 3)
        r = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                         params={"symbol": sym, "period": "1h", "limit": 2}, timeout=10)
        if r.ok and isinstance(r.json(), list) and r.json():
            rows = r.json()
            out["ls_ratio"] = float(rows[-1].get("longShortRatio") or 0.0)
            if len(rows) >= 2:
                a = float(rows[-1].get("longShortRatio") or 0.0)
                b = float(rows[0].get("longShortRatio") or 0.0)
                out["oi_chg_24h"] = round(a - b, 4)
    except Exception:
        pass
    return out


def derivatives_guard(oi: float, funding: float, ls_ratio: float) -> dict:
    """Canh bao cuc doan (muc 11, 27 tai lieu): dong Long + funding cao = de bi short-squeeze
    nguoc lai. Tra {warn: str|None, halve: bool}."""
    if funding >= 0.001 and ls_ratio >= 2.0:
        return {"warn": f"Long dong ({ls_ratio}) + funding cao ({funding}) — de dump",
                "halve": True}
    if funding <= -0.001 and ls_ratio <= 0.5 and ls_ratio > 0:
        return {"warn": f"Short dong ({ls_ratio}) + funding am ({funding}) — de squeeze",
                "halve": True}
    return {"warn": None, "halve": False}


def fetch_liquidations(symbol_ccxt: str, limit: int = 50) -> dict:
    """Lenh thanh ly gan nhat (muc 10.3): Binance forceOrders. Tra {long_liq, short_liq, total}."""
    out = {"long_liq": 0.0, "short_liq": 0.0, "total": 0.0, "dominance": 0.0}
    try:
        base = symbol_ccxt.split("/")[0]
        sym = f"{base}USDT"
        r = requests.get("https://fapi.binance.com/fapi/v1/forceOrders",
                         params={"symbol": sym, "limit": min(limit, 100)}, timeout=10)
        if r.ok and isinstance(r.json(), list):
            for o in r.json():
                q = float(o.get("origQty") or o.get("executedQty") or 0.0)
                px = float(o.get("price") or o.get("avgPrice") or 0.0)
                notional = q * px
                out["total"] += notional
                if str(o.get("side", "")).upper() == "SELL":
                    out["long_liq"] += notional  # Long bi thanh ly = lenh SELL
                else:
                    out["short_liq"] += notional
            tot = out["total"]
            out["dominance"] = round((out["long_liq"] - out["short_liq"]) / max(tot, 1e-9), 3) if tot else 0.0
            for k in ("long_liq", "short_liq", "total"):
                out[k] = round(out[k], 2)
    except Exception:
        pass
    return out
