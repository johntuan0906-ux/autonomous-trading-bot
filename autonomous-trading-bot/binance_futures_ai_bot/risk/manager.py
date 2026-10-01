from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class RiskManager:
    risk_per_trade: float
    max_daily_loss: float
    max_drawdown: float
    max_notional_fraction: float
    max_leverage: int
    min_qty_usdt: float
    day_start_equity: float | None = None
    peak_equity: float | None = None

    _day = None
    def update(self,equity):
        today=datetime.now(timezone.utc).date()
        if self._day != today:
            self._day=today; self.day_start_equity=equity
        self.peak_equity=max(self.peak_equity or equity,equity)

    def halted(self,equity):
        self.update(equity)
        daily=(equity/self.day_start_equity)-1
        dd=(equity/self.peak_equity)-1
        return daily <= -self.max_daily_loss or dd <= -self.max_drawdown

    def qty(self,equity, entry, stop):
        risk_cash=equity*self.risk_per_trade
        per_unit=abs(entry-stop)
        if per_unit<=0: return 0.0
        q=risk_cash/per_unit
        max_notional=equity*self.max_notional_fraction*self.max_leverage
        q=min(q,max_notional/entry)
        return max(0.0,q)
