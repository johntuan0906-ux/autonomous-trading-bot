"""Unit tests cho trade_mgmt / strategy / backtest (bo sung 2025).

Dung unittest.TestCase cho dong bo voi tests/test_bot.py.
"""
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest import VARIANTS, build_signals, simulate, stats, verdict  # noqa: E402
from strategy import bump, classify_strategy, report  # noqa: E402
from trade_mgmt import (manage, manage_trade, new_trade,  # noqa: E402
                        r_multiple, trade_result)


def _df(n=300, drift=0.0015, vol=0.004):
    """Sinh du lieu OHLCV gia lap co xu huong (seeded -> deterministic)."""
    import random
    random.seed(7)
    px = 100.0
    rows = []
    for i in range(n):
        px *= (1 + drift + random.uniform(-vol, vol))
        rows.append({"ts": pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=5 * i),
                     "open": px * 0.999, "high": px * (1 + vol),
                     "low": px * (1 - vol), "close": px,
                     "volume": 100 + random.random() * 50})
    return pd.DataFrame(rows)


class TestTradeMgmt(unittest.TestCase):
    def test_r_multiple_basic(self):
        self.assertAlmostEqual(r_multiple("LONG", 100, 98, 104), 2.0, places=9)
        self.assertAlmostEqual(r_multiple("SHORT", 100, 102, 96), 2.0, places=9)
        self.assertEqual(r_multiple("LONG", 100, 100, 105), 0.0)

    def test_hold_when_inside_range(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        self.assertEqual(manage(t, 100.5, 2.0)["action"], "HOLD")

    def test_partial_and_breakeven_at_1r(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        mg = manage(t, 102.0, 2.0)
        self.assertEqual(mg["action"], "PARTIAL")
        self.assertAlmostEqual(mg["close_qty"], 0.5, places=9)
        self.assertGreater(mg["new_sl"], 100.0)      # SL ve hoa von + phi
        self.assertTrue(t.partial_done and t.be_done)

    def test_partial_win_still_counts_won(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        manage(t, 102.0, 2.0)                        # chot 1 nua tai 1R
        res = trade_result(t, "SL", 100.05)          # phan con lai bi day ve BE
        self.assertTrue(res["won"])
        self.assertGreater(res["pnl"], 0)
        self.assertTrue(res["partial_done"])

    def test_exit_sl_before_tp(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        self.assertEqual(manage(t, 97.5, 2.0)["action"], "EXIT_SL")
        t2 = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        self.assertEqual(manage(t2, 106.5, 2.0)["action"], "EXIT_TP")

    def test_exit_sl_tp_short(self):
        t = new_trade("ETHUSDT", "SHORT", 100, 2, 102, 96)
        self.assertEqual(manage(t, 102.5, 2.0)["action"], "EXIT_SL")
        t2 = new_trade("ETHUSDT", "SHORT", 100, 2, 102, 96)
        self.assertEqual(manage(t2, 95.5, 2.0)["action"], "EXIT_TP")

    def test_trailing_after_partial(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 120)
        manage(t, 102.5, 2.0)                        # partial + BE
        sl_before = t.sl
        mg = manage(t, 105.0, 2.0, trail_atr_mult=1.0)
        self.assertEqual(mg["action"], "TRAIL")
        self.assertGreater(t.sl, sl_before)
        self.assertAlmostEqual(t.sl, 103.0, places=9)

    def test_breakeven_without_partial(self):
        t = new_trade("SOLUSDT", "SHORT", 100, 1, 103, 90)
        mg = manage(t, 96.5, 3.0, partial_at_r=0.0, be_at_r=1.0)
        self.assertEqual(mg["action"], "BE")
        self.assertLess(t.sl, 100.0)
        self.assertGreaterEqual(t.sl, 99.8)

    def test_manage_trade_reads_env(self):
        t = new_trade("BTCUSDT", "LONG", 100, 1, 98, 106)
        mg = manage_trade(t, 101.0, 2.0,
                          env={"PARTIAL_AT_R": "0.5", "PARTIAL_PCT": "0.5",
                               "BE_AT_R": "0.5", "TRAIL_ATR_MULT": "1.0"})
        self.assertEqual(mg["action"], "PARTIAL")

    def test_trade_result_pnl_signs(self):
        win = new_trade("XRPUSDT", "LONG", 1.0, 1000, 0.98, 1.04)
        r1 = trade_result(win, "TP", 1.04)
        self.assertGreater(r1["pnl"], 0)
        self.assertTrue(r1["won"])
        loss = new_trade("XRPUSDT", "LONG", 1.0, 1000, 0.98, 1.04)
        r2 = trade_result(loss, "SL", 0.98)
        self.assertLess(r2["pnl"], 0)
        self.assertFalse(r2["won"])
        self.assertAlmostEqual(r2["r"], -1.0, delta=0.05)


class TestStrategy(unittest.TestCase):
    def test_classify_trend_pullback(self):
        self.assertEqual(
            classify_strategy("LONG", regime="UPTREND", struct=1.0, htf=1, rsi=55),
            "A_TREND_PULLBACK")

    def test_classify_breakout_retest(self):
        self.assertEqual(
            classify_strategy("SHORT", regime="UPTREND", bos="BOS_DOWN",
                              retest=True, struct=-1.0, rsi=45),
            "B_BREAKOUT_RETEST")

    def test_classify_liq_sweep(self):
        self.assertEqual(
            classify_strategy("LONG", sweep=True, sweep_bias=0.6, struct=0.5),
            "C_LIQ_SWEEP_RECLAIM")

    def test_classify_range_reversal(self):
        self.assertEqual(
            classify_strategy("LONG", regime="SIDEWAY", near_sr="S",
                              pattern_bias=0.7, rsi=38),
            "D_RANGE_REVERSAL")

    def test_none_when_no_context(self):
        self.assertEqual(classify_strategy("LONG", regime="UPTREND",
                                            struct=-1.0, htf=-1, rsi=80), "NONE")

    def test_stats_roundtrip(self):
        p = os.path.join(tempfile.mkdtemp(), "st.json")
        bump("A_TREND_PULLBACK", True, 2.0, p)
        bump("A_TREND_PULLBACK", False, -1.0, p)
        rep = report(p)
        self.assertEqual(rep["A_TREND_PULLBACK"]["n"], 2)
        self.assertAlmostEqual(rep["A_TREND_PULLBACK"]["wr"], 0.5, places=9)
        self.assertAlmostEqual(rep["A_TREND_PULLBACK"]["avgR"], 0.5, places=9)


class TestBacktest(unittest.TestCase):
    def test_build_signals_generates_entries(self):
        df = _df(320, drift=0.002)
        sigs = build_signals(df, min_alpha=0.02, warmup=210)
        self.assertIsInstance(sigs, list)
        for s in sigs:
            self.assertIn(s["direction"], ("LONG", "SHORT"))
            self.assertGreaterEqual(s["atr"], 0.0)
            self.assertLess(s["i"], len(df) - 1)

    def test_simulate_variants_and_stats(self):
        df = _df(420, drift=0.002)
        sigs = [dict(x, symbol="BTCUSDT")
                for x in build_signals(df, min_alpha=0.02)]
        self.assertTrue(sigs, "can co tin hieu de test")
        res = {name: simulate(df, sigs, cfg, balance0=1000.0)
               for name, cfg in VARIANTS.items()}
        for name, r in res.items():
            st = r["stats"]
            self.assertEqual(st["n"], len(r["trades"]))
            self.assertGreaterEqual(st["wr"], 0.0)
            self.assertLessEqual(st["wr"], 1.0)
            self.assertGreaterEqual(st["max_dd_pct"], 0.0)
        self.assertGreater(res["V0_baseline_1.5_3"]["stats"]["n"], 0)
        self.assertGreater(res["V2_partial_be_trail"]["stats"]["n"], 0)

    def test_manage_never_worse_than_baseline(self):
        """Partial+BE khong the lam expectancy te hon baseline rat nhieu."""
        df = _df(500, drift=0.002)
        sigs = [dict(x, symbol="BTCUSDT")
                for x in build_signals(df, min_alpha=0.02)]
        if not sigs:
            self.skipTest("khong co tin hieu")
        base = simulate(df, sigs, VARIANTS["V0_baseline_1.5_3"])["stats"]
        mgd = simulate(df, sigs, VARIANTS["V2_partial_be_trail"])["stats"]
        self.assertGreaterEqual(mgd["wr"], base["wr"] - 1e-9)

    def test_stats_and_verdict(self):
        trades = []
        for _ in range(20):
            trades.append({"pnl": 2.0, "r": 2.0, "direction": "LONG",
                           "symbol": "BTCUSDT", "strategy": "A_TREND_PULLBACK",
                           "regime": "UPTREND"})
            trades.append({"pnl": -1.0, "r": -1.0, "direction": "SHORT",
                           "symbol": "ETHUSDT", "strategy": "B_BREAKOUT_RETEST",
                           "regime": "SIDEWAY"})
        st = stats(trades, [1000, 1020, 1000], 1000.0)
        self.assertEqual(st["n"], 40)
        self.assertAlmostEqual(st["wr"], 0.5, places=9)
        self.assertGreater(st["exp_r"], 0)
        self.assertEqual(st["streak_loss"], 1)
        self.assertIn("A_TREND_PULLBACK", st["by_strategy"])
        self.assertIn(verdict(st), ("PASS", "FAIL"))
        self.assertEqual(verdict({"n": 5}), "REVIEW (<30 lenh)")

    def test_stats_empty(self):
        st = stats([], [1000.0], 1000.0)
        self.assertEqual(st["n"], 0)
        self.assertEqual(verdict(st), "REVIEW (<30 lenh)")


if __name__ == "__main__":
    unittest.main()

