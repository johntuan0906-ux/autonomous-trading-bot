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

import os
import time
from dataclasses import dataclass, field

FEE_ROUNDTRIP_PCT = 0.001  # 0.05% x 2 chieu (taker Binance Futures)
#: (26/10) Slippage gia dinh cho MO PHONG (khong ap cho so that: gia khop that da bao gom
#: truot gia). 0.02%/chieu — market order tren cap thanh khoan trung binh.
SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.0002") or 0.0)
#: Tong chi phi 1 vong (phi + slippage 2 chieu) — dung cho mo phong/tham so.
COST_ROUNDTRIP_PCT = FEE_ROUNDTRIP_PCT + 2.0 * SLIPPAGE_PCT


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
    # (01/10) clientOrderId cua lenh bao ve dang TREO tren san: {"sl": "glow...", "tp": ...}
    # Luu vao state de doi soat moi vong (phat hien SL/TP bi mat/huy) va de truy vet.
    prot_ids: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.init_qty <= 0:
            self.init_qty = self.qty
        if self.initial_sl <= 0:
            self.initial_sl = self.sl

    @property
    def risk_per_unit(self) -> float:
        """Khoang cach entry->SL ban dau (1R theo gia)."""
        return abs(self.entry - self.initial_sl)


#: (28/10) B-031 — duoi nguong nay thi "khoang cach 1R" KHONG con la 1R that (SL da bi doi
#: sat entry, hoac vi the adopt khong co SL goc) ⇒ moi R tinh ra deu RAC. Do that tren journal
#: TESTNET: 320/3342 ban ghi CLOSE co |r| > 5 (max r=793.07, mfe_r=802.36).
MIN_RISK_PCT = 0.001


def risk_distance_ok(entry: float, sl: float, *, min_pct: float = MIN_RISK_PCT) -> bool:
    """Khoang cach entry→SL co THAT SU la 1R khong (>= `min_pct`% gia vao)?"""
    try:
        e, s = float(entry), float(sl)
    except (TypeError, ValueError):
        return False
    if e <= 0 or s <= 0:
        return False
    return abs(e - s) >= e * float(min_pct)


def r_multiple(direction: str, entry: float, sl0: float, price: float) -> float:
    """Lai/lo hien tai tinh theo R (1R = |entry - SL ban dau|).

    Tra **0.0** khi khoang cach 1R khong hop le (`risk_distance_ok`). Vi sao phai chan (28/10):
    mot SL bi doi sat entry ⇒ `dist` ≈ 0 ⇒ R khong lo (do that `r=793`), va vi `manage()` dung
    `r` de kich hoat **chot-mot-phan / hoa von**, R rac lam lenh bi chot ngay lap tuc ⇒ dong oan.
    """
    if not risk_distance_ok(entry, sl0):
        return 0.0
    dist = abs(float(entry) - float(sl0))
    d = ((float(price) - float(entry)) if direction.upper() == "LONG"
         else (float(entry) - float(price)))
    return d / dist


def _be_sl(trade: ManagedTrade, buffer_pct: float) -> float:
    """SL hoa von = entry +- buffer phi (khong bao gio lo sau khi BE)."""
    buf = trade.entry * max(buffer_pct, 0.0)
    return trade.entry + buf if trade.direction.upper() == "LONG" else trade.entry - buf


def record_protection(mt, res) -> dict:
    """Luu clientOrderId cua lenh bao ve vua dat vao `mt.prot_ids` -> doi soat sau nay.

    Vi sao (hoi dong 14 model 01/10): state chi luu muc sl/tp, khong luu ID lenh treo,
    nen khong the biet lenh bao ve co con tren san hay da bi huy/mat -> vi the co the
    "mo coi" ma bot khong phat hien. Tra ve dict id hien co.
    """
    ids = dict(getattr(mt, "prot_ids", {}) or {})
    for tag, key in (("sl", "sl_order"), ("tp", "tp_order")):
        order = (res or {}).get(key) or {}
        cid = order.get("clientOrderId") or order.get("id")
        if cid:
            ids[tag] = str(cid)
    if ids and mt is not None:
        try:
            mt.prot_ids = ids
        except Exception:  # noqa: BLE001  (mt la obj la -> bo qua, khong lam chet bot)
            pass
    return ids


def dust_notional(qty: float, price: float, min_notional: float = 0.0) -> bool:
    """`qty*price` co nho hon `min_notional` khong (True = san se TU CHOI).

    Ham thuan -> test duoc. `min_notional <= 0` = khong kiem tra (hanh vi cu).
    """
    try:
        if float(min_notional) <= 0:
            return False
        n = float(qty) * float(price)
        return 0.0 < n < float(min_notional)
    except (TypeError, ValueError):
        return False


