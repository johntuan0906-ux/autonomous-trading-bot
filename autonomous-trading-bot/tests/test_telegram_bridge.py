# -*- coding: utf-8 -*-
"""Test `tools/telegram_bridge.py` — cau noi Telegram 2 chieu (26/10).

Vi sao: bot DA co Telegram 1 chieu (`notify.send`), nhung canh bao cua
`watch_regress`/`ops_queue` (B-028/B-029) khong ra Telegram va KHONG co duong VAO ⇒
nguoi van hanh doc canh bao xong khong the tra loi/ra lenh. Cac test o day chot:
  - cau hoi dang cho PHAI ra Telegram (co chong spam, gui lai khi con treo);
  - lenh GHI (dedupe/reset/restart) mac dinh TAT; reset phai co chu `confirm`;
  - chi nghe tu chat_id duoc phep;
  - goi tool khac bang argv CO DINH (khong `shell=True`);
  - khong co token ⇒ che do DRY (khong im lang: ghi log).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import telegram_bridge as TB      # noqa: E402


def _instance(tmp: Path, questions=None, *, name="TESTNET", env=None) -> Path:
    base = tmp / name.lower()
    (base / "logs").mkdir(parents=True, exist_ok=True)
    (base / "config.py").write_text("# marker", encoding="utf-8")
    if env:
        (base / ".env").write_text(env, encoding="utf-8")
    if questions is not None:
        (base / "logs" / "ops_questions.json").write_text(
            json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    return base


class TestCauHinhVaGui(unittest.TestCase):
    def test_doc_env_tach_token_chat_va_co_cho_ghi(self):
        with tempfile.TemporaryDirectory() as d:
            base = _instance(Path(d), env=(
                "TELEGRAM_BOT_TOKEN=tok123\nTELEGRAM_CHAT_ID=999\n"
                "TELEGRAM_ALLOW_CHAT_IDS=999,555\nTELEGRAM_ALLOW_WRITE=true\n"))
            cfg = TB.cfg_for(base)
            self.assertEqual(cfg["token"], "tok123")
            self.assertEqual(cfg["chat"], "999")
            self.assertEqual(sorted(cfg["allow_ids"]), ["555", "999"])
            self.assertTrue(cfg["allow_write"])

    def test_mac_dinh_KHONG_cho_ghi(self):
        with tempfile.TemporaryDirectory() as d:
            base = _instance(Path(d), env="TELEGRAM_BOT_TOKEN=t\nTELEGRAM_CHAT_ID=1\n")
            self.assertFalse(TB.cfg_for(base)["allow_write"])

    def test_send_dry_thi_ghi_log_khong_goi_mang(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "logs" / "tb.log"
            r = TB.send("xin chao", token="t", chat="1", dry=True, log_path=log)
            self.assertTrue(r["dry"])
            self.assertIn("xin chao", log.read_text(encoding="utf-8"))

    def test_send_that_thi_goi_bot_api(self):
        seen = {}

        def fake_post(token, method, payload):
            seen.update({"token": token, "method": method, "payload": payload})
            return {"ok": True}

        r = TB.send("hi", token="t", chat="42", post=fake_post)
        self.assertTrue(r["ok"])
        self.assertEqual(seen["method"], "sendMessage")
        self.assertEqual(seen["payload"]["chat_id"], "42")

    def test_send_loi_api_thi_tra_ok_false(self):
        r = TB.send("hi", token="t", chat="1",
                    post=lambda *a, **k: {"ok": False, "error": "chat not found"})
        self.assertFalse(r["ok"])
        self.assertIn("chat not found", str(r["error"]))


class TestPush(unittest.TestCase):
    def test_gui_cau_hoi_dang_cho_va_chong_spam(self):
        with tempfile.TemporaryDirectory() as d:
            base = _instance(Path(d), [
                {"id": 7, "question": "Co nen nang tran?", "priority": "high",
                 "status": "OPEN", "ts": 1.0, "why": "vi sao", "options": ["co", "khong"]}])
            log = Path(d) / "tb.log"
            sent: list = []

            def post(tok, m, p):
                sent.append(p["text"])
                return {"ok": True}

            r1 = TB.push({"TESTNET": base}, token="t", chat="1", post=post, state={},
                         now=lambda: 1000.0, log_path=log)
            self.assertEqual(len(r1["pushed"]), 1)
            self.assertIn("/answer TESTNET 7", sent[0])
            r2 = TB.push({"TESTNET": base}, token="t", chat="1", post=post,
                         state=r1["state"], now=lambda: 1060.0, log_path=log)
            self.assertEqual(r2["pushed"], [], "vua gui xong -> khong gui lai (khong spam)")
            r3 = TB.push({"TESTNET": base}, token="t", chat="1", post=post,
                         state=r2["state"], now=lambda: 1000.0 + 8 * 3600, log_path=log)
            self.assertEqual(len(r3["pushed"]), 1, "con treo qua 6h -> nhac lai")

    def test_khong_co_cau_hoi_thi_khong_gui(self):
        with tempfile.TemporaryDirectory() as d:
            base = _instance(Path(d), [])
            r = TB.push({"TESTNET": base}, token="t", chat="1",
                        post=lambda *a: {"ok": True}, now=lambda: 1.0)
            self.assertEqual(r["pushed"], [])


class TestLenh(unittest.TestCase):
    def _cfg(self, write=False):
        return {"token": "t", "chat": "1", "allow_ids": ["1"], "allow_write": write}

    def test_parse_bo_ten_bot(self):
        self.assertEqual(TB.parse_command("/answer@MyBot 3 ok"), ("answer", ["3", "ok"]))
        self.assertEqual(TB.parse_command("khong phai lenh"), ("", []))

    def test_help_va_lenh_la(self):
        r = TB.handle("/help", cfg=self._cfg())
        self.assertIn("/status", r["reply"])
        r2 = TB.handle("/khong-co", cfg=self._cfg())
        self.assertIn("khong ro", r2["reply"])

    def test_list_doc_cau_hoi_2_instance(self):
        with tempfile.TemporaryDirectory() as d:
            a = _instance(Path(d), [{"id": 1, "question": "A?", "status": "OPEN",
                                     "priority": "normal", "ts": 1.0}], name="TESTNET")
            b = _instance(Path(d), [{"id": 2, "question": "B?", "status": "OPEN",
                                     "priority": "high", "ts": 1.0}], name="LIVE")
            r = TB.handle("/list", cfg=self._cfg(), dirs={"TESTNET": a, "LIVE": b})
            self.assertIn("[TESTNET] #1", r["reply"])
            self.assertIn("[LIVE] #2", r["reply"])

    def test_ask_ghi_vao_hang_doi(self):
        calls: list = []

        class FakeQ:
            def add(self, q, **kw):
                calls.append((q, kw))
                return {"ok": True, "id": 5}

        r = TB.handle("/ask kiem tra vi the 1000CAT", cfg=self._cfg(), queue=FakeQ())
        self.assertTrue(r["write"])
        self.assertIn("#5", r["reply"])
        self.assertEqual(calls[0][1]["by"], "telegram")

    def test_answer_phai_ro_instance_khi_id_TRUNG(self):
        with tempfile.TemporaryDirectory() as d:
            a = _instance(Path(d), [{"id": 3, "question": "A?", "status": "OPEN",
                                     "priority": "normal", "ts": 1.0}], name="TESTNET")
            b = _instance(Path(d), [{"id": 3, "question": "B?", "status": "OPEN",
                                     "priority": "normal", "ts": 1.0}], name="LIVE")
            calls: list = []

            class FakeQ:
                def answer(self, qid, text, **kw):
                    calls.append((qid, text, kw))
                    return {"ok": True}

            r = TB.handle("/answer 3 dong y", cfg=self._cfg(),
                          dirs={"TESTNET": a, "LIVE": b}, queue=FakeQ())
            self.assertFalse(calls, "id trung -> khong duoc doan bua")
            self.assertIn("CA 2 instance", r["reply"])
            r2 = TB.handle("/answer LIVE 3 dong y", cfg=self._cfg(),
                           dirs={"TESTNET": a, "LIVE": b}, queue=FakeQ())
            self.assertTrue(r2["write"])
            self.assertTrue(str(calls[0][2]["open_path"]).endswith("ops_questions.json"))

    def test_lenh_GHI_mac_dinh_TAT(self):
        ran: list = []
        r = TB.handle("/dedupe live", cfg=self._cfg(write=False),
                      runner=lambda *a, **k: ran.append(a) or {"ok": True, "out": "x"})
        self.assertTrue(r["blocked"])
        self.assertEqual(ran, [], "khong duoc chay khi chua cho phep")

    def test_dedupe_chay_bang_argv_CO_DINH(self):
        ran: list = []

        def fake_runner(argv, **kw):
            ran.append((argv, kw))
            return {"ok": True, "out": "da huy 2"}

        r = TB.handle("/dedupe live", cfg=self._cfg(write=True), runner=fake_runner)
        self.assertFalse(r.get("blocked"))
        argv = ran[0][0]
        self.assertIsInstance(argv, list)
        self.assertIn("--dedupe", argv)
        self.assertIn("live", argv)
        self.assertNotIn("shell", ran[0][1])

    def test_reset_phai_co_chu_confirm(self):
        ran: list = []

        def runner(*a, **k):
            ran.append(a)
            return {"ok": True, "out": "x"}

        r = TB.handle("/reset live", cfg=self._cfg(write=True), runner=runner)
        self.assertTrue(r["blocked"])
        self.assertIn("confirm", r["reply"])
        self.assertEqual(ran, [])
        r2 = TB.handle("/reset live confirm", cfg=self._cfg(write=True), runner=runner)
        self.assertFalse(r2.get("blocked"))
        self.assertEqual(len(ran), 1)

    def test_khong_co_shell_true_trong_nguon(self):
        """Khong duoc goi `subprocess` voi `shell=` (tranh tiem lenh qua Telegram)."""
        src = (ROOT / "tools" / "telegram_bridge.py").read_text(encoding="utf-8")
        bad = [ln.strip() for ln in src.splitlines()
               if "subprocess" in ln and "shell" in ln]
        self.assertEqual(bad, [], "goi subprocess voi shell= la lo hong tiem lenh")
        self.assertIn("capture_output=True", src)


class TestPoll(unittest.TestCase):
    def _upd(self, chat_id, text, uid=1):
        return {"ok": True, "result": [{"update_id": uid,
                                        "message": {"chat": {"id": chat_id},
                                                    "text": text}}]}

    def test_lenh_tu_chat_id_DUOC_PHEP_thi_tra_loi(self):
        sent: list = []

        def post(tok, m, p):
            sent.append(p)
            return {"ok": True}

        r = TB.poll(token="t", cfg={"token": "t", "chat": "1", "allow_ids": ["1"],
                                    "allow_write": False},
                    post=post, get=lambda tok, off: self._upd("1", "/help"))
        self.assertEqual([h["cmd"] for h in r["handled"]], ["help"])
        self.assertTrue(sent and sent[0]["chat_id"] == "1")

    def test_lenh_tu_chat_id_LA_thi_bo_qua(self):
        sent: list = []
        r = TB.poll(token="t", cfg={"token": "t", "chat": "1", "allow_ids": ["1"],
                                    "allow_write": False},
                    post=lambda tok, m, p: (sent.append(p), {"ok": True})[1],
                    get=lambda tok, off: self._upd("666", "/status"))
        self.assertEqual([h["cmd"] for h in r["handled"]], ["blocked"])
        self.assertEqual(sent, [], "khong tra loi nguoi la")

    def test_offset_tang_de_khong_xu_ly_lai(self):
        r = TB.poll(token="t", cfg={"token": "t", "chat": "1", "allow_ids": ["1"]},
                    post=lambda *a: {"ok": True}, state={},
                    get=lambda tok, off: self._upd("1", "/help", uid=77))
        self.assertEqual(r["state"]["offset"], 77)

    def test_loi_getupdates_thi_ghi_ro_khong_crash(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "tb.log"
            r = TB.poll(token="t", cfg={"token": "t", "chat": "1", "allow_ids": ["1"]},
                        get=lambda tok, off: {"ok": False, "error": "401 Unauthorized"},
                        log_path=log)
            self.assertIn("401", r["error"])
            self.assertIn("POLL loi", log.read_text(encoding="utf-8"))


class TestTaskCommand(unittest.TestCase):
    def test_lenh_task_co_duong_dan_tuyet_doi_va_nhay_kep(self):
        cmd = TB.task_command(python_exe="C:\\py\\python.exe",
                              script="C:\\x\\telegram_bridge.py")
        self.assertIn('"C:\\x\\telegram_bridge.py"', cmd)
        self.assertIn("--once", cmd)
        self.assertTrue(cmd.startswith('"'))


if __name__ == "__main__":
    unittest.main()
