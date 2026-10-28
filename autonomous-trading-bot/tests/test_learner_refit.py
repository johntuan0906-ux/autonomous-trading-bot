# -*- coding: utf-8 -*-
"""Test `tools/learner_refit.py` — dựng lại learner bằng FIT OFFLINE + kiểm định holdout.

Vì sao (28/10, hội đồng 4 ALLOW / 0 VETO): learner online (SGD) **đúng công thức** nhưng chạy trên
chuỗi KHÔNG DỪNG ⇒ trọng số bị chi phối bởi ~100 lệnh gần nhất. Đo thật: TESTNET **WIN thực tế 58%
nhưng learner dự đoán p=23%** (edge −0.53) ⇒ chặn 64% setup ⇒ `BLOCKED_LEARN` ⇒ bot đứng yên.
Nguyên tắc bắt buộc: **model dùng để chặn tiền thật thì phải kiểm định được**, và phải có **lưới an
toàn**: không chứng minh được edge ⇒ **TRUNG TÍNH** (không chặn ai).
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import learner as L          # noqa: E402
import learner_refit as LR   # noqa: E402


def _mk(tmp: Path, n=200, *, signal=True, seed=7) -> Path:
    """Tạo journal giả: feats có/không có tín hiệu ⇒ nhãn theo TIỀN (pnl > 0)."""
    import random
    rnd = random.Random(seed)
    lines = []
    for i in range(n):
        x = rnd.uniform(0, 1)
        feats = {k: rnd.uniform(-0.5, 0.5) for k in L.FEATURES}
        feats["tech"] = x
        p_win = (0.2 + 0.7 * x) if signal else 0.5
        won = rnd.random() < p_win
        lines.append(json.dumps({"ts": float(i), "event": "OPEN", "pair": "P%d/USDT:USDT" % i,
                                 "direction": "LONG", "feats": feats}))
        lines.append(json.dumps({"ts": float(i) + 0.5, "event": "CLOSE",
                                 "pair": "P%d/USDT:USDT" % i, "direction": "LONG",
                                 "pnl": 1.0 if won else -1.0, "won": won, "r": 1.0 if won else -1.0}))
    d = tmp / "logs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "journal.jsonl").write_text("\n".join(lines), encoding="utf-8")
    return tmp


class TestCoBan(unittest.TestCase):
    def test_logit_va_sigmoid(self):
        self.assertAlmostEqual(LR.sigmoid(LR.logit(0.7)), 0.7, places=6)
        self.assertAlmostEqual(LR.sigmoid(0.0), 0.5)

    def test_vector_dao_dau_cho_SHORT(self):
        f = {"tech": 1.0, "sent": -2.0}
        self.assertAlmostEqual(LR.vector(f, "LONG")["tech"], 1.0)
        self.assertAlmostEqual(LR.vector(f, "SHORT")["tech"], -1.0)
        self.assertAlmostEqual(LR.vector(f, "SHORT")["sent"], 2.0)

    def test_edge_giong_learner(self):
        feats = {k: 0.5 for k in L.FEATURES}
        w = {k: 0.0 for k in L.FEATURES}
        self.assertAlmostEqual(LR.edge_of(feats, w, 0.0), 0.0)
        self.assertGreater(LR.edge_of(feats, w, 2.0), 0.7)     # sigmoid(2)=0.88 ⇒ edge 0.76
        self.assertLess(LR.edge_of(feats, w, -2.0), -0.7)

    def test_logloss_base_rate_bang_cong_thuc(self):
        rows = [({k: 0.0 for k in L.FEATURES}, 1.0)] * 7 + \
               [({k: 0.0 for k in L.FEATURES}, 0.0)] * 3
        p = 0.7
        want = -(p * math.log(p) + (1 - p) * math.log(1 - p))
        self.assertAlmostEqual(LR.logloss(rows, {}, LR.logit(p)), want, places=6)


class TestFitVaKiemDinh(unittest.TestCase):
    def test_fit_hoc_duoc_tin_hieu(self):
        rows = [({"tech": 1.0}, 1.0)] * 30 + [({"tech": 0.0}, 0.0)] * 30
        m = LR.fit(rows, iters=300)
        self.assertGreater(m["w"]["tech"], 0.0, "phai hoc ra tech lien quan THANG")

    def test_co_tin_hieu_thi_KHONG_trung_tinh(self):
        with tempfile.TemporaryDirectory() as t:
            base = _mk(Path(t), n=300, signal=True)
            r = LR.refit_one("T", base, holdout=0.25, iters=400)
            self.assertFalse(r["neutral"], r.get("reason"))
            self.assertLess(r["logloss_model"], r["logloss_base"])
            self.assertGreater(r["edge_median_test"], 0.0, "co tin hieu ⇒ edge duong")

    def test_khong_tin_hieu_thi_TRUNG_TINH_va_khong_chan(self):
        with tempfile.TemporaryDirectory() as t:
            base = _mk(Path(t), n=300, signal=False, seed=11)
            r = LR.refit_one("T", base, holdout=0.25, iters=400)
            self.assertTrue(r["neutral"], "khong thang base-rate ⇒ phai TRUNG TINH")
            self.assertEqual(r["blocked_pct_test"], 0.0, "trung tinh ⇒ khong chan gi")

    def test_qua_it_lenh_thi_khong_fit(self):
        with tempfile.TemporaryDirectory() as t:
            base = _mk(Path(t), n=20)
            r = LR.refit_one("T", base, min_train=80)
            self.assertTrue(r["neutral"])
            self.assertIn("KHONG fit", r["reason"])

    def test_write_ghi_file_dung_dang_va_co_backup(self):
        with tempfile.TemporaryDirectory() as t:
            base = _mk(Path(t), n=300, signal=False, seed=3)
            lp = base / "logs" / "learner.json"
            lp.write_text(json.dumps({"w": {k: 9.0 for k in L.FEATURES}, "b": 9.0, "n": 1}),
                          encoding="utf-8")
            r = LR.refit_one("T", base, holdout=0.25, iters=200, write=True)
            self.assertTrue(Path(r["written"]).exists())
            self.assertTrue(Path(str(lp) + ".bak-refit").exists(), "phai backup truoc khi ghi")
            data = json.loads(lp.read_text(encoding="utf-8"))
            self.assertTrue(data["refit"]["neutral"])
            self.assertEqual(set(data["w"]), set(L.FEATURES))
            self.assertAlmostEqual(data["w"]["tech"], 0.0, places=6)
            # learner that doc lai duoc; TRUNG TINH ⇒ khong chan setup nao (bat ke base-rate)
            obj = L.OnlineLearner(path=str(lp))
            for x in (-1.0, 0.0, 1.0):
                self.assertGreater(obj.edge({k: x for k in L.FEATURES}, "LONG"),
                                   LR.LEARN_MIN_EDGE,
                                   "trung tinh khong duoc chan o bat ky bo feats nao")

    def test_khong_co_journal_thi_khong_no(self):
        with tempfile.TemporaryDirectory() as t:
            r = LR.refit_one("T", Path(t))
            self.assertEqual(r["n"], 0)
            self.assertTrue(r["neutral"])


if __name__ == "__main__":
    unittest.main()
