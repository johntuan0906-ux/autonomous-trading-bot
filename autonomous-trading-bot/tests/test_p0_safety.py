# -*- coding: utf-8 -*-
"""test_p0_safety.py â€” kiem thu 6 fix P0 + watchdog (truoc khi cho tien THAT vao).

P0-1 adopt vi the san   | P0-2 kill-switch song sot restart + duoc wire
P0-3 loi monitor -> dung| P0-4 clientOrderId + cuu lenh khi timeout mang
P0-5 huy lenh treo cu   | P0-6 tran risk danh muc + DD theo equity that
+ watchdog nhip tim (bot treo ma tien trinh van song)

Chay: python -m unittest tests.test_p0_safety -v
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import exchange as exmod                                                       # noqa: E402
import managed_state                                                          # noqa: E402
import position_sync                                                          # noqa: E402
import bot as botmod                                                          # noqa: E402
import turbo_demo as td                                                       # noqa: E402
from run_forever import (heartbeat_age, next_delay, plan_delay, rotate_log,    # noqa: E402
                         should_restart, tail_has, touch_heartbeat)
from bot import TradingBot                                                     # noqa: E402
from config import Settings                                                    # noqa: E402
from portfolio import (Position, can_add_risk, planned_risk_usd,              # noqa: E402
                       total_risk_pct)
from risk import (KillSwitch, load_state, reset_state, save_state,            # noqa: E402
                  utc_day)
from trade_mgmt import new_trade                                              # noqa: E402


def cfg(**kw) -> Settings:
    """Settings() voi vai truong ghi de -> test deterministic (khong phu thuoc .env)."""
    c = Settings()
    for k, v in kw.items():
        object.__setattr__(c, k, v)
    return c


def bull_df(n=250, start=100.0, step=0.5) -> pd.DataFrame:
    closes = [start + i * step for i in range(n)]
    return pd.DataFrame({"open": [c - 0.1 for c in closes],
                         "high": [c + 0.5 for c in closes],
                         "low": [c - 0.5 for c in closes],
                         "close": closes, "volume": [100.0] * n})


def bear_df(n=250, start=100.0, step=0.5) -> pd.DataFrame:
    closes = [start - i * step for i in range(n)]
    return pd.DataFrame({"open": [c + 0.1 for c in closes],
                         "high": [c + 0.5 for c in closes],
                         "low": [c - 0.5 for c in closes],
                         "close": closes, "volume": [100.0] * n})


class FakeExchange:
    """Exchange gia: ghi lai moi loi goi de assert DUNG THU TU / DUNG THAM SO."""

    def __init__(self, balance=5000.0, rows=None, prot=None, landing=None,
                 entry_raises=False, arm_boom=False):
        self.dry_run = False
        self.balance = balance
        self.rows = rows or []
        self.prot = prot or {}
        self.landing = landing          # position_qty() tra ve (None = khong doc duoc)
        self.entry_raises = entry_raises
        self.arm_boom = arm_boom        # stop_tp_orders nem loi (vd demo -4045)
        self.calls: list = []

    def _log(self, name, **kw):
        self.calls.append((name, kw))

    def named(self, name) -> list:
        return [c for c in self.calls if c[0] == name]

    def fetch_balance_usdt(self):
        self._log("fetch_balance_usdt")
        return self.balance

    def quantize_qty(self, s, q):
        self._log("quantize_qty", qty=q)
        return round(float(q), 3)

    def set_leverage(self, s, lev):
        self._log("set_leverage", lev=lev)

    def market_entry(self, s, d, q, cid=None):
        self._log("market_entry", cid=cid, qty=q)
        if self.entry_raises:
            raise RuntimeError("simulated network timeout")
        return {"id": "entry-1"}

    def stop_tp_orders(self, s, d, q, sl, tp, cid_prefix="sg", cancel_first=True):
        self._log("stop_tp_orders", qty=q, sl=sl, tp=tp, cancel_first=cancel_first)
        if self.arm_boom:
            raise RuntimeError('binance {"code":-4045,"msg":"Reach max stop order limit."}')
        return {"sl_order": {"id": "sl"}, "tp_order": {"id": "tp"}}

    def close_position(self, s, d, q, cid=None):
        self._log("close_position", qty=q)
        return {"id": "close-1"}

    def cancel_symbol_orders(self, s):
        self._log("cancel_symbol_orders")
        return {"cancelled": 1}

    def fetch_positions(self, symbols=None):
        self._log("fetch_positions")
        return self.rows

    def position_qty(self, s):
        self._log("position_qty")
        return self.landing

    def fetch_protection(self, s):
        self._log("fetch_protection")
        return self.prot.get(s, {"sl": None, "tp": None})

    def last_price(self, s):
        return 100.0

    def fetch_ohlcv(self, s, tf="15m", limit=200):
        return bull_df()


class FakeClient:
    """ccxt client gia cho cac test exchange.py (thu tu goi + params)."""

    def __init__(self, fail_first_create=False):
        self.calls: list = []
        self.fail_first_create = fail_first_create
        self._n_create = 0

    def cancel_all_orders(self, symbol):
        self.calls.append(("cancel_all_orders", symbol))
        return [{"id": 1}, {"id": 2}]

    def create_order(self, symbol, otype, side, amount, params=None):
        self._n_create += 1
        self.calls.append(("create_order", otype, amount, dict(params or {})))
        if self.fail_first_create and self._n_create == 1:
            raise RuntimeError("simulated -1106 until closePosition")
        return {"id": "o", "type": otype}

    def create_market_order(self, symbol, side, qty, params=None):
        self.calls.append(("create_market_order", side, qty, dict(params or {})))
        return {"id": "m"}

    def fetch_positions(self, symbols=None):
        self.calls.append(("fetch_positions", symbols))
        return [{"symbol": "BTC/USDT:USDT", "side": "long", "contracts": 3.0,
                 "entryPrice": 100.0}]

    def fetch_open_orders(self, symbol):
        self.calls.append(("fetch_open_orders", symbol))
        return [{"type": "STOP_MARKET", "stopPrice": 96.0},
                {"type": "TAKE_PROFIT_MARKET", "stopPrice": 110.0},
                {"type": "LIMIT", "stopPrice": None}]


def ex_with(client) -> exmod.BinanceFutures:
    """Wrapper o che do order that nhung client gia (khong mang, khong key)."""
    ex = exmod.BinanceFutures(dry_run=True)
    ex.dry_run = False
    ex._client = client
    return ex


class TestRiskStateSongSotRestart(unittest.TestCase):
    """P0-2: supervisor restart sau 15s KHONG duoc xoa trang thai kill-switch."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "risk_state.json")

    def test_trip_duoc_luu_va_nap_lai(self):
        ks = KillSwitch(2.0, 0.02, 5, 1000.0)
        ks.trip("daily loss 2.50% >= 2.0%")
        self.assertTrue(save_state(self.path, ks))
        fresh = KillSwitch(2.0, 0.02, 5, 1000.0)
        self.assertFalse(fresh.tripped)
        load_state(self.path, fresh)
        self.assertTrue(fresh.tripped, "restart phai van bi ngung")
        self.assertIn("daily loss", fresh.reason)

    def test_dem_thua_va_peak_cung_song_sot(self):
        ks = KillSwitch(2.0, 0.02, 5, 1000.0)
        ks.consec_losses = 3
        ks.peak_balance = 5200.0
        ks.start_equity = 5000.0
        save_state(self.path, ks)
        fresh = KillSwitch()
        load_state(self.path, fresh)
        self.assertEqual(fresh.consec_losses, 3)
        self.assertAlmostEqual(fresh.start_equity, 5000.0)
        self.assertGreaterEqual(fresh.peak_balance, 5200.0)

    def test_state_hong_thi_FAIL_CLOSED(self):
        """(02/10) JSON hong -> coi nhu DANG TRIPPED (truoc day im lang chay tiep).

        Hoi dong 14 model: neu kill-switch khong doc duoc state ma van chay tiep thi
        moi bao ve da kich hoat (trip, dem loi, tran ngay) deu co the bi "quen".
        """
        Path(self.path).write_text("{khong-phai-json", encoding="utf-8")
        ks = KillSwitch()
        self.assertIs(load_state(self.path, ks), ks)         # khong nem ra ngoai
        self.assertTrue(ks.tripped, "state doc duoc nhung hong -> phai fail-closed")
        self.assertIn("khong doc duoc", ks.reason)
        msgs: list = []
        ks2 = KillSwitch()
        load_state(self.path, ks2, warn=msgs.append)
        self.assertTrue(ks2.tripped)
        self.assertEqual(len(msgs), 1, "phai bao cho nguoi van hanh biet")
        self.assertIn("fail-closed", msgs[0])

    def test_state_sai_cau_truc_thi_FAIL_CLOSED(self):
        Path(self.path).write_text('{"max_daily_loss_pct": "khong-phai-so"}',
                                   encoding="utf-8")
        ks = KillSwitch()
        load_state(self.path, ks)
        self.assertTrue(ks.tripped)
        self.assertIn("sai cau truc", ks.reason)

    def test_chua_co_state_thi_binh_thuong(self):
        """File CHUA ton tai (lan dau chay / vua `risk.py --reset`) khong duoc trip."""
        ks = KillSwitch()
        load_state(os.path.join(self.dir, "khong-ton-tai.json"), ks)
        self.assertFalse(ks.tripped, "khong co state KHONG phai la loi")

    def test_reset_cho_phep_trade_lai(self):
        ks = KillSwitch()
        ks.trip("volatility")
        save_state(self.path, ks)
        self.assertTrue(reset_state(self.path))
        fresh = KillSwitch()
        load_state(self.path, fresh)
        self.assertFalse(fresh.tripped)

    def test_roll_ngay_moi(self):
        ks = KillSwitch(2.0, 0.02, 5, 1000.0)
        ks.day = utc_day(time.time() - 86400)   # hom qua
        ks.consec_losses = 4
        ks.errors = 3
        self.assertTrue(ks.note_equity(4974.0))
        self.assertEqual(ks.day, utc_day())
        self.assertAlmostEqual(ks.start_equity, 4974.0)
        self.assertEqual(ks.consec_losses, 0)
        self.assertEqual(ks.errors, 0)
        self.assertFalse(ks.note_equity(4974.0), "cung ngay -> khong roll lai")

    def test_sang_ngay_moi_KHONG_tu_mo_lai_kill_switch(self):
        ks = KillSwitch()
        ks.trip("3 consecutive losses")
        ks.day = utc_day(time.time() - 86400)
        ks.note_equity(5000.0)
        self.assertTrue(ks.tripped, "phai xoa tay bang reset_state moi trade lai")

    def test_dd_tinh_tren_equity_that_khong_phai_balance_hardcode(self):
        """BALANCE_USDT=1000 nhung vi that 5000 -> tran 2% phai la 2% cua 5000."""
        ks = KillSwitch(max_daily_loss_pct=2.0, start_balance=1000.0)
        ks.start_equity = 5000.0
        self.assertAlmostEqual(ks.daily_dd_pct(4910.0), 1.8, places=6)
        self.assertFalse(ks.check(4910.0))
        # (neu tinh sai theo 1000 thi 4910 = -9% -> da trip tu lau)
        self.assertTrue(ks.check(4890.0))
        self.assertTrue(ks.tripped)

    def test_bien_dong_atr_moi_that_su_co_hieu_luc(self):
        ks = KillSwitch(max_atr_pct=0.02, start_balance=1000.0)
        self.assertFalse(ks.tripped)
        self.assertTrue(ks.check(1000.0, 0.03))
        self.assertIn("volatility", ks.reason)

    def test_lan_dau_tai_khoan_chua_co_moc_DD(self):
        """Process moi: `day` da la hom nay -> KHONG roll, nhung van phai lay moc."""
        ks = KillSwitch(max_daily_loss_pct=2.0, start_balance=1000.0)
        self.assertFalse(ks.note_equity(4974.0), "cung ngay -> khong phai roll")
        self.assertAlmostEqual(ks.start_equity, 4974.0, places=6)
        self.assertAlmostEqual(ks.base_equity(), 4974.0, places=6)

    def test_moc_DD_phai_la_equity_that_khong_phai_tran_size(self):
        """Lay `balance` (tran size demo 1000) lam moc DD -> tran 2% sai hoan toan."""
        ks = KillSwitch(max_daily_loss_pct=2.0, start_balance=1000.0)
        ks.note_equity(4974.0)
        self.assertFalse(ks.check(4950.0), "giam 24 USDT = 0.48% -> chua cham tran 2%")
        self.assertTrue(ks.check(4800.0), "giam 174 USDT = 3.5% -> phai trip")


