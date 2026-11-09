"""Test bo GOLDEN SET (`tools/golden_set.py`, `tools/golden_build.py`, `reason_codes.py`).

Vi sao co (09/11): golden set la thuoc do "ban moi co lam MAT hanh vi cu khong". Neu chinh
thuoc do sai (rule `must_not` bi dao nghia, adapter bo qua ca hong, baseline khong phat hien
doi hanh vi, digest tinh ca so lieu tam thoi) thi ca **45 ca** xanh van la xanh GIA — dung lop loi
"im lang" cua du an.

Kiem o day: ngu nghia `must` / `must_not`, ca hong phai FAIL chu khong bien mat, id trung bi
bat, drift so voi baseline duoc bao, va `classify_text` khong doan bua.
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

import golden_build as GB   # noqa: E402
import golden_set as GS     # noqa: E402
import reason_codes as RC   # noqa: E402


def _tmp_cases(cases: list, tmp: str) -> str:
    p = Path(tmp) / "cases.jsonl"
    p.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases),
                 encoding="utf-8")
    return str(p)


def _case(cid="c1", kind="normal", component="risk_cap", inp=None, exp=None) -> dict:
    return {"id": cid, "kind": kind, "component": component, "title": "t",
            "input": inp if inp is not None else {"equity": 1000.0, "cap_pct": 2.0,
                                                  "new_risk_usd": 6.0, "positions": {}},
            "expect": exp if exp is not None else {"output": {"ok": True}}}


class TestReasonCodes(unittest.TestCase):
    """Tu vung ly do: dung de dem/so sanh duoc, khong phai van ban tu do."""

    def test_code_hop_le_va_nhom(self):
        self.assertTrue(RC.known("RISK_CAP"))
        self.assertFalse(RC.known("risk_cap"))          # phai IN HOA
        self.assertEqual(RC.kind_of("RISK_CAP"), "policy")
        self.assertEqual(RC.kind_of("API_BAN"), "tool")
        self.assertEqual(RC.kind_of("khong_ton_tai"), "unknown")
        self.assertIn("RISK_CAP", RC.codes_of_kind("policy"))
        self.assertEqual(RC.codes_of_kind("decision"), ["TAKE"])

    def test_doan_tu_van_ban_that_trong_log(self):
        self.assertEqual(RC.classify_text("tran risk danh muc: dang 1.60% + moi 0.40%"),
                         "RISK_CAP")
        self.assertEqual(RC.classify_text('418 I\'m a teapot {"code":-1003}'), "API_BAN")
        self.assertEqual(RC.classify_text("exceeded your monthly quota"), "QUOTA_EXCEEDED")
        self.assertEqual(RC.classify_text("single-best-setup: BTC already open"),
                         "MAX_POSITIONS")
        self.assertEqual(RC.classify_text(""), "")
        self.assertEqual(RC.classify_text("cau gi do khong khop"), "")

    def test_normalize_uu_tien_code_da_dung(self):
        self.assertEqual(RC.normalize("risk_cap", "tran risk"), "RISK_CAP")
        self.assertEqual(RC.normalize("", "tran risk"), "RISK_CAP")
        self.assertEqual(RC.normalize("LA", ""), "")


class TestRuleEngine(unittest.TestCase):
    """`must` / `must_not` phai dung CUNG mot phep danh gia (khong duoc dao nghia)."""

    def test_must_va_must_not(self):
        out = {"ok": False, "reason": "tran risk danh muc 1.6%", "n": 3}
        self.assertEqual(GS._check_rules(out, ["ok:==:false"], True), [])
        self.assertTrue(GS._check_rules(out, ["ok:==:true"], True))
        # must_not: rule DUNG ⇒ phai bao vi pham
        self.assertTrue(GS._check_rules(out, ["ok:==:false"], False))
        self.assertEqual(GS._check_rules(out, ["ok:==:true"], False), [])

    def test_rule_sai_dinh_dang_hoac_toan_tu_la(self):
        self.assertTrue(GS._check_rules({"a": 1}, ["a>1"], True))
        self.assertTrue(GS._check_rules({"a": 1}, ["a:~~:1"], True))
        self.assertTrue(GS._check_rules({}, ["a:==:1"], True))       # thieu key

    def test_duong_dan_long_va_so_sanh(self):
        out = {"x": {"y": [10, 20]}, "s": "tran risk", "f": 0.1 + 0.2}
        self.assertEqual(GS._check_rules(out, ["x.y.0:==:10"], True), [])
        self.assertEqual(GS._check_rules(out, ["f:==:0.3"], True), [])   # co sai so
        self.assertEqual(GS._check_rules(out, ["s:contains:tran"], True), [])
        self.assertEqual(GS._check_rules(out, ["s:not_contains:abc"], True), [])
        self.assertEqual(GS._check_rules(out, ["s:in:[\"abc\", \"tran risk\"]"], True), [])

    def test_subset_khop_mot_phan(self):
        got = {"ok": True, "reason": "ok", "n_open": 1}
        self.assertEqual(GS._subset_diff(got, {"ok": True}), [])
        self.assertTrue(GS._subset_diff(got, {"ok": False}))
        self.assertTrue(GS._subset_diff(got, {"khong_co": 1}))


class TestBoCa(unittest.TestCase):
    """Bo ca trong git phai chay SACH va phu het cac cong."""

    def test_bo_ca_committed_chay_sach(self):
        cases, errors = GS.load_cases()
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(cases), 20)
        rep = GS.evaluate(cases)
        self.assertTrue(rep["ok"], [f["id"] for f in rep["failures"]])
        self.assertEqual(rep["failed"], 0)

    def test_phu_het_cac_cong(self):
        cases, _e = GS.load_cases()
        comps = {c["component"] for c in cases}
        self.assertEqual(comps, set(GS.COMPONENTS))
        kinds = {c["kind"] for c in cases}
        self.assertEqual(kinds, set(GS.KINDS))

    def test_schema_ca_hong_bi_bao(self):
        self.assertTrue(GS.validate_case({}))
        self.assertTrue(GS.validate_case({"id": "x", "kind": "la", "component": "feats",
                                          "input": {}, "expect": {}}))
        self.assertTrue(GS.validate_case({"id": "x", "kind": "normal", "component": "la",
                                          "input": {}, "expect": {}}))
        self.assertEqual(GS.validate_case(_case()), "")

    def test_id_trung_bi_bat(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = _tmp_cases([_case("same"), _case("same")], tmp)
            cases, errors = GS.load_cases(p)
            self.assertEqual(len(cases), 1)
            self.assertTrue(any("TRUNG" in e for e in errors))


class TestRunner(unittest.TestCase):
    """Ca hong phai FAIL ro rang; adapter nem loi khong duoc lam chet runner."""

    def test_doi_dap_an_thi_ca_FAIL(self):
        bad = _case(exp={"output": {"ok": False}})
        r = GS.run_case(bad)
        self.assertFalse(r["ok"])
        self.assertTrue(r["why"])
        self.assertEqual(GS.evaluate([bad])["failed"], 1)

    def test_adapter_nem_loi_thanh_ca_FAIL(self):
        bad = _case(component="feats", inp={"khong_phai_tham_so": 1})
        r = GS.run_case(bad)
        self.assertFalse(r["ok"])
        self.assertIn("TypeError", r["why"][0])

    def test_component_la_KHONG_bo_qua(self):
        r = GS.run_case(_case(component="khong_co_adapter"))
        self.assertFalse(r["ok"])
        self.assertIn("khong co adapter", r["why"][0])

    def test_check_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok_p = _tmp_cases([_case()], tmp)
            self.assertEqual(GS.main(["--cases", ok_p, "--no-baseline", "--check"]), 0)
            bad_p = _tmp_cases([_case(exp={"output": {"ok": False}})], tmp)
            self.assertEqual(GS.main(["--cases", bad_p, "--no-baseline", "--check"]), 1)
            self.assertEqual(GS.main(["--cases", bad_p, "--no-baseline"]), 0)


class TestBaseline(unittest.TestCase):
    """Baseline la de phat hien "hanh vi DOI du ca van xanh" — phai hoat dong."""

    def test_drift_khi_output_doi(self):
        c = _case()
        rep1 = GS.evaluate([c])
        base = {"digest": rep1["digest"]}
        self.assertEqual(GS.evaluate([c], base)["drift"], [])
        # cung input, nhung output adapter doi GIA TRI cua mot key DA KHAI ⇒ phai bao DRIFT
        orig = GS.ADAPTERS["risk_cap"]
        try:
            GS.ADAPTERS["risk_cap"] = lambda inp: dict(orig(inp), ok=not orig(inp)["ok"])
            rep2 = GS.evaluate([c], base)
        finally:
            GS.ADAPTERS["risk_cap"] = orig
        self.assertTrue(rep2["drift"])
        self.assertFalse(rep2["ok"])
        self.assertEqual(rep2["drift"][0]["id"], "c1")

    def test_ghi_va_doc_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = str(Path(tmp) / "sub" / "b.json")
            rep = GS.evaluate([_case()])
            GS.write_baseline(rep, p)
            b = GS.load_baseline(p)
            self.assertEqual(b["n"], 1)
            self.assertEqual(b["digest"]["c1"], rep["digest"]["c1"])
            self.assertEqual(GS.load_baseline(str(Path(tmp) / "khong_co.json")), {})


class TestJournalThat(unittest.TestCase):
    """Ca `journal_feats` phai bat duoc feats hong trong du lieu THAT."""

    def test_bat_feats_thieu_key_va_ngoai_dai(self):
        import learner as L
        good = {f: 0.0 for f in L.FEATURES}
        rows = [{"ts": 1, "event": "OPEN", "pair": "A", "feats": good},
                {"ts": 2, "event": "OPEN", "pair": "B", "feats": {"tech": 5.0}},
                {"ts": 3, "event": "CLOSE", "pair": "C"},              # bo qua
                {"ts": 4, "event": "OPEN", "pair": "D",
                 "feats": dict(good, rsi_bias=float("nan"))}]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "j.jsonl"
            p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            out = GS._ad_journal_feats({"journal": str(p), "limit": 10})
            self.assertEqual(out["n_checked"], 3)
            self.assertEqual(out["n_open_rows"], 3)
            self.assertEqual(out["n_violations"], 2)
            pairs = {v["pair"] for v in out["violations"]}
            self.assertEqual(pairs, {"B", "D"})

    def test_file_hong_phai_bao_chu_khong_im(self):
        out = GS._ad_journal_feats({"journal": "logs/khong_ton_tai.jsonl"})
        self.assertEqual(out["n_checked"], 0)
        self.assertIn("khong doc duoc", out["violations"][0])


class TestBuilder(unittest.TestCase):
    """Builder phai sinh ca HOP LE va ON DINH (khong phu thuoc thoi diem chay)."""

    def test_sinh_ca_hop_le_va_on_dinh(self):
        a = GB.build("logs/journal.jsonl", 50)
        b = GB.build("logs/journal.jsonl", 50)
        self.assertEqual(a, b)                     # chay 2 lan y het nhau
        self.assertGreaterEqual(len(a), 20)
        ids = [c["id"] for c in a]
        self.assertEqual(len(ids), len(set(ids)))
        for c in a:
            self.assertEqual(GS.validate_case(c), "", c["id"])
        self.assertIn("jrn-feats-integrity", ids)


class TestDigestHopDong(unittest.TestCase):
    """Digest DRIFT chi tinh tren phan DA KHAI (hop dong), khong tinh so lieu tam thoi.

    Lop loi that (09/11): ca `jrn-feats-integrity` doc journal THAT nen `n_checked` tang moi
    ngay ⇒ digest doi moi ngay ⇒ `--check` bao DRIFT gia lien tuc, va DRIFT THAT bi chim.
    """

    def test_so_lieu_khong_khai_TRONG_digest_thi_khong_bao_drift(self):
        base = {"id": "c1", "kind": "normal", "component": "risk_cap",
                "input": {"equity": 1000.0, "cap_pct": 2.0, "new_risk_usd": 6.0,
                          "positions": {}},
                "expect": {"output": {"ok": True}}}
        r1 = GS.run_case(base)
        r2 = GS.run_case(base)                       # cung ca, cung output
        self.assertEqual(r1["digest"], r2["digest"])

    def test_doi_gia_tri_DA_KHAI_thi_digest_doi(self):
        c = {"id": "c2", "kind": "normal", "component": "risk_cap",
             "input": {"equity": 1000.0, "cap_pct": 2.0, "new_risk_usd": 6.0,
                       "positions": {}},
             "expect": {"output": {"ok": True}}}
        actual = GS.run_case(c)["digest"]
        # (a) GIA TRI cua key DA KHAI doi ⇒ digest DOI (drift that phai bat duoc)
        self.assertNotEqual(actual, GS._digest(
            GS._contract_view({"ok": False}, c["expect"])))
        # (b) key KHONG khai xuat hien / doi so lieu ⇒ digest KHONG doi (khong bao dong gia)
        self.assertEqual(actual, GS._digest(
            GS._contract_view({"ok": True, "n_checked": 999, "x": 1}, c["expect"])))

    def test_contract_view_bo_key_khong_khai(self):
        view = GS._contract_view({"ok": True, "n_checked": 999, "violations": []},
                                 {"output": {"violations": []}})
        self.assertEqual(view, {"violations": []})

    def test_contract_view_rong_thi_giu_nguyen(self):
        full = {"a": 1}
        self.assertEqual(GS._contract_view(full, {"output": {}}), full)


