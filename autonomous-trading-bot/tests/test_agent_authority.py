"""Test luat cap quyen VETO (13/10): two_cohort (cu) vs baseline + chot chan NGUOC DAU.

Boi canh that: hoi dong tra **878 NO_OPINION** nhung chi **1 ALLOW** ⇒ luat cu
(`n_allow>=10`) la cho vo dinh. Do that 13/10 bang luat baseline:
  SETUP  : n_veto=57 avgR=+0.0210 vs baseline +0.0330 → gap +0.012 (khong phan biet)
  COUNCIL: n_veto=33 avgR=+0.0717 vs baseline -0.0050 → gap -0.077 (NGUOC DAU)
⇒ Ket luan: KHONG cap quyen veto cho ca 2 nguon.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agents as AG      # noqa: E402


def _rec(ev, **kw) -> str:
    return json.dumps({"event": ev, **kw}, ensure_ascii=False)


def _journal(rows) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "journal.jsonl"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p


def _case(n_veto: int, r_veto: float, n_allow: int, r_allow: float,
          n_noop: int = 0, r_noop: float = 0.0) -> Path:
    """Journal gia: moi phan tu = 1 ban ghi AGENT + 1 lenh CLOSE ngay sau do."""
    rows: list = []
    ts = 1000.0
    def add(status: str, act: str, n: int, r: float) -> None:
        nonlocal ts
        for i in range(n):
            sym = "S%d/USDT:USDT" % (len(rows) + i)
            ts += 1.0
            rows.append(_rec("AGENT", status=status, action=act, symbol=sym,
                             direction="LONG", ts=ts))
            rows.append(_rec("CLOSE", pair=sym, direction="LONG", r=r, pnl=r * 10,
                             won=r > 0, ts=ts + 1.0))
    add("COUNCIL", "VETO", n_veto, r_veto)
    add("COUNCIL", "ALLOW", n_allow, r_allow)
    if n_noop:
        add("COUNCIL", "NO_OPINION", n_noop, r_noop)
    return _journal(rows)


class TestLuatTwoCohort(unittest.TestCase):
    def test_du_ca_2_nhom_thi_cap_quyen(self):
        p = _case(n_veto=12, r_veto=-1.0, n_allow=12, r_allow=+1.0)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="two_cohort",
                               min_n=10, min_n_allow=10, min_gap=0.15)
        self.assertTrue(a["granted"])
        self.assertEqual(a["veto_n"], 12)
        self.assertEqual(a["allow_n"], 12)

    def test_thieu_nhom_allow_thi_KHONG_cap_quyen(self):
        """Chinh la truong hop that 13/10: n_allow=1."""
        p = _case(n_veto=33, r_veto=+0.07, n_allow=1, r_allow=+0.25)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="two_cohort")
        self.assertFalse(a["granted"], "n_allow=1 khong du de so sanh")
        self.assertIn("n_allow", a["reason"])

    def test_veto_tot_hon_allow_thi_khong_cap(self):
        p = _case(n_veto=12, r_veto=+1.0, n_allow=12, r_allow=-1.0)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="two_cohort")
        self.assertFalse(a["granted"], "gap am = veto nguoc dau -> khong cap quyen")


class TestLuatBaseline(unittest.TestCase):
    """Veto chi CHAN lenh ⇒ chi can so sanh voi baseline, khong can nhom ALLOW."""

    def test_baseline_du_mau_va_veto_te_hon_thi_cap_quyen(self):
        p = _case(n_veto=12, r_veto=-1.0, n_allow=0, r_allow=0.0, n_noop=40, r_noop=+0.5)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="baseline",
                               min_n=10, min_gap=0.15, baseline_min_n=30)
        self.assertTrue(a["granted"], "veto -1R te hon ro ret so voi baseline +0.5R")
        self.assertEqual(a["baseline_n"], 52)
        self.assertGreater(a["gap_vs_baseline"], 0,
                           "gap = baseline - VETO > 0 nghia la VETO TE HON -> duoc cap quyen")

    def test_baseline_veto_NGUOC_DAU_thi_khong_cap_quyen(self):
        """Dung so that 13/10: veto +0.0717 vs baseline -0.0050."""
        p = _case(n_veto=33, r_veto=+0.0717, n_allow=0, r_allow=0.0,
                  n_noop=523, r_noop=-0.0099)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="baseline",
                               min_n=10, min_gap=0.15, baseline_min_n=30)
        self.assertFalse(a["granted"])
        self.assertLess(a["gap_vs_baseline"], 0,
                        "gap am = nhom bi veto TOT HON baseline -> chan nham, KHONG cap quyen")

    def test_baseline_thieu_mau_thi_khong_cap_quyen(self):
        p = _case(n_veto=12, r_veto=-1.0, n_allow=0, r_allow=0.0, n_noop=3, r_noop=+0.5)
        a = AG.agent_authority(str(p), status="COUNCIL", rule="baseline",
                               min_n=10, baseline_min_n=30)
        self.assertFalse(a["granted"])

    def test_mac_dinh_giu_hanh_vi_cu(self):
        """Khong truyen `rule` -> two_cohort (de khong doi hanh vi ngoai y muon)."""
        p = _case(n_veto=12, r_veto=-1.0, n_allow=0, r_allow=0.0, n_noop=40, r_noop=+0.5)
        a = AG.agent_authority(str(p), status="COUNCIL", min_n=10, min_gap=0.15)
        self.assertEqual(a["rule"], "two_cohort")
        self.assertFalse(a["granted"], "thieu n_allow -> luat cu khong cap quyen")

    def test_tra_du_truong_cho_bot_kiem_tra(self):
        p = _case(n_veto=12, r_veto=-1.0, n_allow=2, r_allow=+1.0, n_noop=30, r_noop=+0.2)
        a = AG.agent_authority(str(p), status="COUNCIL", min_n=10)
        for k in ("granted", "veto_n", "veto_avg_r", "allow_n", "allow_avg_r",
                  "baseline_n", "baseline_avg_r", "gap_vs_baseline", "rule"):
            self.assertIn(k, a, "thieu truong %s -> bot khong kiem tra duoc" % k)


class TestJournalLoi(unittest.TestCase):
    def test_journal_khong_ton_tai(self):
        a = AG.agent_authority(str(Path("khong/co.jsonl")), status="COUNCIL")
        self.assertFalse(a["granted"])


class TestChotChanNguocDauTrongBot(unittest.TestCase):
    """(13/10) Du `granted=True` (luat two_cohort), neu gap_vs_baseline <= 0 thi
    KHONG duoc chan lenh — vi veto dang chan nham lenh tot (so that COUNCIL)."""

    class Cfg:
        agents_veto_enabled = True
        agents_veto_source = "COUNCIL"

    def _veto(self, auth: dict, layer=None):
        import turbo_demo as TD
        from unittest import mock
        TD._AGENT_AUTH["res"] = auth          # bom ket qua authority
        TD._AGENT_AUTH["ts"] = 1e18           # con han cache
        try:
            with mock.patch.object(TD, "agent_layer",
                                   lambda cfg: layer or object()):
                return TD.agent_veto(self.Cfg(), "X/USDT:USDT", "LONG", 0.5, "S1",
                                     {}, None, "UPTREND")
        finally:
            TD._AGENT_AUTH["res"] = None

    def test_gap_am_thi_khong_chan(self):
        out = self._veto({"granted": True, "reason": "x", "gap_vs_baseline": -0.077,
                          "veto_avg_r": 0.0717, "baseline_avg_r": -0.005})
        self.assertFalse(out["block"])
        self.assertIn("nguoc dau", out["reason"])

    def test_thieu_truong_gap_thi_khong_bi_chan_oan(self):
        """Tuong thich: dict authority cu (khong co gap_vs_baseline) khong bi chan oan."""
        out = self._veto({"granted": True, "reason": "x"})
        self.assertFalse(out["block"])
        self.assertNotIn("nguoc dau", out["reason"])


class TestCouncilHealth(unittest.TestCase):
    """(13/10) Do that 48h: 328 ban ghi AGENT, **0 VETO/0 ALLOW** — hoi dong im lang.

    Nguyen nhan: `cline-pass/mimo-v2.6-flash` treo 144/144 (45% tong so treo) + cac
    ban ghi review dung provider Copilot het quota. Cong cu nay lam viec do LAP LAI duoc.
    """

    NOW = 1_800_000_000.0

    def _j(self, rows) -> Path:
        d = tempfile.mkdtemp()
        p = Path(d) / "journal.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return p

    def _rec(self, agent, action, *, abstained=False, ts=None, status="COUNCIL",
             model=None, note=""):
        return {"event": "AGENT", "agent": agent, "model": model or agent,
                "action": action, "abstained": abstained, "status": status,
                "note": note, "ts": self.NOW - 3600 if ts is None else ts}

    def test_phat_hien_model_treo_va_de_xuat_bo(self):
        rows = ([self._rec("cline-pass/dead", "NO_OPINION", abstained=True,
                           note="treo/loi/het gio") for _ in range(10)]
                + [self._rec("cline-pass/good", "VETO") for _ in range(3)])
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW)
        self.assertEqual(h["records"], 13)
        self.assertIn("cline-pass/dead", h["dead"])
        self.assertIn("cline-pass/good", h["live"])
        self.assertNotIn("cline-pass/good", h["dead"])
        self.assertTrue(any("CLINE_SKIP_MODELS" in ln and "cline-pass/dead" in ln
                            for ln in h["skip_lines"]))

    def test_bo_qua_ban_ghi_ngoai_cua_so(self):
        rows = [self._rec("old", "NO_OPINION", abstained=True, ts=self.NOW - 100 * 3600)
                for _ in range(10)]
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW)
        self.assertEqual(h["records"], 0)
        self.assertEqual(h["dead"], [])

    def test_nhom_theo_agent_khong_theo_model(self):
        """Ban ghi review co model=<model mac dinh cua provider> nhung agent=review_agent."""
        rows = [self._rec("review_agent", "NO_OPINION", abstained=True,
                          model="claude-sonnet-5.5", status="CLOSED")
                for _ in range(10)]
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW)
        self.assertIn("review_agent", h["per_model"])
        self.assertNotIn("claude-sonnet-5.5", h["per_model"])

    def test_model_local_vao_dong_LOCAL_SKIP(self):
        rows = [self._rec("local/llama3.2:3b", "NO_OPINION", abstained=True)
                for _ in range(9)]
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW)
        self.assertTrue(any(ln.startswith("LOCAL_SKIP_MODELS=") for ln in h["skip_lines"]))

    def test_chi_bao_treo_khi_du_mau(self):
        rows = [self._rec("moi-xuat-hien", "NO_OPINION", abstained=True) for _ in range(2)]
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW, min_n=8)
        self.assertEqual(h["dead"], [], "2 mau chua du de ket luan")

    def test_khong_de_xuat_bo_VAI_agent(self):
        """(13/10) `review_agent` la VAI (provider chet), khong phai model -> de xuat
        `CLINE_SKIP_MODELS=review_agent` la SAI (nguoi van hanh dien rac vao .env)."""
        rows = [self._rec("review_agent", "NO_OPINION", abstained=True,
                          model="claude-sonnet-5.5", status="CLOSED")
                for _ in range(10)]
        h = AG.council_health(str(self._j(rows)), hours=48, now=self.NOW)
        self.assertIn("review_agent", h["dead"], "van bao no la muc treo")
        joined = " ".join(h["skip_lines"])
        self.assertNotIn("review_agent", joined, "nhung KHONG duoc de xuat bo vao .env")

    def test_file_khong_ton_tai(self):
        h = AG.council_health(str(Path("khong/co.jsonl")), now=self.NOW)
        self.assertEqual(h["records"], 0)


class TestCauDaoTheoProvider(unittest.TestCase):
    """(13/10) LOI THAT: 5 loi lien tiep tu Copilot (het quota thang) da `disable`
    CA FILE state -> moi provider (cline-pass mien phi, local) bi chan suot ngay =>
    hoi dong im lang hoan toan (do 48h: 328 ban ghi AGENT, 0 VETO/0 ALLOW)."""

    def _b(self, tmp: str, max_errors: int = 3):
        return AG.AgentBudget(path=Path(tmp) / "agent_state.json",
                              daily_calls=1000, daily_budget_usd=100.0,
                              max_errors=max_errors)

    def test_loi_cua_mot_provider_khong_tat_cac_provider_khac(self):
        with tempfile.TemporaryDirectory() as d:
            b = self._b(d, max_errors=3)
            for _ in range(3):
                b.note(ok=False, reason="quota", provider="copilot")
            self.assertTrue(b.provider_disabled("copilot"), "copilot phai bi tat")
            self.assertEqual(b.disabled(), "", "KHONG duoc tat toan cuc")
            ok_c, why_c = b.can_spend(provider="copilot")
            self.assertFalse(ok_c)
            self.assertIn("copilot", why_c)
            ok_k, _ = b.can_spend(provider="cline")
            self.assertTrue(ok_k, "provider khac VAN phai goi duoc")
            ok_l, _ = b.can_spend(provider="local")
            self.assertTrue(ok_l, "local (mien phi) VAN phai goi duoc")

    def test_thanh_cong_thi_xoa_dem_loi_cua_provider(self):
        with tempfile.TemporaryDirectory() as d:
            b = self._b(d, max_errors=3)
            b.note(ok=False, reason="x", provider="cline")
            b.note(ok=False, reason="x", provider="cline")
            b.note(ok=True, provider="cline")
            b.note(ok=False, reason="x", provider="cline")
            self.assertEqual(b.provider_disabled("cline"), "",
                             "thanh cong phai reset dem loi cua provider")

    def test_loi_KHONG_co_provider_van_tat_toan_cuc(self):
        with tempfile.TemporaryDirectory() as d:
            b = self._b(d, max_errors=2)
            b.note(ok=False, reason="loi noi bo")
            b.note(ok=False, reason="loi noi bo")
            self.assertTrue(b.disabled(), "loi noi bo (khong ro provider) van fail-closed")
            self.assertFalse(b.can_spend(provider="cline")[0])

    def test_enable_go_ca_toan_cuc_lan_theo_provider(self):
        with tempfile.TemporaryDirectory() as d:
            b = self._b(d, max_errors=1)
            b.note(ok=False, reason="quota", provider="copilot")
            b.note(ok=False, reason="x")
            b.enable()
            self.assertEqual(b.disabled(), "")
            self.assertEqual(b.provider_disabled("copilot"), "",
                             "enable phai xoa ca disabled theo provider")


if __name__ == "__main__":
    unittest.main()
