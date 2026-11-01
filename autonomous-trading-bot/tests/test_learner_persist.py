# -*- coding: utf-8 -*-
"""(01/11) B-034: `learner.json` phai GIU khoa LA (khoi `refit`) khi bot hoc online.

Do that: sau khi `tools/learner_refit.py --write` ghi model DA KIEM DINH holdout, chi vai gio
sau TESTNET co `n=736`, `w≠0` nhung **`refit: null`** — vi `OnlineLearner.save()` ghi lai
dung `w/b/n/ts`. Mat dau vet ⇒ khong con cach biet model dang chay co phai model da kiem dinh
⇒ moi ket luan ve learner deu khong co nguon goc.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import learner as L        # noqa: E402

REFIT = {"neutral": False, "holdout": 0.2, "logloss_model": 0.6885,
         "logloss_base": 0.6940, "target": "testnet"}


class TestGiuKhoaLa(unittest.TestCase):
    def _f(self, tmp: str) -> Path:
        return Path(tmp) / "learner.json"

    def test_hoc_online_KHONG_xoa_khoi_refit(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._f(d)
            p.write_text(json.dumps({"w": {}, "b": 0.5, "n": 10, "ts": 1.0, "refit": REFIT}),
                         encoding="utf-8")
            lr = L.OnlineLearner(path=str(p))
            self.assertEqual(lr._extra.get("refit"), REFIT, "phai doc duoc khoi refit")
            lr.update({f: 0.0 for f in L.FEATURES}, "LONG", True)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertIn("refit", saved, "B-034: hoc online KHONG duoc xoa khoi refit")
            self.assertEqual(saved["refit"]["logloss_model"], 0.6885)
            self.assertEqual(saved["n"], 11, "van phai ghi n binh thuong")

    def test_learner_moi_thi_khong_co_khoa_la(self):
        with tempfile.TemporaryDirectory() as d:
            lr = L.OnlineLearner(path=str(self._f(d)))
            self.assertEqual(lr._extra, {})
            lr.update({f: 0.0 for f in L.FEATURES}, "SHORT", False)
            saved = json.loads(self._f(d).read_text(encoding="utf-8"))
            self.assertEqual(sorted(saved.keys()), ["b", "n", "ts", "w"])
