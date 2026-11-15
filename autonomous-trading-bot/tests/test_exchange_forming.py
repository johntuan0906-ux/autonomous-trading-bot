"""No-lookahead: `exchange.fetch_ohlcv` phai BO nen DANG HINH THANH (RESEARCH_1115 muc 2).

Vi sao: nen cuoi tu ccxt co the chua chot (close dang chay) ⇒ chi so/score tinh tren du lieu nua voi
va "gia vao lenh" khong tai lap duoc. Test khoa ca 2 chieu: bat ⇒ bo nen dang chay; tat ⇒ giu nguyen.
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import exchange as EX      # noqa: E402

TF_MS = 15 * 60 * 1000


class FakeClient:
    """Tra ve `n_closed` nen da dong + 1 nen DANG CHAY (bat dau cach day it giay)."""

    def __init__(self, n_closed=5):
        now_ms = int(time.time() * 1000)
        start = now_ms - (n_closed + 1) * TF_MS
        self.rows = []
        for i in range(n_closed):
            ts = start + i * TF_MS
            self.rows.append([ts, 100.0, 101.0, 99.0, 100.5, 10.0])
        self.rows.append([now_ms - 60_000, 100.0, 101.0, 99.0, 100.9, 3.0])  # dang chay

    def fetch_ohlcv(self, symbol, timeframe="15m", limit=200):
        return list(self.rows)


def _ex(drop: bool) -> EX.BinanceFutures:
    ex = EX.BinanceFutures(testnet=True, dry_run=True)
    ex._public = FakeClient()
    ex.drop_forming = drop
    return ex


class TestBoNenDangChay(unittest.TestCase):
    def test_bat_thi_bo_nen_cuoi(self):
        df = _ex(True).fetch_ohlcv("BTC/USDT:USDT", "15m", limit=20)
        self.assertEqual(len(df), 5, "5 nen da dong, nen dang chay phai bi bo")

    def test_tat_thi_giu_nguyen(self):
        df = _ex(False).fetch_ohlcv("BTC/USDT:USDT", "15m", limit=20)
        self.assertEqual(len(df), 6)

    def test_mac_dinh_BAT(self):
        import os
        old = os.environ.pop("DROP_FORMING_CANDLE", None)
        try:
            self.assertTrue(EX.BinanceFutures().drop_forming)
        finally:
            if old is not None:
                os.environ["DROP_FORMING_CANDLE"] = old

    def test_du_lieu_qua_it_thi_khong_lam_mat(self):
        """It hon 2 nen "da dong" ⇒ giu nguyen (khong de bot mat du lieu vi bo loc)."""
        ex = _ex(True)
        ex._public = FakeClient(n_closed=1)
        df = ex.fetch_ohlcv("BTC/USDT:USDT", "15m", limit=20)
        self.assertEqual(len(df), 2)


if __name__ == "__main__":
    unittest.main()
