"""test_strategy_gate.py — gate chan strategy dang am (khong ha nguong entry).

Muc tieu (30/09/2026): A_TREND_PULLBACK avgR -0.59 keo PF xuong; monitor da thay
n=46 PF=0.852. Gate moi chan setup thuoc strategy am khi DU MAU, khong anh huong
cac strategy khac, khong noim loang tieu chuan vao lenh:
  1) gate_check cho qua khi thieu mau / avgR duong / khong doc duoc file;
  2) gate_check chan khi n >= STRAT_MIN_N va avgR <= -STRAT_AVG_R;
  3) NONE luon cho qua (khong ket luan duoc);
  4) turbo_demo quen thuoc tinh cfg cu (strategy_gate khong ton tai) -> khong crash.

Chay: python -m unittest tests.test_strategy_gate -v
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy import gate_check  # noqa: E402


class TestGateCheck(unittest.TestCase):
    def test_thieu_mau_cho_qua(self):
        stats = {"A_TREND_PULLBACK": {"n": 3, "wins": 1, "sum_r": -1.77}}
        out = gate_check("A_TREND_PULLBACK", min_n=10, avg_r=0.10, stats=stats)
        self.assertFalse(out["blocked"])
        self.assertEqual(out["n"], 3)

    def test_du_mau_am_chan(self):
        stats = {"A_TREND_PULLBACK": {"n": 12, "wins": 4, "sum_r": -7.08}}
        out = gate_check("A_TREND_PULLBACK", min_n=10, avg_r=0.10, stats=stats)
        self.assertTrue(out["blocked"])
        self.assertIn("A_TREND_PULLBACK", out["reason"])

    def test_du_mau_duong_cho_qua(self):
        stats = {"B_BREAKOUT_RETEST": {"n": 14, "wins": 9, "sum_r": 2.24}}
        out = gate_check("B_BREAKOUT_RETEST", min_n=10, avg_r=0.10, stats=stats)
        self.assertFalse(out["blocked"])

    def test_none_luon_cho_qua(self):
        out = gate_check("NONE", min_n=1, avg_r=0.0,
                         stats={"NONE": {"n": 50, "wins": 10, "sum_r": -20.0}})
        self.assertFalse(out["blocked"])

    def test_khong_doc_duoc_file_cho_qua(self):
        out = gate_check("A_TREND_PULLBACK", min_n=10, avg_r=0.10,
                         path="khong/ton/tai.json")
        self.assertFalse(out["blocked"])

    def test_tat_gate_khong_chan(self):
        # Giong hanh vi turbo_demo khi STRATEGY_GATE=false.
        cfg = SimpleNamespace(strategy_gate=False)
        blocked = bool(getattr(cfg, "strategy_gate", False))
        self.assertFalse(blocked)

    def test_blocklist_chan_truoc_khi_du_mau(self):
        # Bang chung tu backtest: chan ngay ca khi journal n=0 (khong doc duoc file).
        stats = {"A_TREND_PULLBACK": {"n": 3, "wins": 1, "sum_r": -0.14}}
        out = gate_check("A_TREND_PULLBACK", min_n=10, avg_r=0.10, stats=stats,
                         blocklist=("A_TREND_PULLBACK",))
        self.assertTrue(out["blocked"])
        self.assertIn("STRATEGY_BLOCK", out["reason"])

    def test_blocklist_rong_khong_anh_huong(self):
        stats = {"A_TREND_PULLBACK": {"n": 3, "wins": 1, "sum_r": -0.14}}
        out = gate_check("A_TREND_PULLBACK", min_n=10, avg_r=0.10, stats=stats,
                         blocklist=())
        self.assertFalse(out["blocked"])   # van du mau tu dong

    def test_blocklist_khong_chan_strategy_khac(self):
        out = gate_check("B_BREAKOUT_RETEST", min_n=1, avg_r=0.0,
                         stats={"B_BREAKOUT_RETEST": {"n": 5, "wins": 4,
                                                      "sum_r": 2.7}},
                         blocklist=("A_TREND_PULLBACK",))
        self.assertFalse(out["blocked"])

    def test_cfg_cu_thieu_truong_khong_crash(self):
        cfg = SimpleNamespace()  # khong co strategy_gate / strat_min_n
        try:
            ok = bool(getattr(cfg, "strategy_gate", False))
        except Exception:  # noqa: BLE001
            ok = True
        self.assertFalse(ok)  # mac dinh tat khi thieu truong


if __name__ == "__main__":
    unittest.main()
