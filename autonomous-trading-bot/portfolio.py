"""Non-overlapping position manager: never duplicate a symbol, max 1 best setup
(or optional opposite-direction hedge on different symbols)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    symbol: str
    direction: str  # LONG | SHORT
    entry: float
    qty: float
    sl: float
    tp: float


def planned_risk_usd(entry: float, sl: float, qty: float) -> float:
    """Risk du kien (USDT) neu gia cham SL: |entry - SL| x qty."""
    if entry <= 0 or qty <= 0:
        return 0.0
    return abs(float(entry) - float(sl)) * abs(float(qty))


def total_risk_pct(positions: dict, equity: float,
                   initial_sl: dict | None = None) -> float:
    """Tong risk dang mo (% equity) theo SL BAN DAU (1R) — dung moc 1R de khong
    bi danh lua khi SL da doi ve hoa von (BE lam risk hien tai = 0 nhung risk that
    cua lenh van la khoang entry -> SL ban dau)."""
    if equity <= 0 or not positions:
        return 0.0
    sl0 = initial_sl or {}
    tot = 0.0
    for sym, p in positions.items():
        sl = float(sl0.get(sym) or getattr(p, "sl", 0.0) or 0.0)
        tot += planned_risk_usd(p.entry, sl, p.qty)
    return 100.0 * tot / float(equity)


def can_add_risk(positions: dict, equity: float, cap_pct: float,
                 new_risk_usd: float, initial_sl: dict | None = None) -> tuple:
    """Co duoc mo them 1 lenh risk `new_risk_usd` khong? Tra (ok, ly do).

    P0-6: chan truoc khi tong risk vuot tran (vi du 4 vi the x 1% > 2% lo ngay).
    """
    cur = total_risk_pct(positions, equity, initial_sl)
    add = 100.0 * max(new_risk_usd, 0.0) / max(float(equity), 1e-9)
    if cur + add > cap_pct + 1e-9:
        return False, (f"tran risk danh muc: dang {cur:.2f}% + moi {add:.2f}% > "
                       f"{cap_pct:.2f}% (MAX_TOTAL_RISK_PCT)")
    return True, "ok"


@dataclass
class PortfolioManager:
    max_positions: int = 1
    allow_hedge_opposite: bool = False
    positions: dict = field(default_factory=dict)  # symbol -> Position

    def can_open(self, symbol: str, direction: str) -> tuple[bool, str]:
        if symbol in self.positions:
            return False, f"duplicate blocked: {symbol} already open"
        if len(self.positions) >= self.max_positions:
            return False, f"max positions {self.max_positions} reached"
        if self.positions and not self.allow_hedge_opposite:
            # Single Best Setup: only 1 position at a time, period.
            open_sym = next(iter(self.positions))
            return False, f"single-best-setup: {open_sym} already open"
        if self.allow_hedge_opposite:
            for p in self.positions.values():
                if p.direction == direction:
                    return False, f"same-direction risk blocked ({direction})"
        return True, "ok"

    def open(self, pos: Position) -> None:
        ok, reason = self.can_open(pos.symbol, pos.direction)
        if not ok:
            raise RuntimeError(reason)
        self.positions[pos.symbol] = pos

    def close(self, symbol: str) -> Position | None:
        return self.positions.pop(symbol, None)

    def check_exit(self, symbol: str, price: float) -> str | None:
        """Return 'SL' | 'TP' | None based on current price."""
        p = self.positions.get(symbol)
        if not p:
            return None
        if p.direction == "LONG":
            if price <= p.sl:
                return "SL"
            if price >= p.tp:
                return "TP"
        else:
            if price >= p.sl:
                return "SL"
            if price <= p.tp:
                return "TP"
        return None
