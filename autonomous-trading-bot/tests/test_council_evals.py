# -*- coding: utf-8 -*-
"""test_council_evals.py — shadow A/B + eval dataset tu journal (08/10/2026)."""
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