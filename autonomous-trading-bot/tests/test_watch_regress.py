# -*- coding: utf-8 -*-
"""Test `tools/watch_regress.py` — theo doi TAI PHAT lop loi da va + tien trinh.

Yeu cau cot loi (20/10): sau khi va B-023 (`-2022`), cau hoi "no co tai xuat hien khong"
phai duoc MAY tra loi. Vi vay phep dem PHAI loc theo MOC THOI GIAN da va (khong dem lai
lich su cu), va phai bat duoc: supervisor/con con da CHET (du file nhip tim con do),
nhip tim cu, kill-switch, cong tam dung.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import watch_regress as WR        # noqa: E402


def _ts(text: str) -> float:
    return time.mktime(time.strptime(text, "%Y-%m-%d %H:%M:%S"))


class TestParseTs(unittest.TestCase):
    def test_doc_duoc_timestamp(self):
        self.assertEqual(WR.parse_ts("2026-10-20 10:00:00 WARNING x"),
                         _ts("2026-10-20 10:00:00"))

    def test_dong_khong_co_timestamp(self):
        self.assertIsNone(WR.parse_ts("[supervisor] turbo start #1"))
        self.assertIsNone(WR.parse_ts(""))


class TestScanText(unittest.TestCase):
    """Chi dem dong SAU moc da va — day la ca co che 'bang chung kiem chung duoc'."""

    LINES = ["2026-10-20 09:00:00 WARNING close A failed: -2022",
             "2026-10-20 10:30:00 WARNING close B failed: -2022",
             "2026-10-20 10:31:00 INFO CLOSE C: da dong (khong co ma loi)",
             "2026-10-20 10:32:00 WARNING monitor D failed: -2022"]

    def test_chi_dem_sau_moc(self):
        s = WR.scan_text(self.LINES, "-2022", since=_ts("2026-10-20 10:00:00"))
        self.assertEqual(s["n"], 2)
        self.assertEqual(s["first_ts"], _ts("2026-10-20 10:30:00"))
        self.assertEqual(s["last_ts"], _ts("2026-10-20 10:32:00"))
        self.assertIn("close B", s["sample"][0])

    def test_khong_co_moc_thi_dem_het(self):
        self.assertEqual(WR.scan_text(self.LINES, "-2022")["n"], 3)

    def test_until_gioi_han_cua_so(self):
        s = WR.scan_text(self.LINES, "-2022", until=_ts("2026-10-20 10:31:00"))
        self.assertEqual(s["n"], 2)

    def test_dong_khong_timestamp_bi_bo_qua(self):
        self.assertEqual(WR.scan_text(["-2022 rac khong timestamp"], "-2022")["n"], 0)

    def test_dong_INFO_THANH_CONG_khong_bi_tinh_la_tai_phat(self):
        """Mau phai la `"code":-2022` (JSON loi cua san), khong phai `-2022` tran.

        Do that 20/10: de mau `-2022` ⇒ tu bao dong gia moi lan bot dong lenh DUNG
        (dong INFO `... san tu choi reduceOnly (-2022) -> da dong bang qty THAT ...`).
        """
        pat = [s["pattern"] for s in WR.SIGNATURES if s["code"] == "B-023"][0]
        self.assertIn('"code":-2022', pat)
        line_ok = ('2026-10-20 12:09:36 INFO CLOSE CKB/USDT:USDT: san tu choi '
                   '`reduceOnly` (-2022) -> da dong bang qty THAT cua san (125000.0)')
        line_err = '2026-10-20 12:09:36 WARNING close X failed: binance {"code":-2022,"msg":"ReduceOnly Order is rejected."}'
        self.assertEqual(WR.scan_text([line_ok], pat)["n"], 0,
                         "dong INFO thanh cong KHONG duoc tinh la tai phat")
        self.assertEqual(WR.scan_text([line_err], pat)["n"], 1)


class TestHealth(unittest.TestCase):
    def _rep(self, **kw) -> dict:
        d = {"name": "LIVE", "pid": 100, "supervisor_pid": 200, "hb_age_s": 30.0,
             "kill_tripped": False}
        d.update(kw)
        return d

    def test_khoe_thi_khong_co_van_de(self):
        self.assertEqual(WR.health("LIVE", self._rep(), pids={100, 200}), [])

    def test_supervisor_khong_con_chay(self):
        bad = WR.health("LIVE", self._rep(), pids={100})
        self.assertTrue(any("supervisor pid 200 KHONG chay" in b for b in bad), bad)

    def test_tien_trinh_con_khong_con_chay(self):
        """Nhip tim con 'moi' nhung pid KHONG ton tai = bot da chet (so lieu CU)."""
        bad = WR.health("LIVE", self._rep(hb_age_s=5.0), pids={200})
        self.assertTrue(any("tien trinh con pid 100 KHONG chay" in b for b in bad), bad)

    def test_nhip_tim_cu(self):
        bad = WR.health("LIVE", self._rep(hb_age_s=5000.0), pids={100, 200})
        self.assertTrue(any("nhip tim cu" in b for b in bad), bad)

    def test_khong_co_supervisor(self):
        bad = WR.health("LIVE", self._rep(supervisor_pid=0), pids=set())
        self.assertTrue(any("khong co supervisor" in b for b in bad), bad)

    def test_kill_switch_dang_ngung(self):
        bad = WR.health("LIVE", self._rep(kill_tripped=True, kill_reason="x"), pids={100, 200})
        self.assertTrue(any("KILL-SWITCH" in b for b in bad), bad)



class TestVerdict(unittest.TestCase):
    def test_ok_khi_khong_van_de_va_khong_tai_phat(self):
        inst = [{"name": "LIVE", "problems": [],
                 "sightings": {"B-023": {"n": 0, "pattern": "-2022"}}}]
        v = WR.verdict(inst)
        self.assertTrue(v["ok"])
        self.assertEqual(v["regressions"], [])

    def test_tai_phat_lam_sai_ket_luan(self):
        inst = [{"name": "LIVE", "problems": [],
                 "sightings": {"B-023": {"n": 3, "pattern": "-2022",
                                         "last_ts": _ts("2026-10-20 10:00:00")}}}]
        v = WR.verdict(inst)
        self.assertFalse(v["ok"])
        self.assertEqual(len(v["regressions"]), 1)
        self.assertIn("B-023", v["regressions"][0])


class TestState(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "regress_watch.json"

    def test_mark_fixed_ghi_moc(self):
        r = WR.mark_fixed("B-023", now=lambda: 1234.0, path=self.path)
        self.assertTrue(r["ok"])
        self.assertEqual(WR.load_state(self.path)["fixed_at"]["B-023"], 1234.0)

    def test_mark_fixed_giu_moc_cu_cua_lop_khac(self):
        WR.mark_fixed("B-022", now=lambda: 1.0, path=self.path)
        WR.mark_fixed("B-023", now=lambda: 2.0, path=self.path)
        self.assertEqual(WR.load_state(self.path)["fixed_at"], {"B-022": 1.0, "B-023": 2.0})

    def test_file_hong_thi_tra_rong(self):
        self.path.write_text("{khong-phai-json", encoding="utf-8")
        self.assertEqual(WR.load_state(self.path), {})


class TestNotify(unittest.TestCase):
    def _rep(self) -> dict:
        return {"instances": [{"name": "LIVE",
                               "sightings": {"B-023": {"n": 2, "pattern": "-2022",
                                                       "last_ts": time.time(),
                                                       "sample": ["close X failed: -2022"]}}}],
                "problems": [], "regressions": ["x"]}

    def test_bao_DUNG_1_lan(self):
        st_path = Path(tempfile.mkdtemp()) / "regress_watch.json"
        calls: list = []

        def fake_add(question, **kw):
            calls.append((question, kw))
            return {"ok": True, "id": len(calls)}

        r1 = WR.notify(self._rep(), state={}, enqueue=fake_add, path=st_path)
        self.assertEqual(len(r1["sent"]), 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["priority"], "high")
        r2 = WR.notify(self._rep(), state=r1["state"], enqueue=fake_add, path=st_path)
        self.assertEqual(r2["sent"], [], "da bao roi -> khong bao lai (khong spam)")

    def test_tai_phat_TANG_LEN_thi_bao_lai_sau_cooldown(self):
        """Khong duoc im lang vinh vien: so lan tang + qua cooldown ⇒ bao lai."""
        st_path = Path(tempfile.mkdtemp()) / "regress_watch.json"
        calls: list = []
        r1 = WR.notify(self._rep(), state={}, now=lambda: 1000.0, path=st_path,
                       enqueue=lambda q, **k: calls.append(q) or {"ok": True})
        self.assertEqual(len(r1["sent"]), 1)
        rep2 = self._rep()
        rep2["instances"][0]["sightings"]["B-023"]["n"] = 5
        r2 = WR.notify(rep2, state=r1["state"], now=lambda: 1000.0 + 60, path=st_path,
                       enqueue=lambda q, **k: calls.append(q) or {"ok": True})
        self.assertEqual(r2["sent"], [], "so lan tang nhung CHUA qua cooldown -> chua bao")
        r3 = WR.notify(rep2, state=r2["state"], now=lambda: 1000.0 + 7200, path=st_path,
                       enqueue=lambda q, **k: calls.append(q) or {"ok": True})
        self.assertEqual(len(r3["sent"]), 1, "qua cooldown + so lan tang -> phai bao lai")
        self.assertEqual(len(calls), 2)

    def test_khong_co_tai_phat_thi_khong_bao(self):
        st_path = Path(tempfile.mkdtemp()) / "regress_watch.json"
        rep = {"instances": [{"name": "LIVE",
                              "sightings": {"B-023": {"n": 0, "pattern": "-2022"}}}]}
        r = WR.notify(rep, state={}, enqueue=lambda *a, **k: {"ok": True}, path=st_path)
        self.assertEqual(r["sent"], [])


class TestScanInstance(unittest.TestCase):
    """Doc 1 instance GIA (thu muc tam) -> dung moc da va + dung pid."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "logs").mkdir(parents=True, exist_ok=True)
        old = '2026-10-20 09:00:00 WARNING close A failed: binance {"code":-2022}'
        new = '2026-10-20 10:30:00 WARNING close B failed: binance {"code":-2022}'
        (self.dir / "logs" / "turbo_err.log").write_text(old + "\n" + new + "\n",
                                                        encoding="utf-8")
        (self.dir / "logs" / "heartbeat.json").write_text(
            json.dumps({"ts": time.time(), "pid": 111, "round": 7, "phase": "end"}),
            encoding="utf-8")
        (self.dir / "logs" / ".supervisor.lock").write_text("222", encoding="utf-8")
        (self.dir / "logs" / "entries_pause.json").write_text(
            json.dumps({"paused": True, "until": time.time() + 3600, "reason": "test"}),
            encoding="utf-8")

    def test_dem_dung_va_bat_tien_trinh_chet(self):
        base = {"fixed_at": {"B-023": _ts("2026-10-20 10:00:00")}}
        rep = WR.scan_instance("LIVE", self.dir, baseline=base, pids={222})
        self.assertEqual(rep["sightings"]["B-023"]["n"], 1,
                         "chi tinh dong SAU moc da va")
        self.assertTrue(rep["supervisor_alive"])
        self.assertFalse(rep["child_alive"], "pid 111 khong co trong danh sach -> phai bat")
        self.assertTrue(any("KHONG chay" in p for p in rep["problems"]))
        self.assertGreater(rep["paused_until"], time.time())

    def test_khi_pid_con_song_thi_khong_bao(self):
        base = {"fixed_at": {"B-023": _ts("2026-10-20 10:00:00")}}
        rep = WR.scan_instance("LIVE", self.dir, baseline=base, pids={111, 222})
        self.assertEqual(rep["problems"], [], rep["problems"])
        self.assertTrue(rep["child_alive"])


