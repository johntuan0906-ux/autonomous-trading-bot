"""test_reconcile.py — doi chieu journal voi fill THAT tren san (P0-reconcile).

Muc tieu: bot tat/restart trong luc mo vi the -> san dong bang SL/TP nhung khong
ai ghi CLOSE -> journal thieu lenh -> gate LIVE bi lech. Module reconcile.py phai:
  1) TAI TAO vong lenh (round-trip) tu fill theo khoi luong co dau (FIFO lot):
     partial + stop bi chia nho van gop dung; vi the dang mo tach rieng (khong ghi).
  2) CHI ghi qua OPEN ton tai trong journal (symbol/huong/gia/qty/thoi gian khop)
     -> lenh tay cua nguoi dung / ngoai cua so (unmatched) bi BO QUA dung cach.
  3) KHONG ghi trung CLOSE da co (exit gia leg cuoi + thoi gian): apply 2 lan van 1.
  4) R/PnL tinh bang trade_result (booked_pnl cho cac leg truoc leg cuoi nhu partial).
  5) apply_closes: backup 1 lan truoc khi ghi; throttle trong reconcile().
  6) KHONG bao gio sua risk_state / gui lenh (ham chi doc + ghi log).

Chay: python -m unittest tests.test_reconcile -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import reconcile as R  # noqa: E402

SYM = "SOL/USDT:USDT"


def _mkfill(sym, side, qty, price, ts_ms, pnl=0.0, order="o1"):
    return {"symbol": sym, "side": side, "qty": qty, "price": price, "ts": ts_ms,
            "order_id": order, "pnl_exchange": pnl, "fee": 0.0}


def _mkopen(sym, direction, entry, qty, sl, tp, ts, **kw):
    rec = {"ts": ts, "event": "OPEN", "pair": sym, "direction": direction,
           "timeframe": "15m", "entry": entry, "qty": qty, "sl": sl, "tp": tp}
    rec.update(kw)
    return rec


class TestBuildEpisodes(unittest.TestCase):
    def test_dong_don_1_leg(self):
        fills = [_mkfill(SYM, "SELL", 10.0, 100.0, 1_000_000_000_000, 0.0),
                 _mkfill(SYM, "BUY", 10.0, 99.0, 1_000_001_000_000, 10.0)]
        eps, opened = R.build_episodes(fills)
        self.assertEqual(len(eps), 1)
        ep = eps[0]
        self.assertEqual(ep["direction"], "SHORT")
        self.assertAlmostEqual(ep["entry_px"], 100.0)
        self.assertAlmostEqual(ep["exit_px"], 99.0)
        self.assertAlmostEqual(ep["qty"], 10.0)
        self.assertAlmostEqual(ep["realized_pnl"], 10.0)
        self.assertEqual(opened, [])

    def test_partial_va_stop_chia_nho_gop_dung(self):
        # LONG 13.95: vao 2 leg; ra: partial 6.97 + 7 manh stop (tong 6.97) + leg cuoi
        T = 1_000_000_000_000
        fills = [_mkfill(SYM, "BUY", 8.7, 117.55, T, 0.0),
                 _mkfill(SYM, "BUY", 5.25, 117.59, T + 1, 0.0),
                 _mkfill(SYM, "SELL", 6.97, 118.21, T + 100, 4.4953),
                 _mkfill(SYM, "SELL", 0.37, 117.87, T + 200, 0.1),
                 _mkfill(SYM, "SELL", 6.6, 117.87, T + 201, 2.01),
                 _mkfill(SYM, "SELL", 0.01, 116.79, T + 300, -0.0078)]
        eps, opened = R.build_episodes(fills)
        self.assertEqual(len(eps), 1)
        ep = eps[0]
        self.assertEqual(ep["direction"], "LONG")
        self.assertAlmostEqual(ep["qty"], 13.95)
        self.assertEqual(len(ep["exit_legs"]), 4)
        self.assertAlmostEqual(sum(f["qty"] for f in ep["exit_legs"]), 13.95)
        self.assertEqual(opened, [])

    def test_vi_the_dang_mo_tach_rieng(self):
        fills = [_mkfill(SYM, "SELL", 10.0, 100.0, 1_000_000_000_000, 0.0),
                 _mkfill(SYM, "BUY", 4.0, 99.0, 1_000_001_000_000, 4.0)]
        eps, opened = R.build_episodes(fills)
        self.assertEqual(eps, [])
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened[0]["direction"], "SHORT")
        self.assertAlmostEqual(opened[0]["qty"], 6.0)

    def test_nhieu_vong_ung_thu_tu_dong(self):
        T = 1_000_000_000_000
        fills = [_mkfill(SYM, "SELL", 5.0, 100.0, T, 0.0),
                 _mkfill(SYM, "BUY", 5.0, 99.0, T + 10, 5.0),
                 _mkfill(SYM, "SELL", 5.0, 101.0, T + 20, 0.0),
                 _mkfill(SYM, "BUY", 5.0, 102.0, T + 30, -5.0)]
        eps, _ = R.build_episodes(fills)
        self.assertEqual(len(eps), 2)
        self.assertEqual([e["close_ts"] for e in eps], [T + 10, T + 30])

class TestPairEpisodes(unittest.TestCase):
    def test_khop_open_dung_4_dieu_kien(self):
        T = 1_700_000_000_000
        op = _mkopen(SYM, "SHORT", 100.0, 10.0, 102.0, 95.0, T / 1000.0)
        ep = {"symbol": SYM, "direction": "SHORT", "qty": 10.0, "entry_px": 100.0,
              "exit_px": 99.0, "open_ts": T + 5_000, "close_ts": T + 600_000,
              "exit_qty": 10.0, "realized_pnl": 10.0, "entry_legs": [], "exit_legs": []}
        matched, unmatched = R.pair_episodes_to_opens([ep], [op])
        self.assertEqual(len(matched), 1)
        self.assertEqual(unmatched, [])

    def test_khac_huong_khong_khop(self):
        T = 1_700_000_000_000
        op = _mkopen(SYM, "LONG", 100.0, 10.0, 98.0, 105.0, T / 1000.0)
        ep = {"symbol": SYM, "direction": "SHORT", "qty": 10.0, "entry_px": 100.0,
              "exit_px": 99.0, "open_ts": T + 5_000, "close_ts": T + 600_000,
              "exit_qty": 10.0, "realized_pnl": 10.0, "entry_legs": [], "exit_legs": []}
        matched, unmatched = R.pair_episodes_to_opens([ep], [op])
        self.assertEqual(matched, [])
        self.assertEqual(len(unmatched), 1)

    def test_lenh_tay_khac_qty_roi_unmatched(self):
        # Vong lenh to (basket tay) khong khop OPEN nho cua bot -> bo qua.
        T = 1_700_000_000_000
        op = _mkopen(SYM, "SHORT", 115.335, 12.0, 117.0, 110.0, T / 1000.0)
        ep = {"symbol": SYM, "direction": "SHORT", "qty": 35.85, "entry_px": 115.335,
              "exit_px": 114.59, "open_ts": T + 5_000, "close_ts": T + 600_000,
              "exit_qty": 35.85, "realized_pnl": 26.0, "entry_legs": [], "exit_legs": []}
        matched, unmatched = R.pair_episodes_to_opens([ep], [op])
        self.assertEqual(matched, [])
        self.assertEqual(len(unmatched), 1)

    def test_moi_open_chi_dung_1_lan(self):
        T = 1_700_000_000_000
        op = _mkopen(SYM, "SHORT", 100.0, 10.0, 102.0, 95.0, T / 1000.0)
        def _ep(dt):
            return {"symbol": SYM, "direction": "SHORT", "qty": 10.0, "entry_px": 100.0,
                    "exit_px": 99.0, "open_ts": T + 5_000, "close_ts": T + 600_000 + dt,
                    "exit_qty": 10.0, "realized_pnl": 10.0,
                    "entry_legs": [], "exit_legs": []}
        matched, unmatched = R.pair_episodes_to_opens([_ep(0), _ep(60_000)], [op])
        self.assertEqual(len(matched), 1)
        self.assertEqual(len(unmatched), 1)


class TestBuildClose(unittest.TestCase):
    def test_r_pnl_khop_trade_result_2_leg(self):
        # SHORT 100, sl 102, qty 1: leg1 0.5 @ 98 (partial), leg cuoi 0.5 @ 97.
        T = 1_700_000_000
        op = _mkopen(SYM, "SHORT", 100.0, 1.0, 102.0, 95.0, T)
        legs = [{"symbol": SYM, "side": "BUY", "qty": 0.5, "price": 98.0,
                 "ts": T * 1000 + 100, "order_id": "a", "pnl_exchange": 1.0, "fee": 0.0},
                {"symbol": SYM, "side": "BUY", "qty": 0.5, "price": 97.0,
                 "ts": T * 1000 + 200, "order_id": "b", "pnl_exchange": 1.5, "fee": 0.0}]
        rec = R.build_close(op, legs)
        fee = R.FEE_ROUNDTRIP_PCT
        pnl = (100.0 - 98.0) * 0.5 * (1 - fee) + (100.0 - 97.0) * 0.5 * (1 - fee)
        self.assertAlmostEqual(rec["pnl"], pnl, places=5)
        self.assertAlmostEqual(rec["r"], round(pnl / (2.0 * 1.0), 4), places=5)
        self.assertTrue(rec["won"])
        self.assertEqual(rec["event"], "CLOSE")
        self.assertTrue(rec["reconciled"])
        self.assertEqual(rec["recon_src"], "exchange")
        self.assertEqual(rec["ts"], (T * 1000 + 200) / 1000.0)  # ts = leg cuoi

    def test_sl_hit_1_leg_r_am_1(self):
        T = 1_700_000_000
        op = _mkopen(SYM, "SHORT", 100.0, 1.0, 102.0, 95.0, T)
        legs = [{"symbol": SYM, "side": "BUY", "qty": 1.0, "price": 102.0,
                 "ts": T * 1000 + 100, "order_id": "a", "pnl_exchange": -2.0,
                 "fee": 0.0}]
        rec = R.build_close(op, legs)
        self.assertAlmostEqual(rec["r"], -0.999, places=3)
        self.assertFalse(rec["won"])
        self.assertEqual(rec["reason"], "SL")


class TestPlanBackfill(unittest.TestCase):
    def _writes(self):
        # 1 open SHORT + 1 open LONG; 1 close da ghi cho SHORT.
        T = 1_700_000_000_000
        opens = [_mkopen(SYM, "SHORT", 100.0, 10.0, 102.0, 95.0, T / 1000.0),
                 _mkopen("ETH/USDT:USDT", "LONG", 2000.0, 0.5, 1980.0, 2050.0,
                         (T + 3_600_000) / 1000.0)]
        closes = [{"ts": (T + 60_000) / 1000.0, "event": "CLOSE", "pair": SYM,
                   "direction": "SHORT", "entry": 100.0, "qty": 10.0,
                   "exit_price": 99.0, "r": 0.5, "won": True, "pnl": 5.0,
                   "reason": "TP"}]
        fills = [_mkfill(SYM, "SELL", 10.0, 100.0, T, 0.0),                      # vao
                 _mkfill(SYM, "BUY", 10.0, 99.0, T + 60_000, 10.0),              # ra (da ghi)
                 _mkfill("ETH/USDT:USDT", "BUY", 0.5, 2000.0, T + 3_600_000, 0.0),
                 _mkfill("ETH/USDT:USDT", "SELL", 0.5, 1980.0, T + 7_200_000, -10.0)]
        return opens, closes, fills

    def test_chi_ghi_bu_long_thieu_chu_khong_ghi_lai_short(self):
        opens, closes, fills = self._writes()
        plan = R.plan_backfill(opens, closes, fills)
        self.assertEqual(plan["episodes"], 2)
        self.assertEqual(plan["matched"], 2)
        self.assertEqual(plan["already"], 1)
        self.assertEqual(len(plan["closes"]), 1)
        rec = plan["closes"][0]
        self.assertEqual(rec["pair"], "ETH/USDT:USDT")
        self.assertTrue(rec["reconciled"])
        self.assertLess(rec["r"], 0)

    def test_idempotent_sau_khi_apply(self):
        opens, closes, fills = self._writes()
        with tempfile.TemporaryDirectory() as d:
            jp = os.path.join(d, "journal.jsonl")
            with open(jp, "w", encoding="utf-8") as f:
                for rec in opens + closes:
                    f.write(json.dumps(rec) + "\n")
            plan1 = R.plan_backfill(opens, closes, fills)
            rep = R.apply_closes(jp, plan1["closes"])
            self.assertEqual(rep["written"], 1)
            self.assertTrue(rep["backup"] and os.path.exists(rep["backup"]))
            opens2, closes2 = R.journal_records(jp)
            plan2 = R.plan_backfill(opens2, closes2, fills)
            self.assertEqual(plan2["closes"], [])
            self.assertEqual(R.plan_backfill(opens2, closes2, fills)["closes"], [])

    def test_throttle_khi_vua_chay(self):
        with tempfile.TemporaryDirectory() as d:
            st = os.path.join(d, "st.json")
            cfg = SimpleNamespace(journal_path=os.path.join(d, "j.jsonl"),
                                  reconcile_min_interval_sec=3600,
                                  reconcile_days=7, symbols=(), extra_symbols=())
            with open(st, "w", encoding="utf-8") as f:
                json.dump({"last_run": time.time()}, f)
            out = R.reconcile(cfg, ex=None, log=None, apply=True,
                              fills=[], state_path=st)
            self.assertEqual(out["written"], 0)
            self.assertIn("skipped", out)

    def test_orphan_fifo_chi_de_chan_doan(self):
        T = 1_700_000_000.0
        with tempfile.TemporaryDirectory() as d:
            jp = os.path.join(d, "journal.jsonl")
            recs = [_mkopen(SYM, "SHORT", 100.0, 10.0, 102.0, 95.0, T),
                    {"ts": T + 60, "event": "CLOSE", "pair": SYM, "direction": "SHORT",
                     "entry": 100.0, "qty": 10.0, "exit_price": 99.0, "r": 0.5,
                     "won": True, "pnl": 5.0, "reason": "TP"}]
            with open(jp, "w", encoding="utf-8") as f:
                for rec in recs:
                    f.write(json.dumps(rec) + "\n")
            self.assertEqual(R.orphan_opens(jp), [])


if __name__ == "__main__":
    unittest.main()