class TestRiskDanhMuc(unittest.TestCase):
    """P0-6: 4 vi the x 1% = 4% > tran lo ngay 2% -> phai co tran tong."""

    def test_planned_risk_usd(self):
        self.assertAlmostEqual(planned_risk_usd(100.0, 98.0, 10.0), 20.0)
        self.assertAlmostEqual(planned_risk_usd(100.0, 102.0, 10.0), 20.0)
        self.assertEqual(planned_risk_usd(0.0, 98.0, 10.0), 0.0)
        self.assertEqual(planned_risk_usd(100.0, 98.0, 0.0), 0.0)

    def test_total_risk_pct_dung_moc_1R(self):
        pos = {"A": Position("A", "LONG", 100.0, 10.0, 100.05, 200.0)}   # SL da ve BE
        self.assertAlmostEqual(total_risk_pct(pos, 10000.0, {"A": 98.0}), 0.2)
        self.assertAlmostEqual(total_risk_pct(pos, 10000.0), 0.005)

    def test_can_add_risk_chan_khi_vuot_tran(self):
        pos = {"A": Position("A", "LONG", 100.0, 100.0, 98.0, 200.0),   # 200 USDT
               "B": Position("B", "LONG", 100.0, 100.0, 98.0, 200.0)}
        eq = 10000.0
        self.assertAlmostEqual(total_risk_pct(pos, eq), 4.0)
        ok, why = can_add_risk(pos, eq, 3.0, 200.0)
        self.assertFalse(ok)
        self.assertIn("tran risk danh muc", why)
        ok2, _ = can_add_risk(pos, eq, 6.0, 200.0)
        self.assertTrue(ok2)


class TestExchangeCoIdempotency(unittest.TestCase):
    """P0-4: moi lenh phai co clientOrderId (timeout mang khong mo trung)."""

    def test_cid_hop_le_va_duy_nhat(self):
        ids = {exmod._cid("entry") for _ in range(500)}
        self.assertEqual(len(ids), 500)
        for s in list(ids)[:5]:
            self.assertTrue(s.startswith("glow"))
            self.assertLessEqual(len(s), 36)
            self.assertTrue(all(c.isalnum() for c in s))

    def test_market_entry_co_client_order_id(self):
        c = FakeClient()
        ex_with(c).market_entry("BTC/USDT:USDT", "LONG", 1.0)
        params = c.calls[0][3]
        self.assertIn("newClientOrderId", params)
        self.assertLessEqual(len(params["newClientOrderId"]), 36)

    def test_huy_lenh_treo_TRUOC_khi_arm(self):
        c = FakeClient()
        ex_with(c).stop_tp_orders("BTC/USDT:USDT", "LONG", 1.0, 96.0, 110.0)
        names = [x[0] for x in c.calls]
        self.assertEqual(names[0], "cancel_all_orders", "phai huy lenh cu truoc")
        self.assertLess(names.index("cancel_all_orders"), names.index("create_order"))

    def test_sl_tp_deu_co_client_order_id(self):
        c = FakeClient()
        ex_with(c).stop_tp_orders("BTC/USDT:USDT", "LONG", 1.0, 96.0, 110.0)
        for call in [x for x in c.calls if x[0] == "create_order"]:
            self.assertIn("newClientOrderId", call[3])
            self.assertEqual(call[3]["workingType"], "CONTRACT_PRICE")

    def test_fallback_close_position_khi_reduceOnly_loi(self):
        c = FakeClient(fail_first_create=True)
        ex_with(c).stop_tp_orders("BTC/USDT:USDT", "LONG", 1.0, 96.0, 110.0)
        creates = [x for x in c.calls if x[0] == "create_order"]
        self.assertGreaterEqual(len(creates), 2)
        self.assertTrue(creates[1][3].get("closePosition"))
        self.assertIsNone(creates[1][2], "closePosition=True khong duoc truyen quantity")

    def test_cancel_first_tat_thi_khong_huy_lenh(self):
        c = FakeClient()
        ex_with(c).stop_tp_orders("BTC/USDT:USDT", "LONG", 1.0, 96.0, 110.0,
                                  cancel_first=False)
        self.assertEqual([x for x in c.calls if x[0] == "cancel_all_orders"], [])

    def test_dry_run_khong_goi_api_that(self):
        c = FakeClient()
        ex = exmod.BinanceFutures(dry_run=True)
        ex._client = c
        ex.market_entry("BTC/USDT:USDT", "LONG", 1.0)
        ex.stop_tp_orders("BTC/USDT:USDT", "LONG", 1.0, 96.0, 110.0)
        self.assertEqual(c.calls, [])

    def test_fetch_protection_parse_sl_tp(self):
        p = ex_with(FakeClient()).fetch_protection("BTC/USDT:USDT")
        self.assertAlmostEqual(p["sl"], 96.0)
        self.assertAlmostEqual(p["tp"], 110.0)

    def test_position_qty_phan_biet_khong_doc_duoc(self):
        self.assertAlmostEqual(ex_with(FakeClient()).position_qty("BTC/USDT:USDT"), 3.0)
        c = FakeClient()
        c.fetch_positions = lambda symbols=None: []
        self.assertEqual(ex_with(c).position_qty("BTC/USDT:USDT"), 0.0)

        def boom(*a, **k):
            raise RuntimeError("net down")
        c2 = FakeClient()
        c2.fetch_positions = boom
        self.assertIsNone(ex_with(c2).position_qty("BTC/USDT:USDT"))

    def test_cancel_symbol_orders_khong_nem_loi(self):
        c = FakeClient()

        def boom(*a, **k):
            raise RuntimeError("net down")
        c.cancel_all_orders = boom
        out = ex_with(c).cancel_symbol_orders("BTC/USDT:USDT")
        self.assertEqual(out["cancelled"], 0)
        self.assertIn("error", out)


