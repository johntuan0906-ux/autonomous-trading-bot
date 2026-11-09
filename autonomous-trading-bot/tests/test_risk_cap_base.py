# -*- coding: utf-8 -*-
"""B-049 — tran TONG risk phai tinh tren CUNG goc von voi tu so (`size_base`).

LOP LOI THAT (09/11): risk/lanh = risk_pct x `size_base` (= min(BALANCE_USDT, equity),
TESTNET = 1000) nhung tran `MAX_TOTAL_RISK_PCT` lai tinh tren `equity` THAT cua san
(demo ~3000) ⇒ moi lenh 4 USDT chi chiem 0,13% thay vi 0,4% ⇒ tran 1,6% cho phep ~12
vi the thay vi 4. Do that tren journal TESTNET: **13 vi the mo trong 45 giay**
(09:27:41 → 09:28:07), **20 vi the** con mo, roi moi entry bi `SKIP_RISK`
("dang 1,59% + moi 0,13% > 1,60%") — tuc ngan sach rui ro da bi dot het boi chinh
cai tran le ra phai chan.

Kiem o day: ham `risk_cap_base` (min) + phep mo phong "mo lien tuc den khi bi chan"
de chot SO VI THE TOI DA, khong chi chot gia tri ham.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from portfolio import (Position, can_add_risk, planned_risk_usd,  # noqa: E402
                       risk_cap_base)

CAP_PCT = 1.6          # MAX_TOTAL_RISK_PCT cua TESTNET
RISK_PCT = 0.4         # RISK_PER_TRADE_PCT cua TESTNET
BALANCE = 1000.0       # BALANCE_USDT
EQUITY = 3000.0        # equity THAT cua vi demo (do tren san testnet)


def _one_position(i: int, entry: float = 100.0, sl_dist: float = 2.0) -> Position:
    """1 vi the co risk DUNG bang `risk_pct` cua BALANCE (qty suy ra tu khoang SL)."""
    risk_usd = BALANCE * RISK_PCT / 100.0
    qty = risk_usd / sl_dist
    return Position(f"S{i}/USDT:USDT", "LONG", entry, qty, entry - sl_dist,
                    entry + sl_dist * 2)


def _positions(n: int) -> dict:
    out: dict = {}
    for i in range(n):
        p = _one_position(i)
        out[p.symbol] = p
    return out


def _max_positions(base: float) -> int:
    """Mo phong: mo lien tiep cho toi khi `can_add_risk` chan (giong vong quet that)."""
    risk_usd = BALANCE * RISK_PCT / 100.0
    pos: dict = {}
    while len(pos) <= 50:
        ok, _why = can_add_risk(pos, base, CAP_PCT, risk_usd, {})
        if not ok:
            return len(pos)
        p = _one_position(len(pos))
        pos[p.symbol] = p
    return len(pos)


class TestRiskCapBase(unittest.TestCase):
    def test_mau_so_bang_size_base_khi_equity_lon_hon(self):
        self.assertEqual(risk_cap_base(BALANCE, EQUITY), BALANCE)

    def test_equity_nho_hon_balance_thi_lay_equity(self):
        self.assertEqual(risk_cap_base(BALANCE, 27.9), 27.9)

    def test_thieu_du_lieu_thi_khong_chia_cho_0(self):
        self.assertEqual(risk_cap_base(0, 0), 1.0)
        self.assertEqual(risk_cap_base(BALANCE, 0), BALANCE)
        self.assertEqual(risk_cap_base(0, EQUITY), EQUITY)

    def test_SO_VI_THE_TOI_DA_la_4_khong_phai_12(self):
        """Tran 1,6% / risk 0,4% = 4 vi the. Dung mau so cu (equity 3000) = 12."""
        self.assertEqual(_max_positions(risk_cap_base(BALANCE, EQUITY)), 4)
        # Bang chung loi cu: dung thang `bot.equity` (3000) ⇒ 12 vi the
        self.assertEqual(_max_positions(EQUITY), 12)

    def test_risk_moi_lenh_dung_bang_risk_pct_cua_size_base(self):
        """4 vi the x 0,4% = 1,6% = tran: vua khop, khong lot cung khong thua."""
        pos = _positions(4)
        self.assertAlmostEqual(planned_risk_usd(100.0, 98.0, pos["S0/USDT:USDT"].qty),
                               BALANCE * RISK_PCT / 100.0, places=6)
        ok, _ = can_add_risk(pos, risk_cap_base(BALANCE, EQUITY), CAP_PCT,
                             BALANCE * RISK_PCT / 100.0, {})
        self.assertFalse(ok, "vi the thu 5 phai bi chan")


if __name__ == "__main__":
    unittest.main()
