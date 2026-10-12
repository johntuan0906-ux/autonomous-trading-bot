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
    def __init__(self, dual: bool = False, raise_on_dual: bool = False):
        self.dual = dual
        self.raise_on_dual = raise_on_dual
        self.calls: list = []
        self.options: dict = {}

    def fapiPrivateGetPositionSideDual(self):
        if self.raise_on_dual:
            raise RuntimeError("mang loi")
        return {"dualSidePosition": self.dual}

    def create_market_order(self, symbol, side, qty, params=None):
        self.calls.append(("market", symbol, side, qty, params))
        return {"id": "x"}

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


if __name__ == "__main__":
    unittest.main()
