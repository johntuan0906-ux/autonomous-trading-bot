"""Test state_sync: đồng bộ STATE.md + logic tự động sang LIVE (thuần tuý, không gọi sàn).

Lưu ý an toàn: test KHÔNG được tạo `logs/.live_flipped` thật (sẽ vô hiệu hoá auto-live)
và KHÔNG gọi `restart_bot()` / `git_commit_push()`.
"""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import state_sync as SS


def _journal(path: str, n_win: int = 4, n_loss: int = 2) -> str:
    ts = time.time() - 3600
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n_win + n_loss):
            f.write(json.dumps({"ts": ts + i, "event": "OPEN", "pair": "BTC/USDT:USDT",
                                "direction": "LONG", "entry": 100.0, "qty": 1.0,
                                "strategy": "NONE"}) + "\n")
            win = i < n_win
            f.write(json.dumps({"ts": ts + i + 30, "event": "CLOSE", "pair": "BTC/USDT:USDT",
                                "direction": "LONG", "won": win, "r": 2.0 if win else -1.0,
                                "pnl": 10.0 if win else -5.0}) + "\n")
    return path


def _cfg(**kw):
    base = dict(testnet=True, dry_run=False, live_confirm=False, leverage=8,
                max_total_risk_pct=2.0, risk_state_path="", balance_usdt=1000.0,
                risk_per_trade_pct=1.0, max_positions=4, api_key="k", api_secret="s",
                auto_live_armed=False, auto_live_min_equity=100.0)
    base.update(kw)
    return SimpleNamespace(**base)


class TestSetEnvValues(unittest.TestCase):
    def test_thay_key_co_san(self):
        out = SS.set_env_values("A=1\nBINANCE_TESTNET=true\nC=3\n",
                                {"BINANCE_TESTNET": "false"})
        self.assertIn("BINANCE_TESTNET=false", out)
        self.assertIn("A=1", out)
        self.assertIn("C=3", out)
        self.assertNotIn("BINANCE_TESTNET=true", out)

    def test_them_key_chua_co(self):
        out = SS.set_env_values("A=1\n", {"LIVE_CONFIRM": "true"})
        self.assertIn("LIVE_CONFIRM=true", out)
        self.assertTrue(out.endswith("\n"))

    def test_nhieu_key_cung_luc(self):
        out = SS.set_env_values("RISK_PER_TRADE_PCT=1.0\nMAX_POSITIONS=4\n",
                                {"RISK_PER_TRADE_PCT": "0.5", "MAX_POSITIONS": "3"})
        self.assertIn("RISK_PER_TRADE_PCT=0.5", out)
        self.assertIn("MAX_POSITIONS=3", out)


class TestDecideGoLive(unittest.TestCase):
    def setUp(self):
        self.ok_ready = {"ok": True, "blockers": []}
        self.ok_guard = {"ok": True, "blockers": []}

    def test_chua_bat_armed_thi_khong_doi(self):
        ok, why = SS.decide_go_live(self.ok_ready, self.ok_guard, 500.0, False, False)
        self.assertFalse(ok)
        self.assertIn("AUTO_LIVE_ARMED", why)

    def test_da_doi_1_lan_thi_khong_doi_lai(self):
        ok, why = SS.decide_go_live(self.ok_ready, self.ok_guard, 500.0, True, True)
        self.assertFalse(ok)
        self.assertIn("marker", why)

    def test_live_ready_chua_dat_thi_khong_doi(self):
        ok, why = SS.decide_go_live({"ok": False, "blockers": ["n=291 < 300"]},
                                    self.ok_guard, 500.0, True, False)
        self.assertFalse(ok)
        self.assertIn("live_ready CHUA dat", why)
        self.assertIn("291", why)

    def test_live_guard_chan_thi_khong_doi(self):
        ok, why = SS.decide_go_live(self.ok_ready,
                                    {"ok": False, "blockers": ["kill-switch"]},
                                    500.0, True, False)
        self.assertFalse(ok)
        self.assertIn("live_guard CHAN", why)

    def test_khong_doc_duoc_vi_that_thi_khong_doi(self):
        ok, why = SS.decide_go_live(self.ok_ready, self.ok_guard, None, True, False)
        self.assertFalse(ok)
        self.assertIn("fail-safe", why)

    def test_vi_that_duoi_nguong_thi_khong_doi(self):
        ok, why = SS.decide_go_live(self.ok_ready, self.ok_guard, 50.0, True, False, 100.0)
        self.assertFalse(ok)
        self.assertIn("50.00", why)

    def test_du_het_dieu_kien_thi_doi(self):
        ok, why = SS.decide_go_live(self.ok_ready, self.ok_guard, 500.0, True, False, 100.0)
        self.assertTrue(ok, why)
        self.assertIn("500.00", why)


