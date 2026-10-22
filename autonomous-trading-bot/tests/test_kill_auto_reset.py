# -*- coding: utf-8 -*-
"""Test TU DONG GO kill-switch sau N gio (`risk.KillSwitch.auto_reset`).

Vì sao (22/10): đo thật 15/10 — kill-switch trip rồi **kẹt 3,6 ngày** vì không ai reset tay;
người vận hành yêu cầu "đừng để trì trệ". Cơ chế mới **có hạn** (khác "tự resume ngay" mà
hội đồng 4-0 VETO 19/10): chỉ gỡ khi đã qua đủ số giờ, và ghi vết `last_auto_reset`.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import risk as RK      # noqa: E402


def _ks(**kw):
    ks = RK.KillSwitch(max_daily_loss_pct=6.0, max_atr_pct=0.05, max_errors=5,
                       start_balance=1000.0)
    for k, v in kw.items():
        setattr(ks, k, v)
    return ks


class TestAutoReset(unittest.TestCase):
    def test_tat_thi_khong_tu_go(self):
        ks = _ks(auto_reset_hours=0.0, tripped=True, trip_ts=0.0)
        self.assertFalse(ks.auto_reset(1000.0, now=10 ** 9))
        self.assertTrue(ks.tripped)

    def test_chua_qua_han_thi_van_ngung(self):
        ks = _ks(auto_reset_hours=12.0, tripped=True, trip_ts=1000.0)
        self.assertFalse(ks.auto_reset(1000.0, now=1000.0 + 11 * 3600))
        self.assertTrue(ks.tripped)

    def test_qua_han_thi_tu_go_va_ghi_vet(self):
        ks = _ks(auto_reset_hours=12.0, tripped=True, trip_ts=1000.0, reason="daily loss",
                 consec_losses=4, errors=3)
        self.assertTrue(ks.auto_reset(950.0, now=1000.0 + 13 * 3600))
        self.assertFalse(ks.tripped)
        self.assertEqual(ks.reason, "")
        self.assertEqual(ks.consec_losses, 0)
        self.assertEqual(ks.errors, 0)
        self.assertEqual(ks.auto_reset_count, 1)
        self.assertEqual(ks.last_auto_reset, 1000.0 + 13 * 3600)
        self.assertEqual(ks.peak_balance, 950.0)
        self.assertEqual(ks.start_equity, 950.0)

    def test_state_cu_khong_co_moc_thi_bat_dau_tinh_tu_bay_gio(self):
        ks = _ks(auto_reset_hours=6.0, tripped=True, trip_ts=0.0)
        self.assertFalse(ks.auto_reset(1000.0, now=500.0))
        self.assertEqual(ks.trip_ts, 500.0)
        self.assertTrue(ks.auto_reset(1000.0, now=500.0 + 7 * 3600))

    def test_check_tra_False_sau_khi_tu_go(self):
        import time as _t
        ks = _ks(auto_reset_hours=1.0, tripped=True, trip_ts=_t.time() - 2 * 3600)
        self.assertFalse(ks.check(1000.0, 0.0), "qua han tu go -> cho chay tiep")
        self.assertFalse(ks.tripped)
        self.assertEqual(ks.auto_reset_count, 1)

    def test_luu_va_doc_lai_moc_trip(self):
        ks = _ks(auto_reset_hours=12.0, tripped=True, trip_ts=12345.0,
                 auto_reset_count=2, last_auto_reset=999.0)
        d = ks.to_dict()
        back = RK.KillSwitch.from_dict(d)
        self.assertEqual(back.trip_ts, 12345.0)
        self.assertEqual(back.auto_reset_count, 2)
        self.assertEqual(back.last_auto_reset, 999.0)

    def test_load_state_giu_moc_nhung_nguong_theo_env(self):
        """`.env` thắng cho NGƯỠNG; state chỉ giữ LỊCH SỬ (mốc trip, số lần tự gỡ)."""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "risk_state.json"
            p.write_text(json.dumps({"max_daily_loss_pct": 2.0, "tripped": True,
                                     "trip_ts": 777.0, "auto_reset_count": 1,
                                     "reason": "cu"}), encoding="utf-8")
            ks = _ks(auto_reset_hours=12.0)          # tu .env (6.0% + 12h)
            out = RK.load_state(str(p), ks)
            self.assertEqual(out.max_daily_loss_pct, 6.0, "nguong phai theo .env")
            self.assertEqual(out.trip_ts, 777.0, "moc trip phai giu tu state")
            self.assertEqual(out.auto_reset_count, 1)


if __name__ == "__main__":
    unittest.main()
