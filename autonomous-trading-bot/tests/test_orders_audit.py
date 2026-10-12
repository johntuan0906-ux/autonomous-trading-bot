"""Test `tools/orders_audit.py` + phan ALGO ORDER cua `exchange.py`.

Boi canh that (12/10): Binance chuyen lenh dieu kien sang Algo Order API nen
`fetch_open_orders()` tra 0 trong khi tai khoan dang co 200 lenh SL/TP treo
(LIVE) / 100 (TESTNET) -> bot tuong "chua bao ve" -> re-arm moi 60s -> trung lap
-> cham tran stop-order (`-4045`) -> khong dat duoc bao ve moi nua.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import orders_audit as OA          # noqa: E402
from exchange import (BinanceFutures, to_ccxt_symbol,  # noqa: E402
                      to_raw_symbol)


def _o(sym, typ, ts=0.0, algo=False, oid="1", px=100.0):
    return {"symbol": sym, "type": typ, "ts": ts, "algo": algo, "id": oid,
            "stopPrice": px}


class TestSymbolMap(unittest.TestCase):
    def test_raw_sang_ccxt(self):
        self.assertEqual(to_ccxt_symbol("AEROUSDT"), "AERO/USDT:USDT")
        self.assertEqual(to_ccxt_symbol("1000SHIBUSDT"), "1000SHIB/USDT:USDT")
        self.assertEqual(to_ccxt_symbol("SOL/USDT:USDT"), "SOL/USDT:USDT")

    def test_ccxt_sang_raw(self):
        self.assertEqual(to_raw_symbol("AERO/USDT:USDT"), "AEROUSDT")
        self.assertEqual(to_raw_symbol(""), "")

    def test_orders_audit_dung_cung_quy_uoc(self):
        self.assertEqual(OA.to_raw_symbol(OA.to_ccxt_symbol("BNBUSDT")), "BNBUSDT")


class TestPlanCleanup(unittest.TestCase):
    """Quy tac "it ma chat": 1 SL + 1 TP cho moi vi the dang mo."""

    POS = [{"symbol": "A/USDT:USDT", "contracts": 5},
           {"symbol": "B/USDT:USDT", "contracts": 0}]      # B da dong

    def test_giu_lenh_moi_nhat_va_huy_ban_sao(self):
        orders = [_o("A/USDT:USDT", "STOP_MARKET", ts=1, oid="old"),
                  _o("A/USDT:USDT", "STOP_MARKET", ts=9, oid="new"),
                  _o("A/USDT:USDT", "TAKE_PROFIT_MARKET", ts=2, oid="tp")]
        plan = OA.plan_cleanup(orders, self.POS)
        keep_ids = {o["id"] for o in plan["keep"]}
        self.assertEqual(keep_ids, {"new", "tp"})
        self.assertEqual([o["id"] for o in plan["cancel"]], ["old"])

    def test_huy_lenh_mo_coi_cua_vi_the_da_dong(self):
        orders = [_o("B/USDT:USDT", "STOP_MARKET", ts=5, oid="orphan")]
        plan = OA.plan_cleanup(orders, self.POS)
        self.assertEqual(plan["keep"], [])
        self.assertEqual([o["id"] for o in plan["cancel"]], ["orphan"])

    def test_200_lenh_trung_gom_con_2(self):
        orders = [_o("A/USDT:USDT", "STOP_MARKET", ts=i, oid="sl%d" % i)
                  for i in range(100)]
        orders += [_o("A/USDT:USDT", "TAKE_PROFIT_MARKET", ts=i, oid="tp%d" % i)
                   for i in range(100)]
        plan = OA.plan_cleanup(orders, self.POS)
        self.assertEqual(len(plan["keep"]), 2)
        self.assertEqual(len(plan["cancel"]), 198)


class TestSummarize(unittest.TestCase):
    POS = [{"symbol": "A/USDT:USDT", "contracts": 5}]

    def test_dem_dung_va_ket_luan_dupe(self):
        orders = [_o("A/USDT:USDT", "STOP_MARKET", ts=1),
                  _o("A/USDT:USDT", "STOP_MARKET", ts=2),
                  _o("A/USDT:USDT", "STOP_MARKET", ts=3),
                  _o("A/USDT:USDT", "TAKE_PROFIT_MARKET", ts=1)]
        s = OA.summarize(orders, self.POS)
        self.assertEqual(s["orders"], 4)
        self.assertEqual(s["protect_orders"], 4)
        self.assertEqual(s["per_symbol"]["A/USDT:USDT"], 4)
        self.assertEqual(s["dupes"], {"A/USDT:USDT": 4})
        self.assertEqual((s["keep"], s["to_cancel"]), (2, 2))
        self.assertIn("--dedupe", OA.verdict(s))

    def test_mo_coi_thi_bao_huy(self):
        s = OA.summarize([_o("Z/USDT:USDT", "STOP_MARKET")], self.POS)
        self.assertEqual(s["orphans"], 1)
        self.assertIn("--cancel-orphans", OA.verdict(s))

    def test_gon_thi_khong_canh_bao(self):
        orders = [_o("A/USDT:USDT", "STOP_MARKET"),
                  _o("A/USDT:USDT", "TAKE_PROFIT_MARKET")]
        s = OA.summarize(orders, self.POS)
        self.assertEqual(s["to_cancel"], 0)
        self.assertIn("gon", OA.verdict(s))

    def test_sach(self):
        self.assertIn("sach", OA.verdict(OA.summarize([], self.POS)))


class TestEnvDoc(unittest.TestCase):
    def test_doc_env_bo_qua_comment(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# c\nBINANCE_TESTNET=false\nA=1\n", encoding="utf-8")
            env = OA.read_env(p)
        self.assertEqual(env["BINANCE_TESTNET"], "false")
        self.assertEqual(env["A"], "1")
        self.assertNotIn("# c", env)

    def test_env_khong_ton_tai(self):
        self.assertEqual(OA.read_env(Path("khong/co/that/.env")), {})


class FakeAlgoClient:
    """ccxt gia: lenh dieu kien CHI o endpoint algo (giong Binance that)."""

    def __init__(self, algo=None, fail_algo=False):
        self._algo = algo if algo is not None else []
        self.fail_algo = fail_algo
        self.deleted: list = []
        self.options: dict = {}

    def fetch_open_orders(self, symbol=None):
        return []

    def fapiPrivateGetOpenAlgoOrders(self, params=None):
        if self.fail_algo:
            raise RuntimeError("mang loi")
        return list(self._algo)

    def fapiPrivateDeleteAlgoOpenOrders(self, params=None):
        return [{"algoId": 1}]

    def fapiPrivateDeleteAlgoOrder(self, params=None):
        self.deleted.append(params)
        return {"algoId": params.get("algoId")}

    def cancel_all_orders(self, symbol):
        return []

    def fapiPrivateGetPositionSideDual(self):
        return {"dualSidePosition": False}


class TestExchangeAlgo(unittest.TestCase):
    """`exchange.py` phai NHIN THAY va HUY DUOC lenh dieu kien."""

    def _ex(self, cli):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=False)
        ex._client = cli
        ex._public = cli
        return ex

    def test_algo_orders_chuan_hoa_symbol_va_bo_lenh_da_huy(self):
        cli = FakeAlgoClient(algo=[
            {"algoId": 7, "symbol": "AEROUSDT", "orderType": "STOP_MARKET",
             "triggerPrice": "0.89", "clientAlgoId": "glowsgsl1", "algoStatus": "NEW"},
            {"algoId": 8, "symbol": "AEROUSDT", "orderType": "STOP_MARKET",
             "triggerPrice": "0.89", "algoStatus": "CANCELED"},
        ])
        out = self._ex(cli).algo_orders("AERO/USDT:USDT")
        self.assertEqual(len(out), 1, "lenh da huy khong tinh la dang treo")
        self.assertEqual(out[0]["symbol"], "AERO/USDT:USDT")
        self.assertTrue(out[0]["algo"])

    def test_fetch_protection_thay_sl_tp_trong_algo(self):
        """Day la GOC cua vong lap re-arm: truoc day luon tra {None, None}."""
        cli = FakeAlgoClient(algo=[
            {"algoId": 1, "symbol": "SOLUSDT", "orderType": "STOP_MARKET",
             "triggerPrice": "110.5", "algoStatus": "NEW"},
            {"algoId": 2, "symbol": "SOLUSDT", "orderType": "TAKE_PROFIT_MARKET",
             "triggerPrice": "90.5", "algoStatus": "NEW"},
        ])
        prot = self._ex(cli).fetch_protection("SOL/USDT:USDT")
        self.assertEqual(prot["sl"], 110.5)
        self.assertEqual(prot["tp"], 90.5)

    def test_algo_loi_thi_khong_crash(self):
        prot = self._ex(FakeAlgoClient(fail_algo=True)).fetch_protection("SOL/USDT:USDT")
        self.assertEqual(prot, {"sl": None, "tp": None})

    def test_cancel_symbol_orders_huy_ca_algo(self):
        res = self._ex(FakeAlgoClient()).cancel_symbol_orders("SOL/USDT:USDT")
        self.assertEqual(res["cancelled_algo"], 1)

    def test_dry_run_khong_goi_san(self):
        ex = BinanceFutures(api_key="k", api_secret="s", testnet=False, dry_run=True)
        ex._client = FakeAlgoClient(algo=[{"algoId": 1, "symbol": "SOLUSDT"}])
        self.assertEqual(ex.algo_orders(), [])
        self.assertEqual(ex.fetch_protection("SOL/USDT:USDT"), {"sl": None, "tp": None})


if __name__ == "__main__":
    unittest.main()
