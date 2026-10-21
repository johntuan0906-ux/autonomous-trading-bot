"""Test `exchange`: ho tro HEDGE mode (tai khoan LIVE 2 chieu) + doc trang thai.

Loi that 09/10: tai khoan LIVE o HEDGE (`dualSidePosition=true`) nen MOI lenh khong co
`positionSide` bi tu choi `-4061 Order's position side does not match user's setting`
(tai khoan demo la one-way nen truoc do chay duoc).
"""
from __future__ import annotations

import unittest
from unittest import mock

from exchange import BinanceFutures


class FakeClient:
    def __init__(self, dual: bool = False, raise_on_dual: bool = False,
                 close_error: str | None = None, rows: list | None = None,
                 positions_error: str | None = None,
                 ro_only_error: bool = False, after_rows: list | None = None,
                 positions_error_after: int | None = None):
        self.dual = dual
        self.raise_on_dual = raise_on_dual
        self.close_error = close_error          # nem loi khi dat lenh MARKET (= dong lenh)
        self.ro_only_error = ro_only_error      # ... nhung CHI khi co `reduceOnly`
        self.rows = rows if rows is not None else []
        self.after_rows = after_rows            # vi the SAU khi dat duoc lenh dong
        self.positions_error = positions_error
        self.positions_error_after = positions_error_after   # loi tu lan doc thu N
        self.positions_calls = 0
        self.calls: list = []
        self.options: dict = {}

    def fapiPrivateGetPositionSideDual(self):
        if self.raise_on_dual:
            raise RuntimeError("mang loi")
        return {"dualSidePosition": self.dual}

    def create_market_order(self, symbol, side, qty, params=None):
        self.calls.append(("market", symbol, side, qty, params))
        if self.close_error and (not self.ro_only_error or "reduceOnly" in (params or {})):
            raise RuntimeError(self.close_error)
        if self.after_rows is not None:
            self.rows = list(self.after_rows)   # san cap nhat vi the sau khi khop
        return {"id": "x"}

    def fetch_positions(self, symbols=None):
        self.positions_calls += 1
        if self.positions_error:
            raise RuntimeError(self.positions_error)
        if (self.positions_error_after is not None
                and self.positions_calls >= self.positions_error_after):
            raise RuntimeError("mang loi (lan doc thu %d)" % self.positions_calls)
        return list(self.rows)

    def create_order(self, symbol, otype, side, qty, params=None):
        self.calls.append((otype, symbol, side, qty, params))
        return {"id": "y"}

    def cancel_symbol_orders(self, symbol):
        return 0


def _ex(dual: bool = False, raise_on_dual: bool = False) -> BinanceFutures:
    ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=False)
    ex._client = FakeClient(dual, raise_on_dual)
    ex._public = ex._client
    return ex


class TestHedgeMode(unittest.TestCase):
    def test_one_way_khong_gui_position_side(self):
        ex = _ex(dual=False)
        self.assertFalse(ex.hedge_mode())
        self.assertEqual(ex._pos_side("LONG"), {})
        ex.market_entry("SOL/USDT:USDT", "LONG", 1.0)
        _t, _s, side, _q, params = ex._client.calls[-1]
        self.assertEqual(side, "buy")
        self.assertNotIn("positionSide", params)

    def test_hedge_gui_position_side_dung_phia(self):
        ex = _ex(dual=True)
        self.assertTrue(ex.hedge_mode())
        self.assertEqual(ex._pos_side("LONG"), {"positionSide": "LONG"})
        self.assertEqual(ex._pos_side("SHORT"), {"positionSide": "SHORT"})
        ex.market_entry("SOL/USDT:USDT", "SHORT", 1.0)
        _t, _s, side, _q, params = ex._client.calls[-1]
        self.assertEqual(side, "sell")
        self.assertEqual(params["positionSide"], "SHORT")

    def test_hedge_close_khong_dung_reduce_only(self):
        ex = _ex(dual=True)
        ex.close_position("SOL/USDT:USDT", "LONG", 1.0)
        _t, _s, side, _q, params = ex._client.calls[-1]
        self.assertEqual(side, "sell")
        self.assertEqual(params["positionSide"], "LONG")
        self.assertNotIn("reduceOnly", params)

    def test_one_way_close_dung_reduce_only(self):
        ex = _ex(dual=False)
        ex.close_position("SOL/USDT:USDT", "LONG", 1.0)
        _t, _s, _side, _q, params = ex._client.calls[-1]
        self.assertTrue(params["reduceOnly"])

    def test_hedge_sl_tp_co_position_side(self):
        ex = _ex(dual=True)
        ex.stop_tp_orders("SOL/USDT:USDT", "SHORT", 1.0, sl=110.0, tp=90.0)
        sl = [c for c in ex._client.calls if c[0] == "STOP_MARKET"][-1]
        self.assertEqual(sl[4]["positionSide"], "SHORT")
        self.assertNotIn("reduceOnly", sl[4])

    def test_one_way_sl_tp_dung_reduce_only(self):
        ex = _ex(dual=False)
        ex.stop_tp_orders("SOL/USDT:USDT", "SHORT", 1.0, sl=110.0, tp=90.0)
        sl = [c for c in ex._client.calls if c[0] == "STOP_MARKET"][-1]
        self.assertTrue(sl[4]["reduceOnly"])
        self.assertNotIn("positionSide", sl[4])

    def test_loi_mang_thi_coi_nhu_one_way(self):
        ex = _ex(dual=True, raise_on_dual=True)
        self.assertFalse(ex.hedge_mode())
        self.assertEqual(ex._pos_side("LONG"), {})

    def test_dry_run_khong_goi_san(self):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = FakeClient(dual=True)
        out = ex.market_entry("SOL/USDT:USDT", "LONG", 1.0)
        self.assertTrue(out.get("dry_run"))


