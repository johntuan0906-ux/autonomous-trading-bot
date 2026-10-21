# -*- coding: utf-8 -*-
"""Test `tools/council_daemon.py` — hoi dong chay NEN 24/7 (dry-run mac dinh).

Chot 6 tinh chat de "chay lien tuc" khong bien thanh "chay vo toi":
1. Agenda lap tu BANG CHUNG THAT (journal/cau hoi ton/tai phat/cau hinh rui ro/nhip tim);
2. Dedup theo TTL (khong hoi lai cung van de moi 15 phut);
3. Tran chi phi + tran so chu ky/ngay (cham tran ⇒ nghi, ghi ro ly do);
4. Dry-run KHONG goi LLM va KHONG danh dau `seen`/cursor (de lan live con thay);
5. Live: ghi outbox + `seen` + cursor + chi phi; 1 chu de loi khong lam chet vong;
6. An toan: khong import exchange/bot, khong ghi `.env`, lock 1 tien trinh.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import council_daemon as CD      # noqa: E402


def _write(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return p


def _close(ts, r, pair="BTC/USDT:USDT", partial=False):
    return {"ts": ts, "event": "CLOSE", "pair": pair, "direction": "LONG", "r": r,
            "won": r > 0, "reason": "SL", "partial": partial}


class _Env:
    """Bo duong dan trong thu muc tam (khong dung file that cua instance)."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.journal = tmp / "journal.jsonl"
        self.ops = tmp / "ops_questions.json"
        self.regress = tmp / "regress_watch.json"
        self.env = tmp / ".env"
        self.pause = tmp / "entries_pause.json"
        self.bothb = tmp / "heartbeat.json"
        self.state = tmp / "council_daemon.json"
        self.hb = tmp / "council_heartbeat.json"
        self.lock = tmp / "council_daemon.lock"
        self.outbox = tmp / "council_outbox.json"

    def journal_lines(self, rows):
        self.journal.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
                                encoding="utf-8")

    def env_file(self, per=1.2, day=2.0, total=1.6):
        self.env.write_text("RISK_PER_TRADE_PCT=%s\nMAX_DAILY_LOSS_PCT=%s\n"
                            "MAX_TOTAL_RISK_PCT=%s\n" % (per, day, total), encoding="utf-8")

    def kwargs(self):
        return {"state_path": self.state, "heartbeat_path": self.hb, "lock_path": self.lock,
                "outbox_path": self.outbox, "journal_path": self.journal,
                "ops_path": self.ops, "regress_path": self.regress, "env_path": self.env,
                "pause_path": self.pause, "bot_heartbeat": self.bothb}


class TestJournalCloses(unittest.TestCase):
    def test_chi_lay_CLOSE_sau_moc_va_bo_partial(self):
        with tempfile.TemporaryDirectory() as t:
            e = _Env(Path(t))
            e.journal_lines([{"ts": 100, "event": "OPEN", "pair": "X"},
                             _close(200, -1.0),
                             _close(300, 0.5, partial=True),
                             _close(400, -2.0)])
            rows, mx, cut = CD.journal_closes(e.journal, since=150)
            self.assertEqual([r["ts"] for r in rows], [200, 400], "chi CLOSE, khong partial")
            self.assertEqual(mx, 400.0)
            self.assertFalse(cut)


