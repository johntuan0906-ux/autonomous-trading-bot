"""Test `risk.KillSwitch.note_equity` — mốc DD theo CHẾ ĐỘ (demo vs live).

Lỗi thật 09/10 16:45: kill-switch trip OAN `daily loss 99.49%` vì state còn mốc
`start_equity=4355` (số dư DEMO) trong khi bot vừa sang LIVE (equity 22).
"""
from __future__ import annotations

import unittest

from risk import KillSwitch, utc_day


class TestNoteEquityMode(unittest.TestCase):
    def test_doi_che_do_thi_moc_lai_dd(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(4355.0, mode="demo")          # moc demo
        self.assertAlmostEqual(ks.start_equity, 4355.0)
        self.assertFalse(ks.check(4355.0))           # khong trip
        # doi sang LIVE voi equity 22 -> KHONG duoc coi la lo 99%
        rolled = ks.note_equity(22.0, mode="live")
        self.assertTrue(rolled)
        self.assertAlmostEqual(ks.start_equity, 22.0)
        self.assertEqual(ks.mode, "live")
        self.assertFalse(ks.check(22.0), "khong duoc trip khi vua doi che do")

    def test_cung_che_do_thi_giu_moc(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(100.0, mode="live")
        ks.note_equity(95.0, mode="live")
        self.assertAlmostEqual(ks.start_equity, 100.0)     # giu moc cu
        self.assertFalse(ks.check(98.5))                   # -1.5% < 2% -> khong trip
        self.assertTrue(ks.check(95.0))                    # -5% >= 2% -> trip

    def test_doi_che_do_khong_tu_xoa_tripped(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(4355.0, mode="demo")
        ks.trip("daily loss 99.49% >= 2.0%")
        ks.note_equity(22.0, mode="live")            # doi che do...
        self.assertTrue(ks.tripped, "tripped PHAI xoa tay bang risk.py --reset")

    def test_khong_truyen_mode_thi_nhu_cu(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(100.0)
        self.assertAlmostEqual(ks.start_equity, 100.0)
        self.assertEqual(ks.mode, "")

    def test_lan_dau_chua_biet_che_do_van_lay_moc(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(50.0, mode="live")            # mode cu rong -> khong coi la doi
        self.assertAlmostEqual(ks.start_equity, 50.0)
        self.assertEqual(ks.mode, "live")

    def test_round_trip_json_co_mode(self):
        ks = KillSwitch(start_balance=1000.0)
        ks.note_equity(22.0, mode="live")
        ks2 = KillSwitch.from_dict(ks.to_dict())
        self.assertEqual(ks2.mode, "live")
        self.assertAlmostEqual(ks2.start_equity, 22.0)
        self.assertEqual(ks2.day, utc_day())


if __name__ == "__main__":
    unittest.main()
