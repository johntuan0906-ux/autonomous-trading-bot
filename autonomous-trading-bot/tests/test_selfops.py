"""Test 3 tool moi: `council_gaps` (thieu hut), `selfops` (tu van hanh), `drift_docs`.

Vi sao co (09/11): day la lop "tu hoc + tu van hanh". Lop loi nguy hiem nhat o day KHONG phai
la crash, ma la:
  * hoi dong tu noi "minh on" khi so lieu khong dat (gap analysis bo sot nguong);
  * tu chay viec DUNG VAO STATE cua LIVE (tai khoan that) ma khong ai cho phep;
  * tai lieu/code lech nhau (drift) ma bao cao van "khop".
Test chot dung 3 dieu do, va chot ca chieu NGUOC: khi so lieu da dat thi KHONG duoc bao gap.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import council_gaps as CG   # noqa: E402
import drift_docs as DD     # noqa: E402
import selfops as SO        # noqa: E402


def _rep(**kw) -> dict:
    """Bao cao hoi dong gia (dung khuon `council_evals.model_leaderboard`)."""
    base = {"cases": 40, "per_model": {}, "thin": [], "keep": [], "drop": [],
            "match": {"n": 40, "matched": 40, "via_decision_id": 40, "via_heuristic": 0,
                      "rate": 1.0, "exact_rate": 1.0},
            "calibration": {"brier": 0.20, "n": 40, "bins": []}}
    base.update(kw)
    return base


class TestGaps(unittest.TestCase):
    def test_so_lieu_tot_thi_KHONG_bao_thieu_hut(self):
        data = {"council": _rep(), "stats": {"rows": 100, "codes": {"TAKE": 10},
                                             "open_stale": 0, "bad_rows": 0}}
        self.assertEqual(CG.gaps_from(data), [])

    def test_brier_cao_la_thieu_hut_muc_CAO(self):
        gaps = CG.gaps_from({"council": _rep(calibration={"brier": 0.341}),
                             "stats": {}})
        g = {x["id"]: x for x in gaps}
        self.assertIn("calibration", g)
        self.assertEqual(g["calibration"]["severity"], CG.SEV_HIGH)
        self.assertIn("0.341", json.dumps(g["calibration"]))

    def test_ghep_doan_la_thieu_hut_muc_CAO(self):
        m = {"n": 100, "matched": 60, "via_decision_id": 0, "via_heuristic": 60,
             "rate": 0.6, "exact_rate": 0.0}
        gaps = CG.gaps_from({"council": _rep(match=m), "stats": {}})
        self.assertIn("match_exact", {x["id"] for x in gaps})

    def test_khong_co_phieu_nao_la_thieu_hut_rieng(self):
        m = {"n": 0, "matched": 0, "via_decision_id": 0, "via_heuristic": 0,
             "rate": None, "exact_rate": None}
        ids = {x["id"] for x in CG.gaps_from({"council": _rep(match=m), "stats": {}})}
        self.assertIn("data_absent", ids)

    def test_moi_thieu_hut_phai_co_needs_va_action(self):
        """Chot chan: gap khong co `needs`/`action` la loi khong tu hoc duoc."""
        gaps = CG.gaps_from({"council": _rep(calibration={"brier": 0.5},
                                             thin=["m1", "m2"],
                                             per_model={"m1": {"value_r": -0.1}}),
                             "stats": {"rows": 500, "codes": {"RISK_CAP": 400, "TAKE": 5},
                                       "open_stale": 3, "bad_rows": 2}})
        self.assertGreaterEqual(len(gaps), 4)
        for g in gaps:
            self.assertTrue(g.get("needs"), "%s thieu needs" % g.get("id"))
            self.assertTrue(g.get("action"), "%s thieu action" % g.get("id"))
            self.assertIn(g.get("severity"), (CG.SEV_HIGH, CG.SEV_MED, CG.SEV_LOW))

    def test_block_dominance_chi_bao_khi_du_mau(self):
        few = {"rows": 10, "codes": {"RISK_CAP": 5}}
        self.assertNotIn("block_dominance",
                         {x["id"] for x in CG.gaps_from({"council": _rep(), "stats": few})})
        many = {"rows": 1000, "codes": {"RISK_CAP": 900, "TAKE": 5}}
        self.assertIn("block_dominance",
                      {x["id"] for x in CG.gaps_from({"council": _rep(), "stats": many})})

    def test_ke_hoach_tu_hoc_liet_ke_du_viec_va_thu_tu(self):
        gaps = [{"id": "b", "severity": CG.SEV_MED, "metric": "m", "value": 1,
                 "target": 0, "needs": ["n1"], "action": "a1", "auto": True},
                {"id": "a", "severity": CG.SEV_HIGH, "metric": "m", "value": 2,
                 "target": 0, "needs": ["n2"], "action": "a2", "auto": False}]
        md = CG.study_plan(gaps)
        self.assertLess(md.index("## a"), md.index("## b"), "muc CAO phai dung truoc")
        self.assertIn("- [ ] n2", md)
        self.assertIn("KHONG", md)

    def test_journal_stats_dem_dung(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "j.jsonl"
            p.write_text("\n".join([
                json.dumps({"event": "OPEN", "pair": "A", "reason_code": "TAKE",
                            "data_age": {"candles": {"level": "stale"}}}),
                json.dumps({"event": "AGENT", "decision_id": "d-1"}),
                json.dumps({"event": "AGENT"}),
                "{hong",
            ]) + "\n", encoding="utf-8")
            st = CG.journal_stats(p)
        self.assertEqual(st["rows"], 3)
        self.assertEqual(st["agent"], 2)
        self.assertEqual(st["agent_with_did"], 1)
        self.assertEqual(st["open"], 1)
        self.assertEqual(st["open_stale"], 1)
        self.assertEqual(st["bad_rows"], 1)
        self.assertEqual(st["codes"].get("TAKE"), 1)


class TestSelfOps(unittest.TestCase):
    """`plan()` va `run()`: tu lam trong gioi han, KHONG dung state LIVE khi chua cho phep."""

    NOW = 1_700_000_000.0

    def _st(self, **kw) -> dict:
        base = {"now": self.NOW, "day": "2023-11-14", "heartbeat_age": 30.0,
                "kill_tripped": False, "kill_reason": "", "kill_day": "",
                "open_positions": 0, "entries_paused": False, "entries_reason": "",
                "learner_n": 100, "learner_refit_ts": self.NOW - 3600.0}
        base.update(kw)
        return base

    def test_viec_chi_doc_luon_tu_lam(self):
        items = SO.plan(self._st(), gaps=[])
        ids = {i["id"] for i in items if i["auto"]}
        self.assertTrue({"gaps", "drift_docs", "golden"} <= ids)

    def test_refit_chi_khi_du_mau_va_da_lau(self):
        self.assertNotIn("refit", {i["id"] for i in SO.plan(self._st(), gaps=[])})
        self.assertIn("refit", {i["id"] for i in SO.plan(
            self._st(learner_n=999, learner_refit_ts=0.0), gaps=[])})

    def test_nhip_tim_chet_thi_de_xuat_restart_nhung_LIVE_thi_KHONG_tu_chay(self):
        st = self._st(heartbeat_age=9999.0)
        items = [i for i in SO.plan(st, gaps=[], instance="testnet") if i["id"] == "restart"]
        self.assertTrue(items and items[0]["auto"])
        live = [i for i in SO.plan(st, gaps=[], instance="live") if i["id"] == "restart"]
        self.assertTrue(live and not live[0]["auto"], "LIVE phai do nguoi quyet")

    def test_chi_tu_go_kill_switch_khi_flat_va_sang_ngay_moi(self):
        same_day = SO.plan(self._st(kill_tripped=True, kill_day="2023-11-14"), gaps=[])
        self.assertIn("kill_review", {i["id"] for i in same_day})
        self.assertNotIn("kill_reset", {i["id"] for i in same_day})

        new_day = SO.plan(self._st(kill_tripped=True, kill_day="2023-11-13"), gaps=[])
        self.assertIn("kill_reset", {i["id"] for i in new_day})

        still_open = SO.plan(self._st(kill_tripped=True, kill_day="2023-11-13",
                                      open_positions=2), gaps=[])
        self.assertNotIn("kill_reset", {i["id"] for i in still_open})

    def test_live_state_bi_chan_khi_chua_cho_phep(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "autonomy.jsonl"
            st = self._st(heartbeat_age=9999.0)
            items = SO.plan(st, gaps=[], instance="live")
            rep = SO.run(items, apply=True, allow_live_state=False, instance="live",
                         now=self.NOW, log_path=log)
            self.assertIn("restart", rep["skipped"])
            self.assertNotIn("restart", rep["done"])
            rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(r["action"] != "restart" or r["applied"] is False
                                for r in rows))

    def test_dry_run_khong_chay_gi(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "a.jsonl"
            rep = SO.run(SO.plan(self._st(), gaps=[]), apply=False, now=self.NOW,
                         log_path=log)
            self.assertEqual(rep["done"], [])
            self.assertEqual(rep["n"], len(rep["rows"]))

    def test_apply_thi_ghi_log_va_chay_viec_an_toan(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "a.jsonl"
            items = [{"id": "echo", "action": "in", "why": "thu",
                      "cmd": [sys.executable, "-c", "print('ok')"], "auto": True,
                      "live_state": False, "reason_code": "", "evidence": {}}]
            rep = SO.run(items, apply=True, now=self.NOW, log_path=log)
            self.assertEqual(rep["done"], ["echo"])
            self.assertEqual(rep["failed"], [])
            rec = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
            self.assertTrue(rec["applied"])
            self.assertEqual(rec["rc"], 0)

    def test_lenh_loi_duoc_ghi_khong_lam_chet(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "a.jsonl"
            items = [{"id": "bad", "action": "loi", "why": "thu",
                      "cmd": [sys.executable, "-c", "raise SystemExit(3)"], "auto": True}]
            rep = SO.run(items, apply=True, now=self.NOW, log_path=log)
            self.assertEqual(rep["failed"], ["bad"])
            self.assertTrue(log.exists())


class TestDriftDocs(unittest.TestCase):
    """`drift_docs`: tai lieu phai KHOP code; lech so lieu la LECH (chan), ma cu la WARN."""

    def test_so_lieu_lech_bi_bao(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "OPERATIONS.md").write_text("co **40 mã / 7 nhóm** va (26 ca / 8 cổng)\n",
                                             encoding="utf-8")
            claims = (
                {"file": "OPERATIONS.md", "pattern": r"(\d+) m\u00e3 / (\d+) nh\u00f3m",
                 "values": lambda: ["38", "7"], "what": "ma ly do"},
                {"file": "OPERATIONS.md", "pattern": r"(\d+) ca / (\d+) c\u1ed5ng",
                 "values": lambda: ["45", "14"], "what": "golden"},
            )
            rows = DD.check_claims(claims, d)
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[0]["ok"])
        self.assertIn("40/7", rows[0]["note"])
        self.assertFalse(rows[1]["ok"])

    def test_so_lieu_khop_thi_OK(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "OPERATIONS.md").write_text("**38 mã / 7 nhóm**\n", encoding="utf-8")
            claims = ({"file": "OPERATIONS.md", "pattern": r"(\d+) m\u00e3 / (\d+) nh\u00f3m",
                       "values": lambda: ["38", "7"], "what": "ma ly do"},)
            rows = DD.check_claims(claims, d)
        self.assertTrue(rows[0]["ok"])

    def test_tai_lieu_doi_cau_chu_lam_mat_dau_vet_cung_la_LECH(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "OPERATIONS.md").write_text("khong con so lieu\n", encoding="utf-8")
            claims = ({"file": "OPERATIONS.md", "pattern": r"(\d+) m\u00e3",
                       "values": lambda: ["38"], "what": "ma"},)
            rows = DD.check_claims(claims, d)
        self.assertFalse(rows[0]["ok"])
        self.assertIn("KHONG TIM THAY", rows[0]["note"])

    def test_khoang_cach_sua_bat_loi_go_sai(self):
        self.assertEqual(DD._edit_distance("DATA_STALE", "DATA_STALED"), 1)
        self.assertGreater(DD._edit_distance("DATA_STALE", "RISK_CAP"), 3)

    def test_bien_moi_truong_khong_bi_bao_nham(self):
        """`DATA_TTL_SEC` la ten env trong `config.py` ⇒ KHONG duoc coi la ma ly do sai."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "config.py").write_text('_get("DATA_TTL_SEC", "")\n', encoding="utf-8")
            (d / "OPERATIONS.md").write_text("dat `DATA_TTL_SEC=900`\n", encoding="utf-8")
            rows = DD.check_codes_documented(d, docs=("OPERATIONS.md",))
        self.assertEqual(rows, [])

    def test_report_that_tren_repo_phai_sach(self):
        """Chot chan: repo THAT phai khong co drift (neu co, sua tai lieu chu khong noi nguong)."""
        rep = DD.report()
        self.assertEqual(rep["drift"], [], [r["note"] for r in rep["drift"]])


