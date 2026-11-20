"""Test `scan_plan.py` — chia dot quet + do tre khoi dong (19/11, B-068).

Boi canh: 2 instance chung 1 IP, 40 cap/vong ⇒ cham tran weight 2400/phut ⇒ `-1003`, va
moi request trong luc bi chan lam **ban dai them** (11:18 -> 11:59 -> 20:30 trong 1 ngay).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import scan_plan as SP      # noqa: E402


class TestChiaDotQuet(unittest.TestCase):
    SYMS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]

    def test_batch_0_hoac_lon_hon_thi_lay_het(self):
        self.assertEqual(SP.pick_scan_batch(self.SYMS, 0, 0), self.SYMS)
        self.assertEqual(SP.pick_scan_batch(self.SYMS, 50, 3), self.SYMS)
        self.assertEqual(SP.pick_scan_batch([], 5, 0), [])

    def test_moi_vong_dung_so_luong_va_quay_vong(self):
        b = 4
        seen = []
        for r in range(len(self.SYMS) // b):
            part = SP.pick_scan_batch(self.SYMS, b, r)
            self.assertEqual(len(part), b, "dung 4 cap moi vong")
            seen.extend(part)
        self.assertEqual(sorted(seen), self.SYMS, "3 vong phu het 12 cap")

    def test_vi_the_dang_mo_luon_duoc_quet(self):
        for r in range(5):
            part = SP.pick_scan_batch(self.SYMS, 2, r, must_include=["J", "I"])
            self.assertIn("J", part, "vi the dang mo KHONG duoc bo")
            self.assertIn("I", part)
            self.assertLessEqual(len(part), 4)

    def test_khong_trung_lap_trong_1_ket_qua(self):
        part = SP.pick_scan_batch(self.SYMS, 6, 0, must_include=["B"])
        self.assertEqual(len(part), len(set(part)))

    def test_must_include_khong_co_trong_danh_sach_thi_bo_qua(self):
        self.assertEqual(SP.pick_scan_batch(["A", "B"], 1, 0, must_include=["Z"]),
                         ["A"])

    def test_batch_rac_thi_lay_het(self):
        self.assertEqual(SP.pick_scan_batch(self.SYMS, None, 0), self.SYMS)


class TestDoTreKhoiDong(unittest.TestCase):
    def test_vong_dau_va_ngay_sau_ban(self):
        self.assertEqual(SP.warmup_seconds(120, first_round=True, just_unbanned=False), 120)
        self.assertEqual(SP.warmup_seconds(120, first_round=False, just_unbanned=True), 60)
        self.assertEqual(SP.warmup_seconds(120, first_round=False, just_unbanned=False), 0)

    def test_cau_hinh_0_hoac_rac_thi_khong_cho(self):
        self.assertEqual(SP.warmup_seconds(0, first_round=True, just_unbanned=True), 0)
        self.assertEqual(SP.warmup_seconds("rac", first_round=True, just_unbanned=False), 0)
        self.assertEqual(SP.warmup_seconds(-5, first_round=True, just_unbanned=False), 0)


if __name__ == "__main__":
    unittest.main()
