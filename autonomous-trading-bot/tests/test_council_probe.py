# -*- coding: utf-8 -*-
"""Test `tools/council_probe.py` — đo contrast hành vi giữa 2 biến thể harness.

Chốt 4 tính chất:
1. **Không gọi LLM khi chưa `--live`** (0 đồng) — chỉ in kế hoạch;
2. Phát hiện **đổi phiếu** và **đổi kết luận** giữa A và B;
3. Phát hiện **lý do không khớp phiếu** (đo thật 21/10: phiếu VETO + lý do ủng hộ ALLOW);
4. Case file hỏng → báo lỗi rõ, không ném exception.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import council_probe as CP      # noqa: E402

CASE = {"name": "risk",
        "a": {"question": "co doi tran ngay khong?", "allow": "nang tran ngay",
              "veto": "giu nguyen tran ngay", "context": []},
        "b": {"question": "co doi tran ngay khong?", "allow": "DOI: nang MAX_DAILY_LOSS_PCT",
              "veto": "GIU: tran ngay nhu hien tai", "context": ["PHIEU: ALLOW = DOI"]}}


class TestReasonMatches(unittest.TestCase):
    def test_ly_do_khop_phieu(self):
        self.assertTrue(CP.reason_matches("nen nang tran ngay de chiu nhieu lenh thua",
                                          "ALLOW", CASE["a"]))

    def test_ly_do_nguoc_phieu(self):
        # dung ca da gap: phieu VETO nhung ly do ung ho phuong an ALLOW
        self.assertFalse(CP.reason_matches("nang tran ngay de chiu >=3 lenh thua",
                                           "VETO", CASE["a"]))

    def test_khong_du_tin_hieu_thi_None(self):
        self.assertIsNone(CP.reason_matches("", "VETO", CASE["a"]))
        self.assertIsNone(CP.reason_matches("abc", "NO_OPINION", CASE["a"]))

    def test_chi_tinh_tu_rieng_cua_tung_phuong_an(self):
        """Từ CHUNG cho cả 2 phương án không được tính là 'khớp' (sửa lỗi báo oan 22/10)."""
        case = {"allow": "nang tran ngay", "veto": "giu nguyen tran ngay"}
        # "tran ngay" la tu chung -> khong ket luan duoc
        self.assertIsNone(CP.reason_matches("tran ngay", "VETO", case))
        # co tu rieng cua VETO -> ket luan duoc
        self.assertTrue(CP.reason_matches("giu nguyen tran ngay", "VETO", case))


class TestProbe(unittest.TestCase):
    def test_khong_live_thi_khong_goi_LLM(self):
        called = []

        def boom(payload):
            called.append(payload)
            raise AssertionError("khong duoc goi LLM khi chua --live")

        rep = CP.probe([CASE], boom, live=False)
        self.assertEqual(called, [])
        self.assertEqual(rep["n_cases"], 1)
        self.assertIn("plan", rep)
        self.assertEqual(rep["cost_usd"], 0.0)

    def test_phat_hien_doi_phieu_va_doi_ket_luan(self):
        def fake(payload):
            # bien the B (allow co chu 'DOI') -> model doi phieu
            if "DOI" in str(payload.get("option_ALLOW")):
                return {"votes": {"m1": {"action": "ALLOW", "confidence": 0.7,
                                         "reasons": ["nang tran ngay de chiu nhieu lenh"],
                                         "cost_usd": 0.004}}}
            return {"votes": {"m1": {"action": "VETO", "confidence": 0.8,
                                     "reasons": ["nang tran ngay de chiu nhieu lenh"],
                                     "cost_usd": 0.004}}}

        rep = CP.probe([CASE], fake, live=True)
        ct = rep["cases"][0]["contrast"]
        self.assertEqual(ct["verdict_a"], "VETO")
        self.assertEqual(ct["verdict_b"], "ALLOW")
        self.assertTrue(ct["verdict_changed"])
        self.assertEqual(ct["flips"], ["m1"])
        self.assertEqual(ct["flip_rate"], 1.0)
        self.assertEqual(rep["reason_mismatch"], 1, "phieu A (VETO) co ly do ung ho ALLOW")
        self.assertAlmostEqual(rep["cost_usd"], 0.008)
        self.assertIn("KHAC NHAU", rep["ket_luan"])

    def test_dong_nhat_thi_ket_luan_dong_nhat(self):
        def fake(payload):
            return {"votes": {"m1": {"action": "VETO", "confidence": 0.9,
                                     "reasons": ["giu nguyen tran ngay"], "cost_usd": 0.0}}}

        rep = CP.probe([CASE], fake, live=True)
        self.assertEqual(rep["total_flips"], 0)
        self.assertFalse(rep["verdict_changed"])
        self.assertIn("dong nhat", rep["ket_luan"])


class TestLoadCases(unittest.TestCase):
    def test_file_thieu(self):
        cases, err = CP.load_cases(Path(tempfile.gettempdir()) / "khong-co-cases.json")
        self.assertEqual(cases, [])
        self.assertIn("khong doc duoc", err)

    def test_json_hong(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.json"
            p.write_text("{hong", encoding="utf-8")
            cases, err = CP.load_cases(p)
            self.assertEqual(cases, [])
            self.assertIn("JSON hong", err)

    def test_thieu_bien_the(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.json"
            p.write_text('[{"name": "x", "a": {}}]', encoding="utf-8")
            cases, err = CP.load_cases(p)
            self.assertEqual(cases, [])
            self.assertIn("thieu 'b'", err)

    def test_doc_duoc_case_hop_le(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "c.json"
            p.write_text('[{"a": {}, "b": {}}]', encoding="utf-8")
            cases, err = CP.load_cases(p)
            self.assertEqual(err, "")
            self.assertEqual(cases[0]["name"], "case-0")


class TestResolveVerdict(unittest.TestCase):
    """(22/10) Người vận hành giao toàn quyền: KHÔNG được để 'chia rẽ ⇒ không quyết'."""

    def _tal(self, votes):
        import council_vote as CV
        return CV.tally(votes)

    def test_da_so_thang(self):
        import council_vote as CV
        t = self._tal({"a": {"action": "ALLOW"}, "b": {"action": "ALLOW"},
                       "c": {"action": "VETO"}})
        r = CV.resolve_verdict(t)
        self.assertEqual(r["verdict"], "ALLOW")
        self.assertEqual(r["rule"], "majority")

    def test_hoa_thi_theo_confidence(self):
        import council_vote as CV
        t = self._tal({"a": {"action": "ALLOW", "confidence": 0.9},
                       "b": {"action": "VETO", "confidence": 0.5}})
        r = CV.resolve_verdict(t)
        self.assertEqual(r["verdict"], "ALLOW")
        self.assertEqual(r["rule"], "confidence")

    def test_hoa_ca_confidence_thi_giu_hien_trang(self):
        import council_vote as CV
        t = self._tal({"a": {"action": "ALLOW", "confidence": 0.7},
                       "b": {"action": "VETO", "confidence": 0.7}})
        r = CV.resolve_verdict(t)
        self.assertEqual(r["verdict"], "VETO")
        self.assertEqual(r["rule"], "conservative")

    def test_khong_du_quorum_thi_giu_hien_trang(self):
        import council_vote as CV
        t = self._tal({"a": {"action": "ALLOW", "confidence": 0.99}})
        r = CV.resolve_verdict(t)
        self.assertEqual(r["verdict"], "VETO")
        self.assertFalse(r["binding"])
        self.assertEqual(r["rule"], "quorum")

    def test_khong_bao_gio_tra_NO_OPINION(self):
        import council_vote as CV
        for votes in ({"a": {"action": "ALLOW"}},
                      {"a": {"action": "NO_OPINION"}},
                      {"a": {"action": "ALLOW"}, "b": {"action": "VETO"}}):
            self.assertNotEqual(CV.resolve_verdict(self._tal(votes))["verdict"],
                                "NO_OPINION")


if __name__ == "__main__":
    unittest.main()
