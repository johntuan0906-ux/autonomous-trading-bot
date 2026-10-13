"""Test `tools/harness_audit.py` — cham diem setup (tat dinh, offline).

Vi sao co: 13/10 phai chay 3 lenh thu cong moi phat hien LIVE co 3 vi the tran
khong SL/TP. Cong cu nay gom viec do thanh 1 lenh co diem so + cach sua.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import harness_audit as HA      # noqa: E402


class TestReadEnv(unittest.TestCase):
    def test_doc_va_bo_comment(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text('# c\nBINANCE_TESTNET=false\nLEVERAGE="8"\n\n',
                         encoding="utf-8")
            env = HA.read_env(p)
        self.assertEqual(env["BINANCE_TESTNET"], "false")
        self.assertEqual(env["LEVERAGE"], "8", "phai bo dau ngoac kep")
        self.assertEqual(len(env), 2)

    def test_file_khong_ton_tai(self):
        self.assertEqual(HA.read_env(Path("khong/co/.env")), {})


class TestFlag(unittest.TestCase):
    def test_nhan_dang_bool(self):
        for v in ("true", "True", "1", "yes", "YES"):
            self.assertTrue(HA.flag({"X": v}, "X"), v)
        for v in ("false", "0", "no", ""):
            self.assertFalse(HA.flag({"X": v}, "X"), v)

    def test_thieu_key_thi_dung_mac_dinh(self):
        self.assertTrue(HA.flag({}, "X", True))
        self.assertFalse(HA.flag({}, "X"))


class TestJournalBalance(unittest.TestCase):
    def test_dem_open_close(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "journal.jsonl"
            p.write_text('{"event": "OPEN", "pair": "A"}\n'
                         '{"event": "CLOSE", "pair": "A"}\n'
                         '{"event": "AGENT", "role": "review"}\n', encoding="utf-8")
            b = HA.journal_balance(p)
        self.assertEqual((b["open"], b["close"]), (1, 1))
        self.assertEqual(b["orphan"], 0)

    def test_open_nhieu_hon_close(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "journal.jsonl"
            p.write_text('{"event":"OPEN"}\n' * 4 + '{"event":"CLOSE"}\n', encoding="utf-8")
            b = HA.journal_balance(p)
        self.assertEqual(b["orphan"], 3)

    def test_file_khong_ton_tai(self):
        self.assertEqual(HA.journal_balance(Path("khong/co.jsonl"))["open"], 0)


class TestDiemSo(unittest.TestCase):
    def test_sach_thi_100(self):
        checks: list = []
        HA.add(checks, "OK", "a", "on")
        HA.add(checks, "OK", "b", "on")
        self.assertEqual(HA.score(checks), 100)
        self.assertEqual(HA.summarize(checks)["verdict"], "sach")

    def test_tru_diem_va_khong_am(self):
        c: list = []
        HA.add(c, "WARN", "a", "x")
        self.assertEqual(HA.score(c), 96)
        c2: list = []
        for i in range(12):
            HA.add(c2, "FAIL", "f%d" % i, "x")
        self.assertEqual(HA.score(c2), 0, "diem khong duoc am")

    def test_ket_luan_theo_muc_nang_nhat(self):
        c: list = []
        HA.add(c, "WARN", "a", "x")
        s = HA.summarize(c)
        self.assertEqual(s["warn"], 1)
        self.assertIn("WARN", s["verdict"])
        HA.add(c, "FAIL", "b", "y")
        s2 = HA.summarize(c)
        self.assertEqual(s2["ok"], 1)
        self.assertIn("CAN SUA NGAY", s2["verdict"])

    def test_add_giu_cach_sua(self):
        c: list = []
        HA.add(c, "FAIL", "x", "chi tiet", "chay lenh Y")
        self.assertEqual(c[0]["fix"], "chay lenh Y")


class TestCodeParity(unittest.TestCase):
    def test_phat_hien_khac_nhau(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            (Path(d1) / "a.py").write_text("x = 1\n", encoding="utf-8")
            (Path(d2) / "a.py").write_text("x = 2\n", encoding="utf-8")
            par = HA.code_parity(Path(d1), Path(d2), ("a.py",))
        self.assertFalse(par["a.py"][2], "noi dung khac -> khop=False")

    def test_giong_nhau(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            for d in (d1, d2):
                (Path(d) / "a.py").write_text("x = 1\n", encoding="utf-8")
            par = HA.code_parity(Path(d1), Path(d2), ("a.py",))
        self.assertTrue(par["a.py"][2])

    def test_thieu_file_thi_danh_dau(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            h = HA.hash_py(Path(d1), ("khong-co.py",))
        self.assertEqual(h["khong-co.py"], "-")


class TestDemTest(unittest.TestCase):
    def test_dem_ham_test(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "test_a.py").write_text(
                "def test_1():\n    pass\ndef test_2():\n    pass\n", encoding="utf-8")
            (Path(d) / "khong_phai_test.py").write_text(
                "def test_x():\n    pass\n", encoding="utf-8")
            files, n = HA.count_test_funcs(Path(d))
        self.assertEqual(files, 1, "chi dem file test_*.py")
        self.assertEqual(n, 2)

    def test_thu_muc_khong_ton_tai(self):
        self.assertEqual(HA.count_test_funcs(Path("khong/co/")), (0, 0))


if __name__ == "__main__":
    unittest.main()
