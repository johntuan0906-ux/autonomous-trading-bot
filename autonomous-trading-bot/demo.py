"""Demo offline: chay bot voi du lieu gia lap (khong can API key, khong can mang)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from bot import TradingBot
from config import Settings
from exchange import BinanceFutures


def make_trend(start: float, step: float, n: int = 250, noise: float = 20.0,
               seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = [start + i * step + rng.normal(0, noise) for i in range(n)]
    return pd.DataFrame({
        "open": [c - 5 for c in closes],
        "high": [c + 25 for c in closes],
        "low": [c - 25 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


def main() -> None:
    cfg = Settings()  # DRY_RUN mac dinh True
    bot = TradingBot(cfg, exchange=BinanceFutures(dry_run=True))
    # Gia lap macro bullish nhe de bot co co hoi mo lenh
    bot.sentiment.get = lambda token="": type(
        "S", (), {"score": 0.6, "n_articles": 10, "headlines": []})()

    bull = make_trend(30000, 15, seed=7)     # BTC: uptrend
    bear = make_trend(34000, -15, seed=11)   # cac coin con lai: downtrend
    provider = lambda s: bull if s.startswith("BTC") else bear  # noqa: E731

    print("=== STEP 1 (du kien OPENED LONG BTC) ===")
    print(bot.step(candles_provider=provider))
    print("=== STEP 2 (du kien BLOCKED - single best setup) ===")
    print(bot.step(candles_provider=provider))


if __name__ == "__main__":
    main()
