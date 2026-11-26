"""Unit test B-074: `reconcile` phải tìm được CLOSE cho OPEN cũ.

Hai lỗi thật (đo LIVE 26/11):
  1. `fetch_fills` dừng ngay khi một cửa sổ 7 ngày RỖNG ⇒ mất toàn bộ fill cũ hơn
     (1000BONK 19/10, MOG/AAVE 20-23/11 không bao giờ được ghi bù).
  2. `pair_episodes_to_opens` đòi giá vào lệch <= 0,3% ⇒ vị thế ADOPT giữa đời
     (AAVE journal 97.02 vs fill thật 96.48 = 0,56%) bị coi là "lệnh tay".
"""
import time
import unittest

import reconcile as R


def _fill(ts, side, qty, price, sym="AAVE/USDT:USDT"):
    """`ts` tinh bang GIAY (nhu journal); fill luu bang MILI-GIAY (nhu norm_fills)."""
    return {"symbol": sym, "side": side, "qty": qty, "price": price,
            "ts": int(ts * 1000), "order_id": "", "pnl_exchange": 0.0, "fee": 0.0}


def _open(ts, sym="AAVE/USDT:USDT", direction="SHORT", qty=0.1, entry=97.02):
    return {"ts": ts, "event": "OPEN", "pair": sym, "direction": direction,
            "entry": entry, "qty": qty, "sl": 103.15, "tp": 84.76, "strategy": "B"}


class TestLoosePair(unittest.TestCase):
    def test_entry_lech_nhe_van_ghep_duoc_va_ghi_dau_loose(self):
        t0 = 1_700_000_000.0
        fills = [_fill(t0, "SELL", 0.1, 96.48), _fill(t0 + 3600, "BUY", 0.1, 92.0)]
        plan = R.plan_backfill([_open(t0)], [], fills)
        self.assertEqual(len(plan["closes"]), 1)
        c = plan["closes"][0]
        self.assertEqual(c["recon_src"], "exchange_loose")
        self.assertAlmostEqual(c["entry"], 97.02)       # entry lay tu JOURNAL
        self.assertAlmostEqual(c["exit_price"], 92.0)   # gia thoat lay tu FILL
        self.assertEqual(plan["loose"], 1)

    def test_khop_chinh_xac_van_ghi_dau_exchange(self):
        t0 = 1_700_000_000.0
        fills = [_fill(t0, "SELL", 0.1, 97.02), _fill(t0 + 3600, "BUY", 0.1, 92.0)]
        plan = R.plan_backfill([_open(t0)], [], fills)
        self.assertEqual(len(plan["closes"]), 1)
        self.assertEqual(plan["closes"][0]["recon_src"], "exchange")

    def test_nhieu_open_ung_vien_thi_khong_ghep_bua(self):
        t0 = 1_700_000_000.0
        opens = [_open(t0, entry=95.0), _open(t0, entry=97.0)]
        fills = [_fill(t0, "SELL", 0.1, 96.48), _fill(t0 + 3600, "BUY", 0.1, 92.0)]
        plan = R.plan_backfill(opens, [], fills)
        self.assertEqual(plan["closes"], [])
        self.assertEqual(len(plan["unmatched_episodes"]), 1)

    def test_gia_vao_lech_qua_3_phantram_thi_khong_ghep(self):
        t0 = 1_700_000_000.0
        fills = [_fill(t0, "SELL", 0.1, 96.48), _fill(t0 + 3600, "BUY", 0.1, 92.0)]
        plan = R.plan_backfill([_open(t0, entry=120.0)], [], fills)   # lech 24%
        self.assertEqual(plan["closes"], [])
        self.assertEqual(len(plan["unmatched_episodes"]), 1)

    def test_khac_huong_thi_khong_ghep(self):
        t0 = 1_700_000_000.0
        fills = [_fill(t0, "SELL", 0.1, 96.48), _fill(t0 + 3600, "BUY", 0.1, 92.0)]
        plan = R.plan_backfill([_open(t0, direction="LONG")], [], fills)
        self.assertEqual(plan["closes"], [])


class _FakeClient:
    """fetch_my_trades giả: cửa sổ 7 ngày ĐẦU rỗng, cửa sổ SAU có fill."""

    def __init__(self, rows_by_call):
        self.rows_by_call = list(rows_by_call)
        self.calls = 0

    def fetch_my_trades(self, sym, since, limit):
        self.calls += 1
        return self.rows_by_call.pop(0) if self.rows_by_call else []


class _FakeEx:
    def __init__(self, client):
        self._client = client


class TestFetchFillsKhongDungSom(unittest.TestCase):
    def test_cua_so_rong_van_quet_tiep(self):
        now = time.time()
        old = int((now - 10 * 86400) * 1000)
        row = {"amount": 0.1, "price": 96.48, "timestamp": old, "side": "sell",
               "symbol": "AAVE/USDT:USDT"}
        client = _FakeClient([[], [row]])
        fills = R.fetch_fills(_FakeEx(client), ["AAVE/USDT:USDT"], days=21)
        self.assertEqual(len(fills), 1)
        self.assertEqual(client.calls, 3)          # quet HET 3 cua so 7 ngay (khong dung o cua so rong)

    def test_loi_api_thi_dung_vong_cua_cap_do(self):
        class Boom(_FakeClient):
            def fetch_my_trades(self, *a, **kw):
                raise RuntimeError("boom")

        fills = R.fetch_fills(_FakeEx(Boom([])), ["AAVE/USDT:USDT"], days=21)
        self.assertEqual(fills, [])


if __name__ == "__main__":
    unittest.main()