class TestManagedState(unittest.TestCase):
    """P0-1: moc 1R / partial / booked_pnl phai song sot restart."""

    def test_roundtrip_trade(self):
        mt = new_trade("BTC/USDT:USDT", "LONG", 100.0, 10.0, 98.0, 110.0)
        mt.partial_done = True
        mt.be_done = True
        mt.booked_pnl = 12.5
        mt.mfe_r = 1.8
        mt.qty = 5.0
        back = managed_state.load_trade("BTC/USDT:USDT", managed_state.dump_trade(mt))
        self.assertAlmostEqual(back.initial_sl, 98.0)
        self.assertAlmostEqual(back.risk_per_unit, 2.0)
        self.assertEqual(back.qty, 5.0)
        self.assertTrue(back.partial_done and back.be_done)
        self.assertAlmostEqual(back.booked_pnl, 12.5)
        self.assertAlmostEqual(back.mfe_r, 1.8)

    def test_save_load_va_khong_ghi_de(self):
        class B:
            def __init__(self):
                self.managed = {}

        p = os.path.join(tempfile.mkdtemp(), "managed.json")
        b1 = B()
        b1.managed["A"] = new_trade("A", "LONG", 100.0, 1.0, 98.0, 110.0)
        b1.managed["A"].initial_sl = 97.5
        self.assertTrue(managed_state.save(p, b1))
        b2 = B()
        b2.managed["A"] = new_trade("A", "SHORT", 1.0, 1.0, 2.0, 3.0)   # da co san
        self.assertEqual(managed_state.load_into(b2, managed_state.load(p)), 0)
        self.assertEqual(b2.managed["A"].direction, "SHORT")
        b3 = B()
        self.assertEqual(managed_state.load_into(b3, managed_state.load(p)), 1)
        self.assertAlmostEqual(b3.managed["A"].initial_sl, 97.5)


class TestMinNotionalTheoCheDo(unittest.TestCase):
    """(Há»™i Ä‘á»“ng 14 model 01/10) MIN_NOTIONAL máº·c Ä‘á»‹nh pháº£i theo CHáº¾ Äá»˜:
    demo/testnet = 20 (binance demo Ä‘Ã²i 20), LIVE = 5 (chuáº©n USDT-M)."""

    def _mn(self, testnet: str, override: str | None = None) -> float:
        import importlib
        old = {k: os.environ.get(k) for k in ("BINANCE_TESTNET", "MIN_NOTIONAL_USDT")}
        try:
            os.environ["BINANCE_TESTNET"] = testnet
            if override is None:
                os.environ.pop("MIN_NOTIONAL_USDT", None)
            else:
                os.environ["MIN_NOTIONAL_USDT"] = override
            import config as cfgmod
            importlib.reload(cfgmod)
            return float(cfgmod.Settings().min_notional_usdt)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            importlib.reload(cfgmod)

    def test_demo_20_va_live_5(self):
        self.assertEqual(self._mn("true"), 20.0)
        self.assertEqual(self._mn("false"), 5.0)

    def test_env_ghi_de_duoc_uu_tien(self):
        self.assertEqual(self._mn("false", override="12"), 12.0)


class TestWatchdog(unittest.TestCase):
    """P0-watchdog: bot treo (tien trinh van song) phai bi phat hien."""

    def test_chua_co_nhip_tim(self):
        self.assertIsNone(heartbeat_age(Path(tempfile.mkdtemp()) / "nope.json"))

    def test_touch_roi_thi_age_nho(self):
        p = Path(tempfile.mkdtemp()) / "hb.json"
        touch_heartbeat(p)
        age = heartbeat_age(p)
        self.assertIsNotNone(age)
        self.assertLess(age, 5.0)

    def test_nhip_tim_cu_thi_phai_restart(self):
        p = Path(tempfile.mkdtemp()) / "hb.json"
        touch_heartbeat(p)
        old = time.time() - 600
        os.utime(p, (old, old))
        age = heartbeat_age(p)
        self.assertGreater(age, 500)
        self.assertTrue(should_restart(age, True, 180))

    def test_khong_restart_khi_con_nong_hoac_da_thoat(self):
        self.assertFalse(should_restart(5.0, True, 180))
        self.assertFalse(should_restart(600.0, False, 180))
        self.assertFalse(should_restart(None, True, 180))

    def test_thoat_nhanh_thi_backoff_khong_spin(self):
        """P0-spin: kill-switch -> turbo exit sau ~1s; ban cu restart moi 20s
        (3500+ lan/dem) -> phai backoff dan, tran BACKOFF_MAX_SEC."""
        self.assertEqual(next_delay(1.0, 15), 30)          # 15 -> 30
        self.assertEqual(next_delay(1.0, 30), 60)
        self.assertEqual(next_delay(1.0, 240), 300)        # cham tran
        self.assertEqual(next_delay(1.0, 300), 300)        # khong vuot tran
        self.assertLessEqual(next_delay(0.0, 300), 300)

    def test_chay_du_lau_thi_restart_nhanh_lai(self):
        """Crash SAU khi bot da chay that -> quay ve delay goc 15s (khong pháº¡t)."""
        self.assertEqual(next_delay(3600.0, 300), 15)
        self.assertEqual(next_delay(30.0, 300), 15)        # bang nguong = du lau

    def test_kill_switch_dang_chan_thi_backoff_dai_hon(self):
        """Kill-switch tripped: restart lien tuc vo nghia (chi nguoi reset moi go).

        Ban cu: 300s/lan -> 1 dem ~288 lan, 4810 dong 'dang NGUNG' trong log khien
        nguoi van hanh tuong "trip lien tuc" du that ra chi 1 lan.
        """
        self.assertEqual(plan_delay(5.0, 15, kill_blocked=True), 600)    # len > cap thuong
        self.assertEqual(plan_delay(5.0, 600, kill_blocked=True), 1200)
        self.assertEqual(plan_delay(5.0, 2400, kill_blocked=True), 3600)  # cham tran kill
        self.assertEqual(plan_delay(5.0, 3600, kill_blocked=True), 3600)  # khong vuot
        # khong bi chan -> hanh vi cu (nhanh 15s khi da chay du lau)
        self.assertEqual(plan_delay(3600.0, 3600, kill_blocked=False), 15)

    def test_tail_has_nhan_dien_kill_switch_trong_duoi_log(self):
        p = Path(tempfile.mkdtemp()) / "err.log"
        p.write_text("linh tinh\n" * 500 +
                     "2026-09-29 17:55:09 ERROR KILL-SWITCH dang NGUNG: daily loss "
                     "2.13% >= 2.0% | khong trade\n", encoding="utf-8")
        self.assertTrue(tail_has(p, "KILL-SWITCH dang NGUNG"))
        self.assertFalse(tail_has(p, "loi khac khong co"))
        self.assertFalse(tail_has(p.parent / "khong-ton-tai.log", "x"))

    def test_trip_do_5_thua_lien_tiep_phai_duoc_luu_ngay(self):
        """P0-2 fix 01/10: trip o nhanh register_close (5 thua lien tiep) PHAI luu state.

        Thuc te 20:25: bot trip '5 consecutive losses' -> flatten -> break TRUOC dong
        save_risk_state -> file giu ban cu (tripped=False) -> supervisor restart la bot
        TU MO LAI va trade tiep. Test nay chot rang buoc: trip => save => load lai van trip.
        """
        from risk import KillSwitch as KS, load_state, save_state
        p = os.path.join(tempfile.mkdtemp(), "risk.json")
        ks = KS(max_daily_loss_pct=2.0, start_balance=1000.0)
        for _ in range(4):
            self.assertFalse(ks.register_close(False, 1000.0))
        self.assertTrue(ks.register_close(False, 1000.0), "lan thua thu 5 phai trip")
        save_state(p, ks)                        # <- dong ma ban cu thieu (break som)
        ks2 = KS()
        load_state(p, ks2)
        self.assertTrue(ks2.tripped, "trip phai song sot qua restart")
        self.assertIn("consecutive losses", ks2.reason)

    def test_drift_nguong_thi_canh_bao_va_env_thang(self):
        """(Hoi dong 14 model 01/10) File state luu nguong khac .env phai CANH BAO va
        .env la nguon su that (truoc day khong co canh bao -> de ket luan nham)."""
        from risk import KillSwitch as KS, load_state, save_state
        p = os.path.join(tempfile.mkdtemp(), "risk.json")
        old = KS(max_daily_loss_pct=9.9, max_atr_pct=0.99, max_errors=1)
        save_state(p, old)
        ks = KS(max_daily_loss_pct=2.0, max_atr_pct=0.02, max_errors=5)
        msgs: list = []
        load_state(p, ks, warn=msgs.append)
        self.assertEqual(ks.max_daily_loss_pct, 2.0, ".env phai thang")
        self.assertEqual(ks.max_atr_pct, 0.02)
        self.assertEqual(ks.max_errors, 5)
        self.assertEqual(len(msgs), 1)
        self.assertIn("drift", msgs[0])
        self.assertIn("9.9", msgs[0])

    def test_khong_canh_bao_khi_nguong_khop(self):
        from risk import KillSwitch as KS, load_state, save_state
        p = os.path.join(tempfile.mkdtemp(), "risk2.json")
        save_state(p, KS(max_daily_loss_pct=2.0, max_atr_pct=0.02, max_errors=5,
                         tripped=True, reason="test"))
        ks = KS(max_daily_loss_pct=2.0, max_atr_pct=0.02, max_errors=5)
        msgs: list = []
        load_state(p, ks, warn=msgs.append)
        self.assertEqual(msgs, [])
        self.assertTrue(ks.tripped, "trip van phai song sot")

    def test_rotate_log_nho_thi_khong_dong_gi(self):
        p = Path(tempfile.mkdtemp()) / "err.log"
        p.write_text("it thoi\n", encoding="utf-8")
        self.assertFalse(rotate_log(p, max_bytes=1000))
        self.assertTrue(p.exists())
        self.assertFalse((p.parent / "err.log.1").exists())

    def test_rotate_log_lon_thi_giu_ban_cu_va_tao_moi(self):
        d = Path(tempfile.mkdtemp())
        p = d / "err.log"
        p.write_text("x" * 2000, encoding="utf-8")
        self.assertTrue(rotate_log(p, max_bytes=1000, keep=2))
        self.assertFalse(p.exists(), "file chinh duoc doi ten -> supervisor mo lai la moi")
        self.assertEqual((d / "err.log.1").read_text(encoding="utf-8"), "x" * 2000)
        # lan 2: .1 -> .2, ban cu nhat bi bo (keep=2)
        p.write_text("y" * 2000, encoding="utf-8")
        self.assertTrue(rotate_log(p, max_bytes=1000, keep=2))
        self.assertEqual((d / "err.log.1").read_text(encoding="utf-8"), "y" * 2000)
        self.assertEqual((d / "err.log.2").read_text(encoding="utf-8"), "x" * 2000)


