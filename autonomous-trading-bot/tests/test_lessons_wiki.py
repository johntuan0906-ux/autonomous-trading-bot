"""`tools/lessons_wiki.py` — LESSONS.md sinh từ journal, có trích dẫn, máy kiểm lại được.

Chốt 3 điều: (a) số sinh từ journal (không viết tay); (b) mỗi dòng có trích dẫn; (c) sửa một con số
trong tài liệu thì `--check` PHẢI báo lệch ("số không khớp nguồn"), và khối HUMAN không bị ghi đè.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import lessons as LS             # noqa: E402
import lessons_wiki as LW        # noqa: E402

T0 = 1_760_000_000.0


def _open(pair, strategy="S1", setup="BOS_UP", regime="UPTREND", direction="LONG"):
    return {"ts": T0, "event": "OPEN", "pair": pair, "entry": 1.0, "strategy": strategy,
            "setup_type": setup, "market_regime": regime, "direction": direction}


def _close(ts, r, pnl=None, pair="A", did=None):
    rec = {"ts": ts, "event": "CLOSE", "pair": pair, "r": r,
           "pnl": pnl if pnl is not None else (10.0 if r > 0 else -5.0)}
    if did:
        rec["decision_id"] = did
    return rec


def _rows(n_win=6, n_loss=4):
    """Moi lenh co 1 OPEN rieng (giong journal that: OPEN ... CLOSE tung cap)."""
    rows = []
    for i in range(n_win):
        rows.append(_open("A"))
        rows.append(_close(T0 + 60 + i, 1.0, did="d%d" % i))
    for i in range(n_loss):
        rows.append(_open("A"))
        rows.append(_close(T0 + 120 + i, -1.0))
    return rows


class TestSinhBaiHoc(unittest.TestCase):
    def test_tinh_dung_va_co_trich_dan(self):
        data = LW.collect(_rows(), min_n=8)
        self.assertEqual(len(data), 1)
        key = next(iter(data))
        self.assertIn("S1", key, "khoa phai theo lessons.KEYS_DEFAULT")
        s = data[key]
        self.assertEqual(s["n"], 10)
        self.assertEqual(s["wins"], 6)
        self.assertAlmostEqual(s["winrate"], 60.0)
        self.assertAlmostEqual(s["avg_r"], 0.2)          # (6*1 + 4*(-1))/10
        self.assertTrue(s["refs"], "phai co trich dan")
        self.assertEqual(s["refs"][0], "d0")

    def test_nguong_mau_loc_dung(self):
        self.assertEqual(LW.collect(_rows(2, 1), min_n=8), {})

    def test_khoa_khac_nhau_tach_dong(self):
        rows = _rows()
        for i in range(8):
            rows.append(_open("B", setup="SWEEP"))
            rows.append(_close(T0 + 200 + i, 0.5, pair="B"))
        data = LW.collect(rows, min_n=8)
        self.assertEqual(len(data), 2)
        self.assertTrue(any("SWEEP" in k for k in data), list(data))

    def test_render_co_json_va_bang(self):
        txt = LW.render(LW.collect(_rows(), 8), 8, "x.jsonl")
        self.assertIn(LW.AUTO_BEGIN, txt)
        self.assertIn("```json", txt)
        self.assertIn("avg R", txt)


class TestKiemLai(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.md = Path(self.td.name) / "LESSONS.md"

    def tearDown(self):
        self.td.cleanup()

    def _write(self, human=False):
        body = ("# LESSONS\n\n" + (LS.HUMAN_BEGIN + "\nghi tay\n" + LS.HUMAN_END + "\n")
                if human else "# LESSONS\n\n")
        self.md.write_text(body, encoding="utf-8")
        r = LW.write(self.md, _rows(), 8)
        self.assertTrue(r["ok"], r)

    def test_ghi_roi_kiem_thi_KHOP(self):
        self._write()
        rep = LW.check(self.md, _rows(), 8)
        self.assertTrue(rep["ok"], rep)
        self.assertIn(LW.AUTO_BEGIN, self.md.read_text(encoding="utf-8"))

    def test_sua_so_trong_tai_lieu_thi_bao_LECH(self):
        self._write()
        txt = self.md.read_text(encoding="utf-8")
        data = LW.parse_auto(txt)
        key = next(iter(data))
        data[key]["n"] = 999
        broken = txt.replace(json.dumps(LW.parse_auto(txt), sort_keys=True, indent=1),
                             json.dumps(data, sort_keys=True, indent=1))
        self.md.write_text(broken, encoding="utf-8")
        rep = LW.check(self.md, _rows(), 8)
        self.assertFalse(rep["ok"])
        self.assertIn("KHONG khop", rep["reason"])

    def test_ghi_lai_KHONG_mat_khoi_HUMAN(self):
        self._write(human=True)
        txt = self.md.read_text(encoding="utf-8")
        self.assertIn(LS.HUMAN_BEGIN, txt)
        self.assertIn("ghi tay", txt)
        LW.write(self.md, _rows(), 8)
        self.assertIn("ghi tay", self.md.read_text(encoding="utf-8"))

    def test_thieu_khoi_auto_thi_bao(self):
        self.md.write_text("# LESSONS\n", encoding="utf-8")
        rep = LW.check(self.md, _rows(), 8)
        self.assertFalse(rep["ok"])
        self.assertIn("--write", rep["reason"])


if __name__ == "__main__":
    unittest.main()
