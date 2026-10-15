"""Test (15/10) 4 cong cu van hanh moi:
  - `tools/deadman.py`  : dead-man switch (bao khi bot ngung) — quyet dinh THUAN TUY
  - `run_forever`       : tu chay llamafile khi boot (`plan_autostart`, `ensure_llamafile`)
  - `lessons.py`        : `/evolve` (ky nang co ten) + `/prune` (truc xuat to hop cu)
  - `tools/backup.py`   : dang ky Task Scheduler

Khong goi mang, khong chay schtasks, khong spawn tien trinh: moi thu deu tiem duoc.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import backup as BK       # noqa: E402
import deadman as DM      # noqa: E402
import lessons as LES     # noqa: E402
import run_forever as RF  # noqa: E402


class TestDeadman(unittest.TestCase):
    """Dead-man switch: quyet dinh + URL + gui ping (gia lap)."""

    def _rep(self, **kw):
        r = {"name": "TESTNET", "hb_age_s": 5.0, "supervisor_pid": 123,
             "kill_tripped": False, "errors_win": {}}
        r.update(kw)
        return r

    def test_ping_url_dung_chuan_healthchecks(self):
        self.assertEqual(DM.ping_url("https://hc-ping.com/abc", True),
                         "https://hc-ping.com/abc")
        self.assertEqual(DM.ping_url("https://hc-ping.com/abc/", False),
                         "https://hc-ping.com/abc/fail")
        self.assertEqual(DM.ping_url("", True), "")

    def test_decide_ok_khi_bot_song(self):
        d = DM.decide([self._rep(), self._rep(name="LIVE")])
        self.assertTrue(d["ok"])
        self.assertEqual(d["problems"], [])
        self.assertEqual(d["reason"], "OK")

    def test_decide_bat_loi_nhip_tim_cu_va_khong_supervisor(self):
        d = DM.decide([self._rep(hb_age_s=2000.0, supervisor_pid=0)])
        self.assertFalse(d["ok"])
        self.assertEqual(len(d["problems"]), 2)
        self.assertIn("nhip tim cu", d["reason"])
        self.assertIn("khong co supervisor", d["reason"])

    def test_decide_bat_kill_switch_va_loi(self):
        d = DM.decide([self._rep(kill_tripped=True, kill_reason="drawdown",
                                 errors_win={"ORDER_FAILED": 2})])
        self.assertFalse(d["ok"])
        self.assertTrue(any("KILL-SWITCH" in p for p in d["problems"]))
        self.assertTrue(any("2 loi" in p for p in d["problems"]))

    def test_skip_data_khong_phai_la_chet(self):
        d = DM.decide([self._rep(errors_win={"SKIP_DATA": 9})])
        self.assertTrue(d["ok"], d)

    def test_send_ping_tiem_duoc_get(self):
        seen = []

        def fake_get(url, timeout):
            seen.append(url)
            return 200

        r = DM.send_ping("https://hc-ping.com/x/fail", get=fake_get)
        self.assertTrue(r["ok"])
        self.assertEqual(seen, ["https://hc-ping.com/x/fail"])

    def test_send_ping_khong_nem_loi(self):
        def boom(url, timeout):
            raise OSError("khong co mang")

        r = DM.send_ping("https://hc-ping.com/x", get=boom)
        self.assertFalse(r["ok"])
        self.assertIn("khong co mang", r["error"])
        self.assertFalse(DM.send_ping("")["ok"])

    def test_urls_for_uu_tien_url_rieng(self):
        env = {"HEALTHCHECKS_URL": "https://hc/g",
               "HEALTHCHECKS_URL_LIVE": "https://hc/live"}
        self.assertEqual(DM.urls_for(env, "both"),
                         [("testnet", "https://hc/g"), ("live", "https://hc/live")])
        self.assertEqual(DM.urls_for(env, "live"), [("live", "https://hc/live")])

    def test_save_state_ghi_json_va_log(self):
        with tempfile.TemporaryDirectory() as td:
            st, lg = Path(td) / "deadman.json", Path(td) / "deadman.log"
            rec = {"ok": False, "reason": "nhip tim cu", "target": "both"}
            rep = DM.save_state(rec, state=st, log=lg)
            self.assertTrue(Path(rep["state"]).exists())
            self.assertIn("FAIL", lg.read_text(encoding="utf-8"))
            self.assertIn("nhip tim cu", lg.read_text(encoding="utf-8"))


class TestLlamafileAutostart(unittest.TestCase):
    """(15/10) Supervisor tu chay llamafile — hoi dong khong duoc cam."""

    LOCAL_ENV = {"AGENT_COUNCIL_LOCAL": "llama3.2-3b-local",
                 "AGENT_LOCAL_BASE_URL": "http://127.0.0.1:8080/v1"}

    def test_local_base_url_chi_nhan_server_cuc_bo(self):
        self.assertEqual(RF.local_base_url(self.LOCAL_ENV), "http://127.0.0.1:8080/v1")
        self.assertEqual(RF.local_base_url({**self.LOCAL_ENV, "AGENT_COUNCIL_LOCAL": ""}), "")
        self.assertEqual(RF.local_base_url({**self.LOCAL_ENV, "AGENT_LOCAL_BASE_URL": ""}), "")
        # server o may khac -> khong phai llamafile cua ta -> khong spawn
        self.assertEqual(RF.local_base_url(
            {**self.LOCAL_ENV, "AGENT_LOCAL_BASE_URL": "http://10.0.0.9:8080/v1"}), "")

    def test_plan_autostart_ma_tran(self):
        env = self.LOCAL_ENV
        self.assertEqual(RF.plan_autostart(env, True, True), "already_up")
        self.assertEqual(RF.plan_autostart(env, False, True), "start")
        self.assertEqual(RF.plan_autostart(env, False, False), "skip_no_binary")
        self.assertEqual(RF.plan_autostart(env, False, True, False), "skip_disabled")
        self.assertEqual(RF.plan_autostart({}, False, True), "skip_no_local")
        self.assertEqual(RF.plan_autostart(
            {**env, "AGENT_LOCAL_BASE_URL": "http://10.0.0.9:8080/v1"}, False, True),
            "skip_remote")

    def test_ensure_llamafile_khong_spawn_khi_server_dang_chay(self):
        marks = []
        act = RF.ensure_llamafile(self.LOCAL_ENV, enabled=True, probe=lambda b: True,
                                  binary=None, mark=marks.append)
        self.assertEqual(act, "already_up")
        self.assertEqual(len(marks), 1)

    def test_ensure_llamafile_bao_thieu_binary_chu_khong_spawn(self):
        act = RF.ensure_llamafile(self.LOCAL_ENV, enabled=True, probe=lambda b: False,
                                  binary=None, mark=lambda m: None)
        self.assertEqual(act, "skip_no_binary")

    def test_ensure_llamafile_tat_bang_env_thi_khong_do(self):
        act = RF.ensure_llamafile(self.LOCAL_ENV, enabled=False, probe=lambda b: False,
                                  binary=Path("x.exe"), mark=lambda m: None)
        self.assertEqual(act, "skip_disabled")

    def test_llamafile_binary_uu_tien_thin_va_gguf(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            self.assertIsNone(RF.llamafile_binary(d))
            (d / "Qwen3.5-0.8B-Q8_0.llamafile").write_bytes(b"x")
            self.assertEqual(RF.llamafile_binary(d).name, "Qwen3.5-0.8B-Q8_0.llamafile")
            (d / "llamafile-0.10.6-thin.exe").write_bytes(b"x")
            (d / "Llama-3.2-3B-Q4.gguf").write_bytes(b"x")
            self.assertEqual(RF.llamafile_binary(d).name, "llamafile-0.10.6-thin.exe")


class TestLessonsEvolvePrune(unittest.TestCase):
    """`/evolve` (ky nang co ten) + `/prune` (truc xuat to hop cu)."""

    NOW = 1_800_000_000.0
    DAY = 86400.0

    def _buckets(self):
        old = self.NOW - 60 * self.DAY
        new = self.NOW - 2 * self.DAY
        return {
            "trend | BOS | up | LONG": {"n": 30, "wins": 6, "sum_r": -9.0, "avg_r": -0.30,
                                        "wr": 20.0, "pnl": -20.0, "pf": 0.3, "last_ts": new},
            "range | FVG | down | SHORT": {"n": 25, "wins": 18, "sum_r": 5.0, "avg_r": 0.20,
                                           "wr": 72.0, "pnl": 15.0, "pf": 2.0, "last_ts": new},
            "cu | BOS | up | LONG": {"n": 22, "wins": 5, "sum_r": -6.0, "avg_r": -0.27,
                                     "wr": 23.0, "pnl": -12.0, "pf": 0.4, "last_ts": old},
            "it mau | BOS | up | LONG": {"n": 2, "wins": 1, "sum_r": 0.0, "avg_r": 0.0,
                                         "wr": 50.0, "pnl": 0.0, "pf": None, "last_ts": new},
        }

    def test_prune_stale_truc_xuat_to_hop_cu_va_it_mau(self):
        keep, drop = LES.prune_stale(self._buckets(), stale_days=30.0, now=self.NOW)
        self.assertIn("trend | BOS | up | LONG", keep)
        self.assertIn("range | FVG | down | SHORT", keep)
        self.assertNotIn("cu | BOS | up | LONG", keep)
        self.assertIn("khong con lenh trong 30 ngay",
                      drop["cu | BOS | up | LONG"]["prune_reason"])
        # `min_n` la tham so rieng (mac dinh 1 = giu ca to hop it mau de con hoc tiep)
        _, drop2 = LES.prune_stale(self._buckets(), stale_days=30.0, now=self.NOW, min_n=5)
        self.assertIn("qua it mau", drop2["it mau | BOS | up | LONG"]["prune_reason"])

    def test_evolve_rut_ra_ky_nang_co_ten_va_xep_theo_tac_dong(self):
        sk = LES.evolve(self._buckets(), min_n=5)
        names = [s["name"] for s in sk]
        self.assertTrue(all(s["kind"] in ("tranh", "uu_tien") for s in sk))
        # tac dong = |avg_r| * n: 0.30*30=9.0 > 0.27*22=5.94 > 0.20*25=5.0
        self.assertEqual(names[0], "tranh: trend / BOS / up / LONG")
        self.assertEqual(sk[0]["impact"], 9.0)
        self.assertNotIn("it mau", " ".join(names))          # n=2 < min_n=5

    def test_build_voi_stale_days_va_skills(self):
        with tempfile.TemporaryDirectory() as td:
            j = Path(td) / "journal.jsonl"
            j.write_text("", encoding="utf-8")
            les = LES.build(j, stale_days=30.0, now=self.NOW)
            self.assertIn("skills", les)
            self.assertIn("stale", les)
            self.assertEqual(les["trades"], 0)

    def test_skills_md_rong_va_co_du_lieu(self):
        self.assertIn("chua du mau", LES.skills_md([])[0])
        md = LES.skills_md(LES.evolve(self._buckets(), min_n=5))
        self.assertIn("| Ky nang | loai | n |", md[0])

    def test_write_files_co_phan_ky_nang_va_archive_ly_do(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            les = {"trades": 5, "buckets": self._buckets(), "gates": [], "notes": [],
                   "skills": LES.evolve(self._buckets(), min_n=5), "pruned": ["x"],
                   "stale": {"cu | BOS | up | LONG": "khong con lenh trong 30 ngay"},
                   "ts": self.NOW}
            arch = base / "archive.jsonl"
            rep = LES.write_files(les, json_path=base / "lessons.json",
                                  md_path=base / "LESSONS.md", archive_path=arch)
            md = (base / "LESSONS.md").read_text(encoding="utf-8")
            self.assertIn("## Ky nang da rut ra", md)
            self.assertIn("/prune", md)
            self.assertGreaterEqual(rep["archived"], 2)
            self.assertIn("khong con lenh trong 30 ngay", arch.read_text(encoding="utf-8"))


class TestBackupTask(unittest.TestCase):
    """Dang ky Task Scheduler cho backup hang ngay."""

    def test_task_command_co_duong_dan_tuyet_doi_va_tham_so(self):
        cmd = BK.task_command(python_exe=r"C:\py\python.exe",
                              script=Path(r"C:\repo\tools\backup.py"))
        self.assertTrue(cmd.startswith('"C:\\py\\python.exe" "C:\\repo\\tools\\backup.py"'))
        self.assertIn("--target both", cmd)
        self.assertIn("--keep 14", cmd)

    def test_schtasks_argv_install_uninstall_status(self):
        a = BK.schtasks_argv("install", time_str="03:30", command="py x.py")
        self.assertEqual(a[:6], ["schtasks", "/Create", "/TN", BK.TASK_NAME, "/SC", "DAILY"])
        self.assertIn("/ST", a)
        self.assertIn("03:30", a)
        self.assertIn("/F", a)
        self.assertEqual(BK.schtasks_argv("uninstall")[:4],
                         ["schtasks", "/Delete", "/TN", BK.TASK_NAME])
        self.assertEqual(BK.schtasks_argv("status"),
                         ["schtasks", "/Query", "/TN", BK.TASK_NAME])

    def test_run_schtasks_tiem_duoc_runner(self):
        class P:
            returncode = 0
            stdout = "SUCCESS: The scheduled task created."
            stderr = ""

        seen = []

        def fake_run(argv, **kw):
            seen.append(argv)
            return P()

        r = BK.run_schtasks(["schtasks", "/Query"], run=fake_run)
        self.assertTrue(r["ok"])
        self.assertIn("SUCCESS", r["out"])
        self.assertEqual(seen[0][0], "schtasks")

    def test_run_schtasks_khong_nem_loi(self):
        def boom(argv, **kw):
            raise OSError("schtasks khong ton tai")

        r = BK.run_schtasks(["schtasks"], run=boom)
        self.assertFalse(r["ok"])
        self.assertIn("khong ton tai", r["out"])

    def test_hidden_python_doi_sang_pythonw_de_khong_bat_popup(self):
        """(15/10) Cu 15 phut hien 1 cua so cmd den -> task phai goi pythonw.exe."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            py, pyw = d / "python.exe", d / "pythonw.exe"
            py.write_bytes(b"x")
            self.assertTrue(BK.hidden_python(py).endswith("python.exe"))   # chua co pythonw
            pyw.write_bytes(b"x")
            self.assertTrue(BK.hidden_python(py).endswith("pythonw.exe"))
            self.assertTrue(BK.hidden_python(pyw).endswith("pythonw.exe"))  # da la pythonw
            self.assertTrue(BK.hidden_python(d / "python3.exe").endswith("python3.exe"))

    def test_task_command_mac_dinh_dung_pythonw(self):
        cmd = BK.task_command(script=Path(r"C:\repo\tools\backup.py"))
        self.assertNotIn("python.exe ", cmd.replace("pythonw.exe", ""))
        self.assertIn("--target both", cmd)


