# -*- coding: utf-8 -*-
"""Test `tools/atr_quality_probe.py` — do chat luong proxy bien dong (26/10).

Y tuong lay tu Kronos (§21 REPO_IDEAS): truoc khi nghi toi model nang, phai do duoc
"ATR co phan anh dung bien dong that khong" bang du lieu THAT cua bot. Cac test o day
chot phan THUAN (khong mang): khoang cach SL, bien do thuan, chi phi quy ra R, ATR Wilder,
tuong quan hang Spearman, va ket luan.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atr_quality_probe as P      # noqa: E402


def _o(entry=100.0, sl=98.0, qty=10.0, risk_usdt=20.0, ts=1000.0, pair="SOL/USDT:USDT"):
    return {"event": "OPEN", "pair": pair, "entry": entry, "sl": sl, "qty": qty,
            "risk_usdt": risk_usdt, "ts": ts}


def _c(mfe_r=0.5, r=0.1, pair="SOL/USDT:USDT", ts=2000.0):
    return {"event": "CLOSE", "pair": pair, "mfe_r": mfe_r, "r": r, "ts": ts}


class TestCoBan(unittest.TestCase):
    def test_sl_pct_va_truong_hop_hong(self):
        self.assertAlmostEqual(P.sl_pct(_o(entry=100.0, sl=98.0)), 0.02, places=6)
        self.assertEqual(P.sl_pct({"entry": 0, "sl": 98}), 0.0)
        self.assertEqual(P.sl_pct({}), 0.0)

    def test_mfe_pct_la_bien_do_thuan_that(self):
        # mfe_r=0.5, SL cach 2% => gia da di duoc 1% theo huong co loi
        self.assertAlmostEqual(P.mfe_pct(_o(), _c(mfe_r=0.5)), 0.01, places=6)
        self.assertEqual(P.mfe_pct(_o(), _c(mfe_r=-1)), 0.0)

    def test_cost_r_theo_risk_usdt(self):
        # notional = 10 x 100 = 1000; chi phi = 2 x (0.0005+0.0002) x 1000 = 1.4
        # risk = 20 USDT => cost = 0.07R
        self.assertAlmostEqual(P.cost_r(_o()), 0.07, places=6)

    def test_cost_r_tu_tinh_risk_khi_thieu_risk_usdt(self):
        o = _o(risk_usdt=0.0)                      # risk = |100-98| x 10 = 20
        self.assertAlmostEqual(P.cost_r(o), 0.07, places=6)
        self.assertEqual(P.cost_r({"entry": 0, "qty": 0}), 0.0)


class TestSpearman(unittest.TestCase):
    def test_dong_bien_va_nghich_bien(self):
        self.assertEqual(P.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertEqual(P.spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    def test_gia_tri_bang_nhau_va_mau_nho(self):
        self.assertEqual(P.spearman([1, 1, 1], [1, 2, 3]), 0.0)
        self.assertEqual(P.spearman([1, 2], [1, 2]), 0.0, "duoi 3 diem -> khong ket luan")


class TestATR(unittest.TestCase):
    def test_atr_wilder_tren_chuoi_don_gian(self):
        # 3 nen bien do 2,2,2 (khong gap) => ATR = 2 sau khi hoi tu
        rows = [[0, 10, 11, 9, 10, 1], [1, 10, 11, 9, 10, 1], [2, 10, 11, 9, 10, 1]]
        atr = P.atr_from_ohlcv(rows, period=2)
        self.assertAlmostEqual(atr[-1], 2.0, places=6)

    def test_atr_pct_at_chon_nen_dung_moc(self):
        rows = [[1000, 10, 11, 9, 10, 1], [901000, 10, 12, 10, 11, 1],
                [1801000, 10, 13, 11, 12, 1]]
        a = P.atr_pct_at(rows, 1500.0, period=2)     # moc nam trong nen dau
        self.assertGreater(a, 0.0)
        b = P.atr_pct_at(rows, 1801500.0, period=2)  # moc o nen cuoi
        self.assertGreater(b, 0.0)
        self.assertEqual(P.atr_pct_at([], 1.0), 0.0)


class TestGhepLenhVaTongHop(unittest.TestCase):
    def test_match_pairs_FIFO_cung_cap(self):
        opens = [_o(ts=1.0), _o(ts=2.0)]
        closes = [_c(ts=3.0), _c(ts=4.0)]
        pairs = P.match_pairs(opens, closes)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][0]["ts"], 1.0)

    def test_summarize_va_ket_luan_SL_rong(self):
        pairs = [(_o(), _c(mfe_r=0.3)) for _ in range(25)]
        s = P.summarize(pairs)
        self.assertEqual(s["n"], 25)
        self.assertAlmostEqual(s["mfe_r_p90"], 0.3, places=3)
        v = P.verdict(s)
        self.assertIn("RONG", v)
        self.assertIn("p90", v)

    def test_ket_luan_neu_bien_do_chi_gap_2_lan_chi_phi(self):
        """Bien do thuan nho hon ~3 lan chi phi ⇒ phai noi ro 'khong du day tra chi phi'."""
        pairs = [(_o(), _c(mfe_r=0.05)) for _ in range(25)]
        s = P.summarize(pairs)
        v = P.verdict(s)
        self.assertIn("chi phi", v)

    def test_verdict_khi_chua_du_mau(self):
        s = P.summarize([(_o(), _c()) for _ in range(5)])
        self.assertIn("chua du mau", P.verdict(s))

    def test_summarize_co_atr_thi_bao_mfe_over_atr(self):
        pairs = [(_o(), _c(mfe_r=1.0)) for _ in range(25)]
        s = P.summarize(pairs, atr_pcts=[0.02] * 25)
        self.assertAlmostEqual(s["mfe_over_atr_med"], 1.0, places=3)
        self.assertIn("ATR phan anh dung bien do", P.verdict(s))

    def test_summarize_bao_ATR_phong_dai(self):
        pairs = [(_o(), _c(mfe_r=0.2)) for _ in range(25)]
        s = P.summarize(pairs, atr_pcts=[0.02] * 25)     # mfe 0.4% vs ATR 2% -> 0.2
        self.assertIn("PHONG DAI", P.verdict(s))


class TestFetchATR(unittest.TestCase):
    def test_fetch_tiem_duoc_va_cache_theo_gio(self):
        calls: list = []

        def fetch(sym, since, limit):
            calls.append((sym, since, limit))
            return [[1000, 10, 11, 9, 10, 1], [901000, 10, 12, 10, 11, 1]]

        pairs = [(_o(ts=1000.0), _c()), (_o(ts=1500.0), _c())]
        out = P.fetch_atr_pcts(pairs, fetch)
        self.assertEqual(len(out), 2)
        self.assertEqual(len(calls), 1, "cung cap + cung gio => chi goi san 1 lan")

    def test_fetch_loi_thi_tra_0_khong_crash(self):
        def boom(*a, **k):
            raise RuntimeError("san loi")

        out = P.fetch_atr_pcts([(_o(), _c())], boom)
        self.assertEqual(out, [0.0])


if __name__ == "__main__":
    unittest.main()
