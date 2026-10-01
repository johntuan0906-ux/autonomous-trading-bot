"""
Lớp bọc (wrapper) quanh python-binance để thao tác với Binance USDⓈ-M Futures.
Mọi lệnh thật sự gửi lên sàn đều đi qua đây, và đều tôn trọng cờ DRY_RUN.

LƯU Ý QUAN TRỌNG: Kể từ 2025-12-09, Binance yêu cầu các lệnh điều kiện
(STOP_MARKET, TAKE_PROFIT_MARKET, STOP, TAKE_PROFIT, TRAILING_STOP_MARKET)
phải đặt qua Algo Order API (/fapi/v1/algoOrder) thay vì endpoint lệnh
thường (/fapi/v1/order) — endpoint cũ sẽ trả lỗi -4120 cho các loại lệnh
này. Module này dùng client.futures_create_algo_order(...) cho SL/TP,
và futures_create_order(...) (endpoint thường) chỉ cho lệnh MARKET
vào/thoát vị thế (không bị ảnh hưởng bởi thay đổi trên).
"""
import logging
from decimal import Decimal

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

logger = logging.getLogger("futures_bot.exchange")


class ExchangeClient:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True, dry_run: bool = True):
        self.dry_run = dry_run
        self.testnet = testnet
        self._symbol_filters_cache = {}

        if not api_key or not api_secret:
            logger.warning("Thiếu API key/secret — chỉ có thể chạy ở chế độ mô phỏng (DRY_RUN).")
            self.client = None
            return

        self.client = Client(api_key, api_secret, testnet=testnet)
        logger.info(
            "Đang kết nối tới Binance Futures %s.",
            "TESTNET" if testnet else "MAINNET (tiền thật)",
        )

    # ---------------- Thiết lập tài khoản ----------------
    def ensure_one_way_mode(self):
        """Đảm bảo tài khoản ở chế độ One-way (không phải Hedge Mode), để logic
        đặt lệnh trong bot (không set positionSide) hoạt động đúng."""
        if not self.client:
            return
        try:
            mode = self.client.futures_get_position_mode()
            if mode.get("dualSidePosition"):
                self.client.futures_change_position_mode(dualSidePosition="false")
                logger.info("Đã chuyển sang chế độ One-way Position Mode.")
        except BinanceAPIException as e:
            # -4067/-4068: không đổi được vì đang có lệnh/vị thế mở -> bỏ qua an toàn
            logger.warning(f"Không thể kiểm tra/đổi position mode: {e}")

    def set_leverage(self, symbol: str, leverage: int):
        if not self.client:
            return
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
        except BinanceAPIException as e:
            logger.warning(f"[{symbol}] Không thể đổi leverage: {e}")

    def set_margin_type(self, symbol: str, margin_type: str):
        if not self.client:
            return
        try:
            self.client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
        except BinanceAPIException as e:
            if getattr(e, "code", None) != -4046:  # -4046 = đã đúng margin type sẵn rồi
                logger.warning(f"[{symbol}] Không thể đổi margin type: {e}")

    # ---------------- Dữ liệu thị trường ----------------
    def get_klines(self, symbol: str, interval: str, limit: int = 300):
        if not self.client:
            raise RuntimeError("Chưa kết nối tới Binance (thiếu API key).")
        return self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)

    def get_account_equity(self) -> float:
        if not self.client:
            return 0.0
        acc = self.client.futures_account()
        return float(acc["totalWalletBalance"])

    def get_open_position(self, symbol: str):
        """Trả về dict vị thế đang mở cho symbol, hoặc None nếu không có.
        Đây là nguồn sự thật duy nhất — bot luôn hỏi lại sàn, không tự suy đoán."""
        if not self.client:
            return None
        positions = self.client.futures_position_information(symbol=symbol)
        for p in positions:
            amt = float(p["positionAmt"])
            if abs(amt) > 1e-12:
                return {
                    "symbol": symbol,
                    "amount": amt,
                    "entry_price": float(p["entryPrice"]),
                    "unrealized_pnl": float(p["unRealizedProfit"]),
                    "side": "LONG" if amt > 0 else "SHORT",
                }
        return None

    # ---------------- Làm tròn số lượng / giá theo luật sàn ----------------
    def _get_symbol_filters(self, symbol: str) -> dict:
        if symbol in self._symbol_filters_cache:
            return self._symbol_filters_cache[symbol]
        if not self.client:
            return {"stepSize": 0.001, "minQty": 0.001, "tickSize": 0.01}

        info = self.client.futures_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                filters = {f["filterType"]: f for f in s["filters"]}
                result = {
                    "stepSize": float(filters["LOT_SIZE"]["stepSize"]),
                    "minQty": float(filters["LOT_SIZE"]["minQty"]),
                    "tickSize": float(filters["PRICE_FILTER"]["tickSize"]),
                }
                self._symbol_filters_cache[symbol] = result
                return result
        raise ValueError(f"Không tìm thấy thông tin symbol {symbol} trên sàn.")

    @staticmethod
    def _round_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        d_value, d_step = Decimal(str(value)), Decimal(str(step))
        return float((d_value // d_step) * d_step)

    def round_qty(self, symbol: str, qty: float) -> float:
        f = self._get_symbol_filters(symbol)
        return max(self._round_step(qty, f["stepSize"]), f["minQty"])

    def round_price(self, symbol: str, price: float) -> float:
        f = self._get_symbol_filters(symbol)
        return self._round_step(price, f["tickSize"])

    # ---------------- Đặt lệnh vào/thoát vị thế (MARKET — endpoint thường) ----------------
    def open_market_position(self, symbol: str, side: str, quantity: float):
        """side: 'BUY' (mở LONG) hoặc 'SELL' (mở SHORT)."""
        qty = self.round_qty(symbol, quantity)
        if self.dry_run or not self.client:
            logger.info(f"[DRY_RUN] Sẽ mở lệnh MARKET {side} {qty} {symbol}")
            return {"dry_run": True, "symbol": symbol, "side": side, "qty": qty}
        try:
            order = self.client.futures_create_order(
                symbol=symbol, side=side, type="MARKET", quantity=qty
            )
            logger.info(f"[{symbol}] Đã mở lệnh {side} MARKET, qty={qty}")
            return order
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error(f"[{symbol}] Lỗi khi mở lệnh MARKET: {e}")
            raise

    def close_position_market(self, symbol: str):
        pos = self.get_open_position(symbol)
        if not pos:
            return None
        close_side = "SELL" if pos["side"] == "LONG" else "BUY"
        qty = abs(pos["amount"])
        if self.dry_run or not self.client:
            logger.info(f"[DRY_RUN] Sẽ đóng vị thế {symbol} ({pos['side']}, qty={qty})")
            return {"dry_run": True}
        try:
            order = self.client.futures_create_order(
                symbol=symbol, side=close_side, type="MARKET",
                quantity=qty, reduceOnly="true",
            )
            self.cancel_all_algo_orders(symbol)
            return order
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error(f"[{symbol}] Lỗi khi đóng vị thế: {e}")
            raise

    # ---------------- SL/TP — bắt buộc qua Algo Order API (từ 2025-12-09) ----------------
    def place_stop_loss(self, symbol: str, close_side: str, stop_price: float):
        """close_side: 'SELL' để đóng LONG, 'BUY' để đóng SHORT."""
        price = self.round_price(symbol, stop_price)
        if self.dry_run or not self.client:
            logger.info(f"[DRY_RUN] Sẽ đặt SL (STOP_MARKET) {close_side} {symbol} @ {price}")
            return {"dry_run": True}
        try:
            return self.client.futures_create_algo_order(
                algoType="CONDITIONAL",
                symbol=symbol,
                side=close_side,
                type="STOP_MARKET",
                triggerPrice=price,
                closePosition="true",
                workingType="MARK_PRICE",
                priceProtect="true",
            )
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error(f"[{symbol}] Lỗi khi đặt SL: {e}")
            raise

    def place_take_profit(self, symbol: str, close_side: str, tp_price: float):
        price = self.round_price(symbol, tp_price)
        if self.dry_run or not self.client:
            logger.info(f"[DRY_RUN] Sẽ đặt TP (TAKE_PROFIT_MARKET) {close_side} {symbol} @ {price}")
            return {"dry_run": True}
        try:
            return self.client.futures_create_algo_order(
                algoType="CONDITIONAL",
                symbol=symbol,
                side=close_side,
                type="TAKE_PROFIT_MARKET",
                triggerPrice=price,
                closePosition="true",
                workingType="MARK_PRICE",
                priceProtect="true",
            )
        except (BinanceAPIException, BinanceOrderException) as e:
            logger.error(f"[{symbol}] Lỗi khi đặt TP: {e}")
            raise

    def cancel_all_algo_orders(self, symbol: str):
        """Huỷ mọi lệnh SL/TP (algo order) còn treo trên symbol — gọi sau khi
        đóng vị thế thủ công để tránh lệnh mồ côi kích hoạt sai."""
        if self.dry_run or not self.client:
            return
        try:
            self.client.futures_cancel_all_algo_open_orders(symbol=symbol)
        except BinanceAPIException as e:
            logger.warning(f"[{symbol}] Không thể huỷ algo order đang treo: {e}")

    def cancel_all_orders(self, symbol: str):
        """Huỷ mọi lệnh thường (không phải algo) còn treo — phòng hờ, ví dụ
        lệnh LIMIT bị kẹt."""
        if self.dry_run or not self.client:
            return
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
        except BinanceAPIException as e:
            logger.warning(f"[{symbol}] Không thể huỷ lệnh thường đang treo: {e}")
