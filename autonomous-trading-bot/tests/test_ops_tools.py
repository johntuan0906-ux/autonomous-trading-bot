"""Test bo cong cu van hanh moi (12/10): `tools/ops.py`, `tools/restart_bot.py`,
`tools/pick_symbols.py`, `winproc` (an cua so console).

Tat ca deu la ham THUAN TUY / doc file -> khong goi mang, chay nhanh.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import apply_symbols as AS       # noqa: E402
import entries_gate as EG        # noqa: E402
import ops as OPS                # noqa: E402
import pick_symbols as PS        # noqa: E402
import restart_bot as RB         # noqa: E402
import restart_when_flat as RWF  # noqa: E402
import winproc as WP             # noqa: E402


class TestWinproc(unittest.TestCase):
    """Moi tien trinh con phai chay NGAM (het cua so console nhay len)."""

    def test_an_cua_so_tren_windows(self):
        kw = WP.hide_kwargs()
        if sys.platform == "win32":
            import subprocess
            self.assertEqual(kw.get("creationflags"), subprocess.CREATE_NO_WINDOW)
            self.assertIn("startupinfo", kw, "phai ep SW_HIDE cho cua so con")
            self.assertTrue(kw["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW)
            self.assertEqual(kw["startupinfo"].wShowWindow, 0)
        else:
            self.assertEqual(kw, {})

    def test_run_hidden_tra_ket_qua(self):
        r = WP.run_hidden([sys.executable, "-c", "print('ok')"],
                          capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0)
        self.assertIn("ok", r.stdout)


class TestPickSymbols(unittest.TestCase):
    def test_xep_hang_theo_thanh_khoan_va_bo_cap_thua(self):
        vols = {"A/USDT:USDT": 100.0, "B/USDT:USDT": 500.0, "C/USDT:USDT": 50.0,
                "D/USDT:USDT": 900.0}
        banned = {"D/USDT:USDT"}
        stats = {"C/USDT:USDT": {"n": 8, "avgR": -0.40}}     # da chung minh thua
        rows = PS.rank_pairs(vols, banned, stats, set(), top=10)
        syms = [s for s, _ in rows]
        self.assertEqual(syms, ["B/USDT:USDT", "A/USDT:USDT"])
        self.assertNotIn("D/USDT:USDT", syms, "cap bi ban khong duoc vao")
        self.assertNotIn("C/USDT:USDT", syms, "cap thua (avgR -0.40) bi loai")

    def test_giu_cap_dang_co_vi_the_du_thanh_khoan_thap(self):
        vols = {"A/USDT:USDT": 100.0, "Z/USDT:USDT": 1.0}
        rows = PS.rank_pairs(vols, set(), {}, {"Z/USDT:USDT"}, top=1)
        self.assertIn("Z/USDT:USDT", [s for s, _ in rows],
                      "khong duoc bo roi vi the dang mo")

    def test_top_gioi_han_so_cap(self):
        vols = {"S%d/USDT:USDT" % i: float(i) for i in range(20)}
        rows = PS.rank_pairs(vols, set(), {}, set(), top=5)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0][0], "S19/USDT:USDT")

    def test_thong_ke_journal_chi_tinh_cap_du_mau(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "journal.jsonl"
            recs = [{"event": "CLOSE", "pair": "A", "r": 1.0},
                    {"event": "CLOSE", "pair": "A", "r": -0.5},
                    {"event": "CLOSE", "pair": "B", "r": -1.0},
                    {"event": "OPEN", "pair": "C"},
                    {"event": "CLOSE", "pair": "A", "r": None}]
            p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
            st = PS.load_journal_stats(p, min_n=2)
        self.assertEqual(st["A"]["n"], 2)
        self.assertAlmostEqual(st["A"]["avgR"], 0.25)
        self.assertNotIn("B", st, "n < min_n thi khong ket luan")

    def test_whitelist_doc_ghi_bo_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "logs"
            d.mkdir(parents=True)
            (d / "live_whitelist.txt").write_text(
                "# comment\nSOL/USDT:USDT\n\n  XRP/USDT:USDT  \n", encoding="utf-8")
            old = PS.TARGETS["live"]
            PS.TARGETS["live"] = Path(tmp)
            try:
                self.assertEqual(PS.read_whitelist("live"),
                                 ["SOL/USDT:USDT", "XRP/USDT:USDT"])
            finally:
                PS.TARGETS["live"] = old



class TestRestartBot(unittest.TestCase):
    def test_vi_the_mo_tinh_theo_OPEN_tru_CLOSE(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "logs").mkdir(parents=True)
            recs = [{"event": "OPEN", "pair": "A"}, {"event": "CLOSE", "pair": "A"},
                    {"event": "OPEN", "pair": "B"}, {"event": "OPEN", "pair": "B"},
                    {"event": "CLOSE", "pair": "B"}, {"event": "OPEN", "pair": "C"}]
            (d / "logs" / "journal.jsonl").write_text(
                "\n".join(json.dumps(r) for r in recs), encoding="utf-8")
            self.assertEqual(RB.open_positions(d), 2)   # B (con 1) + C

    def test_khong_co_journal_thi_coi_nhu_phang(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(RB.open_positions(Path(tmp)), 0)

    def test_anh_xa_thu_muc_instance(self):
        self.assertEqual(RB.instance_dir("testnet"), ROOT)
        self.assertEqual(RB.instance_dir("LIVE").name, "atb-live")

    def test_reset_killswitch_xoa_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "logs").mkdir(parents=True)
            p = d / "logs" / "risk_state.json"
            p.write_text('{"tripped": true}', encoding="utf-8")
            self.assertTrue(RB.reset_killswitch(d))
            self.assertFalse(p.exists())
            self.assertTrue(RB.reset_killswitch(d), "xoa lai lan 2 van phai True")

    def test_doc_env_cua_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / ".env").write_text("# comment\nBINANCE_TESTNET=false\n"
                                    "BINANCE_API_KEY=abc\n\nBINANCE_API_SECRET=xyz\n",
                                    encoding="utf-8")
            kv = RB.env_kv(d)
        self.assertEqual(kv["BINANCE_TESTNET"], "false")
        self.assertEqual(kv["BINANCE_API_KEY"], "abc")
        self.assertNotIn("# comment", kv)

    def test_vi_the_san_dung_nguon_su_that(self):
        class _Ex:
            def __init__(self, rows):
                self.rows = rows

            def fetch_positions(self):
                return self.rows

        rows = [{"symbol": "A", "contracts": 1.0},
                {"symbol": "B", "contracts": 0.0},      # da dong -> khong tinh
                {"symbol": "C", "contracts": -2.5}]
        self.assertEqual(RB.live_open_positions(Path("."), client=_Ex(rows)), 2)

    def test_doc_san_loi_thi_tra_None(self):
        class _Bad:
            def fetch_positions(self):
                raise RuntimeError("mang loi")

        self.assertIsNone(RB.live_open_positions(Path("."), client=_Bad()),
                          "khong doc duoc phai la None (fail-safe, khong restart)")

    def test_thieu_key_thi_khong_doc_duoc_san(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(RB.live_open_positions(Path(tmp)),
                              "khong co .env/key -> None (khong suy dien)")


class TestOpsReport(unittest.TestCase):
    LOG = (
        "2026-10-12 12:00:01,000 INFO round 1 monitor={} -> "
        "[{'symbol': 'A', 'status': 'OPENED'}, {'symbol': 'B', 'status': 'WAIT'}, "
        "{'symbol': 'C', 'error': 'FETCH_TIMEOUT round_timeout_sec'}]\n"
        "2026-10-12 12:05:02,000 WARNING fetch X qua han 280s -> bo qua vong nay\n"
        "2026-10-12 12:05:03,000 WARNING DATA_FAIL cho Y\n"
        "2026-10-12 12:05:04,000 INFO round 2 monitor={} -> "
        "[{'symbol': 'A', 'status': 'SKIP_RISK'}]\n"
    )

    def test_dem_vong_va_status_vong_cuoi(self):
        n, last, st = OPS._last_round(self.LOG)
        self.assertEqual(n, 2)
        self.assertEqual(last, "2")
        self.assertEqual(st["SKIP_RISK"], 1)

    def test_cua_so_thoi_gian_loai_dong_cu(self):
        win = OPS._window_lines(self.LOG, minutes=1)
        self.assertEqual(win, [], "log 12/10 12:00 da qua xa so voi hien tai")
        win_all = OPS._window_lines(self.LOG, minutes=10 ** 7)
        self.assertEqual(len(win_all), 4)

    def test_dem_loi_theo_mau(self):
        win = OPS._window_lines(self.LOG, minutes=10 ** 7)
        counts = {p: sum(p in ln for ln in win) for p in OPS.COUNT_PATTERNS}
        self.assertEqual(counts["FETCH_TIMEOUT"], 1)
        self.assertEqual(counts["DATA_FAIL"], 1)
        self.assertEqual(counts["OPENED"], 1)
        self.assertEqual(counts["qua han"], 1,
                         "canh bao tieng Viet cung phai duoc dem")


class TestTuneScanTheoSoCap(unittest.TestCase):
    """Danh sach nho -> vong quet ngan hon (nhanh hon, may nhe hon)."""

    def test_poll_theo_so_cap(self):
        self.assertEqual(AS.tune_for(40)["POLL_INTERVAL_SEC"], "120")
        self.assertEqual(AS.tune_for(60)["POLL_INTERVAL_SEC"], "120")
        self.assertEqual(AS.tune_for(150)["POLL_INTERVAL_SEC"], "180")
        self.assertEqual(AS.tune_for(458)["POLL_INTERVAL_SEC"], "300")

    def test_round_timeout_nho_hon_poll_va_du_lon(self):
        for n in (10, 40, 150, 458):
            t = AS.tune_for(n)
            self.assertGreaterEqual(int(t["ROUND_TIMEOUT_SEC"]), 120)
            self.assertLessEqual(int(t["ROUND_TIMEOUT_SEC"]), 300)

    def test_giu_nguyen_cac_tham_so_khac(self):
        t = AS.tune_for(40)
        self.assertEqual(t["SCAN_WORKERS"], AS.SCAN_TUNE["SCAN_WORKERS"])
        self.assertEqual(t["COOLDOWN_SEC"], AS.SCAN_TUNE["COOLDOWN_SEC"])


class TestProtectionDrift(unittest.TestCase):
    """(12/10) Lenh dieu kien o Algo Order API truoc day KHONG huy duoc -> ban SL
    CU (truoc BE/trail) van nam tren san. Neu chi hoi "co SL/TP chua" thi bot
    tuong da bao ve va KHONG bao gio keo SL ve hoa von."""

    def test_khop_thi_khong_dat_lai(self):
        import turbo_demo as TD
        self.assertFalse(TD.protection_drift({"sl": 100.0, "tp": 120.0}, 100.0, 120.0))

    def test_lech_nho_trong_dung_sai_so(self):
        import turbo_demo as TD
        self.assertFalse(TD.protection_drift({"sl": 100.1, "tp": 120.0}, 100.0, 120.0))

    def test_sl_cu_lech_nhieu_thi_phai_dat_lai(self):
        import turbo_demo as TD
        # san con SL cu 95 (truoc BE) trong khi state da keo ve 100 (hoa von)
        self.assertTrue(TD.protection_drift({"sl": 95.0, "tp": 120.0}, 100.0, 120.0))

    def test_tp_lech_cung_phai_dat_lai(self):
        import turbo_demo as TD
        self.assertTrue(TD.protection_drift({"sl": 100.0, "tp": 130.0}, 100.0, 120.0))

    def test_thieu_hoac_khong_doc_duoc_thi_dat_lai(self):
        import turbo_demo as TD
        self.assertTrue(TD.protection_drift({}, 100.0, 120.0))
        self.assertTrue(TD.protection_drift({"sl": None, "tp": 120.0}, 100.0, 120.0))
        self.assertTrue(TD.protection_drift({"sl": "x", "tp": "y"}, 100.0, 120.0))

    def test_khong_co_moc_so_sanh_thi_giu_nguyen(self):
        import turbo_demo as TD
        self.assertFalse(TD.protection_drift({"sl": 100.0, "tp": 120.0}, 0.0, 0.0))


class TestPromMetrics(unittest.TestCase):
    """`logs/metrics.prom` (Prometheus textfile) tu bao cao ops — y tuong tu pentagi."""

    REP = [{"name": "TESTNET", "equity": 3615.22, "round": 135, "hb_age_s": 41.5,
            "kill_tripped": False, "positions": 7, "orders": 14, "orphans": 0,
            "errors_win": {"OPENED": 2, "ORDER_FAILED": 1}},
           {"name": "LIVE", "equity": 19.46, "round": 5, "hb_age_s": 33.0,
            "kill_tripped": True, "positions": 0, "orders": 0, "orphans": 0}]

    def test_co_help_type_va_gia_tri(self):
        txt = "\n".join(OPS.prom_lines(self.REP))
        self.assertIn("# TYPE bot_equity gauge", txt)
        self.assertIn('bot_equity{instance="testnet"} 3615.22', txt)
        self.assertIn('bot_positions{instance="live"} 0', txt)
        self.assertIn('bot_kill_switch{instance="live"} 1', txt)
        self.assertIn('bot_errors_15m{instance="testnet",kind="OPENED"} 2', txt)

    def test_equity_khong_doc_duoc_thi_0(self):
        txt = "\n".join(OPS.prom_lines([{"name": "X", "equity": None}]))
        self.assertIn('bot_equity{instance="x"} 0.0', txt)

    def test_write_prom_ghi_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = OPS.write_prom(self.REP, path=Path(d) / "m.prom")
            self.assertTrue(p)
            txt = Path(p).read_text(encoding="utf-8")
        self.assertIn("bot_round", txt)

    def test_prom_rong_thi_khong_crash(self):
        self.assertIn("# TYPE bot_equity gauge", "\n".join(OPS.prom_lines([])))


class TestLocalModelProbe(unittest.TestCase):
    """(13/10) Phieu LOCAL cua hoi dong chet thi IM LANG mat (fail-open) -> phai kiem tra.

    Ham nay doc AGENT_LOCAL_BASE_URL va goi /v1/models (llamafile) hoac /api/tags (Ollama).
    """

    def test_thieu_base_url_thi_bao_loi_ro(self):
        import harness_audit as HA
        r = HA.probe_local_model({})
        self.assertFalse(r["ok"])
        self.assertIn("trong", r["error"])

    def test_url_sai_thi_khong_crash(self):
        import harness_audit as HA
        r = HA.probe_local_model({"AGENT_LOCAL_BASE_URL": "http://127.0.0.1:1/v1"},
                                 timeout=0.5)
        self.assertFalse(r["ok"])
        self.assertTrue(r["error"])

    def test_doc_duoc_danh_sach_model_tu_may_chu_gia(self):
        import http.server
        import harness_audit as HA
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):                       # noqa: N802
                body = b'{"data":[{"id":"model-a"},{"id":"model-b"}]}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):              # im lang
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            r = HA.probe_local_model({"AGENT_LOCAL_BASE_URL": "http://127.0.0.1:%d/v1" % port})
        finally:
            srv.shutdown()
        self.assertTrue(r["ok"])
        self.assertEqual(r["ids"], ["model-a", "model-b"])

    def test_check_them_muc_model_local(self):
        import harness_audit as HA
        checks: list = []
        HA._chk_local_model(checks, {})
        self.assertEqual(checks[0]["name"], "model-local")
        self.assertEqual(checks[0]["level"], "OK")

    def test_canh_bao_khi_local_chet(self):
        import harness_audit as HA
        checks: list = []
        HA._chk_local_model(checks, {"AGENT_COUNCIL_LOCAL": "x",
                                     "AGENT_LOCAL_BASE_URL": "http://127.0.0.1:1/v1"})
        self.assertEqual(checks[0]["level"], "WARN")
        self.assertIn("llamafile", checks[0]["fix"])

    def test_hai_ham_kiem_tra_tach_biet(self):
        """(13/10) Loi that: xoa nham `def _chk_protection` -> than ham dinh vao
        `_chk_local_model` => muc 'bao-ve' (goi san THAT) bi them o CA hai duong.
        Test nay chan tai phat: `_chk_local_model` KHONG duoc them muc 'bao-ve'."""
        import harness_audit as HA
        self.assertTrue(callable(getattr(HA, "_chk_protection", None)),
                        "_chk_protection phai la ham rieng")
        checks: list = []
        HA._chk_local_model(checks, {})              # khong co model local
        names = [c["name"] for c in checks]
        self.assertEqual(names, ["model-local"],
                         "chi duoc them 1 muc model-local, khong keo theo 'bao-ve'")

    def test_khong_co_with_exchange_thi_khong_goi_san(self):
        """`audit_one` khong co --with-exchange => muc 'bao-ve' phai la 'bo qua'."""
        import harness_audit as HA
        rep = HA.audit_one(HA.ROOT, "TESTNET", with_exchange=False)
        bv = [c for c in rep["checks"] if c["name"] == "bao-ve"]
        self.assertEqual(len(bv), 1, "chi duoc co DUNG 1 muc bao-ve")
        self.assertIn("bo qua", bv[0]["detail"])


class TestBackupTool(unittest.TestCase):
    """(14/10) tools/backup.py — sao luu .env + journal + state, CO KIEM CHUNG doc lai."""

    def _mod(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backup_tool", str(ROOT / "tools" / "backup.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _fake_instance(self, base):
        (base / "logs").mkdir(parents=True, exist_ok=True)
        (base / "logs" / "journal.jsonl").write_text('{"event":"OPEN"}\n', encoding="utf-8")
        (base / "logs" / "agent_state.json").write_text('{"calls":1}', encoding="utf-8")
        (base / ".env").write_text("A=1\n", encoding="utf-8")
        (base / "logs" / "rong.json").write_text("", encoding="utf-8")   # bo qua
        return base

    def test_dry_run_liet_ke_khong_tao_file(self):
        mod = self._mod()
        with tempfile.TemporaryDirectory() as td:
            base = self._fake_instance(Path(td) / "inst")
            out = Path(td) / "backups"
            rep = mod.make_backup("testnet", base, out, dry_run=True)
            self.assertEqual(rep["files"], 3)
            self.assertFalse(out.exists())
            self.assertIn(".env", rep["sources"])

    def test_nen_va_kiem_chung_doc_lai(self):
        mod = self._mod()
        with tempfile.TemporaryDirectory() as td:
            base = self._fake_instance(Path(td) / "inst")
            out = Path(td) / "backups"
            rep = mod.make_backup("testnet", base, out, keep=14)
            self.assertTrue(rep["ok"], rep)
            self.assertTrue(rep["verify"]["has_journal"])
            self.assertEqual(rep["verify"]["entries"], 3)
            self.assertTrue(Path(rep["path"]).exists())

    def test_giu_keep_ban_moi_nhat_va_xoa_cu(self):
        mod = self._mod()
        with tempfile.TemporaryDirectory() as td:
            base = self._fake_instance(Path(td) / "inst")
            out = Path(td) / "backups"
            for i in range(3):
                p = out / ("atb-testnet-2026010%d-000000.zip" % i)
                out.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"cu")
                os.utime(p, (1000 + i, 1000 + i))
            removed = mod.prune(out, "testnet", 1)
            self.assertEqual(len(removed), 2)
            self.assertEqual([p.name for p in out.glob("atb-testnet-*.zip")],
                             ["atb-testnet-20260102-000000.zip"])

    def test_khong_co_file_thi_bao_loi_khong_crash(self):
        mod = self._mod()
        with tempfile.TemporaryDirectory() as td:
            rep = mod.make_backup("live", Path(td) / "khong-co", Path(td) / "b")
            self.assertFalse(rep["ok"])
            self.assertIn("khong co file", rep["error"])


class TestJournalTail(unittest.TestCase):
    """(13/10) tools/journal_tail.py — cong cu doc ly do that cua tung phieu AGENT."""

    def test_chi_lay_ban_ghi_agent_va_lay_cuoi(self):
        import tempfile
        import json as _j
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "journal_tail", str(ROOT / "tools" / "journal_tail.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "journal.jsonl"
            lines = [
                _j.dumps({"event": "OPEN", "symbol": "BTC"}),
                _j.dumps({"event": "AGENT", "model": "m1", "note": "treo"}),
                "khong-phai-json",
                _j.dumps({"event": "AGENT", "model": "m2", "note": "loi provider"}),
                _j.dumps({"event": "CLOSE", "symbol": "BTC"}),
            ]
            p.write_text("\n".join(lines), encoding="utf-8")
            got = mod.tail_agents(p, 5)
            self.assertEqual([r["model"] for r in got], ["m1", "m2"])
            self.assertEqual([r["model"] for r in mod.tail_agents(p, 1)], ["m2"])
            self.assertEqual(mod.tail_agents(Path(td) / "khong-co.jsonl", 5), [])
            self.assertIn("m2", mod.format_row({"model": "m2", "note": "loi provider"}))


class TestRestartWhenFlatTarget(unittest.TestCase):
    """(15/10) `restart_when_flat.py` phai nham DUNG instance.

    Loi that: `ROOT = Path(__file__).parent` co dinh ⇒ chay
    `python ..\\autonomous-trading-bot\\restart_when_flat.py` tu `atb-live` van doc `.env`
    va kill supervisor cua **TESTNET** (LIVE khong bao gio duoc ap cau hinh moi; va nguy
    hon: kill nham instance dang co vi the mo).
    """

    def test_anh_xa_instance(self):
        self.assertEqual(RWF.target_dir("testnet"), ROOT)
        self.assertEqual(RWF.target_dir("LIVE").name, "atb-live")

    def test_target_la_thi_thoat(self):
        with self.assertRaises(SystemExit):
            RWF.target_dir("khong-ton-tai")

    def test_doc_cap_theo_thu_muc_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / ".env").write_text(
                "SYMBOLS=A/USDT:USDT,B/USDT:USDT\nEXTRA_SYMBOLS=C/USDT:USDT\n",
                encoding="utf-8")
            self.assertEqual(RWF.env_symbols(d),
                             ["A/USDT:USDT", "B/USDT:USDT", "C/USDT:USDT"])

    def test_vien_journal_do_theo_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "logs").mkdir(parents=True)
            (d / "logs" / "journal.jsonl").write_text(
                '{"event": "OPEN", "pair": "A"}\n', encoding="utf-8")
            self.assertEqual(RWF.supervisor_pid(d), 0)      # khong co lock -> 0 (an toan)


class TestEntriesGateExpiry(unittest.TestCase):
    """(19/10) Cong tam dung vao lenh phai CO HAN va TU MO LAI khi het han.

    Vi sao: lop loi da gap THAT — "tam dung roi quen mo lai" (BTW 16-18/10 phai viet
    watcher rieng; TESTNET ket pause 3.6 ngay vi `tripped` khong tu xoa). Phieu hoi dong
    LIVE 4-0 VETO: het vi the thi pause 24h nguoi — nguoi van hanh khong the tin vao tri nho.
    """

    def test_het_han_thi_tu_mo_lai(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "logs" / "entries_pause.json"
            t0 = 1_000_000.0
            EG.pause("cho 24h nguoi", path=p, hours=24, now=lambda: t0)
            self.assertTrue(EG.paused(path=p, now=lambda: t0 + 60)[0])
            self.assertTrue(EG.paused(path=p, now=lambda: t0 + 23 * 3600)[0])
            ok, why = EG.paused(path=p, now=lambda: t0 + 25 * 3600)
            self.assertFalse(ok)
            self.assertIn("het han", why)
            # da ghi vet vao file => lan sau KHONG con tam dung
            self.assertFalse(EG.paused(path=p, now=lambda: t0 + 26 * 3600)[0])
            self.assertFalse(json.loads(p.read_text(encoding="utf-8"))["paused"])

    def test_khong_co_han_thi_vo_thoi_han(self):
        """Hanh vi cu (16/10) khong doi: `pause()` khong `hours` => tam dung toi khi mo tay."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "entries_pause.json"
            EG.pause("khong co han", path=p, now=lambda: 0.0)
            self.assertTrue(EG.paused(path=p, now=lambda: 10 ** 9)[0])

    def test_until_hong_thi_van_tam_dung(self):
        """Fail-safe: `until` khong phai so => KHONG duoc tu mo lai."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "entries_pause.json"
            p.write_text(json.dumps({"paused": True, "reason": "x", "until": "mai"}),
                         encoding="utf-8")
            self.assertTrue(EG.paused(path=p, now=lambda: 10 ** 9)[0])

    def test_file_hong_van_la_fail_open(self):
        """File hong = chua tung tam dung (giu nguyen hanh vi cu, khong doi)."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "entries_pause.json"
            p.write_text("{hong", encoding="utf-8")
            self.assertFalse(EG.paused(path=p)[0])


