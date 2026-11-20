"""Test `arm_protection.py` (them `--target live` 19/11, B-061).

Boi canh that: LIVE co **3 vi the khong co lenh bao ve nao tren san** (BTC/SOL/XRP) trong
luc dang bi san chan IP — bot khong goi duoc API nen cung khong the tu re-arm. Cong cu
phai: (a) tu choi dat lenh THAT neu thieu `--yes-live`, (b) KHONG goi API khi dang bi
chan (moi request lam ban dai them, B-044/B-059).
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import arm_protection as AP      # noqa: E402


class TestArmProtectionLive(unittest.TestCase):
    def test_live_arm_can_yes_live(self):
        self.assertEqual(AP.main(["--target", "live", "--arm"]), 2)

    def test_live_thieu_key_thi_tu_choi(self):
        with tempfile.TemporaryDirectory() as d:
            with open(Path(d) / ".env", "w", encoding="utf-8") as f:
                f.write("BINANCE_TESTNET=false\n")
            old = AP.LIVE_DIR
            AP.LIVE_DIR = Path(d)
            try:
                self.assertEqual(AP.main(["--target", "live"]), 2)
            finally:
                AP.LIVE_DIR = old

    def test_dang_bi_chan_thi_khong_goi_api(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "logs").mkdir()
            (base / "logs" / "api_ban.json").write_text(
                json.dumps({"until": time.time() + 3600}), encoding="utf-8")
            (base / ".env").write_text(
                "BINANCE_TESTNET=false\nBINANCE_API_KEY=k\nBINANCE_API_SECRET=s\n",
                encoding="utf-8")

            def _no_client(*a, **k):
                raise AssertionError("KHONG duoc tao client/ goi API khi dang bi chan")

            old_dir, old_cli = AP.LIVE_DIR, AP._client_keys
            AP.LIVE_DIR, AP._client_keys = base, _no_client
            try:
                self.assertEqual(AP.main(["--target", "live", "--arm", "--yes-live"]), 3)
            finally:
                AP.LIVE_DIR, AP._client_keys = old_dir, old_cli

    def test_ban_left_doc_ms_va_file_hong(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "logs").mkdir()
            self.assertEqual(AP._ban_left(base), 0.0)
            (base / "logs" / "api_ban.json").write_text("{hong", encoding="utf-8")
            self.assertEqual(AP._ban_left(base), 0.0)
            (base / "logs" / "api_ban.json").write_text(
                json.dumps({"until": time.time() + 120}), encoding="utf-8")
            self.assertGreater(AP._ban_left(base), 60.0)


class TestMissingLegs(unittest.TestCase):
    """(20/11, B-069) `--arm` dat VO DIEU KIEN ⇒ 14 lenh trung tren LIVE. Moi LOAI chi 1 lenh."""

    def test_chua_co_lenh_nao_thi_dat_ca_hai(self):
        legs = AP.missing_legs([], 100.0, 120.0)
        self.assertEqual([x[0] for x in legs], ["SL", "TP"])
        self.assertEqual([x[1] for x in legs], ["STOP_MARKET", "TAKE_PROFIT_MARKET"])

    def test_da_co_sl_thi_chi_dat_tp(self):
        legs = AP.missing_legs([{"type": "STOP_MARKET"}], 100.0, 120.0)
        self.assertEqual([x[0] for x in legs], ["TP"])

    def test_da_co_tp_thi_chi_dat_sl(self):
        legs = AP.missing_legs([{"type": "TAKE_PROFIT_MARKET"}], 100.0, 120.0)
        self.assertEqual([x[0] for x in legs], ["SL"])

    def test_du_ca_hai_thi_khong_dat_them(self):
        self.assertEqual(AP.missing_legs(
            [{"type": "STOP_MARKET"}, {"type": "TAKE_PROFIT_MARKET"}], 100.0, 120.0), [])

    def test_bien_the_ten_loai_va_chu_thuong(self):
        # Algo API tra `orderType` khac nhau (STOP / TAKE_PROFIT / trailing) — van tinh la co
        self.assertEqual(AP.missing_legs([{"type": "stop"}, {"type": "TAKE_PROFIT"}], 1.0, 2.0), [])
        self.assertEqual(AP.missing_legs([{"type": "TRAILING_STOP_MARKET"}], 1.0, 2.0)[0][0], "TP")

    def test_lenh_khac_loai_khong_duoc_tinh_la_bao_ve(self):
        # LIMIT/khong co type ⇒ van thieu ca hai (LIMIT KHONG phai SL/TP)
        self.assertEqual(len(AP.missing_legs([{"type": "LIMIT"}, {}, None], 1.0, 2.0)), 2)

    def test_gia_0_thi_bo_qua_chan_do(self):
        self.assertEqual(AP.missing_legs([], 0, 120.0), [("TP", "TAKE_PROFIT_MARKET", 120.0)])
        self.assertEqual(AP.missing_legs([], 100.0, 0), [("SL", "STOP_MARKET", 100.0)])
        self.assertEqual(AP.missing_legs([], 0, 0), [])


if __name__ == "__main__":
    unittest.main()
