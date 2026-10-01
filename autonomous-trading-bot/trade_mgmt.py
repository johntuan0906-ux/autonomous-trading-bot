"""Quan ly lenh dong (muc 12/16/18/27 tai lieu): partial TP + break-even + trailing.

Vi sao: vao lenh ATR 1.5x / TP 3x ma khong quan ly giua lenh thi win-rate thap
(~20-25%) vi gia chi can di nguoc 1 lan la cham SL truoc khi toi TP. Ba ky thuat
duoi day chuyen mot phan "lenh sap cham TP" thanh "lenh hoa / lai nho":

1. PARTIAL   — chot 50% vi the tai +1R (khoa lai, giam rui ro cho phan con lai).
2. BREAK-EVEN — sau +1R, doi SL ve entry (+buffer phi) -> lenh toi da hoa von.
3. TRAILING  — sau +1R, keo SL theo gia cach 1xATR -> bat duoc xu huong dai.

Toan bo la ham thuan (pure) + dataclass de unit-test duoc, khong goi API.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

FEE_ROUNDTRIP_PCT = 0.001  # 0.05% x 2 chieu (taker Binance Futures)


@dataclass
class ManagedTrade:
    """Trang thai quan ly cua 1 vi the (ngoai entry/sl/tp/qty co ban)."""

    symbol: str
    direction: str  # LONG | SHORT
    entry: float
    qty: float          # qty con lai
    sl: float
    tp: float
    initial_sl: float = 0.0   # SL ban dau — moc tinh 1R (KHONG doi khi BE/trail)
    init_qty: float = 0.0
    partial_done: bool = False
    be_done: bool = False
    booked_pnl: float = 0.0   # PnL da chot tu partial (USDT)
    mfe_r: float = 0.0        # MFE lon nhat tinh bang R
    opened_ts: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.init_qty <= 0:
            self.init_qty = self.qty
        if self.initial_sl <= 0:
            self.initial_sl = self.sl

    @property
    def risk_per_unit(self) -> float:
        """Khoang cach entry->SL ban dau (1R theo gia)."""
        return abs(self.entry - self.initial_sl)


def r_multiple(direction: str, entry: float, sl0: float, price: float) -> float:
    """Lai/lo hien tai tinh theo R (1R = |entry - SL ban dau|)."""
    dist = abs(entry - sl0)
    if dist <= 0:
        return 0.0
    d = (price - entry) if direction.upper() == "LONG" else (entry - price)
    return d / dist


def _be_sl(trade: ManagedTrade, buffer_pct: float) -> float:
    """SL hoa von = entry +- buffer phi (khong bao gio lo sau khi BE)."""
    buf = trade.entry * max(buffer_pct, 0.0)
    return trade.entry + buf if trade.direction.upper() == "LONG" else trade.entry - buf


def manage(trade: ManagedTrade, price: float, atr: float = 0.0, *,
           partial_at_r: float = 1.0, partial_pct: float = 0.5,
           be_at_r: float = 1.0, be_buffer_pct: float = FEE_ROUNDTRIP_PCT,
           trail_atr_mult: float = 0.0) -> dict:
    """Quyet dinh cho 1 vi the tai gia `price`.

    Tra dict: action (HOLD|PARTIAL|BE|TRAIL|EXIT_SL|EXIT_TP), close_qty,
    new_sl, reason, r.
    """
    d = trade.direction.upper()
    r = r_multiple(d, trade.entry, trade.initial_sl, price)
    trade.mfe_r = max(trade.mfe_r, r)

    # 1) Cham SL/TP truoc (uu tien bao ve von)
    if d == "LONG":
        if price <= trade.sl:
            return {"action": "EXIT_SL", "close_qty": trade.qty, "new_sl": None,
                    "reason": "cham SL", "r": r}
        if price >= trade.tp:
            return {"action": "EXIT_TP", "close_qty": trade.qty, "new_sl": None,
                    "reason": "cham TP", "r": r}
    else:
        if price >= trade.sl:
            return {"action": "EXIT_SL", "close_qty": trade.qty, "new_sl": None,
                    "reason": "cham SL", "r": r}
        if price <= trade.tp:
            return {"action": "EXIT_TP", "close_qty": trade.qty, "new_sl": None,
                    "reason": "cham TP", "r": r}

    # 2) Partial TP: chot mot phan tai +partial_at_r, dong thoi dua SL ve hoa von
    if (partial_at_r > 0 and not trade.partial_done and r >= partial_at_r
            and 0.0 < partial_pct < 1.0 and trade.qty > 0):
        cq = max(0.0, min(round(trade.qty * partial_pct, 10), trade.qty))
        if cq > 0:
            trade.booked_pnl += (cq * abs(price - trade.entry)) * (1.0 - FEE_ROUNDTRIP_PCT)
            trade.qty = round(trade.qty - cq, 10)
            trade.partial_done = True
            trade.sl = _be_sl(trade, be_buffer_pct)
            trade.be_done = True
            return {"action": "PARTIAL", "close_qty": cq, "new_sl": trade.sl,
                    "reason": f"chot {partial_pct:.0%} tai {r:.2f}R, SL->hoa von", "r": r}

    # 3) Break-even: doi SL ve entry (khi khong dung partial)
    if be_at_r > 0 and not trade.be_done and r >= be_at_r:
        new_sl = _be_sl(trade, be_buffer_pct)
        improved = (new_sl > trade.sl) if d == "LONG" else (new_sl < trade.sl)
        trade.be_done = True
        if improved:
            trade.sl = new_sl
            return {"action": "BE", "close_qty": 0.0, "new_sl": new_sl,
                    "reason": f"doi SL ve hoa von tai {r:.2f}R", "r": r}

    # 4) Trailing theo ATR (chi sau khi da BE/partial)
    if trail_atr_mult > 0 and atr > 0 and (trade.be_done or trade.partial_done):
        cand = (price - trail_atr_mult * atr) if d == "LONG" else (price + trail_atr_mult * atr)
        improved = (cand > trade.sl) if d == "LONG" else (cand < trade.sl)
        if improved:
            trade.sl = cand
            return {"action": "TRAIL", "close_qty": 0.0, "new_sl": cand,
                    "reason": f"trail SL {trail_atr_mult}xATR", "r": r}

    return {"action": "HOLD", "close_qty": 0.0, "new_sl": None,
            "reason": "giu lenh", "r": r}


def new_trade(symbol: str, direction: str, entry: float, qty: float,
              sl: float, tp: float) -> ManagedTrade:
    """Khoi tao trade co luu SL ban dau (dung lam moc 1R)."""
    return ManagedTrade(symbol=symbol, direction=direction.upper(), entry=entry,
                        qty=qty, sl=sl, tp=tp, initial_sl=sl, init_qty=qty)


def cfg_from_env(env: dict | None = None) -> dict:
    """Doc tham so quan ly lenh tu .env (co default an toan)."""
    import os
    e = env if env is not None else os.environ

    def f(name: str, d: float) -> float:
        try:
            return float(e.get(name, d))
        except (TypeError, ValueError):
            return d

    return {"partial_at_r": f("PARTIAL_AT_R", 1.0),
            "partial_pct": f("PARTIAL_PCT", 0.5),
            "be_at_r": f("BE_AT_R", 1.0),
            "trail_atr_mult": f("TRAIL_ATR_MULT", 1.0)}


def manage_trade(trade: ManagedTrade, price: float, atr: float = 0.0,
                 env: dict | None = None) -> dict:
    """Wrapper: manage() voi tham so lay tu .env."""
    return manage(trade, price, atr, **cfg_from_env(env))


def trade_result(trade: ManagedTrade, exit_reason: str, exit_price: float) -> dict:
    """Ket qua cuoi cung: PnL (USDT), R, va 'won' cho learner.

    Won = TP/TRAIL, hoac BE sau khi da chot partial (thuc te khong lo).
    """
    rem = (trade.qty * (exit_price - trade.entry)
           if trade.direction.upper() == "LONG"
           else trade.qty * (trade.entry - exit_price))
    rem *= (1.0 - FEE_ROUNDTRIP_PCT)
    pnl = trade.booked_pnl + rem
    dist = abs(trade.entry - trade.initial_sl) or 1e-12
    full_qty = trade.init_qty or trade.qty
    r = pnl / (dist * full_qty)
    reason = exit_reason.upper()
    won = reason in ("TP", "TRAIL") or (reason == "BE" and trade.partial_done)
    return {"pnl": round(pnl, 6), "r": round(r, 4),
            "won": bool(won or (trade.partial_done and pnl > 0)),
            "exit_reason": reason, "partial_done": trade.partial_done,
            "mfe_r": round(trade.mfe_r, 3)}

