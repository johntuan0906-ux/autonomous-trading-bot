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


if __name__ == "__main__":
    unittest.main()
