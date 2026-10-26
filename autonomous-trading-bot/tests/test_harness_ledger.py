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


class TestDecide(unittest.TestCase):
    """Chốt quyết định cho mục đã ghi (giữ lịch sử) — tránh `--check` báo 'treo' giả."""

    def test_chot_rejected_va_giu_lich_su(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rid = HL.add("prompt", "nhan DOI/GIU", "chua do", path=p, now=1.0)["record"]["id"]
            r = HL.decide(rid, "rejected", evidence="probe A/B: B tut xuong NO_OPINION",
                          note="hoan tac", path=p, now=2.0)
            self.assertTrue(r["ok"])
            rec = r["record"]
            self.assertEqual(rec["decision"], "rejected")
            self.assertEqual(len(rec["history"]), 1)
            self.assertEqual(rec["history"][0]["decision"], "proposed")
            self.assertIn("probe", rec["evidence"])

    def test_khong_tim_thay_id(self):
        with tempfile.TemporaryDirectory() as t:
            r = HL.decide("H-99999999-999", "rejected", path=Path(t) / "l.jsonl")
            self.assertFalse(r["ok"])
            self.assertIn("khong tim thay", r["err"])

    def test_decision_sai_thi_tu_choi(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rid = HL.add("prompt", "x", path=p, now=1.0)["record"]["id"]
            self.assertFalse(HL.decide(rid, "bua", path=p)["ok"])

    def test_sau_khi_chot_thi_check_khong_bao_treo(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rid = HL.add("prompt", "x", path=p, now=0.0)["record"]["id"]
            HL.decide(rid, "rejected", evidence="da do", path=p, now=1.0)
            rows = HL.read_all(p)
            rep = HL.check(rows, now=30 * 86400.0)
            self.assertTrue(rep["ok"], rep["problems"])


class TestHenRaSoat(unittest.TestCase):
    """(26/10) "Xác nhận sau vài ngày" phải nằm trong SỔ, không phải trí nhớ người.

    Yêu cầu người vận hành: *"theo dõi tiếp, vài ngày sau xác nhận lại"* — nếu chỉ ghi vào
    docs/ghi chú thì không ai nhắc ⇒ thay đổi vào hệ thống rồi "vả rồi để đó" (lớp lỗi B-028).
    """

    def test_add_co_review_days_thi_dat_hen(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rec = HL.add("risk", "doi hinh hoc", "backtest", decision="adopted",
                         path=p, now=1_000_000.0, review_days=3.0)["record"]
            self.assertAlmostEqual(rec["review_at"], 1_000_000.0 + 3 * 86400.0)
            self.assertAlmostEqual(rec["review_days"], 3.0)

    def test_add_khong_hen_thi_khong_co_review_at(self):
        with tempfile.TemporaryDirectory() as t:
            rec = HL.add("prompt", "x", "ev", path=Path(t) / "l.jsonl", now=0.0)["record"]
            self.assertNotIn("review_at", rec)

    def test_due_chi_lay_adopted_qua_han_chua_ra_soat(self):
        rows = [{"id": "A", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0, "review_at": 100.0},
                {"id": "B", "kind": "risk", "decision": "proposed", "evidence": "x",
                 "ts": 0.0, "review_at": 100.0},
                {"id": "C", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0, "review_at": 10 ** 9},
                {"id": "D", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0, "review_at": 100.0, "reviewed_at": 50.0},
                {"id": "E", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0}]
        self.assertEqual([r["id"] for r in HL.due(rows, now=200.0)], ["A"])

    def test_schedule_hen_lai_va_mo_lai_muc_da_ra_soat(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rid = HL.add("risk", "x", "ev", decision="adopted", path=p, now=0.0,
                         review_days=1.0)["record"]["id"]
            HL.mark_review(rid, "da xac nhan", path=p, now=2 * 86400.0)
            self.assertEqual(HL.due(HL.read_all(p), now=2 * 86400.0), [])
            r = HL.schedule(rid, 3.0, path=p, now=2 * 86400.0)
            self.assertTrue(r["ok"])
            self.assertEqual(r["record"]["reviewed_at"], 0)
            self.assertAlmostEqual(r["record"]["review_at"], 5 * 86400.0)
            self.assertEqual(len(HL.due(HL.read_all(p), now=6 * 86400.0)), 1)

    def test_mark_review_ghi_ket_luan_vao_lich_su(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            rid = HL.add("risk", "x", "ev", decision="adopted", path=p,
                         now=0.0)["record"]["id"]
            r = HL.mark_review(rid, "giu nguyen, n=64 PF 1.2", by="nguoi van hanh",
                               path=p, now=5.0)
            self.assertTrue(r["ok"])
            self.assertEqual(r["record"]["review_note"], "giu nguyen, n=64 PF 1.2")
            self.assertEqual(r["record"]["history"][0]["kind"], "review")
            self.assertEqual(r["record"]["history"][0]["by"], "nguoi van hanh")

    def test_check_bao_khi_qua_han_chua_xac_nhan(self):
        rows = [{"id": "H-9", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0, "review_at": 100.0}]
        rep = HL.check(rows, now=200.0)
        self.assertFalse(rep["ok"])
        self.assertIn("CHUA xac nhan", rep["problems"][0])

    def test_sau_khi_ra_soat_thi_check_sach(self):
        rows = [{"id": "H-9", "kind": "risk", "decision": "adopted", "evidence": "x",
                 "ts": 0.0, "review_at": 100.0, "reviewed_at": 150.0}]
        self.assertTrue(HL.check(rows, now=200.0)["ok"])

    def test_khong_tim_thay_id(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            self.assertFalse(HL.schedule("H-1", 1.0, path=p)["ok"])
            self.assertFalse(HL.mark_review("H-1", "x", path=p)["ok"])


if __name__ == "__main__":
    unittest.main()
