"""Test `exchange`: ho tro HEDGE mode (tai khoan LIVE 2 chieu) + doc trang thai.

Loi that 09/10: tai khoan LIVE o HEDGE (`dualSidePosition=true`) nen MOI lenh khong co
`positionSide` bi tu choi `-4061 Order's position side does not match user's setting`
(tai khoan demo la one-way nen truoc do chay duoc).
"""
from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
