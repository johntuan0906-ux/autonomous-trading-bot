"""Test `check_live_key` — chẩn đoán key LIVE theo IP (không gọi sàn thật)."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

import check_live_key as CLK


def _cfg(**kw):
    base = dict(api_key="demo", api_secret="demo", live_api_key="LK", live_api_secret="LS",
                auto_live_min_equity=10.0)
    base.update(kw)
    return SimpleNamespace(**base)


class TestIpDiag(unittest.TestCase):
    def test_gom_ket_qua_theo_tung_ip(self):
        ips = iter(["1.1.1.1", "2.2.2.2", "1.1.1.1", "2.2.2.2"])
        oks = iter([True, False, True, False])
        with mock.patch.object(CLK, "public_ip", lambda: next(ips)), \
                mock.patch.object(CLK, "equity_ok_once", lambda cfg: next(oks)), \
                mock.patch("state_sync.last_live_error", lambda: ""):
            out = CLK.ip_diag(object(), tries=4, sleep_s=0.0)
        self.assertEqual(out["by_ip"]["1.1.1.1"], (2, 2))
        self.assertEqual(out["by_ip"]["2.2.2.2"], (0, 2))
        self.assertEqual(out["rejected"], {})   # khong co IP trong message loi

    def test_ghi_lai_ip_bi_binance_tu_choi(self):
        err = 'binance {"code":-2015,"msg":"..., request ip: 9.9.9.9"}'
        with mock.patch.object(CLK, "public_ip", lambda: "1.1.1.1"), \
                mock.patch.object(CLK, "equity_ok_once", lambda cfg: False), \
                mock.patch("state_sync.last_live_error", lambda: err):
            out = CLK.ip_diag(object(), tries=3, sleep_s=0.0)
        self.assertEqual(out["rejected"], {"9.9.9.9": 3})

    def test_in_bang_chi_ra_ip_bi_chan(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            CLK.print_ip_table({"by_ip": {"1.1.1.1": (2, 2)}, "rejected": {"2.2.2.2": 2}})
        txt = buf.getvalue()
        self.assertIn("1.1.1.1", txt)
        self.assertIn("KHONG nam trong whitelist", txt)
        self.assertIn("2.2.2.2", txt)
        self.assertIn("TAT 'Restrict access to trusted IPs only'", txt)

    def test_bang_rong_thi_khong_in(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            CLK.print_ip_table({})
        self.assertEqual(buf.getvalue(), "")


class TestMain(unittest.TestCase):
    def test_thieu_key_live_thi_bao_va_exit_2(self):
        buf = io.StringIO()
        with mock.patch("config.Settings", lambda: _cfg(live_api_key="", live_api_secret="")), \
                redirect_stdout(buf):
            code = CLK.main([])
        self.assertEqual(code, 2)
        self.assertIn("CHUA dien key LIVE", buf.getvalue())

    def test_key_on_dinh_thi_exit_0(self):
        buf = io.StringIO()
        health = {"eq": 21.9, "ok_n": 5, "tries": 5, "min_ok": 4, "stable": True, "err": ""}
        with mock.patch("config.Settings", lambda: _cfg()), \
                mock.patch("state_sync.real_equity_health", lambda cfg, tries=5: health), \
                mock.patch.object(CLK, "public_ip", lambda: "1.1.1.1"), \
                redirect_stdout(buf):
            code = CLK.main([])
        txt = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("5/5 lan thanh cong", txt)
        self.assertIn("balanced", txt)

    def test_key_khong_on_dinh_thi_exit_2_va_in_bang_ip(self):
        buf = io.StringIO()
        health = {"eq": 21.9, "ok_n": 2, "tries": 5, "min_ok": 4, "stable": False,
                  "err": 'AuthenticationError: binance {"code":-2015,...}'}
        with mock.patch("config.Settings", lambda: _cfg()), \
                mock.patch("state_sync.real_equity_health", lambda cfg, tries=5: health), \
                mock.patch.object(CLK, "public_ip", lambda: "2.2.2.2"), \
                mock.patch.object(CLK, "ip_diag", lambda cfg, tries=6, sleep_s=0.6: {
                    "by_ip": {"2.2.2.2": (0, 6)}, "rejected": {"2.2.2.2": 3}}), \
                redirect_stdout(buf):
            code = CLK.main(["--retry", "5"])
        txt = buf.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("KHONG ON DINH", txt)
        self.assertIn("KHONG nam trong whitelist", txt)


if __name__ == "__main__":
    unittest.main()
