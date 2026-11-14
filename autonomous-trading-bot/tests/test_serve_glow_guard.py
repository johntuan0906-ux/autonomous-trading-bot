"""`serve_glow.py` — chan file bi mat (B-054).

Do that tren ban CU: `GET http://127.0.0.1:8897/.env` => **200, 29.804 byte** = nguyen file key that
(API key Binance, token Telegram). Test nay chot 2 chieu: file thuong VAN phuc vu duoc, file bi mat
KHONG con phuc vu duoc.
"""
from __future__ import annotations

import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import serve_glow as SG      # noqa: E402


class TestChanFileBiMat(unittest.TestCase):
    def test_chan_theo_ten(self):
        for bad in (".env", ".env.bak-2026", "sub/.env", "logs/journal.jsonl",
                    "id_rsa", ".git/config", "__pycache__/x.pyc"):
            self.assertTrue(SG.denied(bad), bad)

    def test_file_thuong_van_phuc_vu_duoc(self):
        for ok in ("glow_map.html", "glow_signals.json", "tools/ops.py",
                   "memory_map_data.json"):
            self.assertFalse(SG.denied(ok), ok)

    def test_khong_chan_ten_chi_CHUA_chu_env(self):
        """"environment.md" khong phai file bi mat — khong duoc chan qua tay."""
        self.assertFalse(SG.denied("docs/environment.md"))
        self.assertFalse(SG.denied("envelope.py"))


class TestServerThat(unittest.TestCase):
    """Dung server that tren cong ngau nhien: `/.env` phai 404, file thuong phai 200."""

    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        cls._cwd = os.getcwd()
        os.chdir(str(ROOT))
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), SG.Handler)
        cls.port = cls.srv.server_address[1]
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        os.chdir(cls._cwd)

    def _status(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path),
                                        timeout=5) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_env_tra_404(self):
        self.assertEqual(self._status("/.env"), 404)

    def test_env_bak_tra_404(self):
        self.assertEqual(self._status("/.env.bak-2026"), 404)

    def test_file_thuong_tra_200(self):
        self.assertEqual(self._status("/serve_glow.py"), 200)


if __name__ == "__main__":
    unittest.main()
