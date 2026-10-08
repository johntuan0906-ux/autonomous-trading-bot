"""Test cổng HOÀN THÀNH TESTNET (live_ready) — thuần tuý, không gọi sàn/LLM."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import live_ready as LR


def _mk(path, n_win, n_loss, *, r_win=2.0, r_loss=-1.0, pnl_win=10.0, pnl_loss=-5.0,
        days_ago=0.0, pair="BTC/USDT:USDT", direction="LONG", strategy="NONE"):
    """Ghi thêm journal giả (OPEN+CLOSE) cách hiện tại `days_ago` ngày."""
    base = time.time() - float(days_ago) * 86400.0 - 7200.0
    with open(path, "a", encoding="utf-8") as f:
        for i in range(n_win + n_loss):
            ts = base + i * 60
            f.write(json.dumps({"ts": ts, "event": "OPEN", "pair": pair,
                                "direction": direction, "entry": 100.0, "qty": 1.0,
                                "strategy": strategy}) + "\n")
            win = i < n_win
            f.write(json.dumps({"ts": ts + 30, "event": "CLOSE", "pair": pair,
                                "direction": direction, "won": win,
                                "r": r_win if win else r_loss,
                                "pnl": pnl_win if win else pnl_loss}) + "\n")
    return path


def _cfg(**kw):
    base = dict(testnet=True, dry_run=False, live_confirm=False, leverage=8,
                max_total_risk_pct=2.0, risk_state_path="")
    base.update(kw)
    return SimpleNamespace(**base)


def _blockers(rep) -> str:
    return " | ".join(rep["blockers"])


class TestLiveReady(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.jp = os.path.join(self.tmp, "j.jsonl")
        self.env = mock.patch.dict(os.environ,
                                   {"STRATEGY_GATE": "true", "STRATEGY_BLOCK": "",
                                    "STRAT_MIN_N": "10", "STRAT_AVG_R": "0.10"})
        self.env.start()
        self.addCleanup(self.env.stop)

    # ---------- đạt hết cổng ----------
    def test_dat_het_cong(self):
        _mk(self.jp, 200, 100, direction="LONG")
        _mk(self.jp, 15, 5, direction="SHORT")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertTrue(rep["ok"], rep["blockers"])
        self.assertEqual(rep["verdict"], "HOAN THANH")
        self.assertEqual(rep["facts"]["n_all"], 320)

    # ---------- cửa sổ 14 ngày yếu (dù tổng vẫn có thể đẹp) ----------
    def test_cua_so_14_ngay_duoi_1_2_thi_chan(self):
        _mk(self.jp, 120, 100, direction="LONG")            # 7 ngày: PF 2.4
        _mk(self.jp, 10, 200, direction="LONG", days_ago=10.0)   # cũ, âm nặng
        _mk(self.jp, 10, 5, direction="SHORT")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("14 ngay", _blockers(rep))
        self.assertGreater(rep["windows"][7]["pf_r"], rep["windows"][14]["pf_r"])

    # ---------- PF($) thấp (phí ăn hết edge) ----------
    def test_pf_dollar_duoi_1_1_thi_chan(self):
        _mk(self.jp, 200, 100, pnl_win=1.0, pnl_loss=-2.0, direction="LONG")
        _mk(self.jp, 15, 5, pnl_win=1.0, pnl_loss=-2.0, direction="SHORT")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("PF($)", _blockers(rep))

    # ---------- chưa đủ mẫu ----------
    def test_n_toan_bo_duoi_300_thi_chan(self):
        _mk(self.jp, 60, 40, direction="LONG")
        _mk(self.jp, 10, 5, direction="SHORT")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("n lenh dong toan bo = 115 < 300", _blockers(rep))

    def test_thieu_mau_mot_huong_thi_chan(self):
        _mk(self.jp, 250, 100, direction="LONG")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("huong SHORT", _blockers(rep))

    # ---------- kill-switch / đòn bẩy ----------
    def test_kill_switch_tripped_thi_chan(self):
        _mk(self.jp, 200, 100, direction="LONG")
        _mk(self.jp, 15, 5, direction="SHORT")
        ks = os.path.join(self.tmp, "risk_state.json")
        with open(ks, "w", encoding="utf-8") as f:
            json.dump({"tripped": True, "reason": "daily loss"}, f)
        rep = LR.check(_cfg(risk_state_path=ks), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("kill-switch", _blockers(rep))

    def test_leverage_10_khi_pf_duoi_1_5_thi_chan(self):
        _mk(self.jp, 130, 200, direction="LONG")     # PF(R)=1.366 < 1.5
        _mk(self.jp, 10, 5, direction="SHORT")
        rep = LR.check(_cfg(leverage=10), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("LEVERAGE = 10 > 8", _blockers(rep))
        # leverage 8 thì không bị chặn bởi cổng đòn bẩy
        rep8 = LR.check(_cfg(leverage=8), journal_path=self.jp)
        self.assertNotIn("LEVERAGE", _blockers(rep8))

    def test_risk_tong_tren_2pct_thi_chan(self):
        _mk(self.jp, 200, 100, direction="LONG")
        _mk(self.jp, 15, 5, direction="SHORT")
        rep = LR.check(_cfg(max_total_risk_pct=3.0), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("MAX_TOTAL_RISK_PCT = 3.00%", _blockers(rep))

    # ---------- chiến lược âm ----------
    def test_chien_luoc_am_chua_block_thi_chan(self):
        _mk(self.jp, 200, 100, direction="LONG")
        _mk(self.jp, 15, 5, direction="SHORT")
        _mk(self.jp, 0, 12, direction="LONG", strategy="D_RANGE_REVERSAL")
        rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertIn("D_RANGE_REVERSAL", _blockers(rep))
        self.assertIn("CHUA nam trong STRATEGY_BLOCK", _blockers(rep))

    def test_chien_luoc_am_da_block_thi_khong_chan(self):
        _mk(self.jp, 200, 100, direction="LONG")
        _mk(self.jp, 15, 5, direction="SHORT")
        _mk(self.jp, 0, 12, direction="LONG", strategy="D_RANGE_REVERSAL")
        with mock.patch.dict(os.environ, {"STRATEGY_BLOCK": "D_RANGE_REVERSAL"}):
            rep = LR.check(_cfg(), journal_path=self.jp)
        self.assertTrue(rep["ok"], rep["blockers"])
        self.assertNotIn("D_RANGE_REVERSAL", _blockers(rep))
        self.assertTrue(any("D_RANGE_REVERSAL" in w for w in rep["warnings"]))

    # ---------- biên ----------
    def test_journal_khong_ton_tai(self):
        rep = LR.check(_cfg(), journal_path=os.path.join(self.tmp, "khong-co.jsonl"))
        self.assertFalse(rep["ok"])
        self.assertIn("n=0", _blockers(rep))

    def test_window_pairs_0_la_tat_ca(self):
        _mk(self.jp, 5, 5)
        opens, closes = LR.load_journal(self.jp)
        pairs, _ = LR.match_pairs(opens, closes)
        self.assertEqual(len(LR.window_pairs(pairs, 0, time.time())), 10)
        self.assertEqual(len(LR.window_pairs(pairs, 1, time.time())), 10)

    def test_main_tra_exit_code_2_khi_chua_dat(self):
        rc = LR.main(["--journal", os.path.join(self.tmp, "rong.jsonl")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()