class TestRestartWhenFlatPause(unittest.TestCase):
    """(19/10) `--pause-entries-hours`: het vi the => TAM DUNG (co han) ROI MOI restart.

    Phieu hoi dong LIVE 4-0 VETO viec resume ngay: bot phai dung mo lenh moi trong khi
    van quan ly vi the + hoc bai. Thu tu quan trong: pause TRUOC, restart SAU.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._log = RWF.LOG
        self._logfn = RWF.log
        RWF.LOG = Path(self.tmp.name) / "restart_when_flat.log"
        RWF.log = lambda msg: None          # test khong can in ra man hinh

    def tearDown(self):
        RWF.LOG = self._log
        RWF.log = self._logfn
        self.tmp.cleanup()

    def test_pause_truoc_khi_restart(self):
        calls = []
        res = RWF.wait_flat(None, poll=0.01, max_hours=1, fetch=lambda e: 0,
                            do_restart=lambda: (calls.append("restart"), {"ok": True})[1],
                            pause_hours=24,
                            pause_entries_fn=lambda: (calls.append("pause"),
                                                      {"ok": True})[1])
        self.assertEqual(calls, ["pause", "restart"])
        self.assertTrue(res["ok"])
        self.assertTrue(res["pause"]["ok"])

    def test_mac_dinh_khong_pause(self):
        calls = []
        RWF.wait_flat(None, poll=0.01, max_hours=1, fetch=lambda e: 0,
                      do_restart=lambda: (calls.append("restart"), {"ok": True})[1])
        self.assertEqual(calls, ["restart"])

    def test_pause_ghi_dung_file_instance(self):
        d = Path(self.tmp.name) / "instance"
        r = RWF.pause_entries(d, 24, "vi du", now=lambda: 500.0)
        self.assertTrue(r["ok"], r)
        p = d / "logs" / "entries_pause.json"
        self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["by"],
                         "restart_when_flat")     # ghi vet AI bat cong
        self.assertTrue(EG.paused(path=p, now=lambda: 600.0)[0])
        self.assertFalse(EG.paused(path=p, now=lambda: 500.0 + 25 * 3600)[0])
        # het han thi TU MO LAI va ghi ro AI mo (provenance)
        rec = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(rec["by"], "entries_gate")
        self.assertEqual(rec["reason"], "het han tam dung")



class TestEnvTheoInstance(unittest.TestCase):
    """(15/10) Tool chay "cho instance khac" phai doc DUNG `.env` cua instance do.

    Do that: `load_dotenv()` tim `.env` theo thu muc cua `config.py` => tool chay tu repo
    chinh ma nham `../atb-live` van dung `.env` testnet (key demo + `BINANCE_TESTNET=true`)
    => `-2015 Invalid API-key`, snapshot LIVE ghi `testnet=true` => `live_guard` BO QUA
    moi chot chan trong bao cao.
    """

    def test_load_instance_env_ghi_de_bien_cu(self):
        import config as CFG
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / ".env"
            p.write_text("BINANCE_TESTNET=false\nATB_TEST_INSTANCE=live\n", encoding="utf-8")
            old = os.environ.get("BINANCE_TESTNET")
            os.environ["BINANCE_TESTNET"] = "true"
            try:
                got = CFG.load_instance_env(tmp)
                self.assertEqual(got, str(p))
                self.assertEqual(os.environ.get("BINANCE_TESTNET"), "false",
                                 "phai ghi de: day la chi dinh ro rang")
                self.assertEqual(os.environ.get("ATB_TEST_INSTANCE"), "live")
            finally:
                os.environ.pop("ATB_TEST_INSTANCE", None)
                if old is None:
                    os.environ.pop("BINANCE_TESTNET", None)
                else:
                    os.environ["BINANCE_TESTNET"] = old

    def test_load_instance_env_thieu_file_thi_khong_lam_gi(self):
        import config as CFG
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(CFG.load_instance_env(tmp), "")

    def test_state_sync_duong_dan_theo_instance(self):
        import state_sync as SS
        base, md, snap = SS.target_paths("testnet")
        self.assertEqual(base, SS.ROOT)
        self.assertEqual(md, SS.ROOT / "STATE.md")
        base2, md2, snap2 = SS.target_paths("live")
        self.assertEqual(base2.name, "atb-live")
        self.assertEqual(md2, base2 / "STATE.md")
        self.assertEqual(snap2, base2 / "logs" / "state_snapshot.json")


class TestCapabilities(unittest.TestCase):
    """(16/10) Manifest nang luc — y tuong tu HKUDS/CLI-Anything: tool phai TU MO TA duoc
    de agent (hoi dong) kham pha va goi dung, thay vi doan ten."""

    def test_quet_duoc_tool_va_muc_dich(self):
        import capabilities as CAP
        items = CAP.scan()
        names = {i["name"] for i in items}
        self.assertIn("margin_audit", names)
        self.assertIn("council_vote", names)
        one = next(i for i in items if i["name"] == "margin_audit")
        self.assertTrue(one["documented"], "moi tool phai co docstring (chong 'slop')")
        self.assertIn("MARGIN", one["purpose"].upper())

    def test_check_phat_hien_tool_thieu_docstring(self):
        import capabilities as CAP
        rep = CAP.check([{"name": "a", "purpose": "", "tests": 0, "documented": False},
                         {"name": "b", "purpose": "co", "tests": 1, "documented": True}])
        self.assertFalse(rep["ok"])
        self.assertEqual(rep["missing_doc"], ["a"])
        self.assertEqual(rep["no_test"], ["a"])

    def test_quet_thu_muc_rong_khong_loi(self):
        import capabilities as CAP
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "tools").mkdir()
            self.assertEqual(CAP.scan(root=d, tests_dir=d), [])


class TestCouncilVoteReport(unittest.TestCase):
    """(19/10) Lop loi B-011: model duoc LIET KE nhung khong bo phieu phai duoc bao RO.

    Do that: `muse-spark-1.3-contributor` probe tra JSON hop le nhung 3/3 lan deu vao
    `abstained` => hoi dong "6 model" thuc chat chi 5. Khong duoc de viec nay im lang
    (dung lop loi da lam hoi dong "im lang" 48h).
    """

    def test_model_khong_tra_phieu_duoc_bao_ro(self):
        import council_vote as CV
        rows = [{"model": "cline-pass/a", "action": "ALLOW"},
                {"model": "cline-pass/b", "action": "VETO"}]
        ms = ["cline-pass/a", "cline-pass/b", "cline-pass/muse-spark", "local/x"]
        self.assertEqual(CV.missing_models(ms, rows),
                         ["cline-pass/muse-spark", "local/x"])
        self.assertEqual(CV.missing_models(ms, ms and [{"model": m} for m in ms]), [])

    def test_hoa_phieu_la_no_opinion(self):
        """Hoa KHONG duoc doc thanh dong thuan (B-018) — quyet dinh thuoc ve nguoi van hanh."""
        import council_vote as CV
        rep = CV.tally({"m1": {"action": "ALLOW"}, "m2": {"action": "VETO"}})
        self.assertEqual(rep["verdict"], "NO_OPINION")
        self.assertEqual((rep["n_allow"], rep["n_veto"], rep["n_abstain"]), (1, 1, 0))
        self.assertEqual(CV.tally({"m1": {"action": "VETO"}, "m2": {"action": "ALLOW"},
                                   "m3": {"action": "VETO"}})["verdict"], "VETO")


class TestBugCatalog(unittest.TestCase):
    """(19/10) Danh muc lop loi <-> test: "moi lop loi phai co test chot" phai KIEM TRA DUOC.

    Vi sao: sua 1 lop loi roi ve sau vo tinh xoa/doi ten test => mat chot chan ma khong ai
    biet. `--check` doc `tests/` va bao test bi thieu.
    """

    def setUp(self):
        import bug_catalog as BC
        self.BC = BC

    def test_moi_muc_du_truong_va_ma_khong_trung(self):
        codes = [c["code"] for c in self.BC.CLASSES]
        self.assertEqual(len(codes), len(set(codes)), "ma lop loi bi trung")
        for c in self.BC.CLASSES:
            for k in ("code", "kind", "title", "symptom", "guard", "files", "tests"):
                self.assertTrue(c.get(k), "%s thieu truong %s" % (c.get("code"), k))
            self.assertIn(c["kind"], self.BC.KINDS)

    def test_check_tren_repo_that_phai_OK(self):
        """Chot chan that: MOI test duoc dan trong danh muc phai TON TAI trong `tests/`."""
        rep = self.BC.check()
        self.assertEqual(rep["missing"], [], "test bi thieu: %s" % rep["missing"])
        self.assertEqual(rep["no_test"], [])
        self.assertTrue(rep["ok"])
        self.assertGreaterEqual(rep["n"], 15)
        self.assertGreaterEqual(rep["pinned"], 20)

    def test_check_bao_thieu_khi_test_bien_mat(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "test_ops_tools.py").write_text("class A:\n    def test_x(self):\n        pass\n",
                                                 encoding="utf-8")
            rep = self.BC.check([{"code": "B-999", "tests": ["test_ops_tools.py::A::test_khong_co"]}],
                                tests_dir=d)
            self.assertFalse(rep["ok"])
            self.assertEqual(rep["missing"], ["B-999 -> test_ops_tools.py::A::test_khong_co"])
            rep2 = self.BC.check([{"code": "B-998", "tests": []}], tests_dir=d)
            self.assertEqual(rep2["no_test"], ["B-998"])

    def test_tim_khong_dau(self):
        self.assertIn("B-009", [c["code"] for c in self.BC.find(text="tam dung")])
        self.assertIn("B-011", [c["code"] for c in self.BC.find(text="probe")])
        self.assertEqual(self.BC.find(text="zzz-khong-co-gi"), [])

    def test_chi_tiet_in_ra_test(self):
        c = self.BC.find(text="B-001")[0]
        txt = "\n".join(self.BC.detail(c))
        self.assertIn("Test chot", txt)
        self.assertIn(c["tests"][0], txt)



if __name__ == "__main__":
    unittest.main()