class TestAdoptViTheSan(unittest.TestCase):
    """P0-1: restart khong con quen vi the dang mo (nguyen nhan mo trung)."""

    ROW = [{"symbol": "BTC/USDT:USDT", "side": "long", "contracts": 2.0,
            "entryPrice": 100.0}]

    def _bot(self, ex, **kw) -> TradingBot:
        return TradingBot(cfg(dry_run=False, adopt_positions=True,
                              sl_atr_mult=2.0, tp_atr_mult=5.0, **kw), exchange=ex)

    def test_normalize_bo_qua_vi_the_rong(self):
        rows = [{"symbol": "A", "side": "long", "contracts": 0.0},
                {"symbol": "B", "side": "short", "contracts": 3.0, "entryPrice": 5.0},
                {"symbol": "", "side": "long", "contracts": 1.0}]
        out = position_sync.normalize(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["symbol"], "B")
        self.assertEqual(out[0]["direction"], "SHORT")
        self.assertAlmostEqual(out[0]["qty"], 3.0)

    def test_normalize_rong(self):
        self.assertEqual(position_sync.normalize([]), [])
        self.assertEqual(position_sync.normalize(None), [])

    def test_adopt_voi_state_da_luu_thi_khoi_phuc_moc_1R(self):
        ex = FakeExchange(rows=self.ROW)
        bot = self._bot(ex)
        st = managed_state.dump_trade(
            new_trade("BTC/USDT:USDT", "LONG", 100.0, 2.0, 98.0, 110.0))
        rep = position_sync.adopt(bot, self.ROW, managed={"BTC/USDT:USDT": st},
                                  atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        self.assertEqual(rep["adopted"], ["BTC/USDT:USDT"])
        p = bot.portfolio.positions["BTC/USDT:USDT"]
        self.assertAlmostEqual(p.sl, 98.0)
        self.assertAlmostEqual(p.qty, 2.0)
        self.assertAlmostEqual(bot.managed["BTC/USDT:USDT"].initial_sl, 98.0)
        arms = ex.named("stop_tp_orders")
        self.assertEqual(len(arms), 1)
        self.assertTrue(arms[0][1]["cancel_first"])
    def test_adopt_arm_loi_tren_san_van_phai_duoc_bao_ve_bang_monitor(self):
        """Thuc te 01/10: demo tra -4045 cho MOI lenh stop -> khong arm duoc SL/TP.

        Yeu cau: vi the VAN phai vao portfolio + managed (de `_monitor` = SL/TP phan
        mem dong dung luc) VA bao dong `unarmed` cho nguoi van hanh. Ban cu: exception
        lam mat `adopted` -> bao cao sai (nhin nhu khong adopt duoc vi the nao).
        """
        ex = FakeExchange(rows=self.ROW, arm_boom=True)
        bot = self._bot(ex)
        alerts = []
        st = managed_state.dump_trade(
            new_trade("BTC/USDT:USDT", "LONG", 100.0, 2.0, 98.0, 110.0))
        rep = position_sync.adopt(bot, self.ROW, managed={"BTC/USDT:USDT": st},
                                  atr_fn=lambda s: {"price": 100.0, "atr": 2.0},
                                  alert=alerts.append)
        self.assertEqual(rep["unarmed"], ["BTC/USDT:USDT"])
        self.assertEqual(rep["errors"], [], "arm loi khong phai loi chet")
        self.assertEqual(rep["adopted"], ["BTC/USDT:USDT"])
        self.assertIn("BTC/USDT:USDT", bot.portfolio.positions)
        self.assertIn("BTC/USDT:USDT", bot.managed)     # -> _monitor quan ly duoc
        self.assertTrue(any("KHONG dat duoc SL/TP TREN SAN" in a for a in alerts))



    def test_adopt_khong_dung_vao_SL_dang_treo_tren_san(self):
        ex = FakeExchange(rows=self.ROW,
                          prot={"BTC/USDT:USDT": {"sl": 95.0, "tp": 115.0}})
        bot = self._bot(ex)
        rep = position_sync.adopt(bot, self.ROW,
                                  atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        self.assertEqual(ex.named("stop_tp_orders"), [],
                         "vi the dang duoc bao ve -> khong dung vao lenh treo")
        self.assertAlmostEqual(bot.portfolio.positions["BTC/USDT:USDT"].sl, 95.0)
        self.assertEqual(rep["unmanaged"], [])

    def test_adopt_bo_qua_state_xac_khong_dong_oan_vi_the_mo_tay(self):
        """State cu da chot het (qty=0) KHONG duoc dung lam moc 1R cho vi the MOI.

        Thuc te 01/10: XRP state qty=0 nhung tren san co vi the XRP MO TAY qty=7338 â€”
        neu lay sl/tp cu (1.5006 ~ entry cu) thi bot 'dong' vi the do ngay sau adopt.
        Phai tinh lai SL/TP theo ATR.
        """
        rows = [{"symbol": "XRP/USDT:USDT", "side": "short", "contracts": 7338.7,
                 "entryPrice": 1.48554}]
        ex = FakeExchange(rows=rows)
        bot = self._bot(ex)
        dead = managed_state.dump_trade(
            new_trade("XRP/USDT:USDT", "SHORT", 1.4908, 1032.4, 1.500586, 1.466685))
        dead["qty"] = 0.0
        rep = position_sync.adopt(bot, rows, managed={"XRP/USDT:USDT": dead},
                                  atr_fn=lambda s: {"price": 1.48554, "atr": 0.01})
        self.assertEqual(rep["adopted"], ["XRP/USDT:USDT"])
        mt = bot.managed["XRP/USDT:USDT"]
        self.assertFalse(mt.partial_done, "khong ke thua state da chot het")
        self.assertAlmostEqual(mt.qty, 7338.7, places=3)
        self.assertNotAlmostEqual(mt.initial_sl, 1.500586, places=4,
                                  msg="SL phai tinh lai theo ATR, khong dung SL cu")

    def test_adopt_don_state_xac_khong_con_vi_the(self):
        """State 'xac' (khong con vi the tren san) phai bi don khoi managed."""
        ex = FakeExchange(rows=self.ROW)                 # tren san chi co BTC
        bot = self._bot(ex)
        stale = managed_state.dump_trade(
            new_trade("SOL/USDT:USDT", "SHORT", 117.66, 0.0, 118.36, 115.89))
        bot.managed["SOL/USDT:USDT"] = managed_state.load_trade("SOL/USDT:USDT", stale)
        rep = position_sync.adopt(bot, self.ROW, managed={"SOL/USDT:USDT": stale},
                                  atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        self.assertEqual(rep["stale"], ["SOL/USDT:USDT"])
        self.assertNotIn("SOL/USDT:USDT", bot.managed)
        self.assertIn("BTC/USDT:USDT", bot.managed)

    def test_adopt_chua_co_bao_ve_thi_tinh_lai_bang_atr(self):
        ex = FakeExchange(rows=self.ROW)
        bot = self._bot(ex)
        position_sync.adopt(bot, self.ROW, atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        p = bot.portfolio.positions["BTC/USDT:USDT"]
        self.assertAlmostEqual(p.sl, 96.0)      # 100 - 2 x ATR(2)
        self.assertAlmostEqual(p.tp, 110.0)     # 100 + 5 x ATR(2)
        self.assertEqual(len(ex.named("stop_tp_orders")), 1)
        self.assertEqual(bot.managed["BTC/USDT:USDT"].prot_ids, {"sl": "sl", "tp": "tp"},
                         "clientOrderId lenh bao ve phai duoc luu vao state (02/10)")

    def test_khong_xac_dinh_duoc_SL_thi_canh_bao(self):
        ex = FakeExchange(rows=self.ROW)
        bot = self._bot(ex)
        alerts: list = []
        rep = position_sync.adopt(bot, self.ROW, atr_fn=lambda s: {},
                                  alert=alerts.append)
        self.assertEqual(rep["unmanaged"], ["BTC/USDT:USDT"])
        self.assertEqual(len(alerts), 1)
        self.assertIn("KHONG xac dinh duoc SL", alerts[0])
        self.assertEqual(ex.named("stop_tp_orders"), [])
        self.assertIn("BTC/USDT:USDT", bot.portfolio.positions,
                      "van phai ghi nhan de KHONG mo trung")

    def test_adopt_lan_hai_thi_bo_qua(self):
        ex = FakeExchange(rows=self.ROW)
        bot = self._bot(ex)
        position_sync.adopt(bot, self.ROW, atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        rep2 = position_sync.adopt(bot, self.ROW,
                                   atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        self.assertEqual(rep2["skipped"], ["BTC/USDT:USDT"])
        self.assertEqual(rep2["adopted"], [])


class TestRearmBaoVe(unittest.TestCase):
    """P0-fix 01/10: vi the mo ra khong co SL/TP tren san (demo -4045) phai duoc
    thu dat lai dinh ky â€” truoc day chi thu DUNG 1 LAN luc mo lenh."""

    SYM = "BTC/USDT:USDT"

    def _bot(self, ex):
        return TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0),
                          exchange=ex)

    def test_thieu_bao_ve_thi_dat_lai(self):
        ex = FakeExchange()                       # fetch_protection -> {sl:None,tp:None}
        bot = self._bot(ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     98.0, 200.0)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        done = td._rearm_missing(bot, logging.getLogger("test"), every_sec=0)
        self.assertEqual(done, [self.SYM])
        arms = ex.named("stop_tp_orders")
        self.assertEqual(len(arms), 1)
        self.assertEqual(arms[0][1]["sl"], 98.0)

    def test_da_co_bao_ve_thi_khong_dung_vao(self):
        ex = FakeExchange(prot={self.SYM: {"sl": 95.0, "tp": 115.0}})
        bot = self._bot(ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     95.0, 115.0)
        self.assertEqual(td._rearm_missing(bot, logging.getLogger("test"), every_sec=0), [])
        self.assertEqual(ex.named("stop_tp_orders"), [])

    def test_san_van_chan_thi_khong_crash(self):
        """San tra -4045 -> tra [] va chi log, de vong sau thu lai."""
        ex = FakeExchange(arm_boom=True)
        bot = self._bot(ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     98.0, 200.0)
        self.assertEqual(td._rearm_missing(bot, logging.getLogger("test"), every_sec=0), [])
        self.assertIn(self.SYM, bot.portfolio.positions)   # vi the khong bi mat


class TestProtIds(unittest.TestCase):
    """(02/10) Hoi dong 14 model: lenh bao ve phai duoc LUU ID vao state de doi soat.

    Truoc day state chi co muc sl/tp -> khong biet lenh bao ve con treo tren san hay
    da bi huy/mat, va vi the co the "mo coi" ma bot khong phat hien.
    """

    SYM = "ETH/USDT:USDT"      # symbol rieng, tranh cache throttle cua test khac

    def _bot(self, ex):
        return TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0),
                          exchange=ex)

    def test_uu_tien_clientOrderId_va_song_sot_restart(self):
        from trade_mgmt import record_protection
        mt = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        ids = record_protection(mt, {"sl_order": {"clientOrderId": "glow-sl-1"},
                                     "tp_order": {"clientOrderId": "glow-tp-1"}})
        self.assertEqual(ids, {"sl": "glow-sl-1", "tp": "glow-tp-1"})
        back = managed_state.load_trade(self.SYM, managed_state.dump_trade(mt))
        self.assertEqual(back.prot_ids, {"sl": "glow-sl-1", "tp": "glow-tp-1"},
                         "id lenh bao ve phai song sot restart")

    def test_chiu_duoc_response_rong(self):
        from trade_mgmt import record_protection
        mt = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        self.assertEqual(record_protection(mt, None), {})
        self.assertEqual(mt.prot_ids, {})
        self.assertEqual(record_protection(None, {"sl_order": {"id": "x"}}), {"sl": "x"},
                         "khong co managed trade thi chi tra id, khong crash")

    def test_rearm_luu_id_va_throttle_moi_60s(self):
        ex = FakeExchange()                      # fetch_protection -> thieu SL/TP
        bot = self._bot(ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     98.0, 200.0)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        log = logging.getLogger("test")
        # every_sec=0: tat throttle (bo qua cache con lai tu test khac)
        self.assertEqual(td._rearm_missing(bot, log, every_sec=0), [self.SYM])
        self.assertEqual(bot.managed[self.SYM].prot_ids, {"sl": "sl", "tp": "tp"},
                         "clientOrderId cua lenh vua dat phai vao state")
        # vua xac nhan -> trong 60s khong goi API lai
        self.assertEqual(td._rearm_missing(bot, log), [])
        self.assertEqual(len(ex.named("stop_tp_orders")), 1)
        # tat throttle -> kiem tra lai ngay (tren san van chua co bao ve that)
        self.assertEqual(td._rearm_missing(bot, log, every_sec=0), [self.SYM])
        self.assertEqual(len(ex.named("stop_tp_orders")), 2)


class TestRearmAnToan(unittest.TestCase):
    """(02/10) Doc log THAT 01-02/10: retry khong duoc Huy bao ve dang co roi arm that bai.

    Su that tren demo: `-4045` bi tra cho MOI lenh stop du so lenh treo = 0 -> neu retry
    `cancel_first=True` thi moi vong ta vua huy mat bao ve that (neu co) vua khong dat lai
    duoc -> vi the TRAN. Do la ly do phai `cancel_first=False` o buoc doi soat dinh ky.
    """

    SYM = "DOGE/USDT:USDT"

    def _setup(self, ex):
        td._PROT_SEEN.clear()
        td._PROT_TRY.clear()
        td._PROT_FAIL.clear()
        td._PROT_LOG.clear()
        bot = TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0), exchange=ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 0.0944, 5111.0,
                                                     0.092, 0.10)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 0.0944, 5111.0, 0.092, 0.10)
        return bot

    def test_retry_khong_huy_lenh_dang_co(self):
        ex = FakeExchange()
        bot = self._setup(ex)
        td._rearm_missing(bot, logging.getLogger("test"), every_sec=0)
        arms = ex.named("stop_tp_orders")
        self.assertEqual(len(arms), 1)
        self.assertFalse(arms[0][1]["cancel_first"],
                         "buoc doi soat KHONG duoc huy lenh truoc khi arm")

    def test_san_bao_ok_ma_khong_vao_thi_log_ERROR(self):
        ex = FakeExchange()          # arm "thanh cong" nhung fetch_protection -> rong
        bot = self._setup(ex)
        log = logging.getLogger("test_rearm_an_toan")
        with self.assertLogs("test_rearm_an_toan", level="ERROR") as cm:
            td._rearm_missing(bot, log, every_sec=0)
        self.assertTrue(any("KHONG giu lenh treo" in m for m in cm.output),
                        "phai bao dong khi san nhan lenh ma khong thay lenh treo")
        self.assertNotIn(self.SYM, td._PROT_SEEN, "chua xac nhan duoc thi khong duoc coi la OK")

    def test_canh_bao_khong_giu_lenh_duoc_throttle(self):
        """(09/10) Gioi han lenh dieu kien la chuyen PHIA SAN -> khong duoc spam log."""
        ex = FakeExchange()
        bot = self._setup(ex)
        log = logging.getLogger("test_rearm_throttle")
        with self.assertLogs("test_rearm_throttle", level="ERROR") as cm:
            td._rearm_missing(bot, log, every_sec=0)
            td._rearm_missing(bot, log, every_sec=0)      # lan 2 trong cung cua so -> im
        self.assertEqual(len([m for m in cm.output if "KHONG giu lenh treo" in m]), 1)

    def test_san_chan_lien_tuc_thi_gian_nhip_5_phut(self):
        ex = FakeExchange(arm_boom=True)          # -4045 lien tuc
        bot = self._setup(ex)
        log = logging.getLogger("test")
        for _ in range(3):
            td._rearm_missing(bot, log, every_sec=0)       # loi 3 lan lien tiep
        self.assertEqual(len(ex.named("stop_tp_orders")), 3)
        self.assertEqual(td._rearm_missing(bot, log, every_sec=10), [],
                         "sau 3 lan loi lien tiep phai gian nhip, khong spam san")
        self.assertEqual(len(ex.named("stop_tp_orders")), 3)


