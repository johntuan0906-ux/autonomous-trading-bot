"""test_telegram_report.py — bao cao Telegram: ket luan TESTNET/LIVE + dem lan trip.

Kiem tra phan THUAN (khong goi mang):
  1) config testnet + key doc LIVE bi tu choi  -> ket luan "DEMO/TESTNET, khong phai tien that"
  2) key doc duoc LIVE                         -> canh bao NGUY HIEM
  3) kill-switch tripped + 4810 dong lap       -> noi ro 1 lan trip, de xuat --reset
  4) kill-switch sach                          -> khong de xuat reset
  5) dem_kill doc file log that                -> trips=1, blocked=2
  6) gioi han 4000 ky tu (1 message Telegram)
"""
import os
import tempfile
import time
import unittest

import telegram_report as TR


def _snap(**kw) -> dict:
    snap = {
        "now": time.time(), "testnet": True, "dry_run": False, "leverage": 8,
        "n_symbols": 8,
        "journal": {"n": 46, "wr": 60.9, "pf_r": 0.852, "e_r": -0.054,
                    "pnl": -26.48, "open_unmatched": 7, "last_close_ts": 1790824434.0},
        "managed": 0,
        "kill": {"tripped": False, "reason": "", "day": "2026-10-01"},
        "kill_hist": {"trips": 0, "blocked": 0, "first_trip": ""},
        "san": {"demo": {"api_url": "https://demo-api.binance.com/api/v3",
                         "equity": 4974.0, "orders": 0,
                         "positions": [{"symbol": "BTC/USDT:USDT", "side": "short",
                                        "qty": 0.1812, "entry": 83978.75,
                                        "mark": 83807.8, "upnl": 30.98, "lev": 8}]},
                "live": {"api_url": "https://fapi.binance.com/fapi/v1",
                         "ok": False,
                         "err": "binance {\"code\":-2015,\"msg\":\"Invalid API-key\"}"}},
    }
    snap.update(kw)
    return snap


class TestBuildReport(unittest.TestCase):
    def test_key_demo_bi_live_tu_choi_thi_ket_luan_khong_phai_tien_that(self):
        txt = TR.build_report(_snap())
        self.assertIn("DEMO/TESTNET", txt)
        self.assertIn("KHONG phai tien that", txt)
        self.assertIn("0.1812", txt)          # chi tiet vi the
        self.assertIn("BINANCE_TESTNET=True", txt)

    def test_key_doc_duoc_live_thi_canh_bao_nguy_hiem(self):
        snap = _snap(san={"demo": {"api_url": "https://demo-api.binance.com"},
                          "live": {"ok": True, "equity": 12345.0}})
        txt = TR.build_report(snap)
        self.assertIn("NGUY HIEM", txt)
        self.assertIn("tien THAT", txt)

    def test_kill_tripped_1_lan_nhung_4810_dong_lap(self):
        snap = _snap(kill={"tripped": True, "reason": "daily loss 2.13% >= 2.0%",
                           "day": "2026-09-29"},
                     kill_hist={"trips": 1, "blocked": 4810,
                                "first_trip": "2026-09-29 17:54:47 ERROR KILL-SWITCH: "
                                              "daily loss 2.13% >= 2.0% -> flatten + dung"})
        txt = TR.build_report(snap)
        self.assertIn("DANG TRIPPED", txt)
        self.assertIn("1 lan", txt)
        self.assertIn("4810", txt)
        self.assertIn("KHONG phai so lan trip", txt)
        self.assertIn("risk.py --reset", txt)
        self.assertIn("daily loss 2.13%", txt)

    def test_kill_sach_thi_khong_de_xuat_reset(self):
        txt = TR.build_report(_snap())
        self.assertIn("SACH", txt)
        self.assertNotIn("risk.py --reset", txt)

    def test_canh_bao_khi_khong_co_sl_tren_san(self):
        """Thuc te 01/10: demo tra -4045 -> khong arm duoc SL/TP; bao cao phai noi ro
        vi the dang duoc bao ve bang MONITOR phan mem (khong duoc im lang)."""
        txt = TR.build_report(_snap())
        self.assertIn("KHONG co SL/TP tren san", txt)
        self.assertIn("arm_protection.py", txt)

    def test_khong_canh_bao_khi_co_lenh_treo(self):
        snap = _snap()
        snap["san"]["demo"]["orders"] = 12
        self.assertNotIn("KHONG co SL/TP tren san", TR.build_report(snap))

    def test_gioi_han_1_message_telegram(self):
        big = _snap()
        big["san"]["demo"]["positions"] = [
            {"symbol": "X/USDT:USDT", "side": "long", "qty": 1.0, "entry": 1.0,
             "mark": 1.0, "upnl": 0.0, "lev": 8} for _ in range(400)]
        self.assertLessEqual(len(TR.build_report(big)), TR.MAX_LEN)


class TestApiUrl(unittest.TestCase):
    def test_url_long_nhau_ccxt_van_lay_duoc(self):
        class C:
            urls = {"api": {"private": "https://demo-fapi.binance.com/fapi/v1"}}
        self.assertEqual(TR._api_url(C), "https://demo-fapi.binance.com/fapi/v1")

    def test_url_phang_va_khong_co(self):
        class F:
            urls = {"fapiPrivate": "https://fapi.binance.com/fapi/v1"}

        class N:
            urls = {}
        self.assertEqual(TR._api_url(F), "https://fapi.binance.com/fapi/v1")
        self.assertEqual(TR._api_url(N), "?")


class TestDemKill(unittest.TestCase):
    def test_dem_dung_trip_that_va_dong_lap(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "log.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("2026-09-29 17:54:47,846 ERROR KILL-SWITCH: daily loss 2.13% "
                    ">= 2.0% -> flatten + dung\n")
            f.write("2026-09-29 17:55:09,776 ERROR KILL-SWITCH dang NGUNG: daily loss "
                    "2.13% >= 2.0% | khong trade\n")
            f.write("2026-09-29 18:00:09,776 ERROR KILL-SWITCH dang NGUNG: daily loss "
                    "2.13% >= 2.0% | khong trade\n")
        r = TR.dem_kill(p)
        self.assertEqual(r["trips"], 1)
        self.assertEqual(r["blocked"], 2)
        self.assertIn("17:54:47", r["first_trip"])

    def test_file_khong_ton_tai_thi_tra_zero(self):
        r = TR.dem_kill(os.path.join(tempfile.mkdtemp(), "nope.log"))
        self.assertEqual((r["trips"], r["blocked"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