class TestCouncilIgnore(unittest.TestCase):
    """(15/10) Quyet dinh cua hoi dong: loai model value_r <= 0 khoi phieu (khong xoa)."""

    def test_ignored_models_doc_tu_cfg(self):
        import agents as AG

        class C:
            agent_council_ignore = "local/llama3.2-3b-local, foo ,"

        self.assertEqual(AG._ignored_models(C()), {"local/llama3.2-3b-local", "foo"})
        self.assertEqual(AG._ignored_models(object()), set())      # thieu cau hinh -> rong

    def test_filter_ignored_khop_ca_co_tien_to(self):
        import agents as AG
        d = {"local/llama3.2-3b-local": 1, "claude-sonnet-5.5": 2}
        self.assertEqual(list(AG._filter_ignored(d, {"llama3.2-3b-local"})),
                         ["claude-sonnet-5.5"])       # khop khi ten khong co tien to
        self.assertEqual(list(AG._filter_ignored(d, {"local/llama3.2-3b-local"})),
                         ["claude-sonnet-5.5"])
        self.assertEqual(AG._filter_ignored(d, set()), d)          # khong co gi -> giu het
        self.assertEqual(AG._filter_ignored({}, {"x"}), {})


class TestUnpairedJournal(unittest.TestCase):
    """(15/10) 91 lenh CLOSE khong co OPEN (reason=DUST) tung sinh to hop GIA
    `? | ? | ? | ?` (n=84, avgR +0.383) va bi xep vao 'NEN UU TIEN'."""

    def _journal(self, td):
        j = Path(td) / "journal.jsonl"
        rows = [
            {"event": "OPEN", "pair": "AAA/USDT", "ts": 1.0,
             "strategy": "A_TREND_PULLBACK", "setup_type": "BOS_UP",
             "market_regime": "UPTREND", "direction": "LONG"},
            {"event": "CLOSE", "pair": "AAA/USDT", "ts": 2.0, "r": 1.0, "won": True,
             "reason": "TP"},
            {"event": "CLOSE", "pair": "BBB/USDT", "ts": 3.0, "r": 2.4, "won": True,
             "reason": "DUST", "direction": "SHORT"},      # khong co OPEN
        ]
        j.write_text("\n".join(json.dumps(x) for x in rows) + "\n", encoding="utf-8")
        return j

    def test_load_closed_danh_dau_lenh_khong_co_open(self):
        with tempfile.TemporaryDirectory() as td:
            t = LES.load_closed(self._journal(td))
            self.assertEqual(len(t), 2)
            self.assertIsNone(t[0].get("origin"))            # lenh that: khong co nhan
            self.assertEqual(t[1].get("origin"), "no_open")

    def test_bucket_stats_loai_lenh_khong_co_open(self):
        with tempfile.TemporaryDirectory() as td:
            b = LES.bucket_stats(LES.load_closed(self._journal(td)))
            self.assertEqual(list(b), ["A_TREND_PULLBACK | BOS_UP | UPTREND | LONG"])
            self.assertNotIn("? | ? | ? | ?", b)             # het to hop gia

    def test_build_dem_rieng_va_khong_tinh_vao_thong_ke(self):
        with tempfile.TemporaryDirectory() as td:
            les = LES.build(self._journal(td))
            self.assertEqual(les["trades"], 1)               # chi lenh co OPEN
            self.assertEqual(les["unpaired"], 1)             # van duoc DEM RIENG
            self.assertNotIn("? | ? | ? | ?", les["buckets"])

    def test_unpaired_drop_bo_han_khoi_ket_qua(self):
        with tempfile.TemporaryDirectory() as td:
            t = LES.load_closed(self._journal(td), unpaired="drop")
            self.assertEqual(len(t), 1)

    def test_include_unpaired_giu_hanh_vi_cu_de_doi_chieu(self):
        with tempfile.TemporaryDirectory() as td:
            les = LES.build(self._journal(td), include_unpaired=True)
            self.assertEqual(les["unpaired"], 0)
            self.assertIn("? | ? | ? | ?", les["buckets"])


