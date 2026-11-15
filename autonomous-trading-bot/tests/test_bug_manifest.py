"""Manifest (witness) cua bug catalog — RESEARCH §1 muc 8.

Vi sao: `--check` chi biet "test duoc dan co that hay khong"; neu ai do XOA mot test khoi danh muc
(hoac doi ten) thi `--check` van xanh. Manifest hash DANH SACH test chot ⇒ xoa/doi ten la bao loi.
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

import bug_catalog as BC      # noqa: E402


def _cat():
    return [{"code": "B-901", "kind": "im-lang", "title": "x", "symptom": "y",
             "guard": "z", "files": [], "tests": ["test_a.py::T::test_1",
                                                  "test_b.py::T::test_2"]},
            {"code": "B-902", "kind": "rui-ro", "title": "x", "symptom": "y",
             "guard": "z", "files": [], "tests": ["test_a.py::T::test_3"]}]


class TestManifest(unittest.TestCase):
    def test_hash_on_dinh_va_dem_dung(self):
        a = BC.manifest(_cat())
        b = BC.manifest(_cat())
        self.assertEqual(a["digest"], b["digest"])
        self.assertEqual(a["n_classes"], 2)
        self.assertEqual(a["n_tests"], 3)
        self.assertEqual(a["files"], ["test_a.py", "test_b.py"])

    def test_them_hoac_bot_test_thi_digest_doi(self):
        base = BC.manifest(_cat())["digest"]
        more = _cat()
        more[0]["tests"].append("test_c.py::T::test_9")
        self.assertNotEqual(BC.manifest(more)["digest"], base)
        less = _cat()
        less[1]["tests"] = []
        self.assertNotEqual(BC.manifest(less)["digest"], base)

    def test_ghi_roi_kiem_thi_OK(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            m = BC.write_manifest(p, _cat())
            self.assertTrue(m["ok"])
            self.assertTrue(p.is_file())
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["digest"],
                             m["digest"])
            self.assertTrue(BC.check_manifest(p, _cat())["ok"])

    def test_xoa_test_bi_bat(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            BC.write_manifest(p, _cat())
            less = _cat()
            less[0]["tests"].remove("test_b.py::T::test_2")
            rep = BC.check_manifest(p, less)
            self.assertFalse(rep["ok"])
            self.assertIn("DA DOI", rep["reason"])

    def test_chua_co_manifest_thi_bao_ro(self):
        with tempfile.TemporaryDirectory() as td:
            rep = BC.check_manifest(Path(td) / "khong-co.json", _cat())
            self.assertFalse(rep["ok"])
            self.assertIn("--manifest", rep["reason"])

    def test_manifest_hong_khong_no(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.json"
            p.write_text("{hong", encoding="utf-8")
            rep = BC.check_manifest(p, _cat())
            self.assertFalse(rep["ok"])
            self.assertIn("hong", rep["reason"])

    def test_repo_that_PHAI_co_manifest_khop(self):
        """Chot: repo phai co `golden/bug_manifest.json` va khớp danh mục hiện tại."""
        rep = BC.check_manifest()
        self.assertTrue(rep["ok"], rep.get("reason"))


if __name__ == "__main__":
    unittest.main()
