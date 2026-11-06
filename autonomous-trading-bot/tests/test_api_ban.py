# -*- coding: utf-8 -*-
"""Test guard SÀN CHẶN IP (`-1003` / `418 I'm a teapot`) — lớp lỗi B-044 (06/11).

Vì sao có: LIVE bị Binance chặn IP **367 dòng "I'm a teapot"** từ 16:33 đến 23:20 vì
bot vẫn quét 40 cặp mỗi vòng ⇒ mỗi request làm bịn dài thêm (Binance: 2 phút → 3 ngày).
Guard: đọc mốc `banned until ...` ⇒ **bỏ qua vòng quét** (không gửi request) tới mốc đó.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import turbo_demo as TD          # noqa: E402

MSG_MS = ('DATA_FAIL binance 418 I\'m a teapot {"code":-1003,"msg":"Way too many '
          'requests; IP(222.253.53.82) banned until 1793987694544. Please use '
          'the websocket for live updates."}')


class TestParseBanUntil(unittest.TestCase):
    def test_doc_moc_mili_giay(self):
        """Chuỗi trong thực tế là **mili giây** (13 chữ số) ⇒ phải chia 1000."""
        self.assertAlmostEqual(TD.parse_ban_until(MSG_MS), 1793987694.544, places=3)

    def test_doc_moc_giay(self):
        self.assertEqual(TD.parse_ban_until("banned until 1793987694"), 1793987694.0)

    def test_khong_co_moc_thi_0(self):
        self.assertEqual(TD.parse_ban_until("DATA_FAIL timeout"), 0.0)
        self.assertEqual(TD.parse_ban_until(None), 0.0)
        self.assertEqual(TD.parse_ban_until(""), 0.0)


class TestApiBanFile(unittest.TestCase):
    def test_ghi_va_doc(self):
        p = os.path.join(tempfile.mkdtemp(), "api_ban.json")
        self.assertTrue(TD.set_api_ban(1793987694.0, reason="-1003", path=p))
        self.assertEqual(TD.api_ban_until(p), 1793987694.0)
        d = json.load(open(p, encoding="utf-8"))
        self.assertIn("readable", d)
        self.assertIn("-1003", d.get("reason", ""))

    def test_khong_ghi_lui(self):
        """Mốc mới SỚM hơn mốc cũ ⇒ KHÔNG ghi (tránh mở khoá sớm)."""
        p = os.path.join(tempfile.mkdtemp(), "api_ban.json")
        TD.set_api_ban(2000.0, path=p)
        self.assertFalse(TD.set_api_ban(1000.0, path=p))
        self.assertEqual(TD.api_ban_until(p), 2000.0)

    def test_moc_0_thi_khong_ghi(self):
        p = os.path.join(tempfile.mkdtemp(), "api_ban.json")
        self.assertFalse(TD.set_api_ban(0, path=p))
        self.assertEqual(TD.api_ban_until(p), 0.0)

    def test_file_hong_thi_coi_nhu_KHONG_chan(self):
        """Fail-open ở đây là ĐÚNG: file hỏng không được làm bot ngừng trade mãi mãi."""
        p = os.path.join(tempfile.mkdtemp(), "api_ban.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write("{hong")
        self.assertEqual(TD.api_ban_until(p), 0.0)


if __name__ == "__main__":
    unittest.main()
