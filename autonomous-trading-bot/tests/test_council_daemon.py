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
    def test_8_lenh_dong_tao_chu_de_hieu_nang(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            # 8 lenh trong cua so 6h, tong -6R => bat thuong
            e.journal_lines([_close(now - 3000 + i * 60, -1.0 if i < 6 else 0.0)
                             for i in range(8)])
            e.env_file(per=1.0, day=5.0)
            ag = _agenda(e, now, 0.0)
            perf = [x for x in ag["topics"] if x["kind"] == "perf"]
            self.assertEqual(len(perf), 1)
            self.assertIn("-6.00R", " ".join(perf[0]["context"]))
            self.assertEqual(perf[0]["severity"], "high")

    def test_7_lenh_chua_du_mau_khong_ket_luan(self):
        with tempfile.TemporaryDirectory() as t:
            now = 10_000.0
            e = _Env(Path(t))
            e.journal_lines([_close(now - 1000 + i * 60, -2.0) for i in range(7)])
            e.env_file(per=1.0, day=5.0)
            self.assertEqual(_agenda(e, now, 0.0)["topics"], [], "duoi MIN_CLOSES = nhieu")

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
    """Instance tam co CHU DE ON DINH (cau hinh rui ro 2 lo ⇒ trip), bot con song."""
    e = _Env(tmp)
    e.env_file(per=1.2, day=2.0)
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
            self.assertFalse(st.get("cycles"), "dry-run KHONG tinh la chu ky goi LLM")
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
            self.assertIn("risk:daily-vs-trade", st["seen"])
            self.assertIn("risk", st["seen_kind"])
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

    def test_fallback_bo_sung_khi_thieu_phieu(self):
        """Đo thật 16:24: 1/2 model trả phiếu ⇒ phải hỏi bổ sung bằng model dự phòng."""
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)

            def primary(payload):
                return {"votes": {"m1": {"action": "VETO", "confidence": 0.8,
                                         "reasons": ["x"], "cost_usd": 0.004}}}

            def fallback(payload):
                return {"votes": {"m2": {"action": "ALLOW", "confidence": 0.6,
                                         "reasons": ["y"], "cost_usd": 0.004}}}

            rep = CD.run_cycle(now=self.NOW, live=True, council_fn=primary,
                               fallback_fn=fallback, min_votes=2, **e.kwargs())
            r = rep["results"][0]
            self.assertEqual(r["n"], 2, "phai gop phieu du phong")
            self.assertTrue(r.get("fallback_used"))
            self.assertEqual(r["n_allow"], 1)
            self.assertEqual(r["n_veto"], 1)

    def test_khong_goi_fallback_khi_du_phieu(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            called = []

            def primary(payload):
                return {"votes": {m: {"action": "VETO", "confidence": 0.9, "reasons": ["x"],
                                      "cost_usd": 0.0} for m in ("m1", "m2")}}

            rep = CD.run_cycle(now=self.NOW, live=True, council_fn=primary,
                               fallback_fn=lambda p: called.append(1), min_votes=2,
                               **e.kwargs())
            self.assertEqual(called, [])
            self.assertFalse(rep["results"][0].get("fallback_used"))

    def test_nguon_khong_dung_toi_duong_tien(self):
        """Hoi dong nen CHI duoc de xuat: khong import exchange/bot, khong dung key."""
        src = Path(CD.__file__).read_text(encoding="utf-8")
        for bad in ("import exchange", "from exchange", "from bot import",
                    "BINANCE_API_KEY", "create_order", "close_position"):
            self.assertNotIn(bad, src,
                             "council_daemon khong duoc cham duong tien: %r" % bad)



class TestTaskScheduler(unittest.TestCase):
    """LIVE phai co task RIENG (`ATB-Council-Live`) — khong de len task TESTNET."""

    def test_task_command_chay_once_va_co_live(self):
        c = CD.task_command(live=True, python_exe="C:/py/pythonw.exe", script="C:/x/cd.py")
        self.assertIn("pythonw.exe", c)
        self.assertIn("--once", c)
        self.assertIn("--live", c)
        self.assertNotIn("--live", CD.task_command(live=False))

    def test_task_command_mang_tran_chi_phi(self):
        c = CD.task_command(live=True, python_exe="C:/py/pythonw.exe", script="C:/x/cd.py",
                            extra="--max-usd-day 0.3 --max-models 2 --max-topics 2")
        for part in ("--max-usd-day 0.3", "--max-models 2", "--max-topics 2"):
            self.assertIn(part, c, "task live phai mang tran chi phi da duyet")

    def test_task_argv_mang_dung_ten(self):
        argv = CD.task_argv("install", "ATB-Council-Live", "cmd", 15)
        joined = " ".join(str(a) for a in argv)
        self.assertIn("ATB-Council-Live", joined)
        self.assertIn("MINUTE", joined.upper())
        self.assertIn("15", joined)


class TestNhipTimVaTran(unittest.TestCase):
    """(21/10) B-027: chạm trần KHÔNG được làm mất nhịp tim, và không được tính là 'đã hỏi'.

    Đo thật: daemon TESTNET chạy 15 phút/lần ở chế độ live; mỗi lần *không có chủ đề* vẫn
    bị tính 1 chu kỳ ⇒ hết trần 12 sau ~3 giờ ⇒ `cycles_blocked` **return trước khi ghi nhịp
    tim** ⇒ `--status` báo "KHONG CO NHIP" (nhịp cũ 4,6 giờ) dù daemon hoàn toàn khoẻ.
    """
    NOW = 10_000.0

    def test_khong_co_chu_de_thi_khong_tinh_chu_ky(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            e.env_file(per=1.0, day=5.0)      # khong con chu de nao
            rep = CD.run_cycle(now=self.NOW, live=True, council_fn=lambda p: {},
                               **e.kwargs())
            self.assertEqual(rep["topics"], [])
            st = json.loads(e.state.read_text(encoding="utf-8"))
            self.assertFalse(st.get("cycles"), "khong hoi gi thi khong duoc tinh luot")
            self.assertTrue(json.loads(e.hb.read_text(encoding="utf-8"))["ok"])

    def test_cham_tran_van_ghi_nhip_tim(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.state, {"cycles": {CD._day(self.NOW): 99}})
            rep = CD.run_cycle(now=self.NOW, live=True, max_cycles_day=12,
                               council_fn=lambda p: None, **e.kwargs())
            self.assertEqual(rep["mode"], "cycles_blocked")
            hb = json.loads(e.hb.read_text(encoding="utf-8"))
            self.assertTrue(hb["blocked"], "phai noi ro la bi chan, khong phai im lang")
            self.assertEqual(hb["ts"], self.NOW)

    def test_cham_tran_chi_phi_van_ghi_nhip_tim(self):
        with tempfile.TemporaryDirectory() as t:
            e = _ready(Path(t), self.NOW)
            _write(e.state, {"spend": {CD._day(self.NOW): 5.0}})
            rep = CD.run_cycle(now=self.NOW, live=True, max_usd_day=1.0,
                               council_fn=lambda p: None, **e.kwargs())
            self.assertEqual(rep["mode"], "budget_blocked")
            hb = json.loads(e.hb.read_text(encoding="utf-8"))
            self.assertTrue(hb["blocked"])
            self.assertIn("tran", hb["reason"])


class TestKindCooldown(unittest.TestCase):
    """Cùng MỘT LOẠI chủ đề không được hỏi lại trong cooldown (chống đốt tiền 96 lần/ngày)."""

    def test_cung_loai_bi_chan_trong_cooldown(self):
        now = 10_000.0
        keep, skipped = CD.filter_dedup([{"key": "perf:120:-4.2", "kind": "perf"}], {},
                                       now=now, ttl_s=0.0,
                                       kind_seen={"perf": now - 60},
                                       kind_cooldown_s={"perf": 6 * 3600.0})
        self.assertEqual(keep, [])
        self.assertIn("kind_cooldown_s", skipped[0])

    def test_khac_loai_khong_bi_chan(self):
        now = 10_000.0
        keep, _ = CD.filter_dedup([{"key": "risk:x", "kind": "risk"}], {},
                                  now=now, ttl_s=0.0,
                                  kind_seen={"perf": now - 60},
                                  kind_cooldown_s={"perf": 6 * 3600.0, "risk": 24 * 3600.0})
        self.assertEqual([t["key"] for t in keep], ["risk:x"])

    def test_qua_cooldown_thi_hoi_lai(self):
        now = 10_000.0
        keep, _ = CD.filter_dedup([{"key": "perf:120:-4.2", "kind": "perf"}], {},
                                  now=now, ttl_s=0.0,
                                  kind_seen={"perf": now - 7 * 3600},
                                  kind_cooldown_s={"perf": 6 * 3600.0})
        self.assertEqual(len(keep), 1)


class TestParseModels(unittest.TestCase):
    def test_bo_khoang_trang_va_rong(self):
        self.assertEqual(CD.parse_models(" a , b ,, c "), ["a", "b", "c"])
        self.assertEqual(CD.parse_models(""), [])
        self.assertEqual(CD.parse_models(None), [])


if __name__ == "__main__":
    unittest.main()

