"""Test `tools/terminal_hygiene.py` — don terminal rac cua VS Code (an toan 3 lop).

Vi sao co (19/10): extension Cline tao **1 terminal moi cho moi lan chay lenh** va khong tu
dong ⇒ do that **112 shell PowerShell = 1138 MB RAM**. Test nay chot 3 lop an toan, de
KHONG BAO GIO cat ngang viec dang chay (bot/watcher la con cua shell):
  1. chi shell co parent la `Code.exe`;  2. chi shell RANH (khong co tien trinh con);
  3. bo qua cay tien trinh dang chay tool.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import terminal_hygiene as TH      # noqa: E402

CODE = 1000                        # pid gia cua Code.exe


def _row(name, pid, ppid, mb=50.0) -> dict:
    return {"Name": name, "ProcessId": pid, "ParentProcessId": ppid,
            "WorkingSetSize": int(mb * 1024 * 1024)}


class TestParseRows(unittest.TestCase):
    def test_list_json(self):
        rows = TH.parse_rows('[{"Name": "Code.exe", "ProcessId": 1}]')
        self.assertEqual(rows[0]["ProcessId"], 1)

    def test_1_object_duoc_boc_thanh_list(self):
        """PowerShell tra 1 OBJECT khi chi co 1 dong — phai chiu duoc."""
        self.assertEqual(len(TH.parse_rows('{"Name": "Code.exe", "ProcessId": 7}')), 1)

    def test_rac_khong_lam_sap(self):
        self.assertEqual(TH.parse_rows("khong phai json\n{hong\n[]"), [])

    def test_rong(self):
        self.assertEqual(TH.parse_rows(""), [])


class TestAncestors(unittest.TestCase):
    def test_lay_ca_to_tien(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE),
                _row("python.exe", 12, 11)]
        self.assertEqual(TH.ancestors_of(12, rows), {12, 11, CODE, 1})

    def test_pid_la_khong_treo_vo_han(self):
        rows = [_row("x", 5, 5)]                  # tu lam cha cua chinh no
        self.assertEqual(TH.ancestors_of(5, rows), {5})


class TestPickIdleShells(unittest.TestCase):
    def test_shell_ranh_cua_code_thi_chon(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE, mb=80)]
        got = TH.pick_idle_shells(rows)
        self.assertEqual([s["pid"] for s in got], [11])
        self.assertEqual(got[0]["mb"], 80.0)

    def test_shell_co_tien_trinh_con_thi_bo_qua(self):
        """BOT/WATCHER la con cua shell => shell do KHONG duoc xoa."""
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE),
                _row("python.exe", 12, 11)]
        self.assertEqual(TH.pick_idle_shells(rows), [])

    def test_shell_khong_phai_cua_code_thi_bo_qua(self):
        rows = [_row("explorer.exe", 5, 1), _row("powershell.exe", 11, 5)]
        self.assertEqual(TH.pick_idle_shells(rows), [])

    def test_pid_duoc_bao_ve_thi_bo_qua(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE)]
        self.assertEqual(TH.pick_idle_shells(rows, protect={11}), [])

    def test_cmd_cung_duoc_don(self):
        rows = [_row("Code.exe", CODE, 1), _row("cmd.exe", 13, CODE)]
        self.assertEqual([s["pid"] for s in TH.pick_idle_shells(rows)], [13])

    def test_tien_trinh_khac_khong_bi_dung_toi(self):
        rows = [_row("Code.exe", CODE, 1), _row("notepad.exe", 14, CODE)]
        self.assertEqual(TH.pick_idle_shells(rows), [])

    def test_tu_tim_code_pid(self):
        rows = [_row("Code.exe", 42, 1), _row("powershell.exe", 43, 42)]
        self.assertEqual([s["pid"] for s in TH.pick_idle_shells(rows)], [43])


class TestRunOnce(unittest.TestCase):
    def test_dry_run_khong_xoa(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE),
                _row("powershell.exe", 12, CODE)]
        rep = TH.run_once(dry_run=True, rows=rows)
        self.assertEqual((rep["found"], rep["killed"]), (2, 0))
        self.assertGreater(rep["freed_mb"], 0)

    def test_kill_false_chi_do_luong(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE)]
        rep = TH.run_once(dry_run=False, rows=rows, kill=False)
        self.assertEqual((rep["found"], rep["killed"]), (1, 0))

    def test_khong_co_shell_thi_khong_xoa_gi(self):
        rep = TH.run_once(dry_run=False, rows=[_row("Code.exe", CODE, 1)])
        self.assertEqual((rep["found"], rep["killed"], rep["freed_mb"]), (0, 0, 0.0))

    def test_bao_ve_cay_tien_trinh_dang_chay(self):
        """Shell chua chinh tien trinh test (`os.getpid()`) bi loai o lop 2 va 3."""
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE),
                _row("python.exe", os.getpid(), 11)]
        rep = TH.run_once(dry_run=True, rows=rows)
        self.assertEqual(rep["found"], 0)

    def test_bao_ve_them_bang_protect_extra(self):
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE)]
        rep = TH.run_once(dry_run=True, rows=rows, protect_extra=[11])
        self.assertEqual(rep["found"], 0)

    def test_duoi_nguong_min_thi_khong_don(self):
        """`--min-shells 5`: 2 shell rac ⇒ KHONG xoa (moi lan xoa sinh 1 thong bao VS Code)."""
        rows = [_row("Code.exe", CODE, 1), _row("powershell.exe", 11, CODE),
                _row("powershell.exe", 12, CODE)]
        rep = TH.run_once(dry_run=False, rows=rows, kill=False, min_shells=5)
        self.assertEqual(rep["found"], 2)
        self.assertTrue(rep["below_min"])
        self.assertEqual(rep["killed"], 0)

    def test_dat_nguong_thi_don(self):
        rows = [_row("Code.exe", CODE, 1)] + [_row("powershell.exe", 20 + i, CODE)
                                             for i in range(5)]
        rep = TH.run_once(dry_run=False, rows=rows, kill=False, min_shells=5)
        self.assertEqual(rep["found"], 5)
        self.assertFalse(rep["below_min"])


if __name__ == "__main__":
    unittest.main()
