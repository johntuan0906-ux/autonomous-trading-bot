"""ECONNRESET / lỗi mạng: phân loại + retry có backoff (17/11).

Bối cảnh thật (người vận hành gửi): Cline gateway trả
`Cannot connect to API: read ECONNRESET (ECONNRESET) (Request ID: Xpmdd...)` khi đang chạy
`cline-pass:deepseek-v4.1-flash-1017`. Trước bản sửa này:
  - `classify_provider_error` trả **ERR** ⇒ người vận hành tưởng lỗi cấu hình/key;
  - `_complete_with_retry` chỉ chờ **0,3s cố định** ⇒ ECONNRESET kéo dài vài giây là thất bại cả
    2 lần ⇒ `AgentBudget` TẮT provider ⇒ hội đồng "im lặng" (lớp B-051/B-052) mà không ai biết.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agents as A      # noqa: E402

MSG = ("Cannot connect to API: read ECONNRESET: read ECONNRESET (ECONNRESET) "
       "(Request ID: XpmddNJJXuDZGnEHqXzYtmcgAAjlHfbc)")


class TestPhanLoaiMang(unittest.TestCase):
    def test_econnreset_la_NETWORK(self):
        self.assertEqual(A.classify_provider_error(1, MSG), "NETWORK")

    def test_cac_bien_the_mang(self):
        for t in ("read ECONNRESET", "socket hang up", "connect ECONNREFUSED 1.2.3.4:443",
                  "write EPIPE", "getaddrinfo ENOTFOUND api.example", "network is unreachable",
                  "Cannot connect to API", "connection reset by peer"):
            self.assertEqual(A.classify_provider_error(1, t), "NETWORK", t)

    def test_khong_lam_loan_cac_ma_cu(self):
        self.assertEqual(A.classify_provider_error(0, "OK"), "OK")
        self.assertEqual(A.classify_provider_error(1, "Error: Model \"x\" is not available."),
                         "MODEL_GATED")
        self.assertEqual(A.classify_provider_error(1, "402 Payment Required"), "PAYMENT")
        self.assertEqual(A.classify_provider_error(1, "insufficient quota"), "QUOTA")
        self.assertEqual(A.classify_provider_error(1, "rate limit 429"), "RATE")
        self.assertEqual(A.classify_provider_error(1, "bi loi la"), "ERR")

    def test_transient_bao_gom_econnreset(self):
        self.assertTrue(A._is_transient_error(RuntimeError(MSG)))
        self.assertTrue(A._is_transient_error(RuntimeError("socket hang up")))


class TestBackoff(unittest.TestCase):
    def test_backoff_luy_thua_co_tran(self):
        self.assertAlmostEqual(A._backoff_sleep(1, 0.3), 0.3)
        self.assertAlmostEqual(A._backoff_sleep(2, 0.3), 0.6)
        self.assertAlmostEqual(A._backoff_sleep(3, 0.3), 1.2)
        self.assertAlmostEqual(A._backoff_sleep(10, 0.3), A._RETRY_SLEEP_CAP)   # tran 8s
        self.assertEqual(A._backoff_sleep(0, 0.3), 0.3)                          # khong am

    def test_retry_cho_lau_dan_va_thanh_cong(self):
        sleeps = []

        class P:
            n = 0

            def complete(self, system, user, timeout=None):
                P.n += 1
                if P.n < 3:
                    raise RuntimeError(MSG)
                return {"text": "OK"}

        import agents
        old_sleep = agents.time.sleep
        agents.time.sleep = lambda s: sleeps.append(s)
        try:
            res, used = A._complete_with_retry(P(), "s", "u", attempts=3, sleep_sec=0.3)
        finally:
            agents.time.sleep = old_sleep
        self.assertEqual(res["text"], "OK")
        self.assertEqual(used, 3)
        self.assertEqual(len(sleeps), 2)
        self.assertLess(sleeps[0], sleeps[1], "phai cho lau dan (backoff), khong 0,3s co dinh")

    def test_loi_vinh_vien_khong_retry(self):
        class P:
            n = 0

            def complete(self, system, user, timeout=None):
                P.n += 1
                raise RuntimeError("401 invalid api key")

        with self.assertRaises(RuntimeError):
            A._complete_with_retry(P(), "s", "u", attempts=3, sleep_sec=0.0)
        self.assertEqual(P.n, 1, "loi vinh vien phai fail NGAY (khong dot them quota)")


if __name__ == "__main__":
    unittest.main()
