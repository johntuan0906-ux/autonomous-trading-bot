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

    def test_20_den_duoi_100_la_can_bang(self):
        for eq in (20, 50, 99.99):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "balanced", eq)
            self.assertEqual(t["max_positions"], 2)
            self.assertEqual(t["risk_pct"], 0.5)
            self.assertNotIn("BTC", t["symbols"])
            self.assertIn("LINK", t["symbols"])

    def test_tu_100_tro_len_la_an_toan(self):
        for eq in (100, 500, 10000):
            t = RT.tier_for(eq)
            self.assertEqual(t["name"], "safe", eq)
            self.assertEqual(t["max_positions"], 4)
            self.assertIn("BTC", t["symbols"])

    def test_equity_khong_hop_le_thi_muc_thap_nhat(self):
        for bad in (None, "abc", -5, 0):
            self.assertEqual(RT.tier_for(bad)["name"], "reduced")


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
