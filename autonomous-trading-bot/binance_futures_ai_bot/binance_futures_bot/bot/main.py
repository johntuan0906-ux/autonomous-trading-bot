"""
Vòng lặp chính của bot: định kỳ quét các cặp cấu hình trong config.yaml
(mặc định BTCUSDT/ETHUSDT/SOLUSDT/XRPUSDT), so sánh tín hiệu, và TỰ ĐỘNG
vào/thoát lệnh mà KHÔNG cần xác nhận thủ công.

CẢNH BÁO: Đây là phần mềm giao dịch FUTURES CÓ ĐÒN BẨY, chạy tự động
hoàn toàn. Đọc kỹ README.md trước khi đặt USE_TESTNET=false hoặc
DRY_RUN=false (tức là dùng tiền thật). Đây không phải lời khuyên đầu tư
và không có gì đảm bảo chiến lược này sinh lời.
"""
import logging
import signal as signal_module
import time

from bot.config_loader import load_config
from bot.exchange_client import ExchangeClient
from bot.indicators import compute_technical_score, klines_to_dataframe
from bot.logger_setup import setup_logger
from bot.news_sentiment import NewsSentimentEngine
from bot.notifier import TelegramNotifier
from bot.position_manager import PositionManager
from bot.risk_manager import RiskManager
from bot.signal_engine import evaluate_signal, rank_signals
from bot.trade_executor import TradeExecutor

_running = True


def _handle_shutdown(signum, frame):
    global _running
    logging.getLogger("futures_bot").info("Nhận tín hiệu dừng, đang thoát an toàn...")
    _running = False


def _evaluate_symbol(symbol, cfg, exchange, news_engine, logger):
    """Lấy dữ liệu + tính tín hiệu tổng hợp cho 1 symbol. Trả về None nếu lỗi
    (để 1 symbol lỗi không làm sập cả chu kỳ)."""
    try:
        klines = exchange.get_klines(symbol, cfg["timeframe"], cfg["lookback_candles"])
        df = klines_to_dataframe(klines)
        tech = compute_technical_score(df, cfg["indicators"])
        news_score = news_engine.get_score(symbol)
        return evaluate_signal(symbol, tech, news_score, cfg["signal"])
    except Exception as e:
        logger.exception(f"[{symbol}] Lỗi khi tính tín hiệu: {e}")
        return None


def run_cycle(cfg, exchange, news_engine, risk, positions, executor, logger):
    equity = exchange.get_account_equity()
    risk.refresh_day(equity)
    positions.sync_from_exchange(exchange)

    # 1) Quản lý các vị thế đang mở TRƯỚC (ưu tiên bảo vệ vốn đang có).
    #    SL/TP cứng đã nằm sẵn trên sàn; đây chỉ là lớp thoát sớm bổ sung
    #    khi tín hiệu đảo chiều mạnh.
    for symbol in positions.open_symbols():
        position = positions.get_position(symbol)
        signal = _evaluate_symbol(symbol, cfg, exchange, news_engine, logger)
        if signal:
            executor.check_signal_reversal_exit(symbol, signal, position)

    # 2) Nếu còn "chỗ trống" và chưa bị ngắt mạch -> tìm cơ hội mới
    positions.sync_from_exchange(exchange)  # cập nhật lại nếu bước 1 vừa đóng lệnh
    can_trade = risk.check_daily_circuit_breaker(equity)
    free_slots = positions.free_slots(cfg["risk"]["max_concurrent_positions"])

    if can_trade and free_slots > 0:
        candidates = positions.available_symbols(risk)
        signals = [
            s for s in (
                _evaluate_symbol(sym, cfg, exchange, news_engine, logger) for sym in candidates
            ) if s is not None
        ]

        # So sánh thị trường: xếp hạng các cặp theo độ mạnh tín hiệu, ưu
        # tiên tín hiệu mạnh nhất khi số lệnh mở đồng thời bị giới hạn.
        for signal in rank_signals(signals):
            if free_slots <= 0:
                break
            executor.open_trade(signal, equity)
            free_slots -= 1
    elif not can_trade:
        logger.info("Đang tạm dừng mở lệnh mới do ngắt mạch lỗ ngày.")
    else:
        logger.info("Đã đạt số lệnh mở đồng thời tối đa, chờ chu kỳ sau.")


def run():
    cfg = load_config()
    logger = setup_logger("futures_bot", cfg)

    logger.info("=" * 60)
    logger.info("KHỞI ĐỘNG BOT GIAO DỊCH FUTURES TỰ ĐỘNG")
    logger.info(f"Cặp giao dịch: {cfg['symbols']}")
    logger.info(
        f"Testnet: {cfg['env']['use_testnet']} | Dry-run: {cfg['env']['dry_run']} "
        f"| Đòn bẩy: {cfg['exchange']['leverage']}x"
    )
    if not cfg["env"]["use_testnet"] and not cfg["env"]["dry_run"]:
        logger.warning(
            "!!! ĐANG CHẠY VỚI TIỀN THẬT TRÊN MAINNET (USE_TESTNET=false, DRY_RUN=false) !!!"
        )
    logger.info("=" * 60)

    exchange = ExchangeClient(
        cfg["env"]["api_key"], cfg["env"]["api_secret"],
        testnet=cfg["env"]["use_testnet"], dry_run=cfg["env"]["dry_run"],
    )
    exchange.ensure_one_way_mode()

    news_engine = NewsSentimentEngine(cfg["news"], cfg["env"])
    risk = RiskManager(cfg["risk"])
    positions = PositionManager(cfg["symbols"])
    notifier = TelegramNotifier(cfg["env"]["telegram_bot_token"], cfg["env"]["telegram_chat_id"])
    executor = TradeExecutor(
        exchange, risk, positions,
        leverage=cfg["exchange"]["leverage"], margin_type=cfg["exchange"]["margin_type"],
        notifier=notifier,
    )

    signal_module.signal(signal_module.SIGINT, _handle_shutdown)
    signal_module.signal(signal_module.SIGTERM, _handle_shutdown)

    interval = cfg["cycle_interval_seconds"]
    while _running:
        cycle_start = time.time()
        try:
            run_cycle(cfg, exchange, news_engine, risk, positions, executor, logger)
        except Exception as e:
            # Không để 1 lỗi bất ngờ làm dừng hẳn bot — log lại và tiếp tục ở chu kỳ sau.
            logger.exception(f"Lỗi không mong muốn trong chu kỳ chạy: {e}")

        elapsed = time.time() - cycle_start
        sleep_time = max(0, interval - elapsed)
        logger.info(f"Chu kỳ hoàn tất trong {elapsed:.1f}s, nghỉ {sleep_time:.1f}s.")
        for _ in range(int(sleep_time)):
            if not _running:
                break
            time.sleep(1)

    logger.info("Bot đã dừng.")


if __name__ == "__main__":
    run()
