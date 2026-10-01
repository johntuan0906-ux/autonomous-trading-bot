"""Test Phase 5 (live_guard) + positions.py — thuan tuy, khong goi san/LLM."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from types import SimpleNamespace

import live_guard as LG
import positions as P


def _journal(path: str, n_win: int, n_loss: int, r_win: float = 2.0,
             r_loss: float = -1.0, pair: str = "BTC/USDT:USDT") -> str:
    """Ghi journal gia: n_win lenh thang (r=+2R) + n_loss lenh thua (r=-1R)."""
    ts = time.time() - 3600
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n_win + n_loss):
            f.write(json.dumps({"event": "OPEN", "pair": pair, "direction": "LONG",
                                "entry": 100.0, "qty": 1.0, "ts": ts + i}) + "\n")
            win = i < n_win
            f.write(json.dumps({"event": "CLOSE", "pair": pair, "won": win,
                                "r": r_win if win else r_loss,
                                "pnl": 10.0 if win else -5.0,
                                "ts": ts + i + 60}) + "\n")
    return path


def _cfg(**kw):
    base = dict(testnet=False, dry_run=False, live_confirm=True, leverage=8,
                max_total_risk_pct=2.0, risk_state_path="", managed_state_path="")
    base.update(kw)
    return SimpleNamespace(**base)


class TestLiveGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.jp = _journal(os.path.join(self.tmp, "j.jsonl"), 30, 20)  # n=50 PF=3.0

    def test_testnet_thi_khong_chan(self):
        rep = LG.check(_cfg(testnet=True, live_confirm=False), journal_path=self.jp)
        self.assertTrue(rep["ok"])
        self.assertFalse(rep["live"])          # interlock khong ap dung

    def test_live_du_dieu_kien_thi_cho_phep(self):
        rep = LG.check(_cfg(), journal_path=self.jp)
        self.assertTrue(rep["ok"], rep["blockers"])
        self.assertEqual(rep["blockers"], [])
        self.assertEqual(rep["facts"]["n_closed"], 50)

    def test_live_thieu_live_confirm_thi_chan(self):
        rep = LG.check(_cfg(live_confirm=False), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("LIVE_CONFIRM" in b for b in rep["blockers"]))

    def test_live_chua_du_mau_thi_chan(self):
        jp = _journal(os.path.join(self.tmp, "small.jsonl"), 6, 4)   # n=10
        rep = LG.check(_cfg(), journal_path=jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("10 lenh dong" in b for b in rep["blockers"]))

    def test_live_pf_thap_thi_chan(self):
        jp = _journal(os.path.join(self.tmp, "bad.jsonl"), 20, 40)   # PF=1.0 < 1.2
        rep = LG.check(_cfg(), journal_path=jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("PF(R)" in b for b in rep["blockers"]))

    def test_live_risk_qua_cao_thi_chan(self):
        rep = LG.check(_cfg(max_total_risk_pct=3.0), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("MAX_TOTAL_RISK_PCT=3" in b for b in rep["blockers"]))

    def test_live_lev_cao_khi_pf_thap_thi_chan(self):
        # PF=3.0 (>=1.5) -> lev 10 duoc phep
        ok = LG.check(_cfg(leverage=10), journal_path=self.jp)
        self.assertTrue(ok["ok"], ok["blockers"])
        # PF dung bang 1.5 (bien) -> van duoc phep lev 10 (dung "<" khong phai "<=")
        jp = _journal(os.path.join(self.tmp, "mid.jsonl"), 25, 25, r_win=1.5,
                      r_loss=-1.0)                                   # PF = 37.5/25 = 1.5
        rep = LG.check(_cfg(leverage=10), journal_path=jp)
        self.assertTrue(rep["ok"], rep["blockers"])
        # PF = 1.4 (n=50) -> lev 9 bi chan (chua chung minh edge thi khong tang don)
        jp2 = _journal(os.path.join(self.tmp, "lo.jsonl"), 25, 25, r_win=1.4,
                       r_loss=-1.0)                                  # PF = 35/25 = 1.4
        rep2 = LG.check(_cfg(leverage=9), journal_path=jp2)
        self.assertFalse(rep2["ok"])
        self.assertTrue(any("LEVERAGE=9" in b for b in rep2["blockers"]))

    def test_live_lev_tren_10_luon_chan(self):
        rep = LG.check(_cfg(leverage=12), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("LEVERAGE=12" in b for b in rep["blockers"]))

    def test_kill_switch_tripped_thi_chan(self):
        ks = os.path.join(self.tmp, "risk.json")
        with open(ks, "w", encoding="utf-8") as f:
            json.dump({"tripped": True, "reason": "daily loss 2.13%"}, f)
        rep = LG.check(_cfg(risk_state_path=ks), journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("kill-switch" in b for b in rep["blockers"]))

    def test_enforce_log_bao_chan(self):
        class _L:
            def __init__(self):
                self.errors, self.warns = [], []

            def error(self, *a, **k):
                self.errors.append(a[0] if len(a) == 1 else (a[0] % a[1:]))

            def warning(self, *a, **k):
                self.warns.append(a)

            def info(self, *a, **k):
                pass

        lg = _L()
        rep = LG.enforce(_cfg(live_confirm=False), log=lg, journal_path=self.jp)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("LIVE INTERLOCK CHAN" in str(e) for e in lg.errors))

    def test_cli_testnet_tra_exit_0(self):
        self.assertEqual(LG.main(["--journal", self.jp]), 0)


class TestPositionsDiagnostic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.jp = os.path.join(self.tmp, "j.jsonl")
        with open(self.jp, "w", encoding="utf-8") as f:
            # 1 cap duoc ghep day du (FIFO) + 1 OPEN mo coi (lich su)
            f.write(json.dumps({"event": "OPEN", "pair": "BTC/USDT:USDT",
                                "direction": "SHORT", "entry": 84000, "qty": 0.036,
                                "ts": 1000}) + "\n")
            f.write(json.dumps({"event": "CLOSE", "pair": "BTC/USDT:USDT", "won": True,
                                "r": 1.0, "pnl": 5.0, "ts": 2000}) + "\n")
            f.write(json.dumps({"event": "OPEN", "pair": "ETH/USDT:USDT",
                                "direction": "LONG", "entry": 2715, "qty": 0.62,
                                "ts": 3000}) + "\n")

    def test_journal_orphans_chi_lay_open_chua_ghep(self):
        rows = P.journal_orphans(self.jp)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pair"], "ETH/USDT:USDT")

    def test_collect_voi_san_gia_va_phat_hien_vi_the_mo_tay(self):
        class _Ex:
            def fetch_positions(self, symbols=None):
                return [{"symbol": "BTC/USDT:USDT", "side": "SHORT", "contracts": 0.1812,
                         "entryPrice": 83978.75, "markPrice": 83769.5,
                         "unrealizedPnl": 37.88, "leverage": 8}]

        ms = os.path.join(self.tmp, "ms.json")
        with open(ms, "w", encoding="utf-8") as f:
            json.dump({"trades": {}}, f)                       # bot khong quan ly gi
        cfg = SimpleNamespace(managed_state_path=ms,
                              risk_state_path=os.path.join(self.tmp, "none.json"))
        # khong loc cap: thay du vi the that + orphan cua fixture (BTC da ghep CLOSE,
        # ETH moi la OPEN mo coi) — KHONG bao gio doc journal that trong test.
        rep = P.collect(cfg, ex=_Ex(), journal_path=self.jp)
        self.assertEqual(len(rep["positions"]), 1)
        self.assertEqual(rep["positions"][0]["qty"], 0.1812)
        self.assertEqual(len(rep["unmanaged"]), 1)             # -> vi the MO TAY
        self.assertEqual([r["pair"] for r in rep["orphans"]], ["ETH/USDT:USDT"])
        # loc theo cap BTC: vong BTC trong fixture da duoc ghep -> khong con orphan
        rep_btc = P.collect(cfg, ex=_Ex(), pair_filter="BTC", journal_path=self.jp)
        self.assertEqual(rep_btc["orphans"], [])

    def test_collect_khi_state_co_trade_thi_khong_coi_la_mo_tay(self):
        class _Ex:
            def fetch_positions(self, symbols=None):
                return [{"symbol": "BTC/USDT:USDT", "side": "SHORT", "contracts": 0.05,
                         "entryPrice": 84000, "markPrice": 84000,
                         "unrealizedPnl": 0.0}]

        ms = os.path.join(self.tmp, "ms2.json")
        with open(ms, "w", encoding="utf-8") as f:
            json.dump({"trades": {"BTC/USDT:USDT": {"direction": "SHORT",
                                                    "entry": 84000, "qty": 0.05}}}, f)
        cfg = SimpleNamespace(managed_state_path=ms, risk_state_path="")
        rep = P.collect(cfg, ex=_Ex(), journal_path=self.jp)
        self.assertEqual(rep["unmanaged"], [])
        self.assertIn("BTC/USDT:USDT", rep["managed"])

    def test_collect_khi_san_loi_thi_bao_loi_khong_crash(self):
        class _Bad:
            def fetch_positions(self, symbols=None):
                raise RuntimeError("API down")

        cfg = SimpleNamespace(managed_state_path="", risk_state_path="")
        rep = P.collect(cfg, ex=_Bad(), journal_path=self.jp)
        self.assertEqual(rep["positions"], [])
        self.assertIn("API down", rep["pos_error"])


if __name__ == "__main__":
    unittest.main()
