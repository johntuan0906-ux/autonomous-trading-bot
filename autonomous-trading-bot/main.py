"""Entry point: python main.py [--once]."""
import sys

from bot import TradingBot
from config import Settings


def main() -> None:
    cfg = Settings()
    bot = TradingBot(cfg)
    if "--once" in sys.argv:
        print(bot.step())
    else:
        bot.run_forever()


if __name__ == "__main__":
    main()