def manage(trade: ManagedTrade, price: float, atr: float = 0.0, *,
           partial_at_r: float = 1.0, partial_pct: float = 0.5,
           be_at_r: float = 1.0, be_buffer_pct: float = FEE_ROUNDTRIP_PCT,
           trail_atr_mult: float = 0.0, min_notional: float = 0.0) -> dict:
    """Quyet dinh cho 1 vi the tai gia `price`.

    Tra dict: action (HOLD|PARTIAL|BE|TRAIL|EXIT_SL|EXIT_TP), close_qty,
    new_sl, reason, r.

    `min_notional` (13/10): san TU CHOI dong vi the co notional < nguong nay
    (`-4164 ... unless you choose reduce only`; o HEDGE mode khong dung duoc
    reduceOnly) ⇒ chot mot phan se de lai "bui" khong dong duoc, va vi the do
    nam lai tren san KHONG co bao ve. Vi vay: neu phan CON LAI sau khi chot
    mot phan qua nho thi BO QUA partial (giu nguyen vi the, dong tron khi
    cham TP/SL). Mac dinh 0 = hanh vi cu (test cu khong doi).
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
        remain = round(trade.qty - cq, 10)
        # (13/10) Chan "bui": phan con lai ma nho hon minNotional thi san TU CHOI
        # dong (HEDGE mode khong dung reduceOnly) -> vi the nam lai tren san khong
        # co SL/TP va bot da quen no. Bo qua partial de dong TRON khi cham TP/SL.
        if cq > 0 and not dust_notional(remain, price, min_notional):
            trade.booked_pnl += (cq * abs(price - trade.entry)) * (1.0 - FEE_ROUNDTRIP_PCT)
            trade.qty = remain
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
                 env: dict | None = None, min_notional: float = 0.0) -> dict:
    """Wrapper: manage() voi tham so lay tu .env."""
    return manage(trade, price, atr, min_notional=min_notional,
                  **cfg_from_env(env))


def trade_result(trade: ManagedTrade, exit_reason: str, exit_price: float, *,
                 slippage_pct: float = 0.0) -> dict:
    """Ket qua cuoi cung: PnL (USDT), R, va 'won' cho learner.

    Won = TP/TRAIL, hoac BE sau khi da chot partial (thuc te khong lo).

    `slippage_pct` (26/10): chi phi TRUOT GIA gia dinh cho **mo phong** = 2 chieu x
    slippage_pct x notional. Mac dinh 0.0 ⇒ **khong doi hanh vi that** (so that da bao gom
    truot gia trong gia khop). Backtest truyen `SLIPPAGE_PCT` de so sanh sat thuc te hon.
    """
    rem = (trade.qty * (exit_price - trade.entry)
           if trade.direction.upper() == "LONG"
           else trade.qty * (trade.entry - exit_price))
    rem *= (1.0 - FEE_ROUNDTRIP_PCT)
    slip = 2.0 * float(slippage_pct or 0.0) * (trade.init_qty or trade.qty) * trade.entry
    pnl = trade.booked_pnl + rem - slip
    # (28/10) B-031 — cong thuc `pnl / (dist * full_qty)` LA DUNG (no tinh ca phi 1 vong va
    # phan da chot som — dung thu du an dang do "chi phi quy ra R"). Loi THAT SU nam o cho khac:
    #   (a) `dist = abs(entry - initial_sl) or 1e-12` ⇒ khi SL bi doi sat entry (hoac vi the
    #       adopt khong co SL goc) thi mau so = 1e-12 ⇒ R NO TUNG (do that: r=793.07, mfe_r=802);
    #   (b) `mfe_r` (tu `r_multiple`) cung bi no ⇒ **kich hoat chot-mot-phan/hoa von ngay lap tuc**
    #       ⇒ dong lenh oan.
    # Nay: neu khoang cach 1R khong hop le thi R = 0.0 va `r_valid=False` ⇒ cac noi thong ke
    # (`monitor_report.stats`, `lessons`) LOAI ban ghi do thay vi cong so rac vao PF(R)/avgR.
    valid = risk_distance_ok(trade.entry, trade.initial_sl)
    dist = abs(trade.entry - trade.initial_sl)
    full_qty = trade.init_qty or trade.qty
    risk_usdt = dist * full_qty
    r = (pnl / risk_usdt) if (valid and risk_usdt > 0) else 0.0
    reason = exit_reason.upper()
    won = reason in ("TP", "TRAIL") or (reason == "BE" and trade.partial_done)
    return {"pnl": round(pnl, 6), "r": round(r, 4), "r_valid": bool(valid),
            "won": bool(won or (trade.partial_done and pnl > 0)),
            "exit_reason": reason, "partial_done": trade.partial_done,
            "mfe_r": round(trade.mfe_r, 3) if valid else 0.0,
            "slippage": round(slip, 6)}