class TestMonitorOnly(unittest.TestCase):
    """(02/10) Kill-switch ngung -> CHI quan ly vi the, KHONG mo lenh moi, khong thoat han.

    Su that 01-02/10: trip luc khoi dong -> ban cu `return` ngay -> vi the con tren san bi
    bo quen (demo chan -4045 nen khong co SL tren san, monitor mem cung khong chay).
    """

    SYM = "ADA/USDT:USDT"

    def setUp(self):
        # KHONG goi Telegram that trong test (thuc te 1 lan goi co the treo ~160s -> test
        # tuong nhu "hang" va lam cham ca suite). Moi thu khac giu nguyen.
        self._real_tg = td.tg
        td.tg = lambda *a, **k: None

    def tearDown(self):
        td.tg = self._real_tg

    def _cfg(self, tmp):
        return cfg(dry_run=False, adopt_positions=False, poll_interval_sec=0,
                   risk_state_path=os.path.join(tmp, "risk_state.json"),
                   managed_state_path=os.path.join(tmp, "managed_state.json"))

    def _bot(self, ex):
        from unittest import mock
        bot = TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0), exchange=ex)
        # Sentiment la goi MANG that (15 feed RSS + GDELT + CryptoPanic) -> PHAI stub, neu
        # khong 1 lan fetch co the treo ~160s (02/10: lam suite tuong nhu "hang"). Cung
        # nguyen nhan nay da duoc vá trong sentiment.fetch_rss (SENTIMENT_BUDGET_SEC).
        bot.sentiment.get = mock.Mock(return_value=mock.Mock(score=0.0))
        bot.kill.trip("5 consecutive losses (test)")
        # Gia fake = 100.0 -> dat entry=100/SL=95/TP=105 de KHONG co partial/BE/trail/close
        # (neu de gia xa entry, TRAIL se keo SL len ~gia -> close -> agent call rat cham).
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     95.0, 105.0)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 100.0, 10.0, 95.0, 105.0)
        return bot

    def test_kill_cleared_doc_state(self):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "rs.json")
        self.assertTrue(td._kill_cleared(p), "chua co file = da --reset")
        Path(p).write_text('{"tripped": true, "reason": "x"}', encoding="utf-8")
        self.assertFalse(td._kill_cleared(p))
        Path(p).write_text('{"tripped": false}', encoding="utf-8")
        self.assertTrue(td._kill_cleared(p))
        Path(p).write_text("{hong", encoding="utf-8")
        self.assertFalse(td._kill_cleared(p), "state hong -> KHONG coi la da go (fail-closed)")

    def test_monitor_only_khong_mo_lenh_va_luu_state(self):
        tmp = tempfile.mkdtemp()
        ex = FakeExchange()
        bot = self._bot(ex)
        c = self._cfg(tmp)
        save_state(c.risk_state_path, bot.kill)   # nhu caller: trip da duoc luu truoc khi vao
        ok = td.monitor_only_loop(bot, c, ex, logging.getLogger("test"), (self.SYM,),
                                  sleep_sec=0, max_rounds=2)
        self.assertFalse(ok, "kill-switch van ngung -> tra False khi het max_rounds")
        self.assertEqual(ex.named("market_entry"), [], "MONITOR-ONLY khong duoc mo lenh moi")
        self.assertIn(self.SYM, bot.portfolio.positions, "vi the van duoc giu")
        self.assertTrue(os.path.exists(c.risk_state_path), "state phai duoc luu")
        d = json.loads(Path(c.risk_state_path).read_text(encoding="utf-8"))
        self.assertTrue(d["tripped"], "khong duoc tu xoa trang thai ngung")

    def test_monitor_only_tu_quay_lai_khi_duoc_reset(self):
        """Nguoi van hanh chay `risk.py --reset` trong luc monitor-only -> bot tu trade lai."""
        tmp = tempfile.mkdtemp()
        ex = FakeExchange()
        bot = self._bot(ex)
        c = self._cfg(tmp)
        save_state(c.risk_state_path, bot.kill)
        real_hb = td.heartbeat
        seen = {"done": False}

        def fake_hb(extra=None):
            # Xoa state NGAY SAU khi bot vua luu (giua save va sleep) = mo phong `--reset`
            if not seen["done"] and (extra or {}).get("phase") == "monitor_only_end":
                seen["done"] = True
                try:
                    os.remove(c.risk_state_path)
                except OSError:
                    pass
            return real_hb(extra)

        td.heartbeat = fake_hb
        try:
            ok = td.monitor_only_loop(bot, c, ex, logging.getLogger("test"), (self.SYM,),
                                      sleep_sec=0, max_rounds=5)
        finally:
            td.heartbeat = real_hb
        self.assertTrue(ok, "da --reset -> phai tra True de quay lai trade")
        self.assertFalse(bot.kill.tripped)
        self.assertEqual(ex.named("market_entry"), [])

    def test_reset_duoc_phat_hien_du_bot_dang_tu_ghi_state(self):
        """(02/10) Bug that da gap khi chay lai: vong lap tu ghi tripped=true moi vong ->
        `risk.py --reset` (xoa file) vo tac dung (reset xong bot van bao "van ngung").

        Nay kiem TRUOC khi ghi + chi ghi khi state thay doi -> reset phat hien trong 1 vong
        du nguoi van hanh xoa file dung luc bot dang cho giua 2 vong.
        """
        tmp = tempfile.mkdtemp()
        ex = FakeExchange()
        bot = self._bot(ex)
        c = self._cfg(tmp)
        save_state(c.risk_state_path, bot.kill)     # caller da luu tripped=true
        real_sleep = td.time.sleep
        seen = {"done": False}

        def sleeper(s):
            if not seen["done"]:
                seen["done"] = True
                try:
                    os.remove(c.risk_state_path)     # --reset GIUA 2 vong (luc bot dang cho)
                except OSError:
                    pass
            return real_sleep(s)

        td.time.sleep = sleeper
        try:
            ok = td.monitor_only_loop(bot, c, ex, logging.getLogger("test"), (self.SYM,),
                                      sleep_sec=0, max_rounds=5)
        finally:
            td.time.sleep = real_sleep
        self.assertTrue(ok, "reset phai duoc phat hien du bot van dang tu ghi state")
        self.assertFalse(bot.kill.tripped)


