"""
Điều phối việc mở/đóng lệnh: kết hợp tín hiệu (SignalEngine), quản trị
rủi ro (RiskManager) và sàn giao dịch (ExchangeClient) thành hành động
giao dịch thực tế — hoàn toàn tự động, không cần xác nhận thủ công.
"""
import logging

logger = logging.getLogger("futures_bot.executor")


class TradeExecutor:
    def __init__(self, exchange, risk_manager, position_manager,
                 leverage: int, margin_type: str, notifier=None):
        self.exchange = exchange
        self.risk = risk_manager
        self.positions = position_manager
        self.leverage = leverage
        self.margin_type = margin_type
        self.notifier = notifier

    def open_trade(self, signal, equity: float):
        symbol = signal.symbol
        side = signal.action  # "LONG" hoặc "SHORT"
        entry_price = signal.price

        sl_price, tp_price = self.risk.calc_sl_tp(side, entry_price, signal.atr)
        qty = self.risk.calc_position_size(equity, entry_price, sl_price)
        if qty <= 0:
            logger.warning(f"[{symbol}] Khối lượng tính được = 0, bỏ qua lệnh.")
            return

        self.exchange.set_leverage(symbol, self.leverage)
        self.exchange.set_margin_type(symbol, self.margin_type)

        entry_side = "BUY" if side == "LONG" else "SELL"
        close_side = "SELL" if side == "LONG" else "BUY"

        logger.info(
            f"[{symbol}] MỞ {side} | điểm tín hiệu={signal.score:.2f} "
            f"(kỹ thuật={signal.technical_score:.2f}, tin tức={signal.news_score:.2f}) "
            f"| giá~{entry_price:.4f} SL={sl_price:.4f} TP={tp_price:.4f} qty={qty:.6f}"
        )

        self.exchange.open_market_position(symbol, entry_side, qty)
        self.exchange.place_stop_loss(symbol, close_side, sl_price)
        self.exchange.place_take_profit(symbol, close_side, tp_price)

        if self.notifier:
            self.notifier.send(
                f"🟢 MỞ {side} {symbol}\nGiá vào ~{entry_price:.4f}\n"
                f"SL: {sl_price:.4f} | TP: {tp_price:.4f}\nĐiểm tín hiệu: {signal.score:.2f}"
            )

    def close_trade(self, symbol: str, reason: str = ""):
        logger.info(f"[{symbol}] ĐÓNG vị thế. Lý do: {reason}")
        self.exchange.close_position_market(symbol)
        self.risk.set_cooldown(symbol)
        if self.notifier:
            self.notifier.send(f"🔴 ĐÓNG lệnh {symbol}\nLý do: {reason}")

    def check_signal_reversal_exit(self, symbol: str, signal, position: dict) -> bool:
        """Thoát sớm (bổ sung, KHÔNG thay thế SL/TP cứng đã đặt sẵn trên
        sàn) nếu tín hiệu đảo chiều mạnh và ngược hẳn với vị thế đang giữ."""
        current_side = position["side"]
        if current_side == "LONG" and signal.action == "SHORT":
            self.close_trade(symbol, "Tín hiệu đảo chiều sang SHORT")
            return True
        if current_side == "SHORT" and signal.action == "LONG":
            self.close_trade(symbol, "Tín hiệu đảo chiều sang LONG")
            return True
        return False