if __name__ == "__main__":
    unittest.main()

class TestCrewNoiDoi(unittest.TestCase):
    """(13/11, B-053) 3 kieu "hoi dong noi doi" — hoc tu `foreman` (12 indicator).

    Vi sao phai chot: day la nhung loi **khong co log nao noi ra**. B-051 (ten model khong co
    trong goi) va B-052 (gateway Cline 402) deu co dang: `.env` khai 5 model, thuc te 1 model
    bo phieu, va he thong van bao "hoi dong 5 model". Test chot CA HAI CHIEU: khi thieu thi phai
    bao, khi du thi KHONG duoc bao (bao dong = nguoi van hanh bo qua canh bao that).
    """

    NOW = 1_700_000_000.0

    def _st(self, **kw) -> dict:
        base = {"now": self.NOW, "day": "2023-11-14", "heartbeat_age": 30.0,
                "kill_tripped": False, "kill_day": "", "open_positions": 0,
                "entries_paused": False, "learner_n": 0, "learner_refit_ts": 0.0,
                "roster": [], "votes": {}, "votes_wide": {},
                "autonomy_last_ts": self.NOW - 3600.0}
        base.update(kw)
        return base

    def _ids(self, st) -> set:
        return {i["id"] for i in SO.plan(st, gaps=[])}

    def _item(self, st, id_) -> dict:
        return next(i for i in SO.plan(st, gaps=[]) if i["id"] == id_)

    # --- 1. roster drift -----------------------------------------------------
    def test_roster_khai_5_ma_chi_1_phieu_thi_BAO(self):
        st = self._st(roster=["auto", "cline-pass/a", "cline-pass/b"],
                      votes={"auto": {"votes": 3, "attempts": 3, "last_vote_ts": self.NOW}})
        self.assertIn("roster_drift", self._ids(st))
        it = self._item(st, "roster_drift")
        self.assertEqual(it["reason_code"], "COUNCIL_SILENT")
        self.assertEqual(it["evidence"]["active"], ["auto"])
        self.assertEqual(sorted(it["evidence"]["silent"]), ["cline-pass/a", "cline-pass/b"])
        self.assertFalse(it["auto"], "khong tu sua cau hinh hoi dong: phai de nguoi quyet")

    def test_roster_du_phieu_thi_KHONG_bao(self):
        st = self._st(roster=["auto", "cline-pass/a"],
                      votes={"auto": {"votes": 1, "attempts": 1, "last_vote_ts": self.NOW},
                             "cline-pass/a": {"votes": 2, "attempts": 2,
                                              "last_vote_ts": self.NOW}})
        self.assertNotIn("roster_drift", self._ids(st))

    def test_phan_biet_CHUA_GOI_va_GOI_ma_khong_ra_phieu(self):
        """`attempts` > 0 ma `votes` == 0 => provider loi/het credit (B-052), khac 'khong duoc goi'."""
        st = self._st(roster=["auto", "cline-pass/a", "cline-pass/b"],
                      votes={"auto": {"votes": 1, "attempts": 1, "last_vote_ts": self.NOW},
                             "cline-pass/a": {"votes": 0, "attempts": 9, "last_vote_ts": 0}})
        it = self._item(st, "roster_drift")
        self.assertEqual(it["evidence"]["attempted_but_abstained"], ["cline-pass/a"])
        self.assertIn("NO_OPINION", it["why"])



    # --- 2. dormant model ----------------------------------------------------
    def test_model_TUNG_co_phieu_nay_im_thi_bao_dormant(self):
        st = self._st(roster=["auto", "cline-pass/a"],
                      votes={"auto": {"votes": 1, "attempts": 1, "last_vote_ts": self.NOW}},
                      votes_wide={"auto": {"votes": 9, "attempts": 9, "last_vote_ts": self.NOW},
                                  "cline-pass/a": {"votes": 40, "attempts": 44,
                                                   "last_vote_ts": self.NOW - 5 * 86400}})
        self.assertIn("model_dormant", self._ids(st))
        it = self._item(st, "model_dormant")
        self.assertEqual(it["evidence"]["dormant"], ["cline-pass/a"])
        self.assertEqual(it["reason_code"], "MODEL_DORMANT")

    def test_model_chua_bao_gio_co_phieu_thi_KHONG_goi_la_dormant(self):
        """Chua tung co phieu = cau hinh moi (da bao o roster_drift), KHONG duoc dem 2 lan."""
        st = self._st(roster=["auto", "cline-pass/a"],
                      votes={"auto": {"votes": 1, "attempts": 1, "last_vote_ts": self.NOW}},
                      votes_wide={"auto": {"votes": 1, "attempts": 1, "last_vote_ts": self.NOW}})
        self.assertNotIn("model_dormant", self._ids(st))

    # --- 3. routine silent ---------------------------------------------------
    def test_tu_van_hanh_khong_chay_thi_bao(self):
        st = self._st(autonomy_last_ts=0.0)          # chua bao gio chay
        self.assertIn("routine_silent", self._ids(st))
        it = self._item(st, "routine_silent")
        self.assertEqual(it["reason_code"], "ROUTINE_SILENT")
        self.assertIn("chua bao gio", it["why"])

    def test_tu_van_hanh_moi_chay_thi_KHONG_bao(self):
        st = self._st(autonomy_last_ts=self.NOW - 3600.0)
        self.assertNotIn("routine_silent", self._ids(st))

    # --- ham doc du lieu -----------------------------------------------------
    def test_vote_stats_tach_phieu_that_va_lan_goi(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "j.jsonl"
            rows = [
                {"ts": self.NOW - 60, "event": "AGENT", "model": "cline-pass/a",
                 "action": "VETO"},
                {"ts": self.NOW - 120, "event": "AGENT", "model": "cline-pass/a",
                 "action": "NO_OPINION"},
                {"ts": self.NOW - 60, "event": "AGENT", "model": "auto", "action": "ALLOW"},
                {"ts": self.NOW - 60, "event": "OPEN", "model": "cline-pass/a"},
                {"ts": self.NOW - 3 * 86400, "event": "AGENT", "model": "cline-pass/old",
                 "action": "VETO"},
                {"ts": self.NOW - 60, "event": "AGENT", "agent": "critic_agent",
                 "action": "VETO"},
            ]
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n{hong\n", encoding="utf-8")
            st = SO.vote_stats(p, hours=24, now=self.NOW)
        self.assertEqual(st["cline-pass/a"], {"votes": 1, "attempts": 2,
                                              "last_vote_ts": self.NOW - 60})
        self.assertEqual(st["auto"]["votes"], 1)
        self.assertNotIn("cline-pass/old", st)
        self.assertNotIn("critic_agent", st)

    def test_roster_from_env_ap_tien_to_va_loc_skip_ignore_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text(
                "AGENT_COUNCIL_MODELS=auto\n"
                "AGENT_COUNCIL_MODELS_CANDIDATES=grok-4.7,claude-haiku-4.5\n"
                "AGENT_COUNCIL_CLINE=qwen3.8-max,glm-5.3\n"
                "CLINE_SKIP_MODELS=cline-pass/glm-5.3\n"
                "AGENT_COUNCIL_LOCAL=llama3.2-3b-local\n"
                "AGENT_COUNCIL_IGNORE=local/llama3.2-3b-local\n"
                "AGENT_COUNCIL_QWEN=\n", encoding="utf-8")
            got = SO.roster_from_env(p)
        self.assertEqual(sorted(got), ["auto", "cline-pass/qwen3.8-max"])

    def test_state_doc_roster_va_phieu_tu_instance(self):
        """`state(root=...)` phai doc `.env` + journal cua INSTANCE do (LIVE nam thu muc khac)."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "logs").mkdir()
            (base / ".env").write_text("AGENT_COUNCIL_MODELS=auto\n"
                                       "AGENT_COUNCIL_CLINE=a\n", encoding="utf-8")
            (base / "logs" / "journal.jsonl").write_text(json.dumps(
                {"ts": self.NOW - 60, "event": "AGENT", "model": "auto",
                 "action": "ALLOW"}) + "\n", encoding="utf-8")
            st = SO.state(now=self.NOW, root=base)
        self.assertEqual(st["roster"], ["auto", "cline-pass/a"])
        self.assertEqual(st["votes"]["auto"]["votes"], 1)


