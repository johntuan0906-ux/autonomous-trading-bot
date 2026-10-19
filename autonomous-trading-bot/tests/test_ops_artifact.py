"""Test `tools/ops_artifact.py` — artifact cho moi quyet dinh van hanh (muc 16, 19/10).

Vi sao co: hoi dong **1-4 VETO** viec lam `council_replay` (ton credit) va chon viec re hon:
moi quyet dinh van hanh sinh 1 file `.md` (boi canh -> phieu -> hanh dong -> ket qua) —
y tuong tu MetaGPT (artifact), Dify (log), LangGraph (checkpoint). Test nay chot: phieu
hoi dong duoc lay DUNG cau hoi tu journal, va markdown sinh ra co du muc.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import ops_artifact as OA      # noqa: E402


def _vote(model, action, conf=0.9, reason="vi ly do X", question="Q1"):
    return json.dumps({"ts": 1792397000.0, "status": "COUNCIL", "model": model,
                       "action": action, "confidence": conf, "reasons": [reason],
                       "question": question}, ensure_ascii=False)


class TestSlugify(unittest.TestCase):
    def test_bo_dau_tieng_viet(self):
        self.assertEqual(OA.slugify("Điều kiện nào thì RESUME?"), "dieu-kien-nao-thi-resume")

    def test_rong_thi_mac_dinh(self):
        self.assertEqual(OA.slugify(""), "quyet-dinh")
        self.assertEqual(OA.slugify("!!! ..."), "quyet-dinh")

    def test_cat_do_dai(self):
        self.assertLessEqual(len(OA.slugify("x" * 200)), 48)


class TestVotesForQuestion(unittest.TestCase):
    def _journal(self, d):
        p = Path(d) / "journal.jsonl"
        p.write_text("\n".join([_vote("m1", "ALLOW", question="Q1"),
                                _vote("m2", "VETO", question="Q1"),
                                _vote("m3", "ALLOW", question="Q2"),
                                '{"event": "OPEN"}']) + "\n", encoding="utf-8")
        return p

    def test_chi_lay_dung_cau_hoi(self):
        with tempfile.TemporaryDirectory() as d:
            rows = OA.votes_for_question(self._journal(d), "Q1")
        self.assertEqual([r["model"] for r in rows], ["m1", "m2"])

    def test_khop_mem_khoang_trang_hoa_thuong(self):
        with tempfile.TemporaryDirectory() as d:
            rows = OA.votes_for_question(self._journal(d), "  q1 ")
        self.assertEqual(len(rows), 2)

    def test_file_khong_ton_tai(self):
        self.assertEqual(OA.votes_for_question(Path("khong/co.jsonl"), "Q1"), [])


class TestTally(unittest.TestCase):
    def test_dem_va_ket_luan(self):
        t = OA.tally([{"action": "ALLOW"}, {"action": "VETO"}, {"action": "NO_OPINION"}])
        self.assertEqual((t["allow"], t["veto"], t["abstain"]), (1, 1, 1))
        self.assertEqual(t["verdict"], "NO_OPINION", "hoa => khong du phieu")

    def test_da_so(self):
        t = OA.tally([{"action": "VETO"}, {"action": "VETO"}, {"action": "ALLOW"}])
        self.assertEqual(t["verdict"], "VETO")


class TestRender(unittest.TestCase):
    def _rec(self, **kw):
        base = {"question": "Co nen resume TESTNET?", "why": "kill-switch trip 15/10",
                "options": ["giu pause", "parity LIVE"], "answer": "parity LIVE",
                "by": "agent (hoi dong 3-1 ALLOW)", "ts": 1792397000.0,
                "actions": ["sua .env", "restart --reset"], "results": ["audit 100/100"],
                "votes": [{"model": "m1", "action": "ALLOW", "confidence": 0.9,
                           "reason": "risk giam dang ke"},
                          {"model": "m2", "action": "VETO", "confidence": 0.8,
                           "reason": "edge chua ro"}]}
        base.update(kw)
        return base

    def test_du_muc_va_ket_luan_phieu(self):
        md = OA.render(self._rec())
        for needle in ("# Quyet dinh van hanh: Co nen resume TESTNET?",
                       "## 1. Boi canh", "kill-switch trip 15/10",
                       "## 2. Phieu hoi dong (n=2", "| m1 | ALLOW | 0.90 |",
                       "**Ket qua**: 1 ALLOW / 1 VETO / 0 khong y kien -> **NO_OPINION**",
                       "## 3. Quyet dinh", "parity LIVE",
                       "## 4. Hanh dong da thuc thi", "- sua .env",
                       "## 5. Ket qua / kiem chung", "- audit 100/100",
                       "## 6. Truy vet"):
            self.assertIn(needle, md, needle)

    def test_khong_co_phieu_thi_ghi_ro(self):
        self.assertIn("khong co phieu hoi dong", OA.render(self._rec(votes=[])))

    def test_thieu_truong_khong_sap(self):
        md = OA.render({})
        self.assertIn("(khong ro)", md)
        self.assertIn("CHUA TRA LOI", md)

    def test_pipe_trong_ly_do_khong_lam_vo_bang(self):
        md = OA.render(self._rec(votes=[{"model": "m", "action": "ALLOW",
                                         "confidence": 0.5, "reason": "a|b"}]))
        self.assertIn("a/b", md)


class TestWriteAndQueue(unittest.TestCase):
    def test_artifact_path_co_moc_thoi_gian_va_slug(self):
        p = OA.artifact_path("logs/ops", 1792397000.0, "Co nen resume?")
        self.assertTrue(Path(p).name.endswith("-co-nen-resume.md"))
        self.assertRegex(Path(p).name[:13], r"^\d{8}-\d{4}$")

    def test_write_tao_file_va_thu_muc(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "ops"
            rep = OA.write_artifact({"question": "Q", "ts": 1792397000.0}, outdir=out)
            self.assertTrue(rep["ok"], rep)
            self.assertTrue(Path(rep["path"]).exists())
            self.assertIn("# Quyet dinh van hanh: Q",
                          Path(rep["path"]).read_text(encoding="utf-8"))

    def test_from_queue_lay_phieu_tu_journal(self):
        with tempfile.TemporaryDirectory() as d:
            q = Path(d) / "ops_queue.json"
            q.write_text(json.dumps([{"id": 7, "question": "Q1", "answer": "lam A",
                                      "by": "agent", "ts": 1792397000.0}]),
                         encoding="utf-8")
            j = Path(d) / "journal.jsonl"
            j.write_text(_vote("m1", "ALLOW", question="Q1") + "\n", encoding="utf-8")
            rep = OA.from_queue(7, done_path=q, open_path=Path(d) / "khong-co.json",
                                journal=j, actions=["da chay X"], outdir=Path(d) / "ops")
            self.assertTrue(rep["ok"], rep)
            self.assertEqual(rep["n_votes"], 1)
            self.assertIn("da chay X", Path(rep["path"]).read_text(encoding="utf-8"))

    def test_from_queue_id_la(self):
        with tempfile.TemporaryDirectory() as d:
            rep = OA.from_queue(99, done_path=Path(d) / "q.json",
                                open_path=Path(d) / "o.json", journal=Path(d) / "j.jsonl",
                                outdir=Path(d) / "ops")
        self.assertFalse(rep["ok"])
        self.assertIn("khong thay", rep["err"])

    def test_list_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            OA.write_artifact({"question": "A", "ts": 1792397000.0}, outdir=d)
            OA.write_artifact({"question": "B", "ts": 1792397600.0}, outdir=d)
            self.assertEqual(len(OA.list_artifacts(d)), 2)
        self.assertEqual(OA.list_artifacts("khong/co"), [])


if __name__ == "__main__":
    unittest.main()