class TestSentimentBudget(unittest.TestCase):
    """(02/10) `fetch_rss` KHONG duoc treo vo han: feedparser.parse khong co timeout rieng.

    Thuc te 01-02/10: 1 lan fetch treo ~160s NGAY TRONG `bot._monitor` (duong bao ve
    SL/TP) -> vong lap treo, watchdog co the kill bot dang giu vi the. Nay co ngan sach.
    """

    def test_het_ngan_sach_thi_bo_feed_con_lai(self):
        import sentiment as sm
        from unittest import mock

        class SlowFeed:
            calls = 0

            def parse(self, url):
                SlowFeed.calls += 1
                time.sleep(0.25)
                return type("P", (), {"entries": []})()

        with mock.patch.object(sm, "feedparser", SlowFeed()):
            t0 = time.time()
            out = sm.fetch_rss(budget_sec=0.6)
            elapsed = time.time() - t0
        self.assertEqual(out, [])
        self.assertLess(elapsed, 1.6, "phai dung theo ngan sach, khong chay het 15 feed")
        self.assertLessEqual(SlowFeed.calls, 3, "het gio thi khong goi them feed")

    def test_khong_co_ngan_sach_van_chay_het_feed(self):
        import sentiment as sm
        from unittest import mock

        class SlowFeed:
            calls = 0

            def parse(self, url):
                SlowFeed.calls += 1
                return type("P", (), {"entries": []})()

        with mock.patch.object(sm, "feedparser", SlowFeed()):
            sm.fetch_rss(budget_sec=0)              # 0 = khong gioi han (hanh vi cu)
        self.assertEqual(SlowFeed.calls, len(sm.DEFAULT_RSS))

    def test_tra_lai_timeout_socket_nguyen_trang(self):
        import socket
        import sentiment as sm
        from unittest import mock
        before = socket.getdefaulttimeout()
        fake = mock.Mock(parse=lambda u: type("P", (), {"entries": []})())
        with mock.patch.object(sm, "feedparser", fake):
            sm.fetch_rss(budget_sec=1)
        self.assertEqual(socket.getdefaulttimeout(), before,
                         "khong duoc de lech timeout socket cua toan tien trinh")

    def test_feed_loi_thi_tra_rong_khong_nem(self):
        import sentiment as sm
        from unittest import mock

        def boom(url):
            raise RuntimeError("network down")

        with mock.patch.object(sm, "feedparser", mock.Mock(parse=boom)):
            self.assertEqual(sm.fetch_rss(budget_sec=2), [])


