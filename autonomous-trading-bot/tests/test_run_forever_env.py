"""Test supervisor `run_forever`: tiến trình con phải nhận `.env` MỚI NHẤT (bug 09/10).

Bug thật: `state_sync` tự đổi `.env` sang LIVE rồi `restart_bot()` chỉ kill tiến trình CON;
supervisor spawn lại con với **env cũ** (kế thừa từ lúc supervisor khởi động, `load_dotenv`
không override) ⇒ `.env` ghi LIVE nhưng bot vẫn giao dịch demo (heartbeat 4348 USDT).
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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


class TestSyncKhiConDaThoat(unittest.TestCase):
    """(11/10) `state_sync` phải chạy CẢ KHI tiến trình con đã thoát.

    Bug thật: con thoát sau ~5s (bị kill-switch/interlock chặn) ⇒ trước đây state_sync
    không bao giờ chạy nữa (tick cuối 10/10 08:47, sau đó 15 giờ không cập nhật gì).
    """

    def _run(self, next_sync, sync_proc, now=1000.0):
        calls: list = []

        class P:
            def poll(self):
                return 0

        def fake_popen(*a, **k):
            calls.append(a)
            return P()

        with mock.patch.object(RF.subprocess, "Popen", fake_popen), \
                mock.patch.object(RF, "time", SimpleNamespace(time=lambda: now,
                                                              sleep=lambda s: None)), \
                mock.patch("builtins.open", mock.mock_open()):
            nxt, proc = RF.spawn_sync_if_due(next_sync, sync_proc)
        return nxt, proc, calls

    def test_den_ky_thi_spawn(self):
        nxt, proc, calls = self._run(999.0, None)
        self.assertEqual(len(calls), 1)
        self.assertGreater(nxt, 1000.0)
        self.assertIsNotNone(proc)

    def test_chua_den_ky_thi_khong_spawn(self):
        nxt, proc, calls = self._run(1001.0, None)
        self.assertEqual(calls, [])
        self.assertEqual(nxt, 1001.0)

    def test_lan_truoc_con_dang_chay_thi_doi(self):
        class Alive:
            def poll(self):
                return None

        nxt, _proc, calls = self._run(999.0, Alive())
        self.assertEqual(calls, [])
        self.assertEqual(nxt, 999.0)

    def test_tat_sync_bang_0(self):
        _nxt, _proc, calls = self._run(0.0, None)
        self.assertEqual(calls, [])


class TestTouchHeartbeat(unittest.TestCase):
    """(11/10) `heartbeat.json` phải LUÔN là dict và giữ pid/round của con.

    Bản cũ ghi số trần ⇒ state_sync đọc được số ⇒ crash `'float' ... no attribute 'get'`
    ⇒ sync/auto-live/git ngừng chạy 15 giờ.
    """

    def test_giu_pid_round_va_ghi_dict(self):
        tmp = Path(tempfile.mkdtemp()) / "heartbeat.json"
        tmp.write_text(json.dumps({"ts": 1.0, "pid": 4242, "round": 7}), encoding="utf-8")
        RF.touch_heartbeat(tmp)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        self.assertIsInstance(d, dict)
        self.assertEqual(d["pid"], 4242)
        self.assertEqual(d["round"], 7)
        self.assertGreater(d["ts"], 1.0)

    def test_file_so_tran_cu_thi_thanh_dict(self):
        tmp = Path(tempfile.mkdtemp()) / "heartbeat.json"
        tmp.write_text("1791652772.73", encoding="utf-8")     # bản cũ ghi số trần
        RF.touch_heartbeat(tmp)
        d = json.loads(tmp.read_text(encoding="utf-8"))
        self.assertIsInstance(d, dict)
        self.assertIn("ts", d)

    def test_file_chua_ton_tai(self):
        tmp = Path(tempfile.mkdtemp()) / "moi.json"
        RF.touch_heartbeat(tmp)
        self.assertIsInstance(json.loads(tmp.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