class TestTaskCommand(unittest.TestCase):
    def test_lenh_task_co_check_va_nhay_kep(self):
        cmd = WR.task_command(python_exe="C:\\py\\python.exe",
                              script="C:\\x\\watch_regress.py", target="both")
        self.assertIn('"C:\\x\\watch_regress.py"', cmd)
        self.assertIn("--check", cmd)
        self.assertIn("--target both", cmd)
        self.assertTrue(cmd.startswith('"'))


class TestReadTailLines(unittest.TestCase):
    def test_cat_bot_dong_dau_khi_bi_gioi_han(self):
        p = Path(tempfile.mkdtemp()) / "log.txt"
        p.write_text("\n".join("dong %d" % i for i in range(50)) + "\n", encoding="utf-8")
        lines, cut = WR.read_tail_lines(p, max_bytes=60)
        self.assertTrue(cut)
        self.assertTrue(all(not ln.startswith("dong 0 ") for ln in lines))
        self.assertEqual(lines[-1], "dong 49")

    def test_file_thieu_thi_rong(self):
        lines, cut = WR.read_tail_lines(Path(tempfile.mkdtemp()) / "khong-co.txt")
        self.assertEqual(lines, [])
        self.assertFalse(cut)


if __name__ == "__main__":
    unittest.main()