class TestLessonsHint(unittest.TestCase):
    """(15/10) Cay tri thuc + truy hoi theo pham vi + TRAN TOKEN khi nhoi vao prompt."""

    def _b(self):
        return {
            "A_TREND_PULLBACK | BOS_UP | UPTREND | LONG": {
                "n": 30, "wins": 9, "sum_r": -6.0, "avg_r": -0.20, "wr": 30.0,
                "pnl": -15.0, "last_ts": 10.0},
            "A_TREND_PULLBACK | BOS_UP | UPTREND | SHORT": {
                "n": 20, "wins": 14, "sum_r": 5.0, "avg_r": 0.25, "wr": 70.0,
                "pnl": 20.0, "last_ts": 10.0},
            "B_BREAKOUT_RETEST | BOS_DOWN | DOWNTREND | SHORT": {
                "n": 80, "wins": 50, "sum_r": 8.8, "avg_r": 0.11, "wr": 62.0,
                "pnl": 90.0, "last_ts": 10.0},
            "C_LIQ_SWEEP_RECLAIM | BOS_UP | SIDEWAY | LONG": {
                "n": 3, "wins": 1, "sum_r": -1.5, "avg_r": -0.5, "wr": 33.0,
                "pnl": -2.0, "last_ts": 10.0},
        }

    def test_tree_gom_theo_cap_va_cong_don_so_lieu(self):
        t = LES.tree(self._b())
        self.assertEqual(t["n"], 133)                     # tong so lenh
        self.assertIn("A_TREND_PULLBACK", t["children"])
        st = t["children"]["A_TREND_PULLBACK"]
        self.assertEqual(st["n"], 50)                     # 30 + 20
        self.assertEqual(st["children"]["BOS_UP"]["n"], 50)
        leaf = st["children"]["BOS_UP"]["children"]["UPTREND"]["children"]["LONG"]
        self.assertEqual(leaf["n"], 30)
        self.assertAlmostEqual(leaf["avg_r"], -0.20, places=2)

    def test_relevant_uu_tien_khop_nhieu_chieu(self):
        rows = LES.relevant(self._b(), strategy="A_TREND_PULLBACK", setup="BOS_UP",
                            regime="UPTREND", direction="LONG", max_nodes=2)
        self.assertEqual(rows[0]["key"], "A_TREND_PULLBACK | BOS_UP | UPTREND | LONG")
        self.assertEqual(rows[0]["hits"], 4)
        self.assertTrue(rows[0]["blocked"])               # avgR -0.20 <= -0.05

    def test_hint_chan_so_muc_va_do_dai(self):
        h = LES.hint(self._b(), strategy="A_TREND_PULLBACK", regime="UPTREND",
                     direction="SHORT", max_nodes=2, max_chars=60)
        self.assertEqual(len(h), 2)                       # TRAN: 2 muc
        self.assertTrue(all(len(s) <= 60 for s in h))     # TRAN: do dai
        self.assertIn("n=20", " ".join(h))
        self.assertTrue(all("|" in s for s in h))         # con nguyen khoa to hop

    def test_hint_rong_khi_khong_co_du_lieu(self):
        self.assertEqual(LES.hint({}, strategy="X"), [])
        self.assertEqual(LES.hint(self._b(), strategy="X", max_nodes=0), [])

    def test_hint_bo_qua_to_hop_qua_it_mau(self):
        h = LES.hint(self._b(), strategy="C_LIQ_SWEEP_RECLAIM", max_nodes=5)
        self.assertNotIn("C_LIQ_SWEEP_RECLAIM", " ".join(h))   # n=3 < min_n=5


