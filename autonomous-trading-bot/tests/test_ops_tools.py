"""Test bo cong cu van hanh moi (12/10): `tools/ops.py`, `tools/restart_bot.py`,
`tools/pick_symbols.py`, `winproc` (an cua so console).

Tat ca deu la ham THUAN TUY / doc file -> khong goi mang, chay nhanh.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import apply_symbols as AS       # noqa: E402
import ops as OPS                # noqa: E402
import pick_symbols as PS        # noqa: E402
import restart_bot as RB         # noqa: E402
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


if __name__ == "__main__":
    unittest.main()

if __name__ == "__main__":
    unittest.main()