class TestCollectAndRender(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.jp = _journal(str(self.tmp / "j.jsonl"))
        self.hb = self.tmp / "heartbeat.json"
        self.managed = self.tmp / "managed.json"
        self.learner = self.tmp / "learner.json"
        self.risk = self.tmp / "risk.json"
        self.hb.write_text(json.dumps({"ts": time.time(), "pid": 123, "round": 7,
                                       "phase": "end", "equity": 4321.0}), encoding="utf-8")
        self.managed.write_text(json.dumps({"trades": {
            "BTC/USDT:USDT": {"direction": "SHORT", "qty": 0.01, "entry": 80000.0,
                              "sl": 81000.0, "tp": 78000.0, "mfe_r": 0.5},
            "SOL/USDT:USDT": {"direction": "SHORT", "qty": 3.0, "entry": 108.0,
                              "sl": 111.0, "tp": 102.0, "partial_done": True}}}),
            encoding="utf-8")
        self.learner.write_text(json.dumps({"n": 144, "b": 0.5, "w": {}}), encoding="utf-8")
        self.risk.write_text(json.dumps({"tripped": False, "reason": ""}), encoding="utf-8")
        for name, val in (("HEARTBEAT", self.hb), ("MANAGED", self.managed),
                          ("LEARNER", self.learner)):
            p = mock.patch.object(SS, name, val)
            p.start()
            self.addCleanup(p.stop)

    def _collect(self, **cfg_kw):
        return SS.collect(_cfg(risk_state_path=str(self.risk), **cfg_kw), journal=self.jp)

    def test_snapshot_doc_dung_file_state(self):
        snap = self._collect()
        self.assertEqual(snap["journal"]["n"], 6)
        self.assertEqual(snap["bot"]["pid"], 123)
        self.assertTrue(snap["bot"]["alive"])
        self.assertEqual(len(snap["positions"]), 2)
        self.assertEqual(snap["positions"][0]["symbol"], "BTC/USDT:USDT")
        self.assertEqual(snap["learner"]["n_updates"], 144)
        self.assertFalse(snap["kill_switch"]["tripped"])
        self.assertEqual(snap["equity_demo"], 4321.0)
        self.assertIn("windows", snap)

    def test_snapshot_kill_switch_tripped(self):
        self.risk.write_text(json.dumps({"tripped": True, "reason": "loss ngay"}),
                             encoding="utf-8")
        snap = self._collect()
        self.assertTrue(snap["kill_switch"]["tripped"])
        self.assertIn("loss ngay", SS.render_md(snap))

    def test_render_md_co_du_thong_tin(self):
        md = SS.render_md(self._collect())
        for needle in ("STATE.md", "TỰ ĐỘNG SINH", "Cổng sang LIVE", "Vị thế đang quản lý",
                       "BTC/USDT:USDT", "AUTO_LIVE_ARMED", "CONTEXT.md"):
            self.assertIn(needle, md)
        self.assertIn("TESTNET (demo)", md)


class TestGitBin(unittest.TestCase):
    def test_tra_duong_dan_ton_tai_hoac_fallback(self):
        """Bug thật 09/10: `subprocess.run(["git",...])` lỗi WinError 2 trong process con
        của supervisor -> phải dùng đường dẫn tuyệt đối (hoặc fallback "git")."""
        p = SS._git_bin()
        self.assertTrue(p == "git" or Path(p).exists(), p)
        self.assertTrue(p.lower().endswith("git.exe") or p == "git", p)


class TestGoLive(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.envp = self.tmp / ".env"
        self.envp.write_text("BINANCE_TESTNET=true\nLIVE_CONFIRM=false\n"
                             "RISK_PER_TRADE_PCT=1.0\nMAX_POSITIONS=4\nKEEP=1\n",
                             encoding="utf-8")
        self.marker = self.tmp / ".live_flipped"
        p = mock.patch.object(SS, "FLIP_MARKER", self.marker)
        p.start()
        self.addCleanup(p.stop)

    def test_go_live_doi_env_va_ha_rui_ro(self):
        res = SS.go_live(_cfg(), "test reason", env_path=self.envp)
        self.assertTrue(res["ok"], res)
        txt = self.envp.read_text(encoding="utf-8")
        self.assertIn("BINANCE_TESTNET=false", txt)
        self.assertIn("LIVE_CONFIRM=true", txt)
        self.assertIn("RISK_PER_TRADE_PCT=0.5", txt)
        self.assertIn("MAX_POSITIONS=3", txt)
        self.assertIn("KEEP=1", txt)                              # không làm hỏng dòng khác
        self.assertTrue((self.tmp / ".env.bak-live").exists())     # có backup
        self.assertTrue(self.marker.exists())                      # marker = chỉ đổi 1 lần

    def test_go_live_env_khong_ton_tai_tra_loi(self):
        res = SS.go_live(_cfg(), "x", env_path=self.tmp / "khong-co.env")
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
