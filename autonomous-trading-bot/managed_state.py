"""Luu trang thai quan ly lenh (initial_sl / partial / BE / booked_pnl) ra JSON.

P0-1: thieu file nay thi sau khi restart, `initial_sl` bi mat -> moc 1R sai ->
partial/BE/trail kich hoat sai moc VA cot R trong journal sai theo. State chi luu
nhung gi KHONG the suy ra tu san (moc 1R, da chot partial chua, pnl da chot).
"""
from __future__ import annotations

import json
import os
import time

from trade_mgmt import ManagedTrade

FIELDS = ("entry", "qty", "sl", "tp", "initial_sl", "init_qty",
          "partial_done", "be_done", "booked_pnl", "mfe_r", "direction")


def dump_trade(mt: ManagedTrade) -> dict:
    return {k: getattr(mt, k) for k in FIELDS}


def load_trade(sym: str, d: dict) -> ManagedTrade:
    """Dung lai ManagedTrade tu dict (bo qua dong thieu -> default an toan)."""
    mt = ManagedTrade(symbol=str(d.get("symbol") or sym),
                      direction=str(d.get("direction") or "LONG").upper(),
                      entry=float(d.get("entry") or 0.0),
                      qty=float(d.get("qty") or 0.0),
                      sl=float(d.get("sl") or 0.0),
                      tp=float(d.get("tp") or 0.0))
    mt.initial_sl = float(d.get("initial_sl") or mt.sl or mt.entry or 0.0)
    mt.init_qty = float(d.get("init_qty") or mt.qty or 0.0)
    mt.partial_done = bool(d.get("partial_done"))
    mt.be_done = bool(d.get("be_done"))
    mt.booked_pnl = float(d.get("booked_pnl") or 0.0)
    mt.mfe_r = float(d.get("mfe_r") or 0.0)
    return mt


def dump(bot, extra: dict | None = None) -> dict:
    return {"saved_ts": time.time(),
            "trades": {s: dump_trade(mt) for s, mt in getattr(bot, "managed", {}).items()},
            "extra": extra or {}}


def save(path: str, bot, extra: dict | None = None) -> bool:
    """Ghi nguyen tu (tmp + os.replace) — crash giua chung khong lam hong file."""
    try:
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dump(bot, extra), f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def load(path: str) -> dict:
    """Tra {'trades': {...}, 'extra': {...}} — rong neu chua co/loi."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def load_into(bot, payload: dict) -> int:
    """Nap trade da luu vao `bot.managed` (khong ghi de trade dang co). Tra so luong."""
    n = 0
    for sym, d in (payload.get("trades") or {}).items():
        if sym in getattr(bot, "managed", {}):
            continue
        try:
            bot.managed[sym] = load_trade(sym, d)
            n += 1
        except Exception:
            continue
    return n
