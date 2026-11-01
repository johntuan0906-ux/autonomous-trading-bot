# -*- coding: utf-8 -*-
"""(01/11) Cong NANG hoi dong tu SHADOW len VETO THAT — quyet dinh nguoi van hanh #4:
"khi nao du dieu kien hay lam that". Cong phai do bang SO, khong cam tinh.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import council_eval as CE        # noqa: E402


def _rep(rows, brier=0.18, cases=100):
    return {"cases": cases, "calibration": {"brier": brier},
            "per_model": {m: dict(v) for m, v in rows.items()}}


class TestCongNangHoiDong(unittest.TestCase):
    def test_du_dieu_kien(self):
        r = CE.readiness(_rep({"claude-sonnet-5.5": {"matched": 40, "value_r": 0.099}}),
                         min_n=30)
        self.assertTrue(r["ready"], r["reasons"])
        self.assertEqual(r["models_ok"], ["claude-sonnet-5.5"])

    def test_value_r_am_thi_CHUA_du(self):
        r = CE.readiness(_rep({"local/llama3.2-3b-local": {"matched": 36,
                                                           "value_r": -1.303}}), min_n=30)
        self.assertFalse(r["ready"])
        self.assertTrue(any("value_r" in x for x in r["reasons"]), r["reasons"])

    def test_brier_qua_tu_tin_thi_CHUA_du(self):
        r = CE.readiness(_rep({"m": {"matched": 40, "value_r": 0.2}}, brier=0.302), min_n=30)
        self.assertFalse(r["ready"])
        self.assertTrue(any("brier" in x for x in r["reasons"]), r["reasons"])

    def test_chua_du_mau_thi_CHUA_du(self):
        r = CE.readiness(_rep({"m": {"matched": 7, "value_r": 0.5}}, cases=7), min_n=30)
        self.assertFalse(r["ready"])
        self.assertEqual(r["models_ok"], [])
        self.assertTrue(any("ghep duoc" in x for x in r["reasons"]), r["reasons"])

    def test_thieu_calibration_thi_CHUA_du(self):
        r = CE.readiness({"cases": 100, "per_model": {}}, min_n=30)
        self.assertFalse(r["ready"])
        self.assertTrue(any("calibration" in x for x in r["reasons"]), r["reasons"])
