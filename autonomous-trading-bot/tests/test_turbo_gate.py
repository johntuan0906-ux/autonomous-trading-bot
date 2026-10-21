"""Test chot `MAX_POSITIONS` cua `turbo_demo` (lop loi B-022).

Vi sao co (19/10): `turbo_demo` bo qua `MAX_POSITIONS` **VO DIEU KIEN** (docstring ghi
"chi dung tren demo!"), nhung `run_forever.py` chay CHINH script do cho **CA HAI**
instance ⇒ tren LIVE `MAX_POSITIONS=1` trong `.env` la **chot gia** — do that 19/10:
LIVE **8** vi the, TESTNET **14** vi the du dat 1; thu pham chan that su chi la
`MAX_TOTAL_RISK_PCT`. Nay `max_positions_block()` chan som tren LIVE (`SKIP_MAX_POS`).
"""
from __future__ import annotations

import dataclasses
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config as CFG          # noqa: E402
import turbo_demo as TD       # noqa: E402


def _cfg(**kw) -> SimpleNamespace:
    """cfg gia: mac dinh = LIVE (khong bo qua MAX_POSITIONS), 1 slot."""
    base = dict(max_positions=1, turbo_bypass_max_positions=False)
    base.update(kw)
    return SimpleNamespace(**base)


class TestMaxPositionsBlock(unittest.TestCase):
    def test_demo_thi_bo_qua(self):
        """DEMO: bo qua MAX_POSITIONS nhu cu (giu toc do thu mau)."""
        blocked, why = TD.max_positions_block(_cfg(turbo_bypass_max_positions=True),
                                             {"A": 1, "B": 2, "C": 3}, "D")
        self.assertFalse(blocked)
        self.assertEqual(why, "")

    def test_live_con_slot_thi_cho_mo(self):
        blocked, _ = TD.max_positions_block(_cfg(), {}, "SOL/USDT:USDT")
        self.assertFalse(blocked)

    def test_live_het_slot_thi_chan(self):
        blocked, why = TD.max_positions_block(_cfg(), {"ADA/USDT:USDT": 1},
                                             "SOL/USDT:USDT")
        self.assertTrue(blocked, "1 vi the dang mo + MAX_POSITIONS=1 => phai chan")
        self.assertIn("MAX_POSITIONS", why)

    def test_live_limit_4(self):
        cfg = _cfg(max_positions=4)
        self.assertFalse(TD.max_positions_block(cfg, {"a": 1, "b": 2, "c": 3}, "d")[0])
        self.assertTrue(TD.max_positions_block(cfg, {"a": 1, "b": 2, "c": 3, "d": 4}, "e")[0])

    def test_thieu_thuoc_tinh_thi_ton_trong_gioi_han(self):
        """cfg khong co `turbo_bypass_max_positions` (ban cu/test khac) => FAIL-SAFE: ton trong."""
        cfg = SimpleNamespace(max_positions=1)
        self.assertTrue(TD.max_positions_block(cfg, {"ADA/USDT:USDT": 1}, "SOL/USDT:USDT")[0])

    def test_truyen_bypass_tuong_minh_thang_cfg(self):
        blocked, _ = TD.max_positions_block(_cfg(), {"a": 1}, "b", bypass=True)
        self.assertFalse(blocked)

    def test_positions_rong(self):
        self.assertFalse(TD.max_positions_block(_cfg(), None, "SOL/USDT:USDT")[0])


class TestMacDinhTheoCheDo(unittest.TestCase):
    """`TURBO_BYPASS_MAX_POSITIONS` mac dinh: DEMO = bo qua, LIVE = TON TRONG."""

    def _default(self, env: dict) -> bool:
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("TURBO_BYPASS_MAX_POSITIONS", None)
            return CFG._default_turbo_bypass()

    def test_demo_mac_dinh_bo_qua(self):
        self.assertTrue(self._default({"BINANCE_TESTNET": "true"}))

    def test_live_mac_dinh_ton_trong(self):
        self.assertFalse(self._default({"BINANCE_TESTNET": "false"}),
                         "LIVE phai TON TRONG MAX_POSITIONS")

    def test_bat_tay_tren_live_thi_bo_qua(self):
        with mock.patch.dict(os.environ, {"BINANCE_TESTNET": "false",
                                          "TURBO_BYPASS_MAX_POSITIONS": "true"}, clear=False):
            self.assertTrue(CFG._default_turbo_bypass())

    def test_settings_co_field_nay(self):
        names = [f.name for f in dataclasses.fields(CFG.Settings)]
        self.assertIn("turbo_bypass_max_positions", names)


class TestFloorMinNotional(unittest.TestCase):
    """(21/10) Vốn nhỏ + SL rộng (mẫu người vận hành: 14×ATR15m ≈ −9.5%) ⇒ notional theo
    risk < minNotional 5 USDT ⇒ trước đây `SKIP_NOTIONAL` (không bao giờ vào lệnh).
    `qty_for_min_notional()` nâng qty lên đúng minNotional; người gọi phải kiểm lại
    trần risk (risk thực tăng: minNotional × SL% / equity).
    """

    def _q(self, step: float):
        """quantize giả: cắt xuống bội số `step` (giống TRUNCATE của sàn)."""
        import math
        return lambda x: math.floor(float(x) / step) * step

    def test_nang_len_dung_min_notional(self):
        q = TD.qty_for_min_notional(0.017, 5.0, 1.0)
        self.assertGreater(q, 0)
        self.assertGreaterEqual(q * 0.017, 5.0, "phải đạt notional >= minNotional")
        self.assertLess(q * 0.017, 5.0 + 0.017, "không được phình quá 1 bước")

    def test_lam_tron_LEN_theo_buoc_san(self):
        # 5/0.0263 = 190.11 ⇒ phải lên 191 (không phải 380 như bản "tăng gấp đôi")
        q = TD.qty_for_min_notional(0.0263, 5.0, 1.0)
        self.assertEqual(q, 191)
        self.assertGreaterEqual(q * 0.0263, 5.0)

    def test_buoc_nho_van_dung(self):
        q = TD.qty_for_min_notional(100.0, 5.0, 0.001)
        self.assertAlmostEqual(q, 0.05, places=9)
        self.assertGreaterEqual(q * 100.0, 5.0)

    def test_khong_the_thi_tra_0(self):
        self.assertEqual(TD.qty_for_min_notional(0.0, 5.0, 1.0), 0.0)
        self.assertEqual(TD.qty_for_min_notional(1.0, 0.0, 1.0), 0.0)
        self.assertEqual(TD.qty_for_min_notional(1.0, 5.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()

