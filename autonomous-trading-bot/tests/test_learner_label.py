# -*- coding: utf-8 -*-
"""test_learner_label.py — P0-7: nhan cua learner KHONG duoc phu thuoc huong lenh.

Bug cu: `y = (direction == "LONG") == won` -> SHORT THANG bi gan nhan THUA. Vi demo
co 30/33 lenh SHORT nen learner bi day nguoc hoan toan: setup dang thang bi cham
`edge` am => BLOCKED_LEARN=520 (ke chan so 1). Neu chi nới nguong de co them lenh
thi bot se trade theo NGHICH DAO cua cai da thang.

Chay: python -m unittest tests.test_learner_label -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learner import FEATURES, OnlineLearner                                     # noqa: E402

LEARN_MIN_EDGE = -0.30
FEATS = {f: 1.0 for f in FEATURES}      # moi feature cung huong, rat manh


def fresh(lr: float = 0.1) -> OnlineLearner:
    """Learner trang (w=0, b=0) trong temp dir — khong cham logs/learner.json that."""
    L = OnlineLearner(path=os.path.join(tempfile.mkdtemp(), "l.json"), lr=lr)
    L.w = {f: 0.0 for f in FEATURES}
    L.b = 0.0
    L.n_updates = 0
    return L


class TestNhanLearnerKhongPhuThuocHuongLenh(unittest.TestCase):

    def test_short_thang_phai_TANG_edge_short(self):
        L = fresh()
        before = L.edge(FEATS, "SHORT")
        L.update(FEATS, "SHORT", True)
        self.assertGreater(L.edge(FEATS, "SHORT"), before + 0.05,
                           "SHORT thang ma edge GIAM = nhan bi dao (P0-7)")

    def test_short_thua_phai_GIAM_edge_short(self):
        L = fresh()
        before = L.edge(FEATS, "SHORT")
        L.update(FEATS, "SHORT", False)
        self.assertLess(L.edge(FEATS, "SHORT"), before - 0.05)

    def test_long_thang_phai_TANG_edge_long(self):
        L = fresh()
        before = L.edge(FEATS, "LONG")
        L.update(FEATS, "LONG", True)
        self.assertGreater(L.edge(FEATS, "LONG"), before + 0.05)

    def test_long_thua_phai_GIAM_edge_long(self):
        L = fresh()
        before = L.edge(FEATS, "LONG")
        L.update(FEATS, "LONG", False)
        self.assertLess(L.edge(FEATS, "LONG"), before - 0.05)

    def test_hoc_tu_that_bai_khong_bi_chan_oan(self):
        """Setup thang lap lai -> edge phai vuot LEARN_MIN_EDGE (khong tu chan minh)."""
        L = fresh()
        for _ in range(6):
            L.update(FEATS, "SHORT", True)
        self.assertGreater(L.edge(FEATS, "SHORT"), LEARN_MIN_EDGE)

    def test_doi_xung_long_short(self):
        """Cung mot setup thang: edge LONG va edge SHORT phai bang nhau (doi xung)."""
        a = fresh()
        a.update(FEATS, "LONG", True)
        b = fresh()
        b.update(FEATS, "SHORT", True)
        self.assertAlmostEqual(a.edge(FEATS, "LONG"), b.edge(FEATS, "SHORT"), places=9)

    def test_doi_xung_khi_thua(self):
        a = fresh()
        a.update(FEATS, "LONG", False)
        b = fresh()
        b.update(FEATS, "SHORT", False)
        self.assertAlmostEqual(a.edge(FEATS, "LONG"), b.edge(FEATS, "SHORT"), places=9)

    def test_thang_lien_tuc_thi_edge_duong_va_nguoc_lai(self):
        L = fresh()
        for _ in range(8):
            L.update(FEATS, "SHORT", True)
        self.assertGreater(L.edge(FEATS, "SHORT"), 0.3)
        M = fresh()
        for _ in range(8):
            M.update(FEATS, "SHORT", False)
        self.assertLess(M.edge(FEATS, "SHORT"), -0.3)

    def test_bias_khong_tao_thien_lech_huong(self):
        """b != 0 khong duoc lam lech LONG/SHORT (loi cu: edge dao ket qua)."""
        a = fresh()
        a.b = 1.5                      # bias duong lon, KHONG hoc gi
        self.assertAlmostEqual(a.edge(FEATS, "LONG"), a.edge(FEATS, "SHORT"), places=9)
        self.assertAlmostEqual(a.edge({k: -v for k, v in FEATS.items()}, "LONG"),
                               a.edge(FEATS, "LONG"), places=9)

    def test_predict_luon_trong_0_1(self):
        L = fresh()
        L.w = {f: 50.0 for f in FEATURES}
        L.b = 999.0
        self.assertLessEqual(L.predict(FEATS), 1.0)
        self.assertGreaterEqual(L.predict(FEATS), 0.0)
        L.b = -999.0
        self.assertGreaterEqual(L.predict(FEATS), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
