"""`exchange.classify_error` — MOT bang phan loai cho moi loi san (B-056).

Vi sao phai chot: truoc day 3 noi tu regex 3 kieu (`is_reduce_only_rejected` tim -2022,
`parse_ban_until` tim 'banned until', turbo_demo tim '-1003') nen cung 1 loi duoc hieu khac nhau.
Test khoa bang: ma loi -> (code, retryable, ban_until), va 2 ham cu phai di qua bang nay.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import exchange as EX      # noqa: E402

MSG_BAN_MS = ('{"code":-1003,"msg":"Way too many requests; IP(222.253.53.82) '
              'banned until 1793987694544"}')


class TestPhanLoaiLoi(unittest.TestCase):
    def test_api_ban_doc_moc_ms(self):
        d = EX.classify_error(MSG_BAN_MS)
        self.assertEqual(d["code"], "API_BAN")
        self.assertAlmostEqual(d["ban_until"], 1793987694.544, places=3)
        self.assertEqual(d["binance"], -1003)
        self.assertFalse(d["retryable"], "bi chan IP thi khong thu lai ngay")

    def test_api_ban_418_khong_moc_thi_nghi_15_phut(self):
        d = EX.classify_error("418 I'm a teapot")
        self.assertEqual(d["code"], "API_BAN")
        self.assertGreater(d["ban_until"], 0)

    def test_loi_thuong_khong_bi_coi_la_bi_chan(self):
        d = EX.classify_error('{"code":-2019,"msg":"Margin is insufficient."}')
        self.assertEqual(d["code"], "INSUFFICIENT_MARGIN")
        self.assertEqual(d["ban_until"], 0.0)
        self.assertFalse(d["retryable"])

    def test_reduce_only(self):
        self.assertEqual(EX.classify_error("binance -2022 ReduceOnly Order is rejected")["code"],
                         "REDUCE_ONLY")
        self.assertTrue(EX.is_reduce_only_rejected("-2022 ReduceOnly Order is rejected"))
        self.assertFalse(EX.is_reduce_only_rejected("-2019 Margin is insufficient"))

    def test_notional_va_stop_orders(self):
        self.assertEqual(EX.classify_error("binance -4164 Order's notional must be no smaller "
                                           "than 5")["code"], "MIN_NOTIONAL")
        self.assertEqual(EX.classify_error("binance -4045 Reach max stop order limit."
                                           )["code"], "PROTECTION_LIMIT")

    def test_auth_va_timestamp(self):
        self.assertEqual(EX.classify_error("Invalid API-key, IP, or permissions for action"
                                           )["code"], "AUTH")
        d = EX.classify_error("Timestamp for this request is outside of the recvWindow")
        self.assertEqual(d["code"], "TIMESTAMP")
        self.assertTrue(d["retryable"])

    def test_mang_thi_retryable(self):
        d = EX.classify_error("HTTPSConnectionPool: Max retries exceeded (timeout)")
        self.assertEqual(d["code"], "NETWORK")
        self.assertTrue(d["retryable"])

    def test_la_hoac_rong_khong_no(self):
        for bad in (None, "", "unknown provider hiccup"):
            d = EX.classify_error(bad)
            self.assertEqual(d["code"], "ORDER_REJECT")
            self.assertEqual(d["ban_until"], 0.0)

    def test_parse_ban_until_di_qua_bang_phan_loai(self):
        """turbo_demo.parse_ban_until phai la VO cua classify_error (1 nguon duy nhat)."""
        import turbo_demo as TD
        self.assertAlmostEqual(TD.parse_ban_until(MSG_BAN_MS), 1793987694.544, places=3)
        self.assertEqual(TD.parse_ban_until("DATA_FAIL timeout"), 0.0)
        self.assertEqual(TD.parse_ban_until(None), 0.0)


if __name__ == "__main__":
    unittest.main()