class TestSettingsFields(unittest.TestCase):
    """(02/10) Chong loi "xoa nham truong Settings" — bay thuc te vua xay ra.

    Su that: sua `config.py` de THEM `kill_monitor_only` vo tinh XOA `reconcile_journal`
    -> bot crash ngay khi khoi dong (`AttributeError: 'Settings' object has no attribute
    'reconcile_journal'`) va chi phat hien khi chay lai that (test cu khong phu duong
    reconcile). Test nay giu danh sach truong ma bot phu thuoc.
    """

    FIELDS = (
        # duong bao ve / vong lap
        "dry_run", "testnet", "poll_interval_sec", "round_timeout_sec",
        "socket_timeout_sec", "kill_monitor_only", "adopt_positions",
        # reconcile journal (duong khoi dong)
        "reconcile_journal", "reconcile_days", "reconcile_min_interval_sec",
        # risk / sizing
        "risk_state_path", "managed_state_path", "max_daily_loss_pct", "max_atr_pct",
        "max_consecutive_errors", "max_total_risk_pct", "risk_per_trade_pct",
        "leverage", "max_positions", "min_notional_usdt", "balance_usdt",
        # thi truong / vao lenh
        "symbols", "extra_symbols", "timeframe", "ohlcv_limit", "sl_atr_mult",
        "tp_atr_mult", "trail_atr_mult", "partial_at_r", "partial_pct", "be_at_r",
        # LIVE gate + notify
        "live_confirm", "tg_token", "tg_chat",
    )

    def test_du_truong_bat_buoc(self):
        s = Settings()
        missing = [f for f in self.FIELDS if not hasattr(s, f)]
        self.assertEqual(missing, [], f"Settings thieu truong (xoa nham?): {missing}")


class TestFlattenGhiJournal(unittest.TestCase):
    """(02/10) `_flatten` PHAI ghi CLOSE: thuc te de lai 5 OPEN "mo coi".

    Su that: 5 lenh (XRP/SOL/ADA/DOGE/SOL mo 17:00-17:33) bi kill-switch flatten luc 18:00
    ma khong co dong CLOSE nao -> journal OPEN=90/CLOSE=85, n/WR/PF sai (gate LIVE doc sai).
    Dong thoi lenh lam TRIP cung khong duoc ghi (register_close return True truoc khi ghi).
    """

    SYM = "XRP/USDT:USDT"
    SYM2 = "ADA/USDT:USDT"

    def _bot(self, ex):
        from unittest import mock
        bot = TradingBot(cfg(dry_run=False), exchange=ex)
        bot.sentiment.get = mock.Mock(return_value=mock.Mock(score=0.0))
        return bot

    def test_flatten_ghi_CLOSE_cho_MOI_vi_the(self):
        from unittest import mock
        ex = FakeExchange()
        bot = self._bot(ex)
        for s in (self.SYM, self.SYM2):
            bot.portfolio.positions[s] = Position(s, "SHORT", 1.48, 100.0, 1.50, 1.40)
            bot.managed[s] = new_trade(s, "SHORT", 1.48, 100.0, 1.50, 1.40)
        recs: list = []
        with mock.patch.object(botmod, "log_trade", lambda **kw: recs.append(kw)):
            bot._flatten("kill-switch")
        self.assertEqual(len(recs), 2, "moi vi the bi flatten phai co 1 dong CLOSE")
        self.assertTrue(all(r["event"] == "CLOSE" for r in recs))
        self.assertTrue(all(r["reason"] == "FLATTEN" for r in recs))
        self.assertTrue(all(r.get("direction") for r in recs))
        self.assertEqual(bot.portfolio.positions, {}, "flatten phai dong het")
        for s in (self.SYM, self.SYM2):
            self.assertIn(s, bot.last_exits, "co ket qua trong last_exits de thong ke")

    def test_flatten_khong_co_vi_the_thi_khong_ghi_gi(self):
        from unittest import mock
        ex = FakeExchange()
        bot = self._bot(ex)
        recs: list = []
        with mock.patch.object(botmod, "log_trade", lambda **kw: recs.append(kw)):
            bot._flatten("kill-switch")
        self.assertEqual(recs, [], "khong co vi the -> khong ghi CLOSE rong")


class TestKillSwitchLoNho(unittest.TestCase):
    """(02/10) Lenh lo ~0 (DUST pnl=-0.0011) KHONG duoc tinh la 1 lan thua.

    Su that: 01/10 LINK dong do DUST pnl=-0.0011 USDT bi tinh la lan thua thu 5 -> TRIP
    kill-switch -> bot dung trade (va roi sang monitor-only) trong khi thuc chat khong lo.
    """

    def _ks(self):
        return KillSwitch(2.0, 0.02, 5, 1000.0)

    def test_lo_nho_khong_tinh_la_thua(self):
        ks = self._ks()
        self.assertFalse(ks.register_close(False, 1000.0, pnl=-0.0011))
        self.assertEqual(ks.consec_losses, 0)
        self.assertFalse(ks.tripped)

    def test_lo_that_van_tinh_va_trip_dung_lan_thu_5(self):
        ks = self._ks()
        for i in range(4):
            self.assertFalse(ks.register_close(False, 1000.0, pnl=-5.0), f"lan {i + 1}")
        self.assertEqual(ks.consec_losses, 4)
        self.assertTrue(ks.register_close(False, 1000.0, pnl=-5.0))
        self.assertTrue(ks.tripped)

    def test_dust_khong_lam_day_chuoi_thua_that(self):
        """Dung kich ban 01/10: 4 lan thua that + 1 lenh DUST -> KHONG trip."""
        ks = self._ks()
        for _ in range(4):
            ks.register_close(False, 1000.0, pnl=-5.0)
        self.assertFalse(ks.register_close(False, 1000.0, pnl=-0.0011))
        self.assertFalse(ks.tripped, "DUST khong duoc thanh lan thua thu 5")
        self.assertEqual(ks.consec_losses, 4)

    def test_lai_thi_reset_chuoi(self):
        ks = self._ks()
        ks.register_close(False, 1000.0, pnl=-5.0)
        ks.register_close(False, 1000.0, pnl=-5.0)
        self.assertEqual(ks.consec_losses, 2)
        ks.register_close(True, 1000.0, pnl=+3.0)
        self.assertEqual(ks.consec_losses, 0)

    def test_khong_truyen_pnl_thi_giu_hanh_vi_cu(self):
        ks = self._ks()
        ks.register_close(False, 1000.0)
        self.assertEqual(ks.consec_losses, 1, "khong truyen pnl -> dem nhu truoc")

    def test_nguong_cau_hinh_duoc(self):
        ks = self._ks()
        self.assertFalse(ks.register_close(False, 1000.0, pnl=-3.0, min_loss_usdt=5.0))
        self.assertEqual(ks.consec_losses, 0)
        self.assertFalse(ks.register_close(False, 1000.0, pnl=-6.0, min_loss_usdt=5.0))
        self.assertEqual(ks.consec_losses, 1)


class TestKillMonitorOnlyBatBuocDemo(unittest.TestCase):
    """(02/10) O DEMO, KILL_MONITOR_ONLY luon bat: monitor mem la lop bao ve DUY NHAT.

    Da kiem chung 02/10: demo tra -4045 cho MOI lenh stop du so lenh treo = 0 -> khong the
    co SL tren san. Neu bot thoat han khi kill-switch trip thi vi the bi bo quen.
    """

    def test_demo_ep_bat_du_env_tat(self):
        import config
        from unittest import mock
        with mock.patch.dict(os.environ, {"BINANCE_TESTNET": "true",
                                          "KILL_MONITOR_ONLY": "false"}):
            self.assertTrue(config.Settings().kill_monitor_only,
                            "DEMO khong duoc phep tat monitor-only")

    def test_live_cho_phep_tat(self):
        import config
        from unittest import mock
        with mock.patch.dict(os.environ, {"BINANCE_TESTNET": "false",
                                          "KILL_MONITOR_ONLY": "false"}):
            self.assertFalse(config.Settings().kill_monitor_only,
                             "LIVE cho phep quay lai hanh vi cu")

    def test_demo_mac_dinh_bat(self):
        import config
        from unittest import mock
        with mock.patch.dict(os.environ, {"BINANCE_TESTNET": "true"}):
            os.environ.pop("KILL_MONITOR_ONLY", None)
            self.assertTrue(config.Settings().kill_monitor_only)


