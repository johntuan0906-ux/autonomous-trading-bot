"""ATR-based SL/TP, position sizing, and kill-switch."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

# (02/10) Nguong "lo khong dang ke" cho chuoi thua lien tiep (USDT).
# Vi sao: thuc te 01/10, mot lenh dong do DUST voi pnl = -0.0011 USDT bi tinh la lan
# thua thu 5 -> TRIP kill-switch va bot dung trade, du thuc chat lenh do khong lo.
MIN_LOSS_USDT = float(os.getenv("MIN_LOSS_USDT", "0.5") or 0.5)


def utc_day(ts: float | None = None) -> str:
    """Ngay UTC 'YYYY-MM-DD' — moc reset DD ngay (khop gio san)."""
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() if ts is None else ts))


def atr_levels(entry: float, atr_value: float, direction: str,
               sl_mult: float = 1.5, tp_mult: float = 3.0) -> dict:
    """Dynamic SL = 1.5x ATR, TP = 3x ATR -> R:R = 1:2 guaranteed."""
    if entry <= 0 or atr_value <= 0:
        raise ValueError("entry and atr must be positive")
    d = direction.upper()
    if d == "LONG":
        sl = entry - sl_mult * atr_value
        tp = entry + tp_mult * atr_value
    elif d == "SHORT":
        sl = entry + sl_mult * atr_value
        tp = entry - tp_mult * atr_value
    else:
        raise ValueError("direction must be LONG or SHORT")
    rr = abs(tp - entry) / max(abs(entry - sl), 1e-12)
    return {"entry": entry, "sl": round(sl, 6), "tp": round(tp, 6),
            "rr": round(rr, 4), "sl_dist": round(abs(entry - sl), 6),
            "tp_dist": round(abs(tp - entry), 6)}


def position_size(balance_usdt: float, risk_pct: float, entry: float, sl: float) -> float:
    """Qty (in base units) risking risk_pct% of balance. Futures: qty = risk / |entry-sl|."""
    risk_usdt = balance_usdt * (risk_pct / 100.0)
    dist = abs(entry - sl)
    if dist <= 0:
        raise ValueError("entry == sl")
    return round(risk_usdt / dist, 6)


@dataclass
class KillSwitch:
    max_daily_loss_pct: float = 2.0  # khung moi (muc 12): daily loss 1.5-2.0%
    max_atr_pct: float = 0.05
    max_errors: int = 5
    start_balance: float = 1000.0
    errors: int = 0
    tripped: bool = False
    reason: str = ""
    day_start: float = field(default_factory=time.time)
    consec_losses: int = 0  # khung moi (muc 12): max 5 loss lien tiep -> ngung
    max_consec_losses: int = 5
    peak_balance: float = 0.0  # theo doi Max DD (muc 16/19)
    # ---- P0-2: state phai song sot qua restart (supervisor tu restart sau 15s) ----
    day: str = field(default_factory=lambda: utc_day())   # ngay UTC dang tinh DD
    start_equity: float = 0.0   # equity THAT dau ngay (0 = chua biet -> dung start_balance)
    day_reset_utc: bool = True

    def register_error(self) -> bool:
        self.errors += 1
        if self.errors >= self.max_errors:
            return self.trip(f"{self.errors} consecutive API errors")
        return False

    def reset_errors(self) -> None:
        self.errors = 0

    def register_close(self, won: bool, balance: float, pnl: float | None = None,
                       min_loss_usdt: float | None = None) -> bool:
        """Ghi nhan close: dem loss lien tiep + cap nhat peak. Loss 5 lien tiep -> trip.

        (02/10) Lo "KHONG DANG KE" (|pnl| < nguong) la TRUNG TINH: khong tang chuoi thua,
        cung khong reset chuoi. Vi sao: 01/10 mot lenh dong do DUST voi pnl = -0.0011 USDT
        bi tinh la lan thua thu 5 -> TRIP kill-switch, bot dung trade du lenh do khong lo.
        Nguong: `min_loss_usdt` (mac dinh `MIN_LOSS_USDT`, 0.5 USDT). Truyen pnl=None thi
        giu nguyen hanh vi cu (moi lenh khong thang = 1 lan thua).
        """
        self.peak_balance = max(self.peak_balance or balance, balance)
        if won:
            self.consec_losses = 0
            return False
        thr = MIN_LOSS_USDT if min_loss_usdt is None else float(min_loss_usdt)
        if pnl is not None and abs(float(pnl)) < thr:
            return False                      # trung tinh: khong tinh la thua
        self.consec_losses += 1
        if self.consec_losses >= self.max_consec_losses:
            return self.trip(f"{self.consec_losses} consecutive losses (muc 12)")
        return False

    def check(self, balance: float, atr_pct: float = 0.0) -> bool:
        """Return True if trading must halt. Checks drawdown + volatility."""
        if self.tripped:
            return True
        self.peak_balance = max(self.peak_balance or balance, balance)
        # P0-6: DD tinh tren equity THAT dau ngay (start_equity), khong phai
        # BALANCE_USDT hardcode -> tran 2% dung nghia 2% tai khoan.
        dd = self.daily_dd_pct(balance)
        if dd >= self.max_daily_loss_pct:
            return self.trip(f"daily loss {dd:.2f}% >= {self.max_daily_loss_pct}%")
        if atr_pct and atr_pct >= self.max_atr_pct:
            return self.trip(f"volatility ATR {atr_pct:.2%} >= {self.max_atr_pct:.2%}")
        return False

    def base_equity(self) -> float:
        """Moc tinh DD: uu tien equity THAT dau ngay, fallback BALANCE_USDT."""
        return self.start_equity if self.start_equity > 0 else self.start_balance

    def daily_dd_pct(self, balance: float) -> float:
        base = self.base_equity()
        return (base - balance) / max(base, 1e-9) * 100.0

    def note_equity(self, equity: float, now: float | None = None) -> bool:
        """Dong bo EQUITY THAT tu san; tra True neu vua roll sang ngay moi.

        - Lan dau (chua co moc) -> lay equity hien tai lam moc DD ngay.
        - Sang ngay moi -> moc lai DD + xoa dem trong ngay.
        - `tripped` KHONG bao gio tu xoa (phai xoa tay bang reset_state) — khac ban cu:
          restart la mat kill-switch.
        """
        eq = float(equity or 0.0)
        if eq > 0:
            self.peak_balance = max(self.peak_balance or 0.0, eq)
        today = utc_day(now)
        rolled = bool(self.day_reset_utc and today != self.day)
        if rolled:
            self.day = today
            self.consec_losses = 0
            self.errors = 0
        if eq > 0 and (rolled or self.start_equity <= 0):
            self.start_equity = eq
        return rolled

    def to_dict(self) -> dict:
        return {"max_daily_loss_pct": self.max_daily_loss_pct, "max_atr_pct": self.max_atr_pct,
                "max_errors": self.max_errors, "max_consec_losses": self.max_consec_losses,
                "start_balance": self.start_balance, "start_equity": self.start_equity,
                "peak_balance": self.peak_balance, "errors": self.errors,
                "tripped": bool(self.tripped), "reason": self.reason,
                "consec_losses": self.consec_losses, "day": self.day}

    @classmethod
    def from_dict(cls, d: dict) -> "KillSwitch":
        ks = cls(max_daily_loss_pct=float(d.get("max_daily_loss_pct", 2.0)),
                 max_atr_pct=float(d.get("max_atr_pct", 0.05)),
                 max_errors=int(d.get("max_errors", 5)),
                 start_balance=float(d.get("start_balance", 1000.0)))
        ks.max_consec_losses = int(d.get("max_consec_losses", 5))
        ks.start_equity = float(d.get("start_equity", 0.0) or 0.0)
        ks.peak_balance = float(d.get("peak_balance", 0.0) or 0.0)
        ks.errors = int(d.get("errors", 0))
        ks.consec_losses = int(d.get("consec_losses", 0))
        ks.tripped = bool(d.get("tripped", False))
        ks.reason = str(d.get("reason", "") or "")
        ks.day = str(d.get("day") or utc_day())
        return ks

    def trip(self, reason: str) -> bool:
        self.tripped = True
        self.reason = reason
        return True


def load_state(path: str, ks: KillSwitch, warn=None) -> KillSwitch:
    """Doc state da luu (neu co) va gop vao `ks` -> kill-switch song sot restart.

    Nguon su that cho NGUONG (max_daily_loss_pct / max_atr_pct / max_errors) la
    `ks` (tu .env dang chay) — state cu KHONG ghi de nguong. Neu file luu nguong
    KHAC .env thi goi `warn(msg)` (hoi dong 14 model 01/10 tung ket luan nham rang
    bot dung nguong trong file; thuc te .env thang, va nay co canh bao ro rang).

    FAIL-CLOSED (hoi dong 14 model 01/10, muc P0): file state CO ma doc/parse loi
    (JSON hong, quyen truy cap, dia loi...) -> coi nhu DANG TRIPPED, khong duoc
    im lang chay tiep nhu khong co gi. Truong hop file CHUA TON TAI (lan dau chay /
    vua `python risk.py --reset`) van la binh thuong, khong trip.
    """
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return ks                       # chua co state -> lan dau chay, binh thuong
    except Exception as e:              # noqa: BLE001  hong/khong doc duoc -> fail-closed
        why = f"risk_state khong doc duoc ({type(e).__name__}: {str(e)[:80]})"
        if not ks.tripped:
            ks.trip(f"{why} — fail-closed, can nguoi kiem tra")
        if warn:
            warn(f"{why} -> da TRIP kill-switch (fail-closed). Sua/xoa {path} "
                 f"roi `python risk.py --reset` neu muon chay tiep.")
        return ks
    try:
        old = KillSwitch.from_dict(d)
    except Exception as e:              # noqa: BLE001  cau truc JSON la -> fail-closed
        why = f"risk_state sai cau truc ({type(e).__name__}: {str(e)[:80]})"
        if not ks.tripped:
            ks.trip(f"{why} — fail-closed, can nguoi kiem tra")
        if warn:
            warn(f"{why} -> da TRIP kill-switch (fail-closed).")
        return ks
    ks.tripped = old.tripped
    ks.reason = old.reason
    ks.errors = old.errors
    ks.consec_losses = old.consec_losses
    ks.peak_balance = max(ks.peak_balance, old.peak_balance)
    ks.start_equity = old.start_equity or ks.start_equity
    ks.day = old.day or ks.day
    if warn:
        drift = []
        for name in ("max_daily_loss_pct", "max_atr_pct", "max_errors"):
            was, now = getattr(old, name), getattr(ks, name)
            if was != now:
                drift.append(f"{name}: file={was} -> dung {now} (.env)")
        if drift:
            warn("CANH BAO drift nguong kill-switch (" + "; ".join(drift) + ")")
    return ks


def save_state(path: str, ks: KillSwitch) -> bool:
    """Ghi state nguyen tu (tmp + os.replace) — khong lam hong file khi crash."""
    try:
        import json
        import os
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ks.to_dict(), f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def reset_state(path: str) -> bool:
    """Xoa state -> cho phep trade lai sau khi da kiem tra nguyen nhan trip."""
    import os
    try:
        os.remove(path)
        return True
    except OSError:
        return False


if __name__ == "__main__":  # python risk.py [--reset]
    import json
    import sys
    _p = "logs/risk_state.json"
    if "--reset" in sys.argv:
        print("reset:", reset_state(_p))
    else:
        try:
            print(json.dumps(json.load(open(_p, encoding="utf-8")), indent=1))
        except Exception as e:  # noqa: BLE001
            print("khong doc duoc %s: %s" % (_p, e))