class TestCloseDaDong2022(unittest.TestCase):
    """(20/10) `-2022 ReduceOnly Order is rejected` — xu ly TUONG MINH.

    DO THAT tren API (demo, 20/10) — 3 su that quyet dinh cach va:

      1. `reduceOnly=True` MARKET bi tu choi **VO DIEU KIEN** (qty=1 tren vi the 31 hop
         dong VAN bi tu choi) ⇒ 157 lan `-2022`/ngay, 13 lan `monitor ... failed` ⇒
         **kill-switch TRIP oan** "7 consecutive API errors" 09:06, va `_flatten` dong
         16 vi the ma khong dong duoc vi the nao (san van giu du 16).
      2. `closePosition=true` cho MARKET cung khong dung duoc: `-4136`.
      3. Lenh MARKET **khong reduceOnly** voi qty DUNG BANG vi the that ⇒ FILLED (31 -> 0).

    Vi vay: gap `-2022` ⇒ doc lai vi the cua DUNG PHIA; qty=0 ⇒ `already_closed`; con vi the
    ⇒ dong lai bang qty that (khong reduceOnly, KHONG vuot qua y dinh dong) + doc lai de
    bat `left_over`/`flipped`. Khong doc duoc ⇒ **nem loi nhu cu** (khong doan).
    """

    SYM = "SOL/USDT:USDT"
    ERR = 'binance {"code":-2022,"msg":"ReduceOnly Order is rejected."}'

    def _ex(self, **kw) -> BinanceFutures:
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=False)
        ex._client = FakeClient(**kw)
        ex._public = ex._client
        return ex

    def _rows(self, qty: float, side: str = "long") -> list:
        return [{"symbol": self.SYM, "side": side, "contracts": qty}]

    def test_2022_va_vi_the_da_ve_0_thi_coi_nhu_da_dong(self):
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(0))
        out = ex.close_position(self.SYM, "LONG", 1.0)
        self.assertTrue(out.get("already_closed"), "qty=0 ⇒ coi nhu da dong")
        self.assertEqual(out.get("left_qty"), 0.0)
        self.assertIn("-2022", out.get("reason", ""))
        self.assertEqual(len(ex._client.calls), 1, "qty=0 thi khong gui lenh nao nua")

    def test_2022_con_vi_the_thi_dong_lai_bang_qty_that_khong_reduceOnly(self):
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(31.0),
                      after_rows=[])
        out = ex.close_position(self.SYM, "LONG", 31.0)
        self.assertTrue(out.get("closed_without_reduce_only"))
        self.assertEqual(out.get("qty"), 31.0)
        self.assertEqual(out.get("left_qty"), 0.0)
        last = ex._client.calls[-1]
        self.assertEqual(last[0], "market")
        self.assertNotIn("reduceOnly", last[4], "lan 2 KHONG duoc dung reduceOnly")
        self.assertEqual(last[3], 31.0, "qty phai BANG vi the that tren san")

    def test_dong_lai_KHONG_vuot_qua_y_dinh_dong(self):
        """Chot 50% (PARTIAL) khong duoc bien thanh dong HET vi the."""
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(10.0),
                      after_rows=self._rows(5.0))
        out = ex.close_position(self.SYM, "LONG", 5.0)
        self.assertEqual(out.get("qty"), 5.0, "yeu cau 5 -> gui 5 (khong phai 10)")
        self.assertEqual(out.get("left_qty"), 5.0)

    def test_dong_lai_KHONG_vuot_qua_vi_the_that(self):
        """So sach lech (noi 10, san chi co 3) -> chi duoc dong 3."""
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(3.0),
                      after_rows=[])
        out = ex.close_position(self.SYM, "LONG", 10.0)
        self.assertEqual(out.get("qty"), 3.0)

    def test_con_du_thi_bao_left_over(self):
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(10.0),
                      after_rows=self._rows(2.0))
        out = ex.close_position(self.SYM, "LONG", 10.0)
        self.assertEqual(out.get("left_over"), 2.0, "phai bao con du de vong sau xu ly")

    def test_phat_hien_vi_the_LAT_CHIEU(self):
        """SL khop DUNG LUC gui lenh ⇒ lenh mo nguoc chieu: phai bao `flipped`."""
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(10.0),
                      after_rows=self._rows(10.0, side="short"))
        out = ex.close_position(self.SYM, "LONG", 10.0)
        self.assertEqual(out.get("flipped"), "SHORT")
        self.assertEqual(out.get("flipped_qty"), 10.0)

    def test_doc_lai_loi_thi_ghi_verify_failed_chu_khong_crash(self):
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(10.0),
                      positions_error_after=2)          # lan doc thu 2 (sau khi dong) loi
        out = ex.close_position(self.SYM, "LONG", 10.0)
        self.assertTrue(out.get("closed_without_reduce_only"))
        self.assertTrue(out.get("verify_failed"), "khong xac minh duoc thi phai noi ro")

    def test_memo_chi_thu_reduceOnly_MOT_lan(self):
        """Da biet san tu choi ⇒ lan dong sau khong ton 1 request chac chan that bai."""
        ex = self._ex(ro_only_error=True, close_error=self.ERR, rows=self._rows(5.0),
                      after_rows=[])
        ex.close_position(self.SYM, "LONG", 5.0)
        n1 = len(ex._client.calls)
        self.assertEqual(n1, 2, "lan dau: 1 lenh that bai + 1 lenh thanh cong")
        ex._client.rows = self._rows(5.0)
        ex.close_position(self.SYM, "LONG", 5.0)
        self.assertEqual(len(ex._client.calls) - n1, 1,
                         "lan sau: di thang duong qty chinh xac (1 lenh)")
        self.assertNotIn("reduceOnly", ex._client.calls[-1][4])

    def test_loi_khac_thi_van_nem_loi_va_khong_doc_vi_the(self):
        ex = self._ex(close_error='binance {"code":-2019,"msg":"Margin is insufficient."}')
        with self.assertRaises(RuntimeError):
            ex.close_position(self.SYM, "LONG", 1.0)
        self.assertEqual(ex._client.positions_calls, 0,
                         "chi -2022 moi phai doc lai vi the")

    def test_khong_doc_duoc_vi_the_thi_van_nem_loi(self):
        ex = self._ex(close_error=self.ERR, positions_error="mang loi")
        with self.assertRaises(RuntimeError):
            ex.close_position(self.SYM, "LONG", 1.0)

    def test_hedge_chi_tin_dong_cua_DUNG_PHIA(self):
        """HEDGE: 2 dong LONG/SHORT cung symbol ⇒ phai doc dung phia cua lenh dong.

        Doc nham phia = tuong "da dong" trong khi vi the VAN nam tren san ⇒ vi the
        mo coi khong SL/TP.
        """
        ex = self._ex(dual=True, close_error=self.ERR, rows=self._rows(0.7, side="short"))
        self.assertEqual(ex.position_qty(self.SYM, direction="LONG"), 0.0)
        self.assertTrue(ex.close_position(self.SYM, "LONG", 1.0).get("already_closed"),
                        "phia LONG phang (chi con SHORT cua nguoi dung) ⇒ da dong")
        # HEDGE: phia TA con vi the ⇒ dong lai bang qty that, van giu positionSide
        ex2 = self._ex(dual=True, rows=self._rows(0.7), after_rows=[])
        ex2.close_position(self.SYM, "LONG", 0.7)
        call = ex2._client.calls[-1]
        self.assertEqual(call[3], 0.7)
        self.assertEqual(call[4].get("positionSide"), "LONG")
        self.assertNotIn("reduceOnly", call[4])

    def test_one_way_lech_phia_thi_khong_ket_luan(self):
        """ONE-WAY chi co 1 vi the cho 1 cap ⇒ doc ra LECH phia = bat thuong ⇒ None."""
        ex = self._ex(rows=[{"symbol": self.SYM, "side": "short", "contracts": 0.7}])
        self.assertIsNone(ex.position_qty(self.SYM, direction="LONG"),
                          "khong duoc ket luan 'da dong' khi du lieu lech phia")

    def test_position_qty_khong_chi_dinh_phia_giu_hanh_vi_cu(self):
        ex = self._ex(rows=[{"symbol": self.SYM, "side": "short", "contracts": 0.7}])
        self.assertEqual(ex.position_qty(self.SYM), 0.7)
        self.assertEqual(self._ex(rows=[]).position_qty(self.SYM), 0.0,
                         "khong co dong nao ⇒ phang")


