# -*- coding: utf-8 -*-
"""Test `tools/harness_ledger.py` — sổ thay đổi harness có BẰNG CHỨNG + quyết định.

Vì sao (21/10, đọc `google-research/harness2`): "harnessing" = tối ưu hệ quanh model
(prompt/tool/memory/skill/orchestration). Muốn tối ưu mà không mất dấu thì mỗi thay đổi
phải trả lời được: **đổi gì, vì sao (bằng chứng nào), kết quả đo được, còn giữ hay đã lui**.
`--check` phải bắt được: adopted/rejected mà không có bằng chứng; đề xuất treo quá 7 ngày.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness_ledger as HL      # noqa: E402


class TestAdd(unittest.TestCase):
    def test_them_va_doc_lai(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "ledger.jsonl"
            r = HL.add("prompt", "them vai phan bien", "B-023", decision="adopted",
                       path=p, now=1_000.0)
            self.assertTrue(r["ok"])
            rows = HL.read_all(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["kind"], "prompt")
            self.assertEqual(rows[0]["decision"], "adopted")
            self.assertEqual(rows[0]["evidence"], "B-023")
            self.assertTrue(rows[0]["id"].startswith("H-"))

    def test_id_tang_dan_trong_ngay(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            a = HL.add("gate", "x", path=p, now=1_000.0)["record"]["id"]
            b = HL.add("gate", "y", path=p, now=1_001.0)["record"]["id"]
            self.assertNotEqual(a, b)
            self.assertEqual(b, a[:-3] + "%03d" % (int(a[-3:]) + 1))

    def test_kind_decision_change_sai_thi_tu_choi(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            self.assertFalse(HL.add("khong-co", "x", path=p, now=1.0)["ok"])
            self.assertFalse(HL.add("prompt", "x", path=p, decision="bua", now=1.0)["ok"])
            self.assertFalse(HL.add("prompt", "   ", path=p, now=1.0)["ok"])
            self.assertFalse(p.exists(), "khong duoc ghi file khi input sai")

    def test_giu_chu_viet_va_file_jsonl_hop_le(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            HL.add("lesson", "bài học: đừng bỏ qua -2022", path=p, now=1.0)
            raw = p.read_text(encoding="utf-8")
            self.assertIn("bài học", raw)
            for ln in raw.splitlines():
                json.loads(ln)                       # moi dong phai la JSON


class TestCheck(unittest.TestCase):
    def test_adopted_khong_bang_chung_bi_bat(self):
        rows = [{"id": "H-1", "kind": "prompt", "decision": "adopted", "evidence": "",
                 "ts": 0.0}]
        rep = HL.check(rows, now=10.0)
        self.assertFalse(rep["ok"])
        self.assertIn("KHONG co bang chung", rep["problems"][0])

    def test_de_xuat_treo_qua_7_ngay(self):
        rows = [{"id": "H-2", "kind": "model", "decision": "proposed", "ts": 0.0}]
        rep = HL.check(rows, now=8 * 86400.0)
        self.assertFalse(rep["ok"])
        self.assertIn("chua quyet", rep["problems"][0])

    def test_adopted_co_bang_chung_thi_OK(self):
        rows = [{"id": "H-3", "kind": "risk", "decision": "adopted",
                 "evidence": "EV-abc123", "ts": 0.0}]
        self.assertTrue(HL.check(rows, now=10.0)["ok"])

    def test_kind_la_bi_bat(self):
        rows = [{"id": "H-4", "kind": "bua", "decision": "adopted", "evidence": "x",
                 "ts": 0.0}]
        self.assertIn("kind la", HL.check(rows, now=10.0)["problems"][0])


if __name__ == "__main__":
    unittest.main()
