# -*- coding: utf-8 -*-
"""test_council_evals.py — shadow A/B + eval dataset tu journal (08/10/2026).

Bao phu ca CLI `tools/council_eval.py` (bang diem model: value_r / veto_precision / Brier) —
`tools/capabilities.py` tim test theo TEN tool nen can dong nay de manifest khong bao thieu.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from council_evals import build_eval_dataset, council_ab_report, pair_cases  # noqa: E402
import council_evals as CE                                                     # noqa: E402


def _journal(path: str, with_trade: bool = True) -> str:
    rows = []
    t0 = 1_700_000_000.0
    # VETO -> lenh di theo sau do THUA (veto dung)
    rows.append({"event": "AGENT", "ts": t0, "role": "critic", "status": "SETUP",
                 "symbol": "SOL/USDT:USDT", "direction": "SHORT", "action": "VETO",
                 "confidence": 0.8, "provider": "copilot_cli", "model": "kimi-k3",
                 "alpha": 0.12, "rsi": 22.0})
    if with_trade:
        rows.append({"event": "CLOSE", "ts": t0 + 300, "pair": "SOL/USDT:USDT",
                     "direction": "SHORT", "r": -1.0, "won": False, "pnl": -5.0})
    # ALLOW -> lenh di theo sau do THANG
    rows.append({"event": "AGENT", "ts": t0 + 600, "role": "arbiter", "status": "COUNCIL",
                 "symbol": "BTC/USDT:USDT", "direction": "LONG", "action": "ALLOW",
                 "confidence": 0.6, "provider": "cline", "model": "cline-pass/kimi-k3",
                 "alpha": 0.3})
    if with_trade:
        rows.append({"event": "CLOSE", "ts": t0 + 900, "pair": "BTC/USDT:USDT",
                     "direction": "LONG", "r": 1.2, "won": True, "pnl": 6.0})
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


class TestPairCases(unittest.TestCase):
    def test_ghep_dung_close_sau_quyet_dinh(self):
        jp = _journal(os.path.join(tempfile.mkdtemp(), "j.jsonl"))
        cases = pair_cases(jp, window_sec=3600)
        self.assertEqual(len(cases), 2)
        veto = next(c for c in cases if c["action"] == "VETO")
        allow = next(c for c in cases if c["action"] == "ALLOW")
        self.assertTrue(veto["matched_close"])
        self.assertFalse(veto["outcome"]["won"])
        self.assertTrue(allow["outcome"]["won"])
        self.assertIn("alpha", veto["features"])
        self.assertEqual(veto["features"]["rsi"], 22.0)

    def test_bo_phieu_hau_kiem_khoi_bang_diem(self):
        """(15/10) Phieu HAU KIEM (review sau khi dong lenh) biet ket qua roi -> neu tinh
        vao `value_r` thi thien lech nhin truoc. Do that: bang diem cu co dong
        `claude-sonnet-5.5` (+0.044) — do chinh la model cua agent review.
        """
        jp = os.path.join(tempfile.mkdtemp(), "j.jsonl")
        t0 = 1_700_000_000.0
        rows = [
            {"event": "AGENT", "ts": t0, "role": "critic", "status": "COUNCIL",
             "agent": "critic_agent", "symbol": "SOL/USDT:USDT", "direction": "SHORT",
             "action": "VETO", "confidence": 0.8, "provider": "cline",
             "model": "cline-pass/mimo-v2.6-pro"},
            {"event": "CLOSE", "ts": t0 + 300, "pair": "SOL/USDT:USDT",
             "direction": "SHORT", "r": -1.0, "won": False},
            # phieu HAU KIEM: agent review bo phieu SAU khi lenh da dong (status CLOSED)
            {"event": "AGENT", "ts": t0 + 400, "role": "review", "status": "CLOSED",
             "agent": "review_agent", "symbol": "SOL/USDT:USDT", "direction": "SHORT",
             "action": "ALLOW", "confidence": 0.9, "provider": "cline",
             "model": "claude-sonnet-5.5"},
        ]
        with open(jp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cases = pair_cases(jp, window_sec=3600)
        models = [c["model"] for c in cases]
        self.assertIn("cline-pass/mimo-v2.6-pro", models)
        self.assertNotIn("claude-sonnet-5.5", models,
                         "phieu hau kiem phai bi loai (thien lech nhin truoc)")
        self.assertFalse(CE.is_pre_trade({"role": "review", "status": "CLOSED"}))
        self.assertFalse(CE.is_pre_trade({"role": "review_agent"}))
        self.assertTrue(CE.is_pre_trade({"role": "critic", "status": "COUNCIL"}))

    def test_khong_ghep_khi_ngoai_cua_so(self):
        jp = _journal(os.path.join(tempfile.mkdtemp(), "j.jsonl"))
        cases = pair_cases(jp, window_sec=60)   # close cach 300s/900s > 60s
        self.assertTrue(all(not c["matched_close"] for c in cases))

    def test_bo_qua_ban_ghi_hong(self):
        tmp = tempfile.mkdtemp()
        jp = os.path.join(tmp, "j.jsonl")
        _journal(jp)
        with open(jp, "a", encoding="utf-8") as f:
            f.write("{khong phai json\n")
        self.assertEqual(len(pair_cases(jp)), 2)


class TestAbReport(unittest.TestCase):
    def test_bao_cao_veto_vs_allow(self):
        jp = _journal(os.path.join(tempfile.mkdtemp(), "j.jsonl"))
        rep = council_ab_report(jp, window_sec=3600)
        self.assertEqual(rep["veto"]["n"], 1)
        self.assertEqual(rep["allow"]["n"], 1)
        self.assertEqual(rep["veto"]["wr"], 0.0)
        self.assertEqual(rep["allow"]["wr"], 1.0)
        self.assertEqual(rep["veto_precision"], 1.0)  # veto dung: lenh di theo thua



class TestModelLeaderboard(unittest.TestCase):
    """(14/10) Eval theo TUNG MODEL: model nao bo phieu DUNG (y tuong phase G)."""

    def _j(self, rows) -> str:
        p = os.path.join(tempfile.mkdtemp(), "j.jsonl")
        with open(p, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return p

    def _vote(self, ts, model, action, symbol, conf=0.7):
        return {"event": "AGENT", "ts": ts, "role": "critic", "status": "COUNCIL",
                "symbol": symbol, "direction": "LONG", "action": action,
                "confidence": conf, "provider": "cline", "model": model}

    def _close(self, ts, symbol, r):
        return {"event": "CLOSE", "ts": ts, "pair": symbol, "direction": "LONG",
                "r": r, "won": r > 0, "pnl": r * 10}

    def test_model_phan_biet_duoc_thi_GIU(self):
        """model A: ALLOW -> thang, VETO -> thua  => value_r > 0 => GIU."""
        t0 = 1_700_000_000.0
        rows = []
        for i in range(6):
            s = "A%d/USDT:USDT" % i
            rows += [self._vote(t0 + i * 10, "model-good", "ALLOW", s),
                     self._close(t0 + i * 10 + 5, s, 1.0)]
        for i in range(6):
            s = "B%d/USDT:USDT" % i
            rows += [self._vote(t0 + 100 + i * 10, "model-good", "VETO", s),
                     self._close(t0 + 100 + i * 10 + 5, s, -1.0)]
        rep = CE.model_leaderboard(self._j(rows), min_n=8)
        row = rep["per_model"]["model-good"]
        self.assertEqual(row["matched"], 12)
        self.assertAlmostEqual(row["value_r"], 2.0, places=3)   # +1.0 - (-1.0)
        self.assertEqual(row["veto_precision"], 1.0)
        self.assertIn("model-good", rep["keep"])
        self.assertEqual(rep["drop"], [])

    def test_model_khong_phan_biet_duoc_thi_NEN_BO(self):
        """model B: ALLOW -> thua, VETO -> thang  => value_r < 0 => NEN BO + dong .env."""
        t0 = 1_700_000_000.0
        rows = []
        for i in range(6):
            s = "C%d/USDT:USDT" % i
            rows += [self._vote(t0 + i * 10, "cline-pass/bad-model", "ALLOW", s),
                     self._close(t0 + i * 10 + 5, s, -1.0)]
        for i in range(6):
            s = "D%d/USDT:USDT" % i
            rows += [self._vote(t0 + 100 + i * 10, "cline-pass/bad-model", "VETO", s),
                     self._close(t0 + 100 + i * 10 + 5, s, 1.0)]
        rep = CE.model_leaderboard(self._j(rows), min_n=8)
        self.assertIn("cline-pass/bad-model", rep["drop"])
        self.assertEqual(rep["keep"], [])
        self.assertTrue(any(ln.startswith("CLINE_SKIP_MODELS=") and "bad-model" in ln
                            for ln in rep["skip_lines"]))

    def test_chua_du_mau_thi_KHONG_ket_luan(self):
        t0 = 1_700_000_000.0
        rows = [self._vote(t0, "moi-qua", "VETO", "E/USDT:USDT"),
                self._close(t0 + 5, "E/USDT:USDT", -1.0)]
        rep = CE.model_leaderboard(self._j(rows), min_n=8)
        self.assertEqual(rep["keep"], [])
        self.assertEqual(rep["drop"], [])
        self.assertIn("moi-qua", rep["thin"])

    def test_vai_khong_bi_de_xuat_bo(self):
        """`critic_agent` la VAI, khong phai model -> khong duoc vao dong skip."""
        t0 = 1_700_000_000.0
        rows = []
        for i in range(6):
            s = "F%d/USDT:USDT" % i
            rows += [{"event": "AGENT", "ts": t0 + i * 10, "role": "critic",
                      "status": "COUNCIL", "symbol": s, "direction": "LONG",
                      "action": "ALLOW", "confidence": 0.6, "provider": "copilot_cli",
                      "agent": "critic_agent", "model": "critic_agent"},
                     self._close(t0 + i * 10 + 5, s, -1.0)]
        for i in range(6):
            s = "G%d/USDT:USDT" % i
            rows += [{"event": "AGENT", "ts": t0 + 100 + i * 10, "role": "critic",
                      "status": "COUNCIL", "symbol": s, "direction": "LONG",
                      "action": "VETO", "confidence": 0.6, "provider": "copilot_cli",
                      "agent": "critic_agent", "model": "critic_agent"},
                     self._close(t0 + 100 + i * 10 + 5, s, 1.0)]
        rep = CE.model_leaderboard(self._j(rows), min_n=8)
        self.assertEqual(rep["skip_lines"], [], "khong duoc de xuat bo mot VAI")

    def test_calibration_brier_va_bins(self):
        t0 = 1_700_000_000.0
        rows = []
        for i in range(4):          # conf 0.9 -> thang het
            s = "H%d/USDT:USDT" % i
            rows += [self._vote(t0 + i * 10, "m", "ALLOW", s, conf=0.9),
                     self._close(t0 + i * 10 + 5, s, 1.0)]
        for i in range(4):          # conf 0.1 -> thua het
            s = "I%d/USDT:USDT" % i
            rows += [self._vote(t0 + 100 + i * 10, "m", "ALLOW", s, conf=0.1),
                     self._close(t0 + 100 + i * 10 + 5, s, -1.0)]
        cal = CE.calibration(CE.pair_cases(self._j(rows)))
        self.assertEqual(cal["n"], 8)
        self.assertAlmostEqual(cal["brier"], 0.01, places=3)     # (0.1)^2 trung binh
        self.assertTrue(any(b["n"] == 4 and b["win_rate"] == 1.0 for b in cal["bins"]))

    def test_ngoai_cua_so_hours_thi_bo(self):
        t0 = 1_700_000_000.0
        rows = [self._vote(t0, "cu", "ALLOW", "J/USDT:USDT"),
                self._close(t0 + 5, "J/USDT:USDT", 1.0)]
        rep = CE.model_leaderboard(self._j(rows), hours=1.0, now=t0 + 10 * 3600)
        self.assertEqual(rep["cases"], 0)

    def test_bao_cao_rong_khi_journal_trong(self):
        rep = council_ab_report(os.path.join(tempfile.mkdtemp(), "ko-co.jsonl"))
        self.assertEqual(rep["cases"], 0)
        self.assertIsNone(rep["veto"]["wr"])
        self.assertIsNone(rep["veto_precision"])


class TestEvalDataset(unittest.TestCase):
    def test_xuat_jsonl(self):
        tmp = tempfile.mkdtemp()
        jp = _journal(os.path.join(tmp, "j.jsonl"))
        out = os.path.join(tmp, "eval.jsonl")
        n = build_eval_dataset(jp, out)
        self.assertEqual(n, 2)
        with open(out, encoding="utf-8") as f:
            rows = [json.loads(ln) for ln in f]
        self.assertEqual(rows[0]["action"], "VETO")
        self.assertIn("outcome", rows[0])


if __name__ == "__main__":
    unittest.main()