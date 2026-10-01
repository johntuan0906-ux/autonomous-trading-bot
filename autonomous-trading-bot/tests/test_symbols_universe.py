# -*- coding: utf-8 -*-
"""test_symbols_universe.py — mo rong universe symbol qua env, KHONG doi risk/entry.

Muc tieu: tang van toc thu mau testnet bang cach them cap (EXTRA_SYMBOLS) ma
van giu 1% risk/lenh + tran MAX_TOTAL_RISK_PCT. Do do test chi kiem tra:
  1) config doc SYMBOLS/EXTRA_SYMBOLS tu env (comma-separated), mac dinh van la
     4 cap cu khi env trong;
  2) validate: SYMBOLS khong duoc rong, EXTRA khong duoc trung SYMBOLS;
  3) turbo_demo.active_symbols() ghep + khuring thu tu, va roi ve SYMBOLS mac
     dinh khi cfg thieu truong (giu bot chay du config cu).

Chay: python -m unittest tests.test_symbols_universe -v
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Settings, _get_tuple                                            # noqa: E402

DEFAULT4 = ("BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT")
TURBO_ERR = ""
try:
    import turbo_demo
    HAVE_TURBO = True
except Exception as exc:          # thieu ccxt/dep thi bo qua phan turbo
    turbo_demo = None
    HAVE_TURBO = False
    TURBO_ERR = str(exc)


class TestGetTuple(unittest.TestCase):
    def test_env_trong_tra_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_tuple("SYMBOLS", DEFAULT4), DEFAULT4)
            self.assertEqual(_get_tuple("EXTRA_SYMBOLS", ()), ())

    def test_env_rong_or_toan_dau_phay_tra_default(self):
        with mock.patch.dict(os.environ, {"EXTRA_SYMBOLS": " , , "}, clear=True):
            self.assertEqual(_get_tuple("EXTRA_SYMBOLS", ()), ())

    def test_env_parse_strip_bo_rong(self):
        env = {"EXTRA_SYMBOLS": " ADA/USDT:USDT , ,DOGE/USDT:USDT "}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(_get_tuple("EXTRA_SYMBOLS", ()),
                             ("ADA/USDT:USDT", "DOGE/USDT:USDT"))


class TestSettingsSymbols(unittest.TestCase):
    def test_mac_dinh_4_cap_khi_khong_co_env(self):
        env = {k: "" for k in ("SYMBOLS", "EXTRA_SYMBOLS")}
        with mock.patch.dict(os.environ, env, clear=True):
            s = Settings()
            self.assertEqual(tuple(s.symbols), DEFAULT4)
            self.assertEqual(tuple(s.extra_symbols), ())

    def test_override_env_ap_dung_ngay_ca_symbol_trong_ky_tu(self):
        env = {"SYMBOLS": "BTC/USDT:USDT, ETH/USDT:USDT",
               "EXTRA_SYMBOLS": "ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT"}
        with mock.patch.dict(os.environ, env, clear=True):
            s = Settings()
            self.assertEqual(tuple(s.symbols), ("BTC/USDT:USDT", "ETH/USDT:USDT"))
            self.assertEqual(len(tuple(s.extra_symbols)), 3)

    def test_extra_trung_base_bei_chan(self):
        env = {"EXTRA_SYMBOLS": "SOL/USDT:USDT,ADA/USDT:USDT"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                Settings()

    def test_risk_field_khong_doi_khi_mo_universe(self):
        """Mo universe KHONG duoc ping risk/lenh. Tran danh muc that do
        portfolio.can_add_risk() chan luc mo lenh (max_total_risk_pct), khong
        phai do so cap trong universe — nen them cap van khong tang rui ro."""
        env = {"EXTRA_SYMBOLS": "ADA/USDT:USDT,DOGE/USDT:USDT"}
        with mock.patch.dict(os.environ, env, clear=True):
            s = Settings()
            self.assertAlmostEqual(s.risk_per_trade_pct, 1.0)
            self.assertAlmostEqual(s.max_total_risk_pct, 3.0)
            self.assertAlmostEqual(s.min_alpha_score, 0.35)   # nguong entry giu nguyen
            self.assertAlmostEqual(s.min_edge, 0.10)


@unittest.skipUnless(HAVE_TURBO, f"turbo_demo khong import duoc: {TURBO_ERR}")
class TestActiveSymbols(unittest.TestCase):
    def test_merge_giu_thu_tu_base_truoc(self):
        cfg = SimpleNamespace(symbols=("A/USDT:USDT", "B/USDT:USDT"),
                              extra_symbols=("C/USDT:USDT", "D/USDT:USDT"))
        self.assertEqual(turbo_demo.active_symbols(cfg),
                         ("A/USDT:USDT", "B/USDT:USDT", "C/USDT:USDT", "D/USDT:USDT"))

    def test_khong_extra_tra_dung_base(self):
        cfg = SimpleNamespace(symbols=DEFAULT4, extra_symbols=())
        self.assertEqual(turbo_demo.active_symbols(cfg), DEFAULT4)

    def test_cfg_cu_khong_co_truong_roi_mac_dinh(self):
        self.assertEqual(turbo_demo.active_symbols(SimpleNamespace()),
                         turbo_demo.SYMBOLS)
        self.assertEqual(turbo_demo.active_symbols(
            SimpleNamespace(symbols=(), extra_symbols=None)), turbo_demo.SYMBOLS)

    def test_dupe_ban_trong_extra_bi_khuring(self):
        cfg = SimpleNamespace(symbols=("A/USDT:USDT",),
                              extra_symbols=("A/USDT:USDT", "B/USDT:USDT", "B/USDT:USDT"))
        self.assertEqual(turbo_demo.active_symbols(cfg),
                         ("A/USDT:USDT", "B/USDT:USDT"))

    def test_env_day_du_di_xuyen_config_den_active_symbols(self):
        env = {"SYMBOLS": "BTC/USDT:USDT",
               "EXTRA_SYMBOLS": "ADA/USDT:USDT, DOGE/USDT:USDT"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Settings()
            self.assertEqual(turbo_demo.active_symbols(cfg),
                             ("BTC/USDT:USDT", "ADA/USDT:USDT", "DOGE/USDT:USDT"))


class TestRiskVanTranKhiMoUniverse(unittest.TestCase):
    """Them cap KHONG duoc tang so tien mat: tran MAX_TOTAL_RISK_PCT van chan.

    Chung minh bang loi chay: 3 vi the x 1% (equity 1000) -> lenh thu 4 bi
    portfolio.can_add_risk() tu choi, bat ke universe 4 cap hay 7 cap.
    """
    def _mk(self, sym):
        from portfolio import Position
        # |100 - 101| x 10 = 10 USDT = 1% cua equity 1000 (dung SL BAN DAU = 1R)
        return Position(symbol=sym, direction="SHORT", entry=100.0, qty=10.0,
                        sl=101.0, tp=95.0)

    def _thu_mo(self, extra):
        from portfolio import can_add_risk
        env = {"EXTRA_SYMBOLS": extra} if extra else {}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Settings()
            syms = turbo_demo.active_symbols(cfg) if HAVE_TURBO else tuple(cfg.symbols)
            pos = {s: self._mk(s) for s in syms[:3]}
            # lenh ke tiep (thu 4) se bi chan vi tong 1R da = 3% = tran
            return can_add_risk(pos, 1000.0, cfg.max_total_risk_pct, 10.0), syms

    @unittest.skipUnless(HAVE_TURBO, "turbo_demo khong import duoc")
    def test_universe_7_cap_van_bi_chan_o_lenh_thu_4(self):
        (ok, why), syms = self._thu_mo("ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT")
        self.assertEqual(len(syms), 7)
        self.assertFalse(ok)
        self.assertIn("tran risk danh muc", why)

    def test_universe_4_cap_cung_bat_ky_ket_qua(self):
        (ok, why), syms = self._thu_mo("")
        self.assertEqual(len(syms), 4)
        self.assertFalse(ok)
        self.assertIn("tran risk danh muc", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
