"""`fee_edge.py` — quyet dinh theo PHI vs KY VONG, khong theo "can bao nhieu von".

Chot dieu quan trong nhat: **ti le phi/ky vong KHONG phu thuoc von** — 38 USDT hay 3.800 USDT deu
nhu nhau. Cai phu thuoc von chi la (a) notional >= minNotional 5 USDT, (b) margin kha dung.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fee_edge as FE      # noqa: E402


class TestToanHoc(unittest.TestCase):
    def test_ti_le_KHONG_phu_thuoc_von(self):
        """Cung risk% + cung SL% + cung exp_r ⇒ ti le y het nhau du von 38 hay 3.800."""
        small = FE.plan(equity=38.0, risk_usdt=0.23, stop_pct=0.05, exp_r=0.086)
        big = FE.plan(equity=3800.0, risk_usdt=23.0, stop_pct=0.05, exp_r=0.086)
        self.assertAlmostEqual(small["fee_ratio"], big["fee_ratio"], places=9)

    def test_cong_thuc_ti_le(self):
        # ratio = 2*fee/(exp_r*stop)
        want = 2 * 0.0005 / (0.086 * 0.05)
        got = FE.fee_ratio(notional=0.23 / 0.05, risk_usdt=0.23, exp_r=0.086)
        self.assertAlmostEqual(got, want, places=9)

    def test_sl_mong_thi_phi_an_het(self):
        # SL 1,5% => ratio = 2*0.0005/(0.086*0.015) = 0.775 (>0.35) => chan
        rep = FE.plan(equity=38.0, risk_usdt=0.23, stop_pct=0.015, exp_r=0.086)
        self.assertFalse(rep["ok"])
        self.assertIn("SL rong", rep["why"])
        self.assertGreater(rep["fee_ratio"], 0.35)

    def test_sl_rong_thi_qua(self):
        # SL 5% => ratio 0.233 => dat (dung so do that: sl_pct TESTNET ~5,1%)
        rep = FE.plan(equity=38.0, risk_usdt=0.23, stop_pct=0.05, exp_r=0.086,
                      notional=5.0)
        self.assertTrue(rep["ok"], rep["why"])
        self.assertLess(rep["fee_ratio"], 0.35)

    def test_need_stop_pct(self):
        want = 2 * 0.0005 / (0.086 * 0.35)
        self.assertAlmostEqual(FE.need_stop_pct(0.086), want, places=9)
        self.assertEqual(FE.need_stop_pct(0.0), 0.0)
        self.assertEqual(FE.need_stop_pct(-1), 0.0)

    def test_exp_r_0_thi_khong_trade(self):
        rep = FE.plan(equity=38.0, risk_usdt=0.23, stop_pct=0.05, exp_r=0.0)
        self.assertFalse(rep["ok"])
        self.assertIn("ky vong = 0", rep["why"])
        self.assertEqual(FE.fee_ratio(10, 1, 0), float("inf"))

    def test_duoi_min_notional_thi_bao_dung_loi_san(self):
        rep = FE.plan(equity=38.0, risk_usdt=0.1, stop_pct=0.05, exp_r=0.086, notional=3.0)
        self.assertFalse(rep["ok"])
        self.assertIn("-4164", rep["why"])

    def test_cfg_ghi_de_phi_va_nguong(self):
        cfg = SimpleNamespace(fee_taker_pct=0.1, max_fee_ratio=0.8)   # phí 0,1%, ngưỡng 80%
        rep = FE.plan(equity=38.0, risk_usdt=0.23, stop_pct=0.02, exp_r=0.086, cfg=cfg)
        self.assertAlmostEqual(FE.fee_rate(cfg), 0.001)
        self.assertAlmostEqual(FE.max_ratio(cfg), 0.8)
        self.assertAlmostEqual(rep["fee_ratio"], 2 * 0.001 / (0.086 * 0.02), places=9)

    def test_phi_va_ky_vong(self):
        self.assertAlmostEqual(FE.roundtrip_fee(100.0), 0.1)
        self.assertAlmostEqual(FE.expected_edge(10.0, 0.5), 5.0)


class TestNoiDay(unittest.TestCase):
    def test_turbo_demo_co_chan_FEE_EDGE(self):
        src = (ROOT / "turbo_demo.py").read_text(encoding="utf-8")
        self.assertIn("fee_edge.plan(", src)
        self.assertIn('"status": "SKIP_FEE_EDGE"', src)
        self.assertIn("import fee_edge", src)

    def test_config_co_3_khoa(self):
        src = (ROOT / "config.py").read_text(encoding="utf-8")
        for k in ("FEE_TAKER_PCT", "MAX_FEE_RATIO", "EXP_R_ASSUMED"):
            self.assertIn(k, src)


if __name__ == "__main__":
    unittest.main()
