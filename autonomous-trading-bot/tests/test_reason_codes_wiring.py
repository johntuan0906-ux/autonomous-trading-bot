"""Test phan NOI bang chung: `reason_codes` -> duong GHI (turbo_demo/agents) va
`decision_id` -> phep ghep phieu <-> lenh (`council_evals.pair_cases`).

Vi sao co (09/11, B-045): ca 3 thu nay deu la "lop keo" — neu chung sai thi moi so lieu
ben tren (bang diem model, brier, dem "vi sao bi chan") deu dung tren nen SAI, va khong
ai thay. Test o day chot 4 dieu:
  1. `STATUS_CODES` khong duoc tro toi ma la (go nham 1 chu la bao cao sai im lang);
  2. moi `status` that trong `turbo_demo` deu co ma (khong nhanh nao bi bo sot);
  3. `decision_id` ghep dung cap <-> sai cap (ghep nham con te hon khong ghep);
  4. hieu chuan chi HA confidence, va chi khi mau it.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import agents as A            # noqa: E402
import council_evals as CE    # noqa: E402
import reason_codes as RC     # noqa: E402


def _journal(rows: list) -> str:
    d = tempfile.mkdtemp()
    p = Path(d) / "journal.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")
    return str(p)


class TestStatusMap(unittest.TestCase):
    """Bang status -> ma ly do phai DUNG: day la thu duy nhat gan ma cho vong quet."""

    def test_moi_ma_trong_bang_deu_ton_tai(self):
        bad = {s: c for s, c in RC.STATUS_CODES.items() if not RC.known(c)}
        self.assertEqual(bad, {}, "STATUS_CODES tro toi ma khong co trong CODES")

    def test_status_that_trong_turbo_round_deu_co_ma(self):
        """Doc CHINH ma nguon: moi `"status": "X"` phai co ma."""
        src = (ROOT / "turbo_demo.py").read_text(encoding="utf-8", errors="replace")
        found = set(re.findall(r'"status":\s*"([A-Z_]+)"', src))
        # COUNCIL/SETUP/CLOSED/ERROR la status cua ban ghi AGENT (khong phai ket qua quet)
        skip = {"COUNCIL", "SETUP", "CLOSED", "ERROR"}
        missing = sorted(s for s in found - skip if not RC.code_for_status(s))
        self.assertEqual(missing, [], "status chua duoc gan ma ly do: %s" % missing)

    def test_status_la_khong_nem_loi(self):
        self.assertEqual(RC.code_for_status("KHONG_TON_TAI"), "")
        self.assertEqual(RC.code_for_status(None), "")

    def test_open_la_TAKE(self):
        self.assertEqual(RC.code_for_status("OPENED"), "TAKE")
        self.assertEqual(RC.kind_of(RC.code_for_status("OPENED")), "decision")

    def test_2019_la_order_reject_khong_phai_thieu_du_lieu(self):
        """`-2019 Margin is insufficient` = lenh bi TU CHOI (execution), khong phai data.

        Lop loi that: bo ca `syn-api-ban-none` FAIL vi `insufficient` khop nham
        `DATA_MISSING` (nhom data) ⇒ dem "vi sao bi chan" se thay sai nhom.
        """
        self.assertEqual(RC.classify_text('{"code":-2019,"msg":"Margin is insufficient."}'),
                         "ORDER_REJECT")
        self.assertEqual(RC.kind_of("ORDER_REJECT"), "execution")


class TestDecisionId(unittest.TestCase):
    def test_dinh_dang_va_sap_xep_duoc(self):
        a = RC.new_id("d", ts=1_700_000_000.0)
        b = RC.new_id("d", ts=1_700_000_060.0)
        self.assertRegex(a, r"^d-\d{8}-\d{6}-[0-9a-f]{6}$")
        self.assertLess(a[:17], b[:17], "phai sap duoc theo thoi gian")

    def test_khong_trung_trong_cung_giay(self):
        ids = {RC.new_id("d", ts=1_700_000_000.0) for _ in range(200)}
        self.assertEqual(len(ids), 200)


class TestPairByDecisionId(unittest.TestCase):
    """Ghep phieu <-> lenh: `decision_id` la duong CHINH XAC, cua so thoi gian la du phong."""

    T0 = 1_700_000_000.0

    def _rows(self):
        t0 = self.T0
        return [
            # lenh A: co decision_id, dong SAU 2 gio (ngoai cua so 1h cua phieu)
            {"event": "OPEN", "ts": t0 + 60, "pair": "BTC/USDT:USDT", "direction": "LONG",
             "decision_id": "d-A"},
            {"event": "CLOSE", "ts": t0 + 7200, "pair": "BTC/USDT:USDT", "direction": "LONG",
             "r": 1.5, "won": True, "pnl": 12.0},
            # phieu cua lenh A (bo TRUOC khi vao lenh)
            {"event": "AGENT", "ts": t0, "role": "critic", "status": "COUNCIL",
             "symbol": "BTC/USDT:USDT", "direction": "LONG", "action": "ALLOW",
             "confidence": 0.6, "model": "m1", "decision_id": "d-A"},
            # phieu KHONG co lenh nao (bi chan) -> khong duoc gan bua vao lenh tren
            {"event": "AGENT", "ts": t0 + 10, "role": "arbiter", "status": "COUNCIL",
             "symbol": "BTC/USDT:USDT", "direction": "LONG", "action": "VETO",
             "confidence": 0.9, "model": "m2", "decision_id": "d-B"},
        ]

    def test_ghep_dung_nho_decision_id_ngoai_cua_so(self):
        cases = CE.pair_cases(_journal(self._rows()), window_sec=60)
        by_did = {c["decision_id"]: c for c in cases}
        a = by_did["d-A"]
        self.assertTrue(a["matched_close"], "cung decision_id => phai ghep duoc du lech 2h")
        self.assertEqual(a["match_via"], "decision_id")
        self.assertAlmostEqual(a["outcome"]["r"], 1.5)

    def test_phieu_bi_chan_thi_KHONG_gan_bua_vao_lenh(self):
        cases = CE.pair_cases(_journal(self._rows()), window_sec=60)
        b = next(c for c in cases if c["decision_id"] == "d-B")
        self.assertFalse(b["matched_close"], "phieu khong co lenh KHONG duoc ghep bua")
        self.assertIsNone(b["match_via"])

    def test_cung_lenh_khong_bi_ghep_hai_lan(self):
        cases = CE.pair_cases(_journal(self._rows()), window_sec=7200)
        matched = [c for c in cases if c["matched_close"]]
        self.assertEqual(len(matched), 1, "1 lenh CLOSE chi duoc ghep 1 phieu")

    def test_match_stats_tach_chinh_xac_va_doan(self):
        st = CE.match_stats(CE.pair_cases(_journal(self._rows()), window_sec=60))
        self.assertEqual(st["n"], 2)
        self.assertEqual(st["matched"], 1)
        self.assertEqual(st["via_decision_id"], 1)
        self.assertEqual(st["via_heuristic"], 0)
        self.assertEqual(st["exact_rate"], 1.0)

    def test_ban_ghi_cu_khong_co_decision_id_van_ghep_duoc(self):
        t0 = self.T0
        rows = [
            {"event": "AGENT", "ts": t0, "role": "critic", "status": "SETUP",
             "symbol": "ETH/USDT:USDT", "direction": "SHORT", "action": "ALLOW",
             "confidence": 0.5, "model": "m1"},
            {"event": "CLOSE", "ts": t0 + 300, "pair": "ETH/USDT:USDT",
             "direction": "SHORT", "r": -1.0, "won": False},
        ]
        cases = CE.pair_cases(_journal(rows), window_sec=3600)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["match_via"], "heuristic")
        self.assertTrue(cases[0]["matched_close"])


class TestCalibration(unittest.TestCase):
    """Hieu chuan: `brier 0.341` nghia la hoi dong QUA TU TIN — phai bi chan bang code."""

    def test_dem_mau_bang_chung_tu_lessons_hint(self):
        pay = {"lessons_hint": ["A|B|UP|LONG n=42 avgR=-0.312 WR=38%",
                                "C|D|DOWN|SHORT n=7 avgR=-0.1 WR=45%"]}
        self.assertEqual(A.evidence_n(pay), 42)
        self.assertEqual(A.evidence_n({}), 0)
        self.assertEqual(A.evidence_n({"lessons_hint": ["khong co so"]}), 0)

    def test_ha_tran_khi_mau_it(self):
        self.assertEqual(A.cap_confidence(0.83, 5), 0.7)
        self.assertEqual(A.cap_confidence(0.55, 5), 0.55, "khong duoc TANG")
        self.assertEqual(A.cap_confidence(0.83, 50), 0.83, "du mau thi giu nguyen")
        self.assertEqual(A.cap_confidence(0.83, 20), 0.83, "n = nguong la du")

    def test_ngoai_dai_gia_tri(self):
        self.assertEqual(A.cap_confidence(-1, 100), 0.0)
        self.assertEqual(A.cap_confidence(5, 100), 1.0)
        self.assertEqual(A.cap_confidence("rac", 100), 0.0)

    def test_prompt_co_cau_lenh_hieu_chuan(self):
        _sys, user = A.build_prompt("critic", {"symbol": "BTC/USDT:USDT"})
        self.assertIn("HIEU CHUAN", user)
        self.assertIn("confidence <= 0.7", user)


class TestVoteLogsReasonCode(unittest.TestCase):
    """Phieu phai tu mang `reason_code` + `decision_id` — neu khong thi khong dem duoc gi."""

    def _layer(self, jp: str):
        class _Cfg:
            agents_enabled = True
        return A.AgentLayer(_Cfg(), provider=A.StubProvider(_Cfg()), journal=jp)

    def _last(self, jp: str) -> dict:
        return json.loads(Path(jp).read_text(encoding="utf-8").strip().splitlines()[-1])

    def test_log_decision_tu_suy_ma_tu_van_ban(self):
        with tempfile.TemporaryDirectory() as td:
            jp = str(Path(td) / "j.jsonl")
            layer = self._layer(jp)
            d = A.Decision(role="critic", agent="critic_agent", action="VETO",
                           confidence=0.6, reasons=["tran risk danh muc 1.6%"],
                           note="parse=ok")
            layer.log_decision(d, extra={"symbol": "BTC/USDT:USDT", "status": "SETUP"})
            self.assertEqual(self._last(jp)["reason_code"], "RISK_CAP")

    def test_extra_thang_van_ban(self):
        with tempfile.TemporaryDirectory() as td:
            jp = str(Path(td) / "j.jsonl")
            layer = self._layer(jp)
            d = A.Decision(role="critic", agent="critic_agent", action="ALLOW",
                           confidence=0.4, reasons=["binh thuong"], note="parse=ok")
            layer.log_decision(d, extra={"symbol": "X", "status": "SETUP",
                                         "decision_id": "d-1", "reason_code": "AGENT_VETO"})
            rec = self._last(jp)
            self.assertEqual(rec["reason_code"], "AGENT_VETO")
            self.assertEqual(rec["decision_id"], "d-1")


if __name__ == "__main__":
    unittest.main()


