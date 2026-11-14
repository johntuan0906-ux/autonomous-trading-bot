"""`tools/security_audit.py` — may kiem lai bao cao bao mat (6 pha Cloudflare).

Chot 2 chieu: (a) bao cao that trong repo phai SACH; (b) khi bang chung bi lech thi tool PHAI bao loi —
neu khong thi "kiem tra doc lap" chi la van xuoi.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import security_audit as SA       # noqa: E402


def _repo() -> dict:
    return SA.load()


class TestBaoCaoThat(unittest.TestCase):
    def test_bao_cao_trong_repo_khop_code(self):
        rep = SA.verify(_repo())
        self.assertEqual(rep["errors"], [], rep["errors"])
        self.assertTrue(rep["ok"])
        self.assertGreaterEqual(rep["findings"], 1)

    def test_moi_phat_hien_da_sua_deu_co_test_chot(self):
        for it in _repo()["findings"]:
            if it["status"] == "fixed":
                self.assertTrue(it.get("tests"), it["id"])
                self.assertTrue(it.get("bug"), it["id"])

    def test_muc_do_va_trang_thai_dung_luat(self):
        for it in _repo()["findings"]:
            self.assertIn(it["severity"], SA.SEVERITY, it["id"])
            self.assertIn(it["status"], SA.STATUS, it["id"])


class TestBatDuocLech(unittest.TestCase):
    """Sua JSON (khong sua code) => phai bao LECH."""

    def _verify(self, data):
        return SA.verify(data)

    def test_dong_code_sai_thi_bao_lech(self):
        d = _repo()
        d["findings"][0]["evidence"] = [{"file": "serve_glow.py", "line": 1,
                                         "pattern": "def denied(rel) -> bool:"}]
        rep = self._verify(d)
        self.assertFalse(rep["ok"])
        self.assertTrue(any("serve_glow.py" in e for e in rep["errors"]), rep["errors"])

    def test_mau_phai_bien_mat_ma_con_thi_bao(self):
        d = _repo()
        d["findings"][1]["evidence"] = [{"file": "tools/telegram_bridge.py",
                                         "absent": "import argparse"}]
        rep = self._verify(d)
        self.assertTrue(any("PHAI BIEN MAT" in e for e in rep["errors"]), rep["errors"])

    def test_mau_bat_buoc_thieu_thi_bao(self):
        d = _repo()
        d["findings"][0]["evidence"] = [{"file": ".gitignore",
                                         "present": "khong-bao-gio-co-chuoi-nay"}]
        rep = self._verify(d)
        self.assertTrue(any("thieu mau bat buoc" in e for e in rep["errors"]), rep["errors"])

    def test_test_khong_ton_tai_thi_bao(self):
        d = _repo()
        d["findings"][0]["tests"] = ["test_serve_glow_guard.py::TestThat::test_khong_co"]
        rep = self._verify(d)
        self.assertTrue(any("test_serve_glow_guard.py" in e for e in rep["errors"]),
                        rep["errors"])

    def test_da_sua_ma_khong_co_test_thi_bao(self):
        d = _repo()
        d["findings"][0]["tests"] = []
        rep = self._verify(d)
        self.assertTrue(any("PHAI co test chot" in e for e in rep["errors"]), rep["errors"])

    def test_thieu_truong_thi_bao(self):
        d = _repo()
        del d["findings"][0]["exploit"]
        rep = self._verify(d)
        self.assertTrue(any("thieu truong" in e for e in rep["errors"]), rep["errors"])

    def test_bao_cao_md_lech_so_dong_thi_bao(self):
        d = _repo()
        d["findings"].append(dict(d["findings"][0], id="F-99"))
        rep = self._verify(d)
        self.assertTrue(any("SECURITY_AUDIT.md" in e for e in rep["errors"]), rep["errors"])


class TestQuetSink(unittest.TestCase):
    def test_ast_bat_duoc_shell_true_va_eval(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "x.py").write_text(
                "import subprocess\n"
                "subprocess.run(['ls'], shell=True)\n"
                "eval('1+1')\n"
                "# shell=True trong chu thich thi KHONG tinh\n", encoding="utf-8")
            hits = SA.ast_hits(d, ("*.py",))
        self.assertEqual(sorted(h[2] for h in hits), ["eval", "shell=True"])

    def test_code_that_khong_co_sink(self):
        hits = SA.ast_hits(ROOT, ("*.py", "tools/*.py"))
        self.assertEqual(hits, [], "co sink trong code san xuat: %r" % (hits,))


class TestJsonHopLe(unittest.TestCase):
    def test_json_doc_duoc_va_co_du_2_mang(self):
        d = SA.load()
        self.assertTrue(isinstance(d.get("findings"), list) and d["findings"])
        self.assertTrue(isinstance(d.get("controls"), list) and d["controls"])
        json.dumps(d)          # khong nem loi


if __name__ == "__main__":
    unittest.main()
