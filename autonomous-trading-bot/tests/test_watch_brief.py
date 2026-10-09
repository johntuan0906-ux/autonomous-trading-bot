"""Test `restart_when_flat` (restart khi hết vị thế) + `market_brief` (bản tin thị trường)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import market_brief as MB
import restart_when_flat as RWF


class FakeEx:
    def __init__(self, rows=None, boom=False):
        self.rows = rows or []
        self.boom = boom
        self.calls = 0

    def fetch_positions(self, symbols=None):
        self.calls += 1
        if self.boom:
            raise RuntimeError("mang loi")
        return self.rows


def _pos(c=1.0):
    return {"symbol": "SOL/USDT:USDT", "contracts": c}


class TestRestartWhenFlat(unittest.TestCase):
    def setUp(self):
        self._p = mock.patch.object(RWF, "log", lambda m: None)
        self._p.start()
        self.addCleanup(self._p.stop)

    def test_dem_vi_the_dung(self):
        self.assertEqual(RWF.open_positions(FakeEx([_pos(1), _pos(0), {"contracts": None}])), 1)
        self.assertEqual(RWF.open_positions(FakeEx([])), 0)

    def test_doc_loi_tra_None_fail_safe(self):
        self.assertIsNone(RWF.open_positions(FakeEx(boom=True)))
        self.assertIsNone(RWF.open_positions(None))

    def test_cho_den_khi_het_vi_the_roi_restart(self):
        seq = [3, 1, 0]
        st = {"n": 0, "restart": 0}

        def fetch(_ex):
            v = seq[min(st["n"], len(seq) - 1)]
            st["n"] += 1
            return v

        def do_restart():
            st["restart"] += 1
            return {"ok": True}

        t = {"v": 0.0}
        res = RWF.wait_flat(None, poll=1.0, max_hours=1.0, fetch=fetch, do_restart=do_restart,
                            now=lambda: t["v"],
                            sleep=lambda s: t.__setitem__("v", t["v"] + s))
        self.assertTrue(res["ok"])
        self.assertEqual(st["restart"], 1)
        self.assertEqual(res["checks"], 3)

    def test_doc_loi_lien_tuc_thi_KHONG_restart(self):
        st = {"restart": 0}
        t = {"v": 0.0}
        res = RWF.wait_flat(None, poll=60.0, max_hours=1.0,
                            fetch=lambda _ex: None,
                            do_restart=lambda: (st.__setitem__("restart", st["restart"] + 1),
                                                {"ok": True})[1],
                            now=lambda: t["v"],
                            sleep=lambda s: t.__setitem__("v", t["v"] + s))
        self.assertFalse(res["ok"])
        self.assertEqual(st["restart"], 0, "khong doc duoc san -> khong duoc restart")
        self.assertIn("het thoi gian cho", res["err"])

    def test_dry_run_khong_restart(self):
        st = {"restart": 0}
        res = RWF.wait_flat(None, dry_run=True, fetch=lambda _ex: 0,
                            do_restart=lambda: (st.__setitem__("restart", 1), {"ok": True})[1])
        self.assertTrue(res["ok"])
        self.assertEqual(st["restart"], 0)

    def test_supervisor_pid_doc_lock(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "logs").mkdir()
        (tmp / "logs" / ".supervisor.lock").write_text("12345", encoding="utf-8")
        self.assertEqual(RWF.supervisor_pid(tmp), 12345)
        self.assertEqual(RWF.supervisor_pid(Path(tempfile.mkdtemp())), 0)


class TestMarketBrief(unittest.TestCase):
    def test_parse_last_round(self):
        txt = ("2026-10-09 20:29:19,987 INFO round 30 monitor={} -> "
               "[{'symbol': 'SOL/USDT:USDT', 'status': 'SKIP_RISK', 'reason': 'tran risk'}, "
               "{'symbol': 'ADA/USDT:USDT', 'status': 'BLOCKED_LEARN'}]\n")
        out = MB.parse_last_round(txt)
        self.assertEqual(out["round"], 30)
        self.assertEqual(len(out["rows"]), 2)
        self.assertEqual(out["rows"][0]["status"], "SKIP_RISK")
        self.assertIn("tran risk", out["rows"][0]["reason"])
        self.assertEqual(out["rows"][1]["reason"], "")

    def test_parse_last_round_lay_vong_cuoi(self):
        txt = ("round 1 monitor={} -> [{'symbol': 'A', 'status': 'WAIT'}]\n"
               "round 2 monitor={} -> [{'symbol': 'B', 'status': 'COOLDOWN'}]\n")
        out = MB.parse_last_round(txt)
        self.assertEqual(out["round"], 2)
        self.assertEqual(out["rows"][0]["symbol"], "B")

    def test_parse_last_round_rong(self):
        self.assertEqual(MB.parse_last_round(""), {"round": 0, "rows": []})

    def test_learner_section_sap_xep_theo_do_lon(self):
        tmp = Path(tempfile.mkdtemp()) / "learner.json"
        tmp.write_text(json.dumps({"w": {"a": 0.1, "b": -0.9, "c": 0.5}, "b": 0.02, "n": 7}),
                       encoding="utf-8")
        out = MB.learner_section(tmp, top=2)
        self.assertEqual(out["n"], 7)
        self.assertEqual([k for k, _ in out["top"]], ["b", "c"])

    def test_learner_section_thieu_file(self):
        out = MB.learner_section(Path(tempfile.mkdtemp()) / "khong.json")
        self.assertEqual(out["n"], 0)
        self.assertEqual(out["top"], [])

    def test_render_du_5_phan(self):
        rep = {"ts_human": "09/10/2026 21:00:00", "testnet": False,
               "cfg": SimpleNamespace(max_total_risk_pct=2.0),
               "news": {"score": -0.2, "n": 12, "urgent": 1, "headlines": ["tin A", "tin B"]},
               "context": [{"symbol": "SOL/USDT:USDT", "price": 110.5, "atr_pct": 0.012,
                            "regime": "COMPRESSION", "funding": 0.0001, "oi_change": 1.5}],
               "positions": {"equity": 22.6, "notional": 41.0,
                             "positions": [{"symbol": "XRP/USDT:USDT", "side": "short",
                                            "qty": 4.6, "notional": 6.4, "uPnL": 0.08}]},
               "last_round": {"round": 30, "rows": [{"symbol": "SOL/USDT:USDT",
                                                     "status": "SKIP_RISK",
                                                     "reason": "tran risk"}]},
               "learner": {"n": 188, "bias": 0.01, "top": [("sent", 0.53), ("macd", -0.34)]}}
        txt = MB.render(rep)
        for want in ("TIN TUC", "BOI CANH", "VI THE", "VI SAO CHUA VAO LENH",
                     "BOT HOC DUOC GI", "COMPRESSION", "SKIP_RISK", "LIVE", "sent"):
            self.assertIn(want, txt)

    def test_news_section_khong_crash_khi_loi(self):
        with mock.patch.dict("sys.modules", {"sentiment": None}):
            out = MB.news_section(SimpleNamespace(sentiment_cache_sec=1, cryptopanic_token=""))
        self.assertIn("err", out)


if __name__ == "__main__":
    unittest.main()