class TestRiskDrift(unittest.TestCase):
    def test_2_lo_la_trip(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / ".env"
            p.write_text("RISK_PER_TRADE_PCT=1.2\nMAX_DAILY_LOSS_PCT=2.0\n"
                         "MAX_TOTAL_RISK_PCT=1.6\n", encoding="utf-8")
            d = CD.risk_drift(p)
            self.assertEqual(d["losses_to_trip"], 2)
            self.assertEqual(d["ratio"], 1.67)

    def test_tran_rong_thi_khong_bao(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / ".env"
            p.write_text("RISK_PER_TRADE_PCT=1.0\nMAX_DAILY_LOSS_PCT=5.0\n", encoding="utf-8")
            self.assertIsNone(CD.risk_drift(p))

    def test_thieu_file_tra_None(self):
        self.assertIsNone(CD.risk_drift(Path(tempfile.gettempdir()) / "khong-co.env"))


def _agenda(e: _Env, now: float, cursor: float):
    if not e.bothb.exists():          # mac dinh: bot con song (chi test nao can moi lam cu)
        _write(e.bothb, {"ts": now})
    return CD.build_agenda(state={"cursor": {"journal_ts": cursor}}, now=now,
                           journal_path=e.journal, ops_path=e.ops,
                           regress_path=e.regress, env_path=e.env,
                           pause_path=e.pause, bot_heartbeat=e.bothb)


class TestBuildAgenda(unittest.TestCase):
    def test_3_lenh_dong_tao_chu_de_hieu_nang(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            e.journal_lines([_close(now - 100, -1.0), _close(now - 50, -1.5),
                             _close(now - 10, 0.2)])
            e.env_file(per=1.0, day=5.0)
            ag = _agenda(e, now, now - 3600)
            perf = [x for x in ag["topics"] if x["kind"] == "perf"]
            self.assertEqual(len(perf), 1)
            self.assertIn("-2.30R", " ".join(perf[0]["context"]))
            self.assertEqual(perf[0]["severity"], "high")

    def test_1_lenh_nho_khong_tao_chu_de(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            e.journal_lines([_close(now - 10, 0.4)])
            e.env_file(per=1.0, day=5.0)
            self.assertEqual(_agenda(e, now, now - 3600)["topics"], [])

    def test_cau_hoi_ton_dong_qua_24h(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            _write(e.ops, [{"ts": now - 30 * 3600, "question": "reset kill-switch?"}])
            e.env_file(per=1.0, day=5.0)
            self.assertEqual([x["key"] for x in _agenda(e, now, now)["topics"]], ["ops:1"])

    def test_tai_phat_lop_loi(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            _write(e.regress, {"last_problems": ["child CHET", "-2022 tai phat"]})
            e.env_file(per=1.0, day=5.0)
            top = _agenda(e, now, now)["topics"][0]
            self.assertEqual(top["key"], "regress:2")
            self.assertEqual(top["kind"], "regress")

    def test_pause_khong_han_va_nhip_tim_cu(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            _write(e.pause, {"paused": True, "reason": "cho vi the dong"})
            _write(e.bothb, {"ts": now - 3600, "phase": "manage", "round": 5})
            e.env_file(per=1.0, day=5.0)
            keys = [x["key"] for x in _agenda(e, now, now)["topics"]]
            self.assertIn("pause:no-until", keys)
            self.assertIn("bot:heartbeat", keys)

    def test_pause_co_han_thi_khong_bao(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            _write(e.pause, {"paused": True, "reason": "x", "until": now + 3600})
            _write(e.bothb, {"ts": now - 5})
            e.env_file(per=1.0, day=5.0)
            self.assertEqual(_agenda(e, now, now)["topics"], [])


class TestDedup(unittest.TestCase):
    def test_trong_TTL_thi_bo_qua(self):
        now = 10_000.0
        topics = [{"key": "risk:x"}, {"key": "perf:1"}]
        keep, skipped = CD.filter_dedup(topics, {"risk:x": now - 60}, now=now, ttl_s=3600)
        self.assertEqual([t["key"] for t in keep], ["perf:1"])
        self.assertEqual(skipped[0]["key"], "risk:x")

    def test_qua_TTL_thi_hoi_lai(self):
        now = 10_000.0
        keep, skipped = CD.filter_dedup([{"key": "risk:x"}], {"risk:x": now - 7200},
                                       now=now, ttl_s=3600)
        self.assertEqual(len(keep), 1)
        self.assertEqual(skipped, [])



def _ready(tmp: Path, now: float) -> _Env:
    """Instance tam co 3 lenh dong (tao chu de), cau hinh rui ro sach, bot con song."""
    e = _Env(tmp)
    e.journal_lines([_close(now - 100, -1.0), _close(now - 50, -1.6),
                     _close(now - 10, 0.3)])
    e.env_file(per=1.0, day=5.0)
    _write(e.bothb, {"ts": now, "phase": "scan", "round": 1})
    return e


class TestRunCycle(unittest.TestCase):
    NOW = 10_000.0

    def test_dry_run_khong_goi_LLM_va_khong_danh_dau_seen(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            called = []

            def boom(payload):
                called.append(payload)
                raise AssertionError("dry-run KHONG duoc goi LLM")

            rep = CD.run_cycle(now=self.NOW, live=False, council_fn=boom, **e.kwargs())
            self.assertEqual(called, [])
            self.assertEqual(rep["mode"], "dry-run")
            self.assertEqual(len(rep["results"]), 1)
            self.assertEqual(rep["results"][0]["verdict"], "DRY_RUN")
            st = json.loads(e.state.read_text(encoding="utf-8"))
            self.assertFalse(st.get("seen"), "dry-run khong duoc danh dau da hoi")
            self.assertFalse(st.get("cursor"), "dry-run khong duoc nhay cursor")
            self.assertEqual(st["cycles"][CD._day(self.NOW)], 1)
            self.assertTrue(e.outbox.exists(), "phai ghi outbox de nguoi doc duoc")
            self.assertTrue(json.loads(e.hb.read_text(encoding="utf-8"))["ok"])

    def test_live_ghi_phieu_chi_phi_cursor_va_seen(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)

            def fake(payload):
                return {"votes": {"m1": {"action": "VETO", "confidence": 0.9,
                                         "reasons": ["x"], "cost_usd": 0.01}}}

            rep = CD.run_cycle(now=self.NOW, live=True, council_fn=fake, **e.kwargs())
            self.assertEqual(rep["mode"], "live")
            r = rep["results"][0]
            self.assertEqual(r["verdict"], "VETO")
            self.assertEqual(r["n_veto"], 1)
            self.assertAlmostEqual(rep["cost_usd"], 0.01)
            st = json.loads(e.state.read_text(encoding="utf-8"))
            self.assertGreater(st["cursor"]["journal_ts"], 0)
            self.assertTrue(any(k.startswith("perf:") for k in st["seen"]))
            self.assertAlmostEqual(st["spend"][CD._day(self.NOW)], 0.01, places=6)

    def test_tran_chi_phi_chan_truoc_khi_goi_LLM(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.state, {"spend": {CD._day(self.NOW): 5.0}})
            called = []
            rep = CD.run_cycle(now=self.NOW, live=True, max_usd_day=1.0,
                               council_fn=lambda p: called.append(p), **e.kwargs())
            self.assertEqual(rep["mode"], "budget_blocked")
            self.assertEqual(called, [])
            self.assertIn("tran", rep["reason"])


    def test_tran_so_chu_ky_moi_ngay(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.state, {"cycles": {CD._day(self.NOW): 10}})
            rep = CD.run_cycle(now=self.NOW, live=True, max_cycles_day=10,
                               council_fn=lambda p: None, **e.kwargs())
            self.assertEqual(rep["mode"], "cycles_blocked")

    def test_lock_khi_pid_con_song_thi_thoat(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.lock, {"pid": 4242})
            with mock.patch.object(CD, "pid_alive", return_value=True):
                rep = CD.run_cycle(now=self.NOW, live=True,
                                   council_fn=lambda p: None, **e.kwargs())
            self.assertEqual(rep["mode"], "locked")
            self.assertFalse(rep["lock"]["ok"])

    def test_lock_pid_chet_thi_chiem_quyen(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.lock, {"pid": 4242})
            with mock.patch.object(CD, "pid_alive", return_value=False):
                rep = CD.run_cycle(now=self.NOW, **e.kwargs())
            self.assertTrue(rep["lock"]["ok"])
            self.assertTrue(rep["lock"]["took_over"])

    def test_mot_chu_de_loi_khong_lam_chet_vong(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)

            def bad(payload):
                raise RuntimeError("provider chet")

            rep = CD.run_cycle(now=self.NOW, live=True, council_fn=bad, **e.kwargs())
            self.assertEqual(rep["mode"], "live")
            self.assertEqual(rep["results"][0]["verdict"], "ERROR")
            self.assertIn("provider chet", rep["results"][0]["error"])
            self.assertTrue(json.loads(e.hb.read_text(encoding="utf-8"))["ok"])

    def test_dedup_chan_vong_sau_trong_TTL(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            e.env_file(per=1.2, day=2.0)     # chu de rui ro LUON con (key on dinh)

            def fake(payload):
                return {"votes": {"m1": {"action": "ALLOW", "confidence": 0.5,
                                         "reasons": ["ok"], "cost_usd": 0.0}}}

            r1 = CD.run_cycle(now=self.NOW, live=True, council_fn=fake, **e.kwargs())
            r2 = CD.run_cycle(now=self.NOW + 60, live=True, council_fn=fake, **e.kwargs())
            self.assertTrue(any(x["key"] == "risk:daily-vs-trade" for x in r1["results"]))
            self.assertEqual(r2["results"], [], "trong TTL khong duoc hoi lai")
            self.assertEqual([s["key"] for s in r2["skipped"]], ["risk:daily-vs-trade"])

    def test_nguon_khong_dung_toi_duong_tien(self):
        """Hoi dong nen CHI duoc de xuat: khong import exchange/bot, khong dung key."""
        src = Path(CD.__file__).read_text(encoding="utf-8")
        for bad in ("import exchange", "from exchange", "from bot import",
                    "BINANCE_API_KEY", "create_order", "close_position"):
            self.assertNotIn(bad, src,
                             "council_daemon khong duoc cham duong tien: %r" % bad)

