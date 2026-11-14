"""`notify.redact` + `telegram_bridge.redact` — khong de token vao log (F-04 / B-054)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tools"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import notify as NT              # noqa: E402
import telegram_bridge as TB     # noqa: E402

TOKEN = "8123456789:AAF-abc_DEF123ghi-jkl"


class TestBoTokenTrongLog(unittest.TestCase):
    def test_xoa_token_khoi_url_bot_api(self):
        msg = ("HTTPSConnectionPool(host='api.telegram.org'): Max retries exceeded with url: "
               "/bot%s/sendMessage" % TOKEN)
        out = NT.redact(msg, TOKEN)
        self.assertNotIn(TOKEN, out)
        self.assertNotIn("AAF-abc_DEF123ghi-jkl", out)
        self.assertIn("/bot<token>", out)

    def test_xoa_du_token_khong_truyen_vao(self):
        """Khong truyen token van phai xoa (dang `/bot<so>:<chuoi>`)."""
        out = NT.redact("loi: /bot%s/sendMessage" % TOKEN)
        self.assertNotIn(TOKEN, out)
        self.assertIn("<token>", out)

    def test_telegram_bridge_cung_xoa(self):
        out = TB.redact("Max retries: url: /bot%s/getUpdates" % TOKEN)
        self.assertNotIn(TOKEN, out)
        self.assertIn("/bot<token>", out)

    def test_send_loi_mang_thi_log_khong_co_token(self):
        class Boom:
            def post(self, *a, **kw):
                raise RuntimeError("url: /bot%s/sendMessage" % TOKEN)

        old = NT.requests
        NT.requests = Boom()
        try:
            with self.assertLogs("notify", level="WARNING") as cm:
                ok = NT.send(TOKEN, "1", "xin chao")
        finally:
            NT.requests = old
        self.assertFalse(ok)
        self.assertNotIn(TOKEN, "\n".join(cm.output))
        self.assertIn("/bot<token>", "\n".join(cm.output))


if __name__ == "__main__":
    unittest.main()