class TestIncrementalLessons(unittest.TestCase):
    """(15/10) Doc journal TANG DAN theo fingerprint — ket qua phai GIONG doc lai toan bo."""

    def _lines(self):
        return [
            {"event": "OPEN", "pair": "AAA/USDT", "ts": 1.0,
             "strategy": "A_TREND_PULLBACK", "setup_type": "BOS_UP",
             "market_regime": "UPTREND", "direction": "LONG"},
            {"event": "CLOSE", "pair": "AAA/USDT", "ts": 2.0, "r": 1.0, "pnl": 5.0,
             "won": True, "reason": "TP"},
            {"event": "CLOSE", "pair": "ZZZ/USDT", "ts": 3.0, "r": 2.0, "pnl": 9.0,
             "won": True, "reason": "DUST"},                 # khong co OPEN
        ]

    def _write(self, p, rows, mode="w"):
        with open(p, mode, encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        return p

    def test_tang_dan_khop_voi_doc_lai_toan_bo(self):
        with tempfile.TemporaryDirectory() as td:
            j = self._write(Path(td) / "j.jsonl", self._lines())
            st = LES.update_state({}, j)
            inc = LES.build_from_state(st)
            full = LES.build(j)
            self.assertEqual(sorted(inc["buckets"]), sorted(full["buckets"]))
            for k in full["buckets"]:
                self.assertEqual(inc["buckets"][k]["n"], full["buckets"][k]["n"], k)
                self.assertAlmostEqual(inc["buckets"][k]["avg_r"],
                                       full["buckets"][k]["avg_r"], places=4)
            self.assertEqual(inc["trades"], full["trades"])          # 1
            self.assertEqual(inc["unpaired"], full["unpaired"])      # 1 (DUST)

    def test_them_lenh_moi_thi_chi_doc_phan_moi(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(Path(td) / "j.jsonl", self._lines())
            st = LES.update_state({}, p)
            off1 = st["offset"]
            self._write(p, [
                {"event": "OPEN", "pair": "BBB/USDT", "ts": 4.0,
                 "strategy": "B_BREAKOUT_RETEST", "setup_type": "BOS_DOWN",
                 "market_regime": "DOWNTREND", "direction": "SHORT"},
                {"event": "CLOSE", "pair": "BBB/USDT", "ts": 5.0, "r": 3.0, "pnl": 12.0,
                 "won": True, "reason": "TP"},
            ], mode="a")
            st2 = LES.update_state(st, p)
            self.assertGreater(st2["offset"], off1)                  # da doc them
            self.assertEqual(len(st2["buckets"]), 2)                 # bucket cu + moi
            self.assertEqual(st2["n_closed"], 3)
            # khong co gi moi -> tra ve nguyen trang thai
            st3 = LES.update_state(st2, p)
            self.assertEqual(st3["offset"], st2["offset"])
            self.assertEqual(len(st3["buckets"]), 2)

    def test_journal_bi_xoay_vong_thi_RESET_doc_lai_tu_dau(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._write(Path(td) / "j.jsonl", self._lines())
            st = LES.update_state({}, p)
            self._write(p, [self._lines()[0], self._lines()[1]])     # nho hon -> xoay vong
            st2 = LES.update_state(st, p)
            self.assertEqual(st2["resets"], 1)
            self.assertEqual(st2["n_closed"], 1)
            self.assertEqual(len(st2["buckets"]), 1)

    def test_dong_dang_ghi_do_khong_duoc_tinh(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "j.jsonl"
            self._write(p, self._lines())
            with open(p, "a", encoding="utf-8") as f:
                f.write('{"event":"CLOSE","pair":"AAA/USDT"')       # dong do dang
            st = LES.update_state({}, p)
            self.assertEqual(st["n_closed"], 2)                      # khong tinh dong do

    def test_read_state_save_state_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            c = Path(td) / "cache.json"
            self.assertEqual(LES.read_state(c), {})
            self.assertTrue(LES.save_state(c, {"offset": 5, "buckets": {}}))
            self.assertEqual(LES.read_state(c)["offset"], 5)
            c.write_text("{ hong", encoding="utf-8")
            self.assertEqual(LES.read_state(c), {})                  # hong -> rong, khong crash


if __name__ == "__main__":
    unittest.main()
