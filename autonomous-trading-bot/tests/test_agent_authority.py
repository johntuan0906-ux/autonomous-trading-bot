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


if __name__ == "__main__":
    unittest.main()
