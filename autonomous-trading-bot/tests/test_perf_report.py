"""`tools/perf_report.py` — 8 chi so hieu nang tu journal that.

Chot bang so tinh tay duoc (khong phu thuoc du lieu song): maxDD, ulcer, PF, expectancy,
CAGR, sharpe/sortino (co ca "khong du mau" va "khong co lenh lo"), va viec tach theo
setup/regime phai lay duoc context tu ban ghi OPEN.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import perf_report as PR      # noqa: E402

T0 = 1_760_000_000.0          # 2025-10-09 UTC
DAY = 86400.0


def _close(ts, pnl, r, pair="BTC/USDT:USDT", setup=None, regime=None):
    rec = {"ts": ts, "event": "CLOSE", "pair": pair, "pnl": pnl, "r": r,
           "won": pnl > 0}
    if setup:
        rec["setup_type"] = setup
    if regime:
        rec["market_regime"] = regime
    return rec


class TestChiSo(unittest.TestCase):
    def test_max_drawdown_va_ulcer(self):
        eq = [100.0, 120.0, 90.0, 110.0]
        # dd: 0, 0, 25%, 100*10/120 %
        self.assertAlmostEqual(PR.max_drawdown(eq), 25.0, places=6)
        want = math.sqrt((0 + 0 + 25.0 ** 2 + (100.0 * 10 / 120) ** 2) / 4)
        self.assertAlmostEqual(PR.ulcer_index(eq), want, places=6)

    def test_profit_factor_va_expectancy(self):
        pf, gw, gl = PR.profit_factor([10.0, -5.0, 20.0, -5.0])
        self.assertAlmostEqual(pf, 3.0)
        self.assertAlmostEqual(gw, 30.0)
        self.assertAlmostEqual(gl, 10.0)
        self.assertAlmostEqual(PR.expectancy([1.0, -1.0, 2.0]), 2.0 / 3.0)
        self.assertEqual(PR.profit_factor([1.0, 2.0])[0], float("inf"))
        self.assertEqual(PR.profit_factor([])[0], 0.0)

    def test_cagr_quy_doi_tu_so_ngay(self):
        want = ((1.1 ** (365.0 / 30.0)) - 1.0) * 100.0   # +10% trong 30 ngay
        self.assertAlmostEqual(PR.cagr(1000.0, 1100.0, 30.0), want, places=6)
        self.assertEqual(PR.cagr(1000.0, 1100.0, 0), 0.0)
        self.assertEqual(PR.cagr(0.0, 1100.0, 30), 0.0)

    def test_calmar(self):
        self.assertAlmostEqual(PR.calmar(30.0, 10.0), 3.0)
        self.assertEqual(PR.calmar(30.0, 0.0), 0.0)

    def test_sharpe_va_sortino(self):
        flat = [0.001] * 5
        self.assertEqual(PR.sharpe(flat), 0.0, "khong bien dong => 0, khong chia cho 0")
        self.assertEqual(PR.sharpe([0.01]), 0.0, "1 diem => khong du mau")
        up = [0.01, 0.02, 0.03]
        self.assertGreater(PR.sharpe(up), 0)
        self.assertEqual(PR.sortino(up), 0.0, "khong co ngay lo => 0 (khong chia 0)")
        mixed = [0.01, -0.02, 0.03, -0.01]
        self.assertGreater(PR.sortino(mixed), PR.sharpe(mixed))

    def test_sortino_can_du_2_ngay_lo(self):
        """1 ngay lo ⇒ mau so ~0 ⇒ so nhay len hang nghin (do that LIVE: 1483). Phai tra 0 + note."""
        self.assertEqual(PR.sortino([0.01, -0.001]), 0.0)
        notes = PR._notes([0.01, -0.001], 0.5)
        self.assertTrue(any("Sortino" in n for n in notes), notes)

    def test_calmar_maxdd_qua_nho_thi_khong_in_so_lon(self):
        self.assertEqual(PR.calmar(30.0, 0.01), 0.0)
        self.assertTrue(any("Calmar" in n for n in PR._notes([0.1, -0.1], 0.01)))


class TestJournalThat(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.jp = Path(self.td.name) / "journal.jsonl"

    def tearDown(self):
        self.td.cleanup()

    def _write(self, rows):
        self.jp.write_text("\n".join(json.dumps(r) for r in rows) + "\n{hong\n",
                           encoding="utf-8")

    def test_doc_va_ghep_context_tu_OPEN(self):
        self._write([
            {"ts": T0, "event": "OPEN", "pair": "BTC/USDT:USDT", "entry": 1.0,
             "setup_type": "BOS_UP", "market_regime": "UPTREND"},
            _close(T0 + 60, 10.0, 1.0),
            _close(T0 + 120, -5.0, -0.5),
        ])
        all_rows = PR.rows(self.jp)
        cs = PR.attach_context(all_rows, PR.closes(all_rows))
        self.assertEqual(cs[0]["setup_type"], "BOS_UP")
        self.assertEqual(cs[0]["market_regime"], "UPTREND")
        self.assertIsNone(cs[1].get("setup_type"), "OPEN chi ghep duoc 1 lan (FIFO)")

    def test_build_8_chi_so_va_tach_nhom(self):
        self._write([
            _close(T0 + 10, 20.0, 2.0, setup="BOS_UP", regime="UPTREND"),
            _close(T0 + DAY, -10.0, -1.0, setup="BOS_UP", regime="DOWNTREND"),
            _close(T0 + DAY + 10, 5.0, 0.5, setup="SWEEP", regime="UPTREND"),
        ])
        all_rows = PR.rows(self.jp)
        rep = PR.build(PR.attach_context(all_rows, PR.closes(all_rows)),
                       start_balance=1000.0, days=0)
        self.assertEqual(rep["trades"], 3)
        self.assertAlmostEqual(rep["pnl"], 15.0)
        self.assertAlmostEqual(rep["end_balance"], 1015.0)
        self.assertAlmostEqual(rep["pf"], 25.0 / 10.0)
        self.assertAlmostEqual(rep["winrate"], 200.0 / 3.0, places=6)
        self.assertEqual(rep["days"], 2, "2 ngay co lenh")
        self.assertGreater(rep["max_dd_pct"], 0.0)
        self.assertEqual(sorted(rep["by_setup"]), ["BOS_UP", "SWEEP"])
        self.assertEqual(rep["by_setup"]["BOS_UP"]["n"], 2)
        self.assertEqual(sorted(rep["by_regime"]), ["DOWNTREND", "UPTREND"])
        self.assertAlmostEqual(rep["by_regime"]["UPTREND"]["pnl"], 25.0)

    def test_cua_so_ngay_loc_dung(self):
        self._write([_close(T0, 10.0, 1.0), _close(T0 + 40 * DAY, 5.0, 1.0)])
        all_rows = PR.rows(self.jp)
        cs = PR.attach_context(all_rows, PR.closes(all_rows))
        rep = PR.build(cs, start_balance=1000.0, days=30, now=T0 + 40 * DAY)
        self.assertEqual(rep["trades"], 1, "lenh 40 ngay truoc phai bi loc")

    def test_render_khong_no_va_json_hoa_duoc(self):
        self._write([_close(T0, 10.0, 1.0, setup="BOS_UP")])
        all_rows = PR.rows(self.jp)
        rep = PR.build(PR.attach_context(all_rows, PR.closes(all_rows)),
                       start_balance=1000.0, days=0)
        txt = PR.render(rep)
        self.assertIn("CAGR", txt)
        self.assertIn("SETUP", txt)
        json.dumps({k: v for k, v in rep.items() if k not in ("equity", "daily")},
                   default=str)


    def test_bot_only_loai_lenh_tay(self):
        """(15/11) `--bot-only`: lenh tay (khong OPEN) khong duoc tinh vao chi so."""
        rows_ = [
            {"ts": T0, "event": "OPEN", "pair": "BTC/USDT:USDT", "entry": 1.0},
            _close(T0 + 60, 10.0, 1.0),
            {"ts": T0 + 120, "event": "CLOSE", "pair": "TAY/USDT:USDT", "pnl": -999.0, "r": -9.0},
        ]
        cs = PR.attach_context(rows_, PR.closes(rows_))
        self.assertTrue(cs[0]["_bot"])
        self.assertFalse(cs[1]["_bot"])
        bot = PR.build(cs, start_balance=1000.0, days=0, bot_only=True)
        all_ = PR.build(cs, start_balance=1000.0, days=0)
        self.assertEqual(bot["trades"], 1)
        self.assertEqual(all_["trades"], 2)
        self.assertAlmostEqual(bot["pnl"], 10.0)
        self.assertAlmostEqual(all_["pnl"], -989.0)

    def test_bot_only_rong_thi_khong_no(self):
        rows_ = [{"ts": T0, "event": "CLOSE", "pair": "X", "pnl": -5.0, "r": -1.0}]
        cs = PR.attach_context(rows_, PR.closes(rows_))
        rep = PR.build(cs, start_balance=1000.0, days=0, bot_only=True)
        self.assertEqual(rep["trades"], 0)
        PR.render(rep)                      # khong nem loi


class TestBaoCaoTrenJournalThat(unittest.TestCase):
    def test_chay_duoc_tren_journal_cua_repo(self):
        """Nghiem thu roadmap: bao cao phai chay tren journal THAT, khong chi du lieu gia."""
        p = ROOT / "logs" / "journal.jsonl"
        if not p.is_file():
            self.skipTest("chua co journal")
        all_rows = PR.rows(p)
        cs = PR.attach_context(all_rows, PR.closes(all_rows))
        rep = PR.build(cs, start_balance=1000.0, days=0)
        self.assertGreaterEqual(rep["trades"], 1)
        self.assertIsInstance(rep["pf"], float)


if __name__ == "__main__":
    unittest.main()
