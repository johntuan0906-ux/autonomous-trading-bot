"""Test `lessons.py` — rut kinh nghiem tu journal (ghep OPEN↔CLOSE, gom to hop, chan).

Boi canh (13/10): yeu cau "luon hoc hoi qua tung lan vao lenh, ghi chu, rut kinh nghiem
de PnL cao hon". Ham o day thuan tuy -> test duoc, khong goi mang.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lessons as LES      # noqa: E402


def _line(**kw) -> str:
    return json.dumps(kw, ensure_ascii=False)


def _journal(rows) -> Path:
    d = tempfile.mkdtemp()
    p = Path(d) / "journal.jsonl"
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return p


class TestLoadClosed(unittest.TestCase):
    def test_ghep_open_voi_close(self):
        p = _journal([
            _line(event="OPEN", pair="A/USDT:USDT", strategy="S1", setup_type="BOS_DOWN",
                  market_regime="DOWNTREND", direction="SHORT"),
            _line(event="CLOSE", pair="A/USDT:USDT", r=2.0, pnl=10.0, won=True,
                  reason="TP", ts=5),
        ])
        t = LES.load_closed(p)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]["strategy"], "S1", "phai mang feature cua lenh OPEN")
        self.assertEqual(t[0]["r"], 2.0)
        self.assertTrue(t[0]["won"])

    def test_open_khong_co_close_bi_bo_qua(self):
        p = _journal([_line(event="OPEN", pair="A", strategy="S1")])
        self.assertEqual(LES.load_closed(p), [], "khong suy dien ket qua")

    def test_close_khong_co_open_van_dem_duoc(self):
        p = _journal([_line(event="CLOSE", pair="A", r=-1.0, pnl=-5.0, won=False)])
        t = LES.load_closed(p)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]["r"], -1.0)

    def test_nhieu_open_cung_cap_ghep_fifo(self):
        p = _journal([
            _line(event="OPEN", pair="A", strategy="S1"),
            _line(event="OPEN", pair="A", strategy="S2"),
            _line(event="CLOSE", pair="A", r=1.0, won=True),
            _line(event="CLOSE", pair="A", r=-1.0, won=False),
        ])
        t = LES.load_closed(p)
        self.assertEqual([x["strategy"] for x in t], ["S1", "S2"])

    def test_dong_hong_bi_bo_qua(self):
        p = _journal(["{khong-phai-json", _line(event="CLOSE", pair="A", r=1.0)])
        self.assertEqual(len(LES.load_closed(p)), 1)

    def test_file_khong_ton_tai(self):
        self.assertEqual(LES.load_closed(Path("khong/co.jsonl")), [])


class TestBuckets(unittest.TestCase):
    def _t(self, strat="S1", setup="BOS_DOWN", regime="DOWNTREND", direction="SHORT",
           r=1.0, pnl=10.0, won=True, ts=1.0):
        return {"strategy": strat, "setup_type": setup, "market_regime": regime,
                "direction": direction, "r": r, "pnl": pnl, "won": won, "ts_close": ts}

    def test_gom_theo_to_hop_va_hop_nhat(self):
        b = LES.bucket_stats([self._t(r=1.0, pnl=10.0), self._t(r=-1.0, pnl=-5.0, won=False)])
        self.assertEqual(len(b), 1, "cung to hop -> HOP NHAT, khong xep chong")
        only = list(b.values())[0]
        self.assertEqual(only["n"], 2)
        self.assertEqual(only["wins"], 1)
        self.assertAlmostEqual(only["avg_r"], 0.0)
        self.assertAlmostEqual(only["wr"], 50.0)
        self.assertAlmostEqual(only["pnl"], 5.0)
        self.assertAlmostEqual(only["pf"], 2.0)

    def test_khac_to_hop_thi_tach(self):
        b = LES.bucket_stats([self._t(), self._t(regime="UPTREND")])
        self.assertEqual(len(b), 2)

    def test_thieu_du_lieu_thi_dung_dau_hoi(self):
        self.assertIn("? | ? | ? | ?", LES.bucket_stats([{"r": 1.0, "won": True}]))

    def test_pf_none_khi_khong_co_lenh_thua(self):
        b = LES.bucket_stats([self._t(r=1.0, pnl=3.0)])
        self.assertIsNone(list(b.values())[0]["pf"])


class TestGateVaNotes(unittest.TestCase):
    def _b(self, n, avg_r, pnl=0.0, wr=50.0):
        return {"n": n, "avg_r": avg_r, "pnl": pnl, "wr": wr, "wins": 0}

    def test_chi_chan_khi_du_mau_va_ky_vong_am(self):
        buckets = {"te": self._b(25, -0.35), "it-mau": self._b(5, -0.90),
                   "tot": self._b(30, +0.20), "sat-nguong": self._b(30, -0.10)}
        g = LES.gate_list(buckets, min_n=20, max_avg_r=-0.20)
        self.assertEqual([x["key"] for x in g], ["te"],
                         "it mau / ky vong duong / chua am ro -> KHONG chan")

    def test_nguong_bang_dung_thi_chan(self):
        g = LES.gate_list({"x": self._b(20, -0.20)}, min_n=20, max_avg_r=-0.20)
        self.assertEqual(len(g), 1)

    def test_sap_xep_te_nhat_truoc(self):
        g = LES.gate_list({"a": self._b(20, -0.25), "b": self._b(20, -0.60)},
                          min_n=20, max_avg_r=-0.20)
        self.assertEqual([x["key"] for x in g], ["b", "a"])

    def test_notes_co_so_lieu_va_danh_dau_dang_chan(self):
        buckets = {"x": self._b(25, -0.40, pnl=-12.0, wr=40.0)}
        g = LES.gate_list(buckets, min_n=20, max_avg_r=-0.20)
        txt = "\n".join(LES.notes(buckets, g, min_n=5))
        self.assertIn("NEN TRANH", txt)
        self.assertIn("n=25", txt)
        self.assertIn("avgR=-0.400", txt)
        self.assertIn("DANG CHAN", txt)

    def test_notes_khi_chua_du_mau(self):
        txt = "\n".join(LES.notes({"x": self._b(3, -1.0)}, [], min_n=5))
        self.assertIn("chua du mau", txt)


class TestKyLuatBoNho(unittest.TestCase):
    """Lay tu tigerless-labs/autoharness: tran so muc + truc xuat (khong xoa) +
    KHONG bao gio ghi de phan do NGUOI viet."""

    def test_merge_capped_giu_nhieu_mau_nhat(self):
        buckets = {"a%d" % i: {"n": i, "avg_r": 0.0} for i in range(10)}
        keep, drop = LES.merge_capped(buckets, cap=3)
        self.assertEqual(sorted(keep), ["a7", "a8", "a9"])
        self.assertEqual(len(drop), 7, "muc bi bo van duoc tra ve de luu tru")

    def test_human_section_giu_nguyen(self):
        md = "truoc\n%s\ntoi viet cai nay\nkhong duoc sua\n%s\nsau" % (
            LES.HUMAN_BEGIN, LES.HUMAN_END)
        self.assertIn("khong duoc sua", LES.human_section(md))

    def test_human_section_rong_khi_thieu_marker(self):
        self.assertEqual(LES.human_section("khong co marker"), "")

    def test_write_files_giu_phan_nguoi_viet(self):
        with tempfile.TemporaryDirectory() as d:
            md = Path(d) / "LESSONS.md"
            md.write_text("cu\n%s\nGHI CHU QUAN TRONG\n%s\n" % (LES.HUMAN_BEGIN,
                                                               LES.HUMAN_END),
                          encoding="utf-8")
            les = {"trades": 5, "buckets": {"x": {"n": 3, "avg_r": -0.5}},
                   "gates": [], "notes": ["NEN TRANH (ky vong am):"], "pruned": ["y"],
                   "ts": 1.0}
            rep = LES.write_files(les, json_path=Path(d) / "lessons.json",
                                  md_path=md, archive_path=Path(d) / "arch.jsonl")
            out = md.read_text(encoding="utf-8")
        self.assertIn("GHI CHU QUAN TRONG", out, "ghi chu nguoi viet phai con nguyen")
        self.assertIn("BAI HOC TU JOURNAL", out)
        self.assertTrue(rep["human_kept"])
        self.assertEqual(rep["archived"], 1)

    def test_build_tu_journal_that(self):
        p = _journal([
            _line(event="OPEN", pair="A", strategy="S1", setup_type="BOS_DOWN",
                  market_regime="DOWNTREND", direction="SHORT"),
            _line(event="CLOSE", pair="A", r=-1.0, pnl=-5.0, won=False),
        ])
        les = LES.build(p, min_n=1, max_avg_r=-0.20)
        self.assertEqual(les["trades"], 1)
        self.assertEqual(len(les["gates"]), 1)
        self.assertIn("S1 | BOS_DOWN | DOWNTREND | SHORT", les["gates"][0]["key"])


class FakeCfg:
    """Cau hinh gia cho `lessons_gate` (khong doc .env that)."""

    def __init__(self, path, enforce=True, min_n=20, max_avg_r=-0.20):
        self.lessons_enforce = enforce
        self.lessons_min_n = min_n
        self.lessons_max_avg_r = max_avg_r
        self.lessons_path = str(path)


class TestLessonsGateTrongBot(unittest.TestCase):
    """(13/10) Cong phai ap NGUONG tu `.env` len `buckets` — khong dung truong `gates`
    cua file, vi file co the duoc sinh voi nguong khac (lech nguong = cong trong im lang)."""

    def _les_file(self, d, buckets):
        p = Path(d) / "lessons.json"
        p.write_text(json.dumps({"buckets": buckets, "gates": []}), encoding="utf-8")
        return p

    def _gate(self, cfg, **kw):
        import turbo_demo as TD
        TD._LESSONS["ts"] = 0.0                     # buoc nap lai file
        return TD.lessons_gate(cfg, **kw)

    def test_chan_dung_to_hop_theo_nguong_env(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._les_file(d, {"S1 | BOS_DOWN | DOWNTREND | SHORT":
                                   {"n": 25, "avg_r": -0.40, "pnl": -10, "wr": 40}})
            cfg = FakeCfg(p, min_n=20, max_avg_r=-0.20)
            r = self._gate(cfg, strat="S1", setup="BOS_DOWN", regime="DOWNTREND",
                           direction="SHORT")
            self.assertTrue(r["block"])
            self.assertIn("S1 | BOS_DOWN | DOWNTREND | SHORT", r["reason"])
            # to hop khac -> khong chan
            r2 = self._gate(cfg, strat="S2", setup="BOS_UP", regime="UPTREND",
                            direction="LONG")
            self.assertFalse(r2["block"])

    def test_nguong_trong_env_quyet_dinh(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._les_file(d, {"S1 | NONE | SIDEWAY | LONG":
                                   {"n": 25, "avg_r": -0.25, "pnl": -10, "wr": 40}})
            # nguong long (-0.30) -> KHONG chan
            cfg_long = FakeCfg(p, min_n=20, max_avg_r=-0.30)
            self.assertFalse(self._gate(cfg_long, strat="S1", setup="NONE",
                                        regime="SIDEWAY", direction="LONG")["block"])
            # nguong chat (-0.20) -> CHAN
            cfg_chat = FakeCfg(p, min_n=20, max_avg_r=-0.20)
            self.assertTrue(self._gate(cfg_chat, strat="S1", setup="NONE",
                                       regime="SIDEWAY", direction="LONG")["block"])

    def test_tat_thi_khong_chan_du_co_du_lieu(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._les_file(d, {"S1 | NONE | SIDEWAY | LONG":
                                   {"n": 99, "avg_r": -0.90, "pnl": -99, "wr": 10}})
            cfg = FakeCfg(p, enforce=False)
            self.assertFalse(self._gate(cfg, strat="S1", setup="NONE",
                                        regime="SIDEWAY", direction="LONG")["block"])

    def test_thieu_du_mau_thi_khong_chan(self):
        with tempfile.TemporaryDirectory() as d:
            p = self._les_file(d, {"S1 | NONE | SIDEWAY | LONG":
                                   {"n": 3, "avg_r": -0.90, "pnl": -9, "wr": 10}})
            cfg = FakeCfg(p, min_n=20, max_avg_r=-0.20)
            self.assertFalse(self._gate(cfg, strat="S1", setup="NONE",
                                        regime="SIDEWAY", direction="LONG")["block"])

    def test_file_hong_thi_khong_chan(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lessons.json"
            p.write_text("{hong", encoding="utf-8")
            cfg = FakeCfg(p)
            self.assertFalse(self._gate(cfg, strat="S1", setup="NONE",
                                        regime="SIDEWAY", direction="LONG")["block"])


class TestImpact(unittest.TestCase):
    """(13/10) Cong tiet kiem bao nhieu / bo lo bao nhieu — can cu de siet hay noi nguong."""

    def _b(self, n, avg_r, pnl):
        return {"n": n, "avg_r": avg_r, "pnl": pnl, "wr": 50.0}

    def test_tiet_kiem_khi_chan_pnl_am(self):
        imp = LES.impact({"x": self._b(25, -0.40, -30.0)}, min_n=20, max_avg_r=-0.20)
        self.assertEqual(imp["saved_pnl"], -30.0)
        self.assertEqual(imp["missed_pnl"], 0.0)
        self.assertEqual(imp["net"], -30.0, "net am = tranh duoc lo")
        self.assertEqual(len(imp["blocked"]), 1)

    def test_phat_hien_bo_lo_lenh_thang_BI_CHAN(self):
        """Tổ hợp avgR -0.30 (BỊ chặn ở ngưỡng -0.20) nhưng PnL DƯƠNG = mất thật sự."""
        imp = LES.impact({"y": self._b(25, -0.30, +40.0)}, min_n=20, max_avg_r=-0.20,
                         near=0.10)
        self.assertEqual(len(imp["missed"]), 1, "bi chan ma co lai -> tinh vao bo lo")
        self.assertEqual(imp["missed_pnl"], 40.0)
        self.assertEqual(imp["saved_pnl"], 0.0)

    def test_lenh_thang_sat_nguong_nhung_CHUA_bi_chan(self):
        """avgR -0.15 > ngưỡng -0.20 => CHƯA bị chặn -> chỉ nằm ở danh sách theo dõi."""
        imp = LES.impact({"z": self._b(25, -0.15, +40.0)}, min_n=20, max_avg_r=-0.20,
                         near=0.10)
        self.assertEqual(imp["missed"], [], "chua bi chan thi khong duoc tinh la bo lo")
        self.assertEqual(len(imp["near"]), 1)
        self.assertEqual(imp["missed_pnl"], 0.0)

    def test_it_mau_thi_bo_qua(self):
        imp = LES.impact({"z": self._b(5, -0.90, -99.0)}, min_n=20, max_avg_r=-0.20)
        self.assertEqual(imp["blocked"], [])
        self.assertEqual(imp["missed"], [])

    def test_tinh_net_dung(self):
        buckets = {"a": self._b(25, -0.50, -50.0), "b": self._b(25, -0.10, +20.0)}
        imp = LES.impact(buckets, min_n=20, max_avg_r=-0.20, near=0.15)
        self.assertEqual(imp["saved_pnl"], -50.0)
        self.assertEqual(imp["missed_pnl"], 0.0,
                         "b (avgR -0.10) KHONG bi chan o nguong -0.20 -> khong phai mat lai")
        self.assertEqual(imp["net"], -50.0, "net = tiet kiem - bo lo (am = tranh duoc lo)")
        self.assertEqual(len(imp["near"]), 1, "b nam trong danh sach theo doi")


if __name__ == "__main__":
    unittest.main()
