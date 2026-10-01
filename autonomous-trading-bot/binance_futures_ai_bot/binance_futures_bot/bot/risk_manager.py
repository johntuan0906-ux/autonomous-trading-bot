"""
Quản trị rủi ro: tính khối lượng lệnh theo % vốn chấp nhận rủi ro, tính
SL/TP theo ATR, và các cơ chế "ngắt mạch" (circuit breaker) để tự động
giới hạn thiệt hại — quan trọng vì bot chạy HOÀN TOÀN TỰ ĐỘNG, không có
người xác nhận từng lệnh.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("futures_bot.risk")


class RiskManager:
    def __init__(self, cfg: dict):
        self.risk_per_trade_pct = cfg["risk_per_trade_pct"]
        self.max_concurrent_positions = cfg["max_concurrent_positions"]
        self.max_daily_loss_pct = cfg["max_daily_loss_pct"]
        self.sl_atr_mult = cfg["sl_atr_multiplier"]
        self.tp_atr_mult = cfg["tp_atr_multiplier"]
        self.cooldown_minutes = cfg["cooldown_minutes_after_close"]

        self._day = None
        self._start_of_day_equity = None
        self._cooldowns = {}   # symbol -> datetime hết cooldown (UTC)
        self.trading_halted_today = False

    def refresh_day(self, current_equity: float):
        today = datetime.now(timezone.utc).date()
        if today != self._day or self._start_of_day_equity is None:
            self._day = today
            self._start_of_day_equity = current_equity
            self.trading_halted_today = False
            logger.info(f"Reset ngắt mạch ngày mới. Vốn đầu ngày: {current_equity:.2f} USDT")

    def check_daily_circuit_breaker(self, current_equity: float) -> bool:
        """True nếu ĐƯỢC PHÉP mở lệnh mới, False nếu đã chạm giới hạn lỗ ngày."""
        if not self._start_of_day_equity:
            return True
        loss_pct = (self._start_of_day_equity - current_equity) / self._start_of_day_equity * 100
        if loss_pct >= self.max_daily_loss_pct:
            if not self.trading_halted_today:
                logger.warning(
                    f"NGẮT MẠCH: lỗ trong ngày {loss_pct:.2f}% >= giới hạn "
                    f"{self.max_daily_loss_pct}%. Tạm dừng mở lệnh mới đến hết ngày "
                    f"(vị thế đang mở vẫn được quản lý bình thường)."
                )
            self.trading_halted_today = True
            return False
        return True

    def set_cooldown(self, symbol: str):
        self._cooldowns[symbol] = datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)

    def in_cooldown(self, symbol: str) -> bool:
        until = self._cooldowns.get(symbol)
        return bool(until and datetime.now(timezone.utc) < until)

    def calc_position_size(self, equity: float, entry_price: float, sl_price: float) -> float:
        """Khối lượng (đơn vị base asset) sao cho nếu SL bị chạm, mức lỗ
        đúng bằng risk_per_trade_pct% vốn hiện có."""
        risk_amount = equity * (self.risk_per_trade_pct / 100.0)
        stop_distance = abs(entry_price - sl_price)
        if stop_distance <= 0:
            return 0.0
        return risk_amount / stop_distance

    def calc_sl_tp(self, side: str, entry_price: float, atr_value: float):
        if atr_value <= 0:
            atr_value = entry_price * 0.005  # phòng hờ ATR=0 (dữ liệu quá phẳng)
        if side == "LONG":
            return entry_price - self.sl_atr_mult * atr_value, entry_price + self.tp_atr_mult * atr_value
        return entry_price + self.sl_atr_mult * atr_value, entry_price - self.tp_atr_mult * atr_value