class TestQtyStep(unittest.TestCase):
    """(21/10) `qty_step` = tick size qty của sàn — dùng để nâng qty lên minNotional."""

    class _Src:
        def __init__(self, step=1.0, boom=False):
            self.step, self.boom = step, boom

        def load_markets(self):
            if self.boom:
                raise RuntimeError("mang loi")

        def market(self, s):
            return {"precision": {"amount": self.step}}

    def _ex(self, src):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = None
        ex._public = src
        return ex

    def test_doc_duoc_tick(self):
        self.assertEqual(self._ex(self._Src(1.0)).qty_step("X/USDT:USDT"), 1.0)
        self.assertAlmostEqual(self._ex(self._Src(0.001)).qty_step("X"), 0.001)

    def test_loi_mang_thi_tra_0(self):
        self.assertEqual(self._ex(self._Src(boom=True)).qty_step("X"), 0.0)

    def test_khong_co_src_thi_tra_0(self):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = None
        ex._public = None
        self.assertEqual(ex.qty_step("X"), 0.0)


class TestTuneSession(unittest.TestCase):
    """(11/10) Quét ~460 cặp làm pool HTTP mặc định (10) đầy -> phải nới lên 32."""

    def test_mount_adapter_https(self):
        from exchange import _tune_session

        class S:
            def __init__(self):
                self.mounted = {}

            def mount(self, pre, ad):
                self.mounted[pre] = ad

        class C:
            def __init__(self):
                self.session = S()

        c = C()
        _tune_session(c)
        self.assertIn("https://", c.session.mounted)
        self.assertIn("http://", c.session.mounted)
        self.assertTrue(hasattr(c.session.mounted["https://"], "_pool_maxsize"))

    def test_khong_co_session_thi_khong_crash(self):
        from exchange import _tune_session
        _tune_session(object())          # khong co .session -> bo qua, khong nem loi


