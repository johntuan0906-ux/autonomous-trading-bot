# -*- coding: utf-8 -*-
"""Test `tools/stress_harness.py` — stress-test duong tien bang bootstrap R that (26/10).

Chot cac tinh chat QUAN TRONG:
  - bootstrap TAT DINH theo seed (ket qua lap lai duoc ⇒ bang chung kiem chung duoc);
  - drawdown toi da dung cong thuc;
  - xac suat cham tran NGAY: tran 2% phai >= tran 6% (kiem chung quyet dinh hoi dong 22/10);
  - "suc chiu chi phi": them chi phi X R/lenh phai lam P(ket thuc am) TANG (khong giam).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import stress_harness as SH      # noqa: E402


class TestDocJournal(unittest.TestCase):
    def test_load_rs_chi_lay_lenh_DA_DONG(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "journal.jsonl"
            p.write_text("\n".join([
                json.dumps({"event": "OPEN", "pair": "SOL/USDT:USDT", "entry": 1.0}),
                json.dumps({"event": "CLOSE", "pair": "SOL/USDT:USDT", "r": 1.5}),
                json.dumps({"event": "CLOSE", "pair": "SOL/USDT:USDT", "r": -1.0}),
                json.dumps({"status": "COUNCIL", "r": 99}),          # khong phai CLOSE
            ]) + "\n", encoding="utf-8")
            self.assertEqual(SH.load_rs(p), [1.5, -1.0])

    def test_file_thieu_thi_rong(self):
        self.assertEqual(SH.load_rs(Path("khong/ton/tai.jsonl")), [])


class TestBootstrap(unittest.TestCase):
    def test_tat_dinh_theo_seed(self):
        rs = [1.0, -1.0, 2.0, -0.5]
        a = SH.bootstrap(rs, n_paths=5, n_trades=10, seed=42)
        b = SH.bootstrap(rs, n_paths=5, n_trades=10, seed=42)
        c = SH.bootstrap(rs, n_paths=5, n_trades=10, seed=43)
        self.assertEqual(a, b, "cung seed => cung ket qua (bang chung lap lai duoc)")
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 5)
        self.assertEqual(len(a[0]), 10)

    def test_rong_thi_khong_duong(self):
        self.assertEqual(SH.bootstrap([], n_paths=5, n_trades=10), [])


class TestDrawdown(unittest.TestCase):
    def test_drawdown_dung_cong_thuc(self):
        self.assertEqual(SH.max_drawdown([]), 0.0)
        self.assertEqual(SH.max_drawdown([1, 2, 3]), 0.0)
        # duong LUY KE: +1 roi -2 => dinh 1, day -2 => drawdown 3R
        self.assertEqual(SH.max_drawdown([1.0, -2.0]), 3.0)
        self.assertEqual(SH.max_drawdown([3.0, 1.0, 4.0, 0.5]), 3.5)


class TestThongKeDuong(unittest.TestCase):
    def test_p_am_dung_ty_le(self):
        paths = [[1.0], [-1.0], [-2.0], [3.0]]        # 2/4 am
        s = SH.summarize_paths(paths)
        self.assertEqual(s["paths"], 4)
        self.assertAlmostEqual(s["p_final_neg"], 0.5, places=4)

    def test_rong_thi_paths_0(self):
        self.assertEqual(SH.summarize_paths([]), {"paths": 0})


class TestTranNgay(unittest.TestCase):
    def test_toan_thang_thi_khong_bao_gio_cham_tran(self):
        self.assertEqual(SH.daily_trip_prob([1.0] * 20, risk_pct=1.2, cap_pct=2.0), 0.0)

    def test_toan_thua_thi_cham_tran_chac_chan(self):
        # 8 lenh x -1R x 1.2% = -9.6% <= -2%
        self.assertEqual(SH.daily_trip_prob([-1.0] * 20, risk_pct=1.2, cap_pct=2.0), 1.0)
        self.assertEqual(SH.daily_trip_prob([-1.0] * 20, risk_pct=1.2, cap_pct=20.0), 0.0)

    def test_tran_rong_thi_it_trip_hon(self):
        rs = [1.0, -1.0, -1.0, 0.5, -1.0]
        p2 = SH.daily_trip_prob(rs, risk_pct=1.2, cap_pct=2.0, n_paths=500, seed=1)
        p6 = SH.daily_trip_prob(rs, risk_pct=1.2, cap_pct=6.0, n_paths=500, seed=1)
        self.assertGreaterEqual(p2, p6, "tran 2% khong the it trip hon tran 6%")
        self.assertGreater(p2, 0.0)


class TestSucChiuChiPhi(unittest.TestCase):
    def test_shock_lam_xau_di(self):
        rs = [0.2] * 50                      # edge mong
        base = SH.summarize_paths(SH.bootstrap(rs, n_paths=50, n_trades=20, seed=3))
        shocked = SH.summarize_paths(
            SH.bootstrap(SH.cost_shock(rs, 0.25), n_paths=50, n_trades=20, seed=3))
        self.assertEqual(base["p_final_neg"], 0.0)
        self.assertEqual(shocked["p_final_neg"], 1.0)

    def test_stress_co_du_khoa_va_tran_2_nang_hon(self):
        rs = [1.0, -1.0, -1.0, -1.0, 0.3]
        s = SH.stress(rs, n_paths=300, n_trades=50, seed=5)
        for k in ("p_final_neg", "dd_r_med", "dd_r_p90", "trip_prob_cap_2",
                  "trip_prob_cap_6", "by_cost_shock", "n_rs", "win_rate"):
            self.assertIn(k, s)
        self.assertGreaterEqual(s["trip_prob_cap_2"], s["trip_prob_cap_6"])
        self.assertIn("0.10R", s["by_cost_shock"])


class TestKetLuan(unittest.TestCase):
    def test_report_noi_ro_hai_tran(self):
        rs = [1.0, -1.0, 0.5]
        s = SH.stress(rs, n_paths=200, n_trades=50, seed=2)
        txt = SH.report_text(s, "TEST")
        self.assertIn("tran 2%", txt)
        self.assertIn("tran 6%", txt)
        self.assertIn("KET LUAN", txt)

    def test_rong_thi_bao_chua_du_du_lieu(self):
        self.assertIn("chua du du lieu", SH.verdict({}))


if __name__ == "__main__":
    unittest.main()
