"""Test `freshness.py` — TUOI DU LIEU theo tung nguon (ham thuan tuy, khong mang/file).

Vi sao co (09/11, #4): truoc day khong co khai niem "du lieu cu" trong quyet dinh. Lop loi
nguy hiem nhat o day la **im lang**: nen 3 gio van duoc dung y nhu nen 20 giay, va khong
bao gio co loi nao — chi co ket qua sai. Test chot 4 dieu:
  1. TTL theo khung thoi gian (nen 1m khac nen 1h);
  2. moc thoi gian thieu/khong hop le phai la CHET (khong duoc coi la moi);
  3. nguon BAT BUOC chet thi chan, nguon BOI CANH chet thi khong chan;
  4. doc duoc cau hinh tu cfg (de chinh nguong bang `.env`, khong sua code).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import freshness as F   # noqa: E402


class TestTtl(unittest.TestCase):
    def test_ttl_theo_khung_thoi_gian(self):
        self.assertAlmostEqual(F.ttl_for_timeframe("1m"), 180.0)
        self.assertAlmostEqual(F.ttl_for_timeframe("15m"), 2700.0)
        self.assertAlmostEqual(F.ttl_for_timeframe("1h"), 10800.0)
        self.assertLess(F.ttl_for_timeframe("1m"), F.ttl_for_timeframe("1h"))

    def test_khung_la_khong_no_va_co_san(self):
        self.assertGreaterEqual(F.ttl_for_timeframe(""), 60.0)
        self.assertGreaterEqual(F.ttl_for_timeframe("rac"), 60.0)
        self.assertEqual(F.ttl_for_timeframe("1m", base=120.0), 120.0)

    def test_moc_thoi_gian_thieu_la_CHET(self):
        for bad in (None, 0, 0.0, -5, "rac", float("nan")):
            self.assertEqual(F.age_sec(bad, 1_700_000_000.0), float("inf"), bad)
        self.assertEqual(F.age_sec(1_699_999_940.0, 1_700_000_000.0), 60.0)
        self.assertEqual(F.age_sec(1_700_000_100.0, 1_700_000_000.0), 0.0,
                         "moc tuong lai (cache jitter) khong duoc ra tuoi am")

    def test_phan_loai_bien(self):
        self.assertEqual(F.level_of(100, 900), "fresh")
        self.assertEqual(F.level_of(900, 900), "fresh")
        self.assertEqual(F.level_of(901, 900), "stale")
        self.assertEqual(F.level_of(2700, 900), "stale")
        self.assertEqual(F.level_of(2701, 900), "dead")
        self.assertEqual(F.level_of(float("inf"), 900), "dead")


class TestEvaluate(unittest.TestCase):
    def test_moi_nguon_tuoi(self):
        rep = F.evaluate({"candles": 20.0, "deriv": 600.0})
        self.assertTrue(rep["ok"])
        self.assertEqual(rep["dead"], [])
        self.assertEqual(rep["reason_code"], "")

    def test_nen_cu_nhung_chua_chet_thi_VAN_quyet_dinh(self):
        rep = F.evaluate({"candles": 1500.0})
        self.assertTrue(rep["ok"], "stale chi la canh bao")
        self.assertEqual(rep["stale"], ["candles"])
        self.assertEqual(rep["by_source"]["candles"]["level"], "stale")

    def test_nen_chet_thi_CHAN(self):
        rep = F.evaluate({"candles": 5000.0})
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["blocking"], ["candles"])
        self.assertEqual(rep["reason_code"], "DATA_STALE")

    def test_thieu_moc_nen_cung_bi_chan(self):
        rep = F.evaluate({"deriv": 60.0})
        self.assertFalse(rep["ok"])
        self.assertIn("candles", rep["blocking"])

    def test_boi_canh_chet_KHONG_chan(self):
        rep = F.evaluate({"candles": 10.0, "deriv": 99999.0, "news": 99999.0})
        self.assertTrue(rep["ok"], "thieu boi canh khong duoc lam dung bot")
        self.assertIn("deriv", rep["dead"])
        self.assertEqual(rep["blocking"], [])

    def test_tuoi_khong_hop_le_la_chet(self):
        rep = F.evaluate({"candles": None})
        self.assertFalse(rep["ok"])
        self.assertIsNone(rep["by_source"]["candles"]["age"])

    def test_worst_va_summary(self):
        rep = F.evaluate({"candles": 10.0, "news": 1800.0})
        self.assertEqual(rep["worst"], "news")
        self.assertIn("candles 10s", F.summary_line(rep))


class TestCfg(unittest.TestCase):
    class _Cfg:
        data_ttl_sec = "candles=1200, deriv=60"
        data_ttl_hard_mult = 2.0
        data_ttl_candles_base = 0.0

    def test_doc_ghi_de_tu_env(self):
        ttl = F.ttl_from_cfg(self._Cfg(), "15m")
        self.assertEqual(ttl["candles"], 1200.0)
        self.assertEqual(ttl["deriv"], 60.0)

    def test_ghi_de_nen_bang_giay(self):
        class C:
            data_ttl_sec = ""
            data_ttl_candles_base = 300.0
        self.assertEqual(F.ttl_from_cfg(C(), "1m")["candles"], 300.0)

    def test_hard_mult_tu_cfg(self):
        self.assertEqual(F.hard_mult_from_cfg(self._Cfg()), 2.0)

        class Bad:
            data_ttl_hard_mult = 0.5          # < 1 la vo nghia

        self.assertEqual(F.hard_mult_from_cfg(Bad()), F.HARD_MULT)
        self.assertEqual(F.hard_mult_from_cfg(object()), F.HARD_MULT)


if __name__ == "__main__":
    unittest.main()