class TestOhlcvCache(unittest.TestCase):
    """(11/10) Cache tang dan de quet ~460 cap khong chet rate-limit:
    vong dau fetch day du; trong 45s dung cache; 45s-1h chi ghep 8 nen moi;
    >1h fetch lai day du. Sau khi ghep, df van du `limit` dong, ts khong trung."""

    def _ex_with_src(self):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        src = FakeOhlcvSrc()
        ex._client = None
        ex._public = src
        return ex, src

    def test_vong_dau_fetch_day_du(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            df = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(len(df), 200)
        self.assertEqual(src.calls, [("BTC/USDT:USDT", "1m", 200)])

    def test_trong_45s_dung_cache_khong_goi_san(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            d1 = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
            d2 = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(len(src.calls), 1)
        self.assertTrue(d1.equals(d2))
        # Tra ve copy -> sua ket qua khong pha cache.
        d2.loc[0, "close"] = -1.0
        self.assertNotEqual(float(d1["close"].iloc[0]), -1.0)

    def test_sau_45s_ghep_8_nen_moi(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            d1 = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
            clock["t"] = 60.0
            d2 = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(src.calls[1], ("BTC/USDT:USDT", "1m", 8))
        self.assertEqual(len(d2), 200)               # van du limit dong
        self.assertTrue(d2["ts"].is_unique)          # nen trung da bi bo
        self.assertGreater(d2["ts"].iloc[-1], d1["ts"].iloc[-1])  # co nen moi nhat

    def test_sau_1h_fetch_lai_day_du(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
            clock["t"] = 4000.0
            ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(src.calls[-1], ("BTC/USDT:USDT", "1m", 200))

    # ---- (11/10) TTL 900s cho timeframe cao (1h+) + cooldown loi 120s ----

    def test_tf_cao_dung_cache_900s_khong_goi_san(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            ex.fetch_ohlcv("BTC/USDT:USDT", "1h", 60)
            clock["t"] = 100.0                    # qua 45s nhung chua 900s
            d2 = ex.fetch_ohlcv("BTC/USDT:USDT", "1h", 60)
        self.assertEqual(len(src.calls), 1)       # mtf khong fetch moi vong
        self.assertEqual(len(d2), 60)

    def test_tf_cao_sau_900s_ghep_nen(self):
        ex, src = self._ex_with_src()
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            ex.fetch_ohlcv("BTC/USDT:USDT", "1h", 60)
            clock["t"] = 1000.0
            ex.fetch_ohlcv("BTC/USDT:USDT", "1h", 60)
        self.assertEqual(src.calls[-1], ("BTC/USDT:USDT", "1h", 8))

    def test_fetch_loi_thi_cooldown_120s(self):
        ex, src = self._ex_with_src()
        src.fail = True
        clock = {"t": 0.0}
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            with self.assertRaises(RuntimeError):
                ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
            clock["t"] = 60.0                     # trong cooldown: khong goi san
            with self.assertRaises(RuntimeError):
                ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(len(src.calls), 1)       # khong retry-storm
        src.fail = False
        clock["t"] = 200.0                        # het cooldown: thu lai day du
        with mock.patch("exchange.time.monotonic", side_effect=lambda: clock["t"]):
            d3 = ex.fetch_ohlcv("BTC/USDT:USDT", "1m", 200)
        self.assertEqual(src.calls[-1], ("BTC/USDT:USDT", "1m", 200))
        self.assertEqual(len(d3), 200)


class FakeOhlcvSrc:
    """Tra nen gia 1 phut; moi lan goi, nen moi nhat tien them 1 phut."""

    def __init__(self):
        self.calls: list = []
        self._n = 0
        self._base_ms = 1_700_000_000_000
        self.fail = False

    def fetch_ohlcv(self, symbol, timeframe, limit):
        self._n += 1
        self.calls.append((symbol, timeframe, limit))
        if self.fail:
            raise RuntimeError("san deo tra loi (fake)")
        end_ms = self._base_ms + self._n * 60_000
        out = []
        for i in range(limit):
            t = end_ms - (limit - 1 - i) * 60_000
            o = 100.0 + i
            out.append([t, o, o + 1.0, o - 1.0, o + 0.5, 10.0])
        return out


class FakeMarketSrc:
    """Fake ccxt cho `quantize_qty`: chi can load_markets + amount_to_precision."""

    def __init__(self, min_amt=None, max_amt=None):
        self._m = {"limits": {"amount": {"min": min_amt, "max": max_amt}}}

    def load_markets(self):
        return {"X/USDT:USDT": self._m}

    def amount_to_precision(self, symbol, q):
        return "%.3f" % float(q)


class TestQuantizeQty(unittest.TestCase):
    """(12/10) Kep ca MIN lan MAX cua san.

    Bug that: chi kep min -> cap co maxQty nho tra `-4005 Quantity greater than
    max quantity` (da gap voi 1000BONK/1000PEPE tren LIVE).
    """

    def _ex(self, min_amt=None, max_amt=None):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = None
        ex._public = FakeMarketSrc(min_amt, max_amt)
        return ex

    def test_kep_max(self):
        ex = self._ex(min_amt=1.0, max_amt=100.0)
        self.assertEqual(ex.quantize_qty("X/USDT:USDT", 5000.0), 100.0,
                         "qty vuot max phai bi kep ve max (khong de san tu choi)")

    def test_duoi_min_tra_0(self):
        ex = self._ex(min_amt=10.0, max_amt=1000.0)
        self.assertEqual(ex.quantize_qty("X/USDT:USDT", 5.0), 0.0)

    def test_trong_khoang_thi_cat_precision(self):
        ex = self._ex(min_amt=1.0, max_amt=1000.0)
        self.assertAlmostEqual(ex.quantize_qty("X/USDT:USDT", 12.3456), 12.346)

    def test_khong_co_max_thi_giu_nguyen(self):
        ex = self._ex(min_amt=1.0, max_amt=None)
        self.assertAlmostEqual(ex.quantize_qty("X/USDT:USDT", 5000.0), 5000.0)

    def test_khong_co_src_thi_lam_tron(self):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = None
        ex._public = None
        self.assertAlmostEqual(ex.quantize_qty("X/USDT:USDT", 1.23456789), 1.234568)


if __name__ == "__main__":
    unittest.main()
