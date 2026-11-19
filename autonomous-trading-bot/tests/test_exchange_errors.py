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


class TestGhiMocBanTuCongCu(unittest.TestCase):
    """(19/11, B-063) Công cụ chạm `-1003` phải **ghi** `api_ban.json`, không chỉ in ra.

    Đo thật: 11:18 hết ban, một request đọc (`arm_protection`) chạm `-1003` ⇒ Binance
    cộng thêm 40 phút (11:59) mà **không file nào ghi lại** ⇒ lần sau lại gọi tiếp.
    """

    def _ban_msg(self, until_ms: int) -> str:
        return ('{"code":-1003,"msg":"Way too many requests; IP(1.2.3.4) '
                'banned until %d"}' % int(until_ms))

    def test_loi_ban_thi_ghi_va_chi_tang(self):
        import json
        import time
        import tempfile
        until_ms = int((time.time() + 1800) * 1000)
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            until = EX.note_error_ban(base, self._ban_msg(until_ms))
            self.assertGreater(until, time.time())
            data = json.loads((base / "logs" / "api_ban.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(data["until"], until_ms / 1000.0, places=3)
            # moc CU hon khong duoc ghi de
            self.assertAlmostEqual(EX.save_api_ban(base, until - 600), until, places=3)

    def test_loi_thuong_khong_tao_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            self.assertEqual(EX.note_error_ban(base, "Timeout 30s"), 0.0)
            self.assertEqual(EX.note_error_ban(base, ""), 0.0)
            self.assertFalse((base / "logs" / "api_ban.json").exists())


class TestDoiCheDoTaiKhoan(unittest.TestCase):
    """(19/11, B-064) Chế độ tài khoản đổi (hedge -> one-way) ⇒ cache cũ làm **mọi** lệnh
    `-4061` (22 lần/vòng, 2 vị thế LIVE không có SL/TP). Phải: cache có TTL + `-4061`
    xoá cache và thử lại 1 lần.
    """

    class Fake:
        def __init__(self, dual=False, fail_first=1):
            self.dual = dual
            self.fail_left = fail_first
            self.calls = []
            self.mode_calls = 0

        def fapiPrivateGetPositionSideDual(self):
            self.mode_calls += 1
            return {"dualSidePosition": self.dual}

        def create_market_order(self, symbol, side, qty, params=None):
            self.calls.append(dict(params or {}))
            if self.fail_left > 0:
                self.fail_left -= 1
                raise Exception('binance {"code":-4061,"msg":"Order\'s position side does '
                                'not match user\'s setting."}')
            return {"id": "ok", "symbol": symbol, "side": side, "qty": qty}

        def create_order(self, symbol, otype, side, qty, params=None):
            self.calls.append(dict(params or {}))
            if self.fail_left > 0:
                self.fail_left -= 1
                raise Exception('binance {"code":-4061,"msg":"Order\'s position side does '
                                'not match user\'s setting."}')
            return {"id": otype}

        def cancel_open_orders(self, *a, **k):
            return []

    def _ex(self, fake, stale_hedge=True):
        import time
        import exchange as EX
        ex = EX.BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=False)
        ex._client = fake
        ex._hedge = stale_hedge          # cache CU: tuong tai khoan dang HEDGE
        ex._hedge_ts = time.time()
        return ex

    def test_vao_lenh_gap_4061_thi_doi_che_do_va_thu_lai(self):
        fake = self.Fake(dual=False, fail_first=1)
        ex = self._ex(fake)
        self.assertEqual(ex.market_entry("SOL/USDT:USDT", "LONG", 1.0)["id"], "ok")
        self.assertEqual(len(fake.calls), 2, "phai thu lai dung 1 lan")
        self.assertIn("positionSide", fake.calls[0], "lan dau dung cache CU")
        self.assertNotIn("positionSide", fake.calls[1], "lan hai theo che do THAT (one-way)")
        self.assertFalse(ex.hedge_mode())

    def test_arm_sltp_gap_4061_thi_doi_che_do_va_thu_lai(self):
        fake = self.Fake(dual=False, fail_first=1)
        ex = self._ex(fake)
        out = ex.stop_tp_orders("SOL/USDT:USDT", "SHORT", 1.0, 110.0, 90.0,
                                cancel_first=False)
        self.assertIn("sl_order", out)
        self.assertIn("tp_order", out)
        self.assertNotIn("positionSide", fake.calls[-1])

    def test_cache_co_ttl(self):
        import time
        import exchange as EX
        fake = self.Fake(dual=True, fail_first=0)
        ex = EX.BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=False)
        ex._client = fake
        self.assertTrue(ex.hedge_mode(ttl=300.0))
        self.assertEqual(fake.mode_calls, 1)
        ex.hedge_mode(ttl=300.0)
        self.assertEqual(fake.mode_calls, 1, "con han cache: khong hoi lai")
        ex._hedge_ts = time.time() - 400.0         # cache het han
        ex.hedge_mode(ttl=300.0)
        self.assertEqual(fake.mode_calls, 2, "het TTL: phai hoi lai che do")


class TestTaiTrongIp(unittest.TestCase):

    """(19/11, B-062) Ban IP het han ma quet tiep 40 cap ⇒ cham `-1003` NGAY va bi
    **cong them 40 phut** (do that: 11:18 -> 11:59). Phai doc header weight de tu nghi
    TRUOC khi bi chan.
    """

    def test_doc_header_weight(self):
        self.assertEqual(EX.weight_used({"X-MBX-USED-WEIGHT-1M": "1830"}), 1830)
        self.assertEqual(EX.weight_used({"x-mbx-used-weight-1m": "12.0"}), 12)
        self.assertEqual(EX.weight_used({}), 0)
        self.assertEqual(EX.weight_used(None), 0)
        self.assertEqual(EX.weight_used({"X-MBX-USED-WEIGHT-1M": "rac"}), 0)

    def test_nguong_nghi_75_phan_tram(self):
        self.assertEqual(EX.throttle_seconds(1000, 2400, 0.75), 0.0,
                         "duoi nguong: chay tiep")
        self.assertEqual(EX.throttle_seconds(1800, 2400, 0.75, now=120.0), 0.0,
                         "dau phut: tran sap reset, khong can nghi")
        self.assertGreaterEqual(EX.throttle_seconds(1800, 2400, 0.75, now=100.0), 19.0)
        self.assertLessEqual(EX.throttle_seconds(2400, 2400, 0.75, now=100.0), 60.0)

    def test_thieu_du_lieu_thi_khong_lam_gi(self):
        self.assertEqual(EX.throttle_seconds(0, 2400, 0.75), 0.0)
        self.assertEqual(EX.throttle_seconds(9999, 0, 0.75), 0.0, "limit=0 ⇒ tat")



if __name__ == "__main__":
    unittest.main()
