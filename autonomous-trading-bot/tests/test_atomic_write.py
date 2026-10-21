# -*- coding: utf-8 -*-
"""Test `atomic.py` — ghi file trang thai NGUYEN TU (tmp -> fsync -> os.replace).

Vi sao (21/10, ra soat repo `ghgrab`): ben do kiem tra thu muc cha/quyen ghi TRUOC khi
luu cau hinh. Doi chieu thi du an con 5 cho ghi TRUC TIEP file trang thai quan trong
(`entries_pause.json`, `.env`, `state.json`, `deadman.json`, artifact quyet dinh) ⇒ mat
dien giua luc ghi la file bi cat ngang. Test nay chot 3 tinh chat:

1. Ghi xong la doc duoc ngay (khong con file nua voi);
2. Loi giua chung ⇒ **file cu GIU NGUYEN** + khong de lai file tam;
3. Bi khoa tam thoi (Windows: AV/indexer) ⇒ RETRY roi moi bao loi.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import atomic               # noqa: E402


def _tmps(d: Path) -> list:
    """Cac file tam con lai trong thu muc (dau '.' + '.tmp')."""
    return [p for p in Path(d).iterdir() if p.name.endswith(".tmp")]


class TestWriteTextAtomic(unittest.TestCase):
    def test_tao_file_moi_va_thu_muc_cha(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "logs" / "sub" / "x.json"
            out = atomic.write_text_atomic(p, '{"a": 1}')
            self.assertEqual(out, p)
            self.assertEqual(p.read_text(encoding="utf-8"), '{"a": 1}')
            self.assertEqual(_tmps(p.parent), [], "khong duoc de lai file tam")

    def test_thay_the_toan_bo_noi_dung_cu(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.txt"
            p.write_text("noi dung cu rat dai " * 50, encoding="utf-8")
            atomic.write_text_atomic(p, "moi")
            self.assertEqual(p.read_text(encoding="utf-8"), "moi",
                             "phai ghi de hoan toan, khong con vet file cu")

    def test_file_tam_nam_cung_thu_muc(self):
        """Khac volume ⇒ `os.replace` khong nguyen tu; phai ghi tmp ngay canh dich."""
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.json"
            seen = {}
            real = atomic.os.replace

            def spy(src, dst):
                seen["src"] = Path(src)
                seen["dst"] = Path(dst)
                return real(src, dst)

            with mock.patch.object(atomic.os, "replace", side_effect=spy):
                atomic.write_text_atomic(p, "{}")
            self.assertEqual(seen["src"].parent, p.parent)
            self.assertEqual(seen["dst"], p)

    def test_loi_khi_replace_thi_giu_nguyen_file_cu(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.json"
            atomic.write_text_atomic(p, '{"cu": true}')
            with mock.patch.object(atomic.os, "replace", side_effect=OSError("bi khoa")):
                with self.assertRaises(OSError):
                    atomic.write_text_atomic(p, '{"moi": true}')
            self.assertEqual(p.read_text(encoding="utf-8"), '{"cu": true}',
                             "file cu PHAI con nguyen (khong bao gio de file nua voi)")
            self.assertEqual(_tmps(p.parent), [], "file tam phai duoc don")

    def test_retry_khi_bi_khoa_tam_thoi(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.txt"
            real = atomic.os.replace
            calls = {"n": 0}

            def flaky(src, dst):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise PermissionError("AV dang mo file")
                return real(src, dst)

            with mock.patch.object(atomic.os, "replace", side_effect=flaky):
                atomic.write_text_atomic(p, "ok", delay=0.0)
            self.assertEqual(calls["n"], 2, "phai thu lai sau PermissionError")
            self.assertEqual(p.read_text(encoding="utf-8"), "ok")

    def test_het_luot_retry_thi_nem_loi_cuoi(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.txt"
            with mock.patch.object(atomic.os, "replace",
                                   side_effect=PermissionError("khong nhuong")):
                with self.assertRaises(PermissionError):
                    atomic.write_text_atomic(p, "x", retries=3, delay=0.0)
            self.assertFalse(p.exists(), "chua ghi duoc thi khong duoc tao file rong")

    def test_unicode_tieng_viet_khong_bi_escape(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.txt"
            atomic.write_text_atomic(p, "Tạm dừng vào lệnh — 21/10")
            self.assertIn("Tạm dừng", p.read_text(encoding="utf-8"))


class TestWriteJsonAtomic(unittest.TestCase):
    def test_roundtrip_giu_chu_viet_va_indent(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.json"
            atomic.write_json_atomic(p, {"ly_do": "chờ vị thế đóng", "n": 3})
            raw = p.read_text(encoding="utf-8")
            self.assertIn("chờ vị thế đóng", raw, "khong duoc escape \\uXXXX")
            self.assertIn("\n", raw, "indent=1 => nhieu dong, de doc bang mat thuong")
            self.assertEqual(json.loads(raw), {"ly_do": "chờ vị thế đóng", "n": 3})

    def test_indent_none_thanh_mot_dong(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "s.json"
            atomic.write_json_atomic(p, {"a": [1, 2]}, indent=None)
            self.assertEqual(p.read_text(encoding="utf-8").strip(), '{"a": [1, 2]}')


class TestReplaceRetry(unittest.TestCase):
    def test_tmp_khong_ton_tai_thi_nem_FileNotFoundError_ngay(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileNotFoundError):
                atomic.replace_retry(Path(t) / "khong-co.tmp", Path(t) / "x", retries=3,
                                     delay=0.0)


if __name__ == "__main__":
    unittest.main()
