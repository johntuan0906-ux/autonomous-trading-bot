"""Test supervisor `run_forever`: tiến trình con phải nhận `.env` MỚI NHẤT (bug 09/10).

Bug thật: `state_sync` tự đổi `.env` sang LIVE rồi `restart_bot()` chỉ kill tiến trình CON;
supervisor spawn lại con với **env cũ** (kế thừa từ lúc supervisor khởi động, `load_dotenv`
không override) ⇒ `.env` ghi LIVE nhưng bot vẫn giao dịch demo (heartbeat 4348 USDT).
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_forever as RF


def _env_file(tmp: Path, text: str) -> None:
    (tmp / ".env").write_text(text, encoding="utf-8")


class TestChildEnv(unittest.TestCase):
    def test_env_moi_thang_env_cu(self):
        tmp = Path(tempfile.mkdtemp())
        _env_file(tmp, "BINANCE_TESTNET=false\nSYMBOLS=SOL/USDT:USDT\n"
                       "RISK_PER_TRADE_PCT=0.5\nMAX_POSITIONS=2\n")
        with mock.patch.object(RF, "ROOT", tmp), \
                mock.patch.dict(os.environ, {"BINANCE_TESTNET": "true",
                                             "SYMBOLS": "BTC/USDT:USDT"}, clear=False):
            env = RF.child_env()
        self.assertEqual(env["BINANCE_TESTNET"], "false")      # .env thang
        self.assertEqual(env["SYMBOLS"], "SOL/USDT:USDT")
        self.assertEqual(env["RISK_PER_TRADE_PCT"], "0.5")
        self.assertEqual(env["MAX_POSITIONS"], "2")

    def test_bien_khac_cua_moi_truong_duoc_giu(self):
        tmp = Path(tempfile.mkdtemp())
        _env_file(tmp, "BINANCE_TESTNET=true\n")
        with mock.patch.object(RF, "ROOT", tmp), \
                mock.patch.dict(os.environ, {"PATH_RIENG_XYZ": "1"}, clear=False):
            env = RF.child_env()
        self.assertEqual(env["PATH_RIENG_XYZ"], "1")
        self.assertEqual(env["BINANCE_TESTNET"], "true")

    def test_thieu_env_khong_crash(self):
        tmp = Path(tempfile.mkdtemp())          # khong co .env
        with mock.patch.object(RF, "ROOT", tmp), \
                mock.patch.dict(os.environ, {"X_KEEP": "1"}, clear=False):
            env = RF.child_env()
        self.assertEqual(env["X_KEEP"], "1")


if __name__ == "__main__":
    unittest.main()
