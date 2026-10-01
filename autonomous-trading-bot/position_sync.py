"""P0-1: adopt vi the dang mo THAT tren san khi bot khoi dong lai.

Ban cu (`turbo_demo.py`) chi `log.info("ke thua vi the san: ...")` roi KHONG ghi
vao `bot.portfolio.positions`. Hau qua: sau khi crash/restart (supervisor tu
restart sau 15s), bot quen mat vi the dang mo -> vong sau mo them 1 lenh nua cung
cap (gap doi risk) va vi the cu mat quan ly partial/BE/trail.

Module nay lam dung viec do:
  1. chuan hoa du lieu ccxt -> {symbol, direction, qty, entry}
  2. uu tien moc 1R da luu (`managed_state`) -> arm lai SL/TP dung chien luoc
  3. khong co state -> lay SL/TP dang TREO tren san (khong dung den)
  4. khong co gi -> tinh lai SL/TP bang ATR
  5. khong xac dinh duoc -> danh dau `unmanaged` + canh bao (KHONG im lang)
"""
from __future__ import annotations

from managed_state import load_trade
from portfolio import Position
from risk import atr_levels
from trade_mgmt import new_trade


def normalize(rows) -> list:
    """ccxt fetch_positions -> [{symbol, direction, qty, entry}] chi vi the dang mo."""
    out: list = []
    for p in rows or []:
        try:
            qty = abs(float(p.get("contracts") or 0))
        except (TypeError, ValueError, AttributeError):
            qty = 0.0
        if qty <= 0:
            continue
        sym = str(p.get("symbol") or "")
        if not sym:
            continue
        side = str(p.get("side") or "").lower()
        direction = "LONG" if side in ("long", "buy") else "SHORT"
        try:
            entry = float(p.get("entryPrice") or 0) or 0.0
        except (TypeError, ValueError):
            entry = 0.0
        out.append({"symbol": sym, "direction": direction, "qty": qty, "entry": entry})
    return out


def _atr_levels_for(bot, sym: str, direction: str, entry: float, atr_fn) -> tuple:
    """Tinh SL/TP bang ATR. Tra (sl, tp, entry) — 0.0 neu khong tinh duoc."""
    a = (atr_fn(sym) if atr_fn else None) or {}
    try:
        atr = float(a.get("atr") or 0)
    except (TypeError, ValueError):
        atr = 0.0
    try:
        px = float(a.get("price") or entry or 0)
    except (TypeError, ValueError):
        px = 0.0
    if atr <= 0 or px <= 0:
        return 0.0, 0.0, entry
    lv = atr_levels(px, atr, direction, bot.cfg.sl_atr_mult, bot.cfg.tp_atr_mult)
    return float(lv["sl"]), float(lv["tp"]), float(entry or lv["entry"])


def adopt(bot, rows, *, atr_fn=None, managed=None, alert=None) -> dict:
    """Gan vi the san vao `bot.portfolio` + `bot.managed`; arm lai SL/TP khi can.

    Tra bao cao: {adopted, armed, unmanaged, skipped, errors}.
    """
    ex = bot.exchange
    rep: dict = {"adopted": [], "armed": [], "unarmed": [], "unmanaged": [],
                 "skipped": [], "errors": []}
    for p in normalize(rows):
        sym, d, qty, entry = p["symbol"], p["direction"], p["qty"], p["entry"]
        if sym in bot.portfolio.positions:
            rep["skipped"].append(sym)
            continue
        try:
            state = (managed or {}).get(sym)
            prot = ex.fetch_protection(sym) if hasattr(ex, "fetch_protection") else {}
            sl = tp = 0.0
            src = "none"
            mt = None
            if state:                                    # 1) moc 1R da luu -> chuan nhat
                mt = load_trade(sym, state)
                mt.qty = qty                             # qty THAT tren san la chuan
                if not mt.entry:
                    mt.entry = entry
                sl, tp = float(mt.sl or 0), float(mt.tp or 0)
                if sl > 0:
                    src = "state"
            if not sl and float(prot.get("sl") or 0) > 0:  # 2) SL dang treo tren san
                sl, src = float(prot["sl"]), "exchange"
            if not tp and float(prot.get("tp") or 0) > 0:
                tp = float(prot["tp"])
            if sl <= 0 or tp <= 0:                       # 3) tinh lai bang ATR
                a_sl, a_tp, entry = _atr_levels_for(bot, sym, d, entry, atr_fn)
                if sl <= 0:
                    sl = a_sl
                if tp <= 0:
                    tp = a_tp
                if sl > 0 and src == "none":
                    src = "atr"
            if entry <= 0:
                entry = sl
            pos = Position(sym, d, float(entry), float(qty), float(sl), float(tp))
            bot.portfolio.positions[sym] = pos
            if mt is None:
                mt = new_trade(sym, d, pos.entry, qty, sl or pos.entry, tp or pos.entry)
            bot.managed[sym] = mt      # luon nap vao de partial/BE/trail tiep tuc dung
            rep["adopted"].append(sym)  # da vao portfolio -> MONITOR phan mem da quan ly
            # src 'state' -> arm lai cho khop chien luoc; 'atr' -> chua co bao ve nao.
            # src 'exchange' -> dang duoc bao ve, KHONG dung vao (tranh huy nham).
            if sl > 0 and tp > 0 and src in ("state", "atr"):
                try:
                    ex.stop_tp_orders(sym, d, qty, sl, tp, cid_prefix="adopt")
                    rep["armed"].append(sym)
                except Exception as e:  # noqa: BLE001
                    # Thuc te gap: demo tra -4045 "Reach max stop order limit" cho MOI
                    # lenh stop (du khong con lenh treo nao) -> khong arm duoc tren san.
                    # Vi the KHONG duoc coi la loi chet: vi the van nam trong portfolio +
                    # managed nen `bot._monitor` (SL/TP phan mem) van dong dung luc. Nhung
                    # phai bao dong ro de nguoi van hanh biet dang chay khong co SL tren san.
                    rep["unarmed"].append(sym)
                    if alert:
                        alert(f"CANH BAO: KHONG dat duoc SL/TP TREN SAN cho {sym} "
                              f"({str(e)[:90]}) — dang duoc bao ve bang MONITOR phan mem "
                              "(chi hoat dong khi bot chay). Kiem tra lai khi san cho phep.")
            if sl <= 0:
                rep["unmanaged"].append(sym)
                if alert:
                    alert(f"CANH BAO: vi the {sym} {d} qty={qty} KHONG xac dinh duoc SL "
                          f"— kiem tra tay tren san ngay!")
        except Exception as e:  # noqa: BLE001
            rep["errors"].append(f"{sym}: {str(e)[:120]}")
    return rep
