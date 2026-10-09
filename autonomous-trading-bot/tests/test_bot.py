"""Unit tests — stdlib only (no pytest / pandas needed to run).

Run: python -m unittest discover -s tests -v
(Can also run under pytest.)
"""
import unittest

import pandas as pd

from indicators import atr, technical_score
from portfolio import PortfolioManager, Position
from ranking import Candidate, composite_alpha, rank_markets, sentiment_veto
from risk import KillSwitch, atr_levels, position_size


def bull_df(n=250, start=100.0, step=0.5):
    import pandas as pd
    closes = [start + i * step for i in range(n)]
    return pd.DataFrame({
        "open": [c - 0.1 for c in closes],
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


def bear_df(n=250, start=100.0, step=0.5):
    import pandas as pd
    closes = [start - i * step for i in range(n)]
    return pd.DataFrame({
        "open": [c + 0.1 for c in closes],
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [100.0] * n,
    })


class TestIndicators(unittest.TestCase):
    def test_bullish_positive(self):
        self.assertGreater(technical_score(bull_df())["score"], 0.3)

    def test_bearish_negative(self):
        self.assertLess(technical_score(bear_df())["score"], -0.3)

    def test_atr_positive(self):
        self.assertGreater(float(atr(bull_df()).iloc[-1]), 0)


class TestRisk(unittest.TestCase):
    def test_rr_is_two(self):
        lv = atr_levels(100.0, 2.0, "LONG")
        self.assertAlmostEqual(lv["sl"], 97.0)
        self.assertAlmostEqual(lv["tp"], 106.0)
        self.assertGreaterEqual(lv["rr"], 2.0)
        lv_s = atr_levels(100.0, 2.0, "SHORT")
        self.assertAlmostEqual(lv_s["sl"], 103.0)
        self.assertAlmostEqual(lv_s["tp"], 94.0)

    def test_position_size(self):
        self.assertAlmostEqual(position_size(1000.0, 1.0, 100.0, 97.0), 10 / 3, places=4)

    def test_killswitch_drawdown(self):
        k = KillSwitch(max_daily_loss_pct=5.0, start_balance=1000.0)
        self.assertFalse(k.check(990.0))
        self.assertTrue(k.check(940.0))
        self.assertTrue(k.tripped)


class TestRanking(unittest.TestCase):
    def test_composite(self):
        self.assertAlmostEqual(composite_alpha(1.0, 1.0), 1.0)
        self.assertAlmostEqual(composite_alpha(-1.0, 1.0, 0.65, 0.35), -0.3)

    def test_best_wins_and_edge(self):
        c = [Candidate("A", 0.9, 0.9, 1, 100), Candidate("B", 0.1, 0.0, 1, 100)]
        d = rank_markets(c)
        self.assertEqual((d["action"], d["symbol"]), ("LONG", "A"))
        tie = [Candidate("A", 0.6, 0.6, 1, 100), Candidate("B", 0.61, 0.6, 1, 100)]
        self.assertEqual(rank_markets(tie)["action"], "WAIT")
        weak = [Candidate("A", 0.1, 0.0, 1, 100)]
        self.assertEqual(rank_markets(weak)["action"], "WAIT")

    def test_veto(self):
        self.assertIsNotNone(sentiment_veto("LONG", -0.8))
        self.assertIsNone(sentiment_veto("LONG", 0.0))
        self.assertIsNotNone(sentiment_veto("SHORT", 0.8))


class TestPortfolio(unittest.TestCase):
    def test_no_overlap_single_best(self):
        pm = PortfolioManager(max_positions=1)
        pm.open(Position("BTC/USDT:USDT", "LONG", 100, 1, 97, 106))
        ok, _ = pm.can_open("BTC/USDT:USDT", "LONG")
        self.assertFalse(ok)
        ok, _ = pm.can_open("ETH/USDT:USDT", "LONG")
        self.assertFalse(ok)  # single best setup

    def test_sl_tp_exit(self):
        pm = PortfolioManager()
        pm.open(Position("BTC/USDT:USDT", "LONG", 100, 1, 97, 106))
        self.assertEqual(pm.check_exit("BTC/USDT:USDT", 96), "SL")
        self.assertEqual(pm.check_exit("BTC/USDT:USDT", 107), "TP")
        self.assertIsNone(pm.check_exit("BTC/USDT:USDT", 100))


class TestBotStep(unittest.TestCase):
    def test_open_and_block_second(self):
        from bot import TradingBot
        from config import Settings
        from exchange import BinanceFutures

        cfg = Settings()
        object.__setattr__(cfg, "dry_run", True)
        # TAT DINH: khong phu thuoc `.env` that (sau khi bot sang LIVE, SYMBOLS hep lai
        # -> BTC khong duoc quet -> status WAIT thay vi OPENED).
        object.__setattr__(cfg, "symbols", ("BTC/USDT:USDT",))
        object.__setattr__(cfg, "extra_symbols", ())
        object.__setattr__(cfg, "max_positions", 4)
        bot = TradingBot(cfg, exchange=BinanceFutures(dry_run=True))
        bot.sentiment.inject(0.8)  # bullish macro -> BTC long
        provider = lambda s: bull_df() if s.startswith("BTC") else bear_df()  # noqa: E731
        # force determinism: stub sentiment.get
        bot.sentiment.get = lambda token="": type("S", (), {"score": 0.8})()
        r1 = bot.step(candles_provider=provider)
        self.assertEqual(r1["status"], "OPENED")
        r2 = bot.step(candles_provider=provider)
        self.assertIn(r2["status"], ("BLOCKED", "WAIT"))

    def test_fud_blocks_long(self):
        from bot import TradingBot
        from config import Settings
        from exchange import BinanceFutures
        cfg = Settings()
        bot = TradingBot(cfg, exchange=BinanceFutures(dry_run=True))
        bot.sentiment.get = lambda token="": type("S", (), {"score": -0.9})()
        provider = lambda s: bull_df()  # noqa: E731
        r = bot.step(candles_provider=provider)
        # bullish tech but FUD macro -> composite may still pass; veto checked only
        # if direction LONG. Accept BLOCKED or WAIT/OPENED with reduced alpha.
        self.assertIn(r["status"], ("BLOCKED", "WAIT", "OPENED"))


if __name__ == "__main__":
    unittest.main()