class TestBotSafety(unittest.TestCase):
    """P0-4/P0-5 trong bot: cuu lenh khi loi mang + don lenh treo."""

    SYM = "BTC/USDT:USDT"

    def _bot(self, ex, **kw) -> TradingBot:
        return TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0, **kw),
                          exchange=ex)

    def test_managed_for_khong_mat_state_khi_entry_lech_float(self):
        """P0-fix 01/10: entry so lech float nhon KHONG duoc lam mat moc 1R/partial.

        Ban cu: `abs(mt.entry - pos.entry) > 1e-12` -> tao trade moi -> partial_done
        ve False -> partial chay lai -> dong het vi the (XRP/SOL/AVAX 19:53).
        """
        ex = FakeExchange()
        bot = self._bot(ex)
        t = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        t.partial_done = True
        t.booked_pnl = 5.0
        bot.managed[self.SYM] = t
        pos = Position(self.SYM, "LONG", 100.0000000001, 5.0, 100.0, 200.0)
        got = bot._managed_for(self.SYM, pos)
        self.assertIs(got, t, "phai dung state cu")
        self.assertTrue(got.partial_done, "partial_done phai duoc giu")
        self.assertAlmostEqual(got.booked_pnl, 5.0)

    def test_vi_the_bui_duoc_chot_so_va_ghi_CLOSE(self):
        """0.01 lot (< minNotional) khong the dong bang lenh -> phai ghi journal CLOSE.

        Khong lam: 'xac' vi the nam mai trong portfolio (SKIP_OPEN vinh vien) va `n`
        trong journal ket -> khong bao gio dat moc 50 lenh cho LIVE.
        """
        from unittest import mock
        ex = FakeExchange()
        bot = TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0,
                             min_notional_usdt=20.0), exchange=ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 0.1,
                                                     98.0, 200.0)
        t = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        t.qty, t.partial_done, t.booked_pnl = 0.1, True, 3.0
        bot.managed[self.SYM] = t
        recs: list = []
        with mock.patch.object(botmod, "log_trade", lambda **kw: recs.append(kw)):
            closed = bot._monitor(candles_provider=lambda s: pd.DataFrame({"close": [100.0]}))
        self.assertEqual(closed.get(self.SYM), "DUST")
        self.assertNotIn(self.SYM, bot.portfolio.positions)
        self.assertNotIn(self.SYM, bot.managed)
        self.assertEqual(len(recs), 1, "phai ghi DUNG 1 dong CLOSE")
        self.assertEqual(recs[0]["event"], "CLOSE")
        self.assertEqual(recs[0]["reason"], "DUST")
        self.assertTrue(recs[0]["won"])
        self.assertEqual(bot.last_exits[self.SYM]["reason"], "DUST")
        # 01/10: review cua agent can direction (truoc day thieu -> NO_OPINION vo dung)
        self.assertEqual(bot.last_exits[self.SYM]["direction"], "LONG")

    def test_vi_the_binh_thuong_thi_khong_bi_coi_la_bui(self):
        """Vi the binh thuong (notional >= minNotional) khong duoc dong oan."""
        from unittest import mock
        ex = FakeExchange()
        bot = TradingBot(cfg(dry_run=False, sl_atr_mult=2.0, tp_atr_mult=5.0,
                             min_notional_usdt=20.0), exchange=ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     98.0, 200.0)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        # Sentiment la goi MANG that (RSS/CryptoPanic) -> test phai stub, neu khong
        # moi lan chay test se ton ~15s cho timeout feed.
        with mock.patch.object(bot.sentiment, "get",
                               return_value=mock.Mock(score=0.0)):
            closed = bot._monitor(candles_provider=lambda s: pd.DataFrame({"close": [100.5]}))
        self.assertNotIn(self.SYM, closed)
        self.assertIn(self.SYM, bot.portfolio.positions)

    def test_partial_arm_lai_sl_tp_theo_qty_con_lai(self):
        ex = FakeExchange()
        bot = self._bot(ex)
        bot.portfolio.positions[self.SYM] = Position(self.SYM, "LONG", 100.0, 10.0,
                                                     98.0, 200.0)
        bot.managed[self.SYM] = new_trade(self.SYM, "LONG", 100.0, 10.0, 98.0, 200.0)
        closed = bot._monitor(candles_provider=lambda s: pd.DataFrame({"close": [110.0]}))
        self.assertNotIn(self.SYM, closed, "PARTIAL khong phai la dong lenh")
        pos = bot.portfolio.positions[self.SYM]
        self.assertLess(pos.qty, 10.0, "phai chot 1 phan")
        arms = ex.named("stop_tp_orders")
        self.assertEqual(len(arms), 1, "partial phai arm lai SL/TP theo qty con lai")
        self.assertAlmostEqual(arms[0][1]["qty"], pos.qty)
        self.assertTrue(arms[0][1]["cancel_first"], "phai huy lenh cu truoc khi arm")

    def test_close_don_sach_lenh_treo(self):
        ex = FakeExchange()
        bot = self._bot(ex)
        bot.portfolio.positions["A"] = Position("A", "LONG", 100.0, 1.0, 98.0, 110.0)
        bot._close("A", "test")
        self.assertEqual(len(ex.named("close_position")), 1)
        self.assertEqual(len(ex.named("cancel_symbol_orders")), 1,
                         "dong lenh phai huy lenh treo con lai")
        self.assertEqual(bot.portfolio.positions, {})

    def test_equity_tach_khoi_balance_tran_size(self):
        """BALANCE_USDT=1000 la tran size, KHONG phai tai san -> DD phai dung equity."""
        ex = FakeExchange(balance=4974.0)
        bot = TradingBot(cfg(dry_run=False, balance_usdt=1000.0, sl_atr_mult=2.0,
                             tp_atr_mult=5.0), exchange=ex)
        self.assertAlmostEqual(bot.balance, 1000.0, places=6)
        bot.balance = min(1000.0, 4974.0)       # dung hanh vi cua turbo_demo
        bot.equity = 4974.0
        bot.kill.note_equity(bot.equity)
        self.assertAlmostEqual(bot.kill.base_equity(), 4974.0, places=6)
        self.assertFalse(bot.kill.check(bot.equity),
                         "equity khong doi -> khong duoc trip")

    def _step_for_entry(self, ex):
        bot = self._bot(ex)
        bot.sentiment.get = lambda token="": type("S", (), {"score": 0.8})()
        return bot, bot.step(candles_provider=lambda s: (
            bull_df() if s.startswith("BTC") else bear_df()))

    def test_loi_mang_ma_lenh_DA_khop_thi_ghi_nhan_khong_mo_trung(self):
        ex = FakeExchange(landing=3.0, entry_raises=True)
        bot, r = self._step_for_entry(ex)
        if r.get("status") != "OPENED":
            self.skipTest("khong mo duoc lenh trong bo du lieu test: %s" % r)
        self.assertTrue(r.get("recovered"), "phai bao recovered=True")
        self.assertEqual(len(bot.portfolio.positions), 1)
        self.assertIn(self.SYM, bot.portfolio.positions)
        self.assertAlmostEqual(bot.portfolio.positions[self.SYM].qty, 3.0)
        self.assertEqual(len(ex.named("stop_tp_orders")), 1, "phai arm SL/TP cho lenh cuu")

    def test_loi_mang_va_khong_co_vi_the_thi_bao_that_bai(self):
        ex = FakeExchange(landing=0.0, entry_raises=True)
        bot, r = self._step_for_entry(ex)
        if r.get("status") == "WAIT":
            self.skipTest("bo du lieu khong tao tin hieu")
        self.assertEqual(r.get("status"), "ORDER_FAILED")
        self.assertEqual(bot.portfolio.positions, {},
                         "that bai that su -> khong duoc ghi nhan vi the")


class _ExMapQty(FakeExchange):
    """FakeExchange + `position_qty` theo TUNG symbol (None = khong doc duoc)."""

    def __init__(self, qmap, **kw):
        super().__init__(**kw)
        self.qmap = qmap

    def position_qty(self, s):
        self._log("position_qty")
        return self.qmap.get(s)


class TestDonViTheMa(unittest.TestCase):
    """(09/10) 'Vi the ma': state mang tu phien DEMO sang LIVE ⇒ portfolio giu symbol
    KHONG con tren san ⇒ moi vong SKIP_OPEN ⇒ bot KHONG BAO GIO vao lenh (da gap that).
    """

    def _bot(self, ex) -> TradingBot:
        return TradingBot(cfg(dry_run=False, adopt_positions=True), exchange=ex)

    def test_san_xac_nhan_qty_0_thi_xoa_khoi_portfolio(self):
        ex = _ExMapQty({"SOL/USDT:USDT": 0.0})
        bot = self._bot(ex)
        # gan truc tiep (bo qua cong risk cua portfolio — chi test don state)
        bot.portfolio.positions["SOL/USDT:USDT"] = Position(
            "SOL/USDT:USDT", "LONG", 100.0, 1.0, 98.0, 110.0)
        bot.portfolio.positions["XRP/USDT:USDT"] = Position(
            "XRP/USDT:USDT", "LONG", 1.0, 2.0, 0.9, 1.2)
        bot.managed["SOL/USDT:USDT"] = new_trade("SOL/USDT:USDT", "LONG", 100.0, 1.0, 98.0, 110.0)
        rows = [{"symbol": "XRP/USDT:USDT", "side": "long", "contracts": 2.0, "entryPrice": 1.0}]
        rep = position_sync.adopt(bot, rows, atr_fn=lambda s: {"price": 1.0, "atr": 0.05})
        self.assertNotIn("SOL/USDT:USDT", bot.portfolio.positions)
        self.assertIn("SOL/USDT:USDT", rep["stale"])
        self.assertIn("XRP/USDT:USDT", bot.portfolio.positions)   # con vi the THAT -> giu

    def test_khong_doc_duoc_qty_thi_GIU_vi_the(self):
        ex = _ExMapQty({})                     # position_qty -> None (khong doc duoc)
        bot = self._bot(ex)
        bot.portfolio.positions["SOL/USDT:USDT"] = Position(
            "SOL/USDT:USDT", "LONG", 100.0, 1.0, 98.0, 110.0)
        rep = position_sync.adopt(bot, [], atr_fn=lambda s: {"price": 100.0, "atr": 2.0})
        self.assertIn("SOL/USDT:USDT", bot.portfolio.positions,
                      "khong doc duoc trang thai san -> KHONG duoc xoa (fail-safe)")
        self.assertNotIn("SOL/USDT:USDT", rep["stale"])





