"""Test ngưỡng rủi ro theo dải (`risk_tier`) — thuần tuý, không gọi sàn/LLM."""
from __future__ import annotations

import unittest

import risk_tier as RT


class TestTierFor(unittest.TestCase):
    def test_duoi_20_la_giam_lenh(self):
        for eq in (0, 1, 19.99):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "reduced", eq)
            self.assertEqual(t["max_positions"], 1)
            self.assertNotIn("BTC", t["symbols"])
            self.assertNotIn("LINK", t["symbols"])

    def test_20_den_duoi_62_la_can_bang(self):
        for eq in (20, 50, 61.99):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "balanced", eq)
            self.assertEqual(t["max_positions"], 2)
            self.assertEqual(t["risk_pct"], 0.5)
            self.assertNotIn("BTC", t["symbols"])

    def test_62_den_duoi_100_co_BTC(self):
        for eq in (62, 80, 99.99):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "balanced_btc", eq)
            self.assertIn("BTC", t["symbols"])
            self.assertEqual(t["max_positions"], 2)

    def test_tu_100_tro_len_la_an_toan(self):
        for eq in (100, 500, 10000):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "safe", eq)
            self.assertEqual(t["max_positions"], 4)
            allsyms = t["symbols"] + "," + t["extra_symbols"]
            self.assertIn("BTC", allsyms)
            self.assertIn("LINK", allsyms)

    def test_equity_khong_hop_le_thi_muc_thap_nhat(self):
        for bad in (None, "abc", -5, 0):
            self.assertEqual(RT.tier_for(bad)["name"], "reduced")


class TestFeasibility(unittest.TestCase):
    def test_loc_link_theo_min_notional(self):
        """LINK (min 20$) chi vao duoc khi notional >= 20$: 20$ -> loai, 50$ -> giu."""
        t20 = RT.tier_for(20)
        self.assertNotIn("LINK", t20["symbols"])
        self.assertIn("LINK/USDT:USDT", t20["dropped"])
        t50 = RT.tier_for(50)
        self.assertIn("LINK", t50["symbols"])
        self.assertEqual(t50["dropped"], [])

    def test_btc_bi_loai_khi_sl_rong(self):
        t = RT.tier_for(100, sl_ref_pct=3.0)      # notional = 1.0/0.03 = 33$
        self.assertNotIn("BTC", t["symbols"])
        self.assertIn("BTC/USDT:USDT", t["dropped"])
        self.assertTrue(t["feasible_any"])         # alt van con

    def test_qua_nho_thi_khong_cap_nao_kha_thi(self):
        t = RT.tier_for(1.0)                       # notional 0.8$ < 5$
        self.assertFalse(t["feasible_any"])
        self.assertEqual(t["symbols"], "")
        self.assertTrue(t["dropped"])

    def test_notional_va_risk_usd(self):
        t = RT.tier_for(100)                       # safe: risk 1% -> notional ~80.6$
        self.assertAlmostEqual(t["risk_usd"], 1.0, places=3)
        self.assertAlmostEqual(t["notional"], 80.65, places=1)

    def test_btc_min_equity(self):
        self.assertAlmostEqual(RT.btc_min_equity(1.0), 62.0, places=1)
        self.assertAlmostEqual(RT.btc_min_equity(0.5), 124.0, places=1)
        self.assertEqual(RT.btc_min_equity(0), 0.0)

    def test_min_notional_mac_dinh_5usd(self):
        self.assertEqual(RT.min_notional("SOL/USDT:USDT"), 5.0)
        self.assertEqual(RT.min_notional("BTC/USDT:USDT"), 50.0)


class TestEnvUpdates(unittest.TestCase):
    def test_env_updates_du_key(self):
        u = RT.env_updates(RT.tier_for(50))
        self.assertEqual(set(u), {"RISK_PER_TRADE_PCT", "MAX_POSITIONS", "SYMBOLS",
                                  "EXTRA_SYMBOLS"})
        self.assertEqual(u["RISK_PER_TRADE_PCT"], "0.5")
        self.assertEqual(u["MAX_POSITIONS"], "2")
        self.assertIn("LINK", u["SYMBOLS"])

    def test_table_md_danh_dau_muc_hien_tai(self):
        md = RT.table_md(50)
        self.assertIn("cân bằng", md)
        self.assertIn("hiện tại", md)
        self.assertNotIn("hiện tại", RT.table_md(None))

    def test_preview_co_muc_va_env(self):
        txt = RT.preview(150)
        self.assertIn("an toàn", txt)
        self.assertIn("MAX_POSITIONS", txt)


if __name__ == "__main__":
    unittest.main()
