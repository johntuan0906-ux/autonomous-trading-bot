from binance_futures_ai_bot.config import load_config
from binance_futures_ai_bot.engine import TradingEngine

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    TradingEngine(cfg).run_forever()
