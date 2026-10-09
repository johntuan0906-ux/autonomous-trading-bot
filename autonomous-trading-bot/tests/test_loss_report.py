"""Test `loss_report` — phân tích lỗ (thuần tuý, không gọi sàn/LLM)."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

import loss_report as LR


def _pair(pair="BTC/USDT:USDT", direction="LONG", strategy="NONE", regime="COMPRESSION",
          reason="SL", r=1.0, hold_min=60.0, ts=1_700_000_000.0, won=None):
    o = {"ts": ts, "event": "OPEN", "pair": pair, "direction": direction,
         "strategy": strategy, "market_regime": regime, "entry": 100.0, "qty": 1.0}
    c = {"ts": ts + hold_min * 60.0, "event": "CLOSE", "pair": pair, "direction": direction,
         "reason": reason, "r": r, "pnl": r * 10.0, "won": (r > 0) if won is None else won}
    return o, c


def _many(n, **kw):
    return [_pair(**kw) for _ in range(n)]


class TestHelpers(unittest.TestCase):
    def test_group_stats(self):
        pairs = _many(3, pair="AAA", r=2.0) + _many(1, pair="AAA", r=-1.0)
        g = LR._grp(pairs, lambda o, c: c["pair"])["AAA"]
        self.assertEqual(g["n"], 4)
        self.assertEqual(g["wr"], 75.0)
        self.assertAlmostEqual(g["sum_r"], 5.0, places=3)
        self.assertAlmostEqual(g["loss_r"], 1.0, places=3)
        self.assertAlmostEqual(g["gain_r"], 6.0, places=3)
        self.assertAlmostEqual(g["avg_r"], 1.25, places=3)

    def test_hour_va_hold_bucket(self):
        self.assertEqual(LR.hour_of(0), 0)
        self.assertIsNone(LR.hour_of("x"))
        self.assertEqual(LR.hold_bucket(*_pair(hold_min=10)), "<30 phut")
        self.assertEqual(LR.hold_bucket(*_pair(hold_min=60)), "30-120 phut")
        self.assertEqual(LR.hold_bucket(*_pair(hold_min=180)), "2-8 gio")
        self.assertEqual(LR.hold_bucket(*_pair(hold_min=600)), ">8 gio")

    def test_propose_theo_kind(self):
        g = {"n": 20, "avg_r": -0.2, "sum_r": -4.0}
        self.assertIn("SYMBOLS", LR.propose("cap", "BTC", g))
        self.assertIn("LON NHAT", LR.propose("cap_top", "BTC", g, 28.0))
        self.assertIn("STRATEGY_BLOCK", LR.propose("chien luoc", "D_X", g))
        self.assertIn("REGIME_BLOCK", LR.propose("regime", "COMPRESSION", g))
        self.assertIn("loc huong", LR.propose("huong", "SHORT", g))
        self.assertIn("CUONG BUC", LR.propose("thoat", "FLATTEN", g))
        self.assertIn("max-hold", LR.propose("giu", ">8 gio", g))


class TestAnalyze(unittest.TestCase):
    def test_cap_xau_bi_de_xuat_bo(self):
        pairs = (_many(20, pair="BAD/USDT:USDT", r=-0.5)
                 + _many(20, pair="GOOD/USDT:USDT", r=1.0))
        rep = LR.analyze(pairs, min_n=15)
        caps = [t for _k, _g, t in rep["props"]["cap"]]
        self.assertTrue(any("BAD" in t and "SYMBOLS" in t for t in caps), caps)

    def test_cap_lo_lon_nhat_du_avgR_chua_toi_nguong(self):
        # BAD: avgR -0.05 (chua toi -0.10) nhung dong gop lo > 20%
        pairs = (_many(60, pair="BAD/USDT:USDT", r=-0.05)
                 + _many(20, pair="GOOD/USDT:USDT", r=0.10))
        rep = LR.analyze(pairs, min_n=15)
        caps = [t for _k, _g, t in rep["props"]["cap"]]
        self.assertTrue(any("LON NHAT" in t and "BAD" in t for t in caps), caps)

    def test_flatten_va_giu_lau_duoc_canh_bao(self):
        pairs = (_many(30, reason="FLATTEN", r=-0.5, hold_min=600)
                 + _many(20, reason="TP", r=1.0, hold_min=60))
        rep = LR.analyze(pairs, min_n=15)
        self.assertTrue(rep["props"]["ly do thoat"], rep["props"])
        self.assertIn("FLATTEN", rep["props"]["ly do thoat"][0][2])
        self.assertTrue(rep["props"]["thoi gian giu"])
        self.assertIn(">8 gio", rep["props"]["thoi gian giu"][0][2])

    def test_sl_share_va_render(self):
        pairs = _many(60, reason="SL", r=-1.0) + _many(10, reason="TP", r=2.0)
        rep = LR.analyze(pairs, min_n=15)
        self.assertAlmostEqual(rep["sl_share"], 85.7, places=1)
        txt = LR.render(rep)
        self.assertIn("PHAN TICH LO", txt)
        self.assertIn("SL chiem", txt)
        self.assertIn("DE XUAT", txt)

    def test_khong_co_nhom_xau_thi_khong_de_xuat(self):
        pairs = _many(30, pair="GOOD/USDT:USDT", r=1.0, reason="TP")
        rep = LR.analyze(pairs, min_n=15)
        self.assertEqual(rep["props"]["cap"], [])
        self.assertIn("khong de xuat gi", LR.render(rep))


class TestLoadPairs(unittest.TestCase):
    def test_loc_theo_so_ngay(self):
        tmp = Path(tempfile.mkdtemp()) / "j.jsonl"
        now = time.time()
        with open(tmp, "w", encoding="utf-8") as f:
            for days_ago, r in ((0.5, 1.0), (10.0, -1.0)):
                o, c = _pair(r=r, ts=now - days_ago * 86400)
                f.write(json.dumps(o) + "\n" + json.dumps(c) + "\n")
        all_pairs, _ = LR.load_pairs(str(tmp))
        self.assertEqual(len(all_pairs), 2)
        recent, _ = LR.load_pairs(str(tmp), days=3)
        self.assertEqual(len(recent), 1)


if __name__ == "__main__":
    unittest.main()
