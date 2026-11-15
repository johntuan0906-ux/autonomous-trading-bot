"""Cooldown THEO CAP sau lenh THUA (B-057) — doc tu journal nen song qua restart.

Yeu cau nghiem thu cua roadmap: **"cap vua SL khong vao lai trong 60 phut"**.
Test chot ca 2 chieu: vua THUA thi chan; vua THANG / da qua han / tat cooldown thi KHONG chan.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import entries_gate as EG      # noqa: E402

NOW = 1_760_000_000.0
PAIR = "SOL/USDT:USDT"


def _write(path: Path, rows: list):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    EG._LOSS_CACHE.clear()          # journal vua doi -> xoa cache (test, khong phai code chay)


def _close(pair=PAIR, ts=NOW - 60, r=-1.0, pnl=-10.0, won=False):
    return {"ts": ts, "event": "CLOSE", "pair": pair, "r": r, "pnl": pnl, "won": won}


class _Cfg:
    def __init__(self, minutes=60.0):
        self.pair_cooldown_min = minutes


class TestCooldownTheoCap(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.jp = Path(self.td.name) / "journal.jsonl"

    def tearDown(self):
        self.td.cleanup()
        EG._LOSS_CACHE.clear()

    def test_cap_vua_SL_khong_vao_lai_trong_60_phut(self):
        _write(self.jp, [_close(ts=NOW - 300)])           # SL 5 phut truoc
        blocked, why = EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)
        self.assertTrue(blocked)
        self.assertIn("THUA", why)
        self.assertIn("60", why)

    def test_qua_60_phut_thi_vao_lai_duoc(self):
        _write(self.jp, [_close(ts=NOW - 61 * 60)])
        self.assertFalse(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])

    def test_lenh_THANG_khong_bi_chan(self):
        """Khong tu trung phat: chi lenh THUA moi bat cooldown."""
        _write(self.jp, [_close(ts=NOW - 60, r=1.5, pnl=15.0, won=True)])
        self.assertFalse(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])

    def test_cap_KHAC_khong_bi_anh_huong(self):
        _write(self.jp, [_close(ts=NOW - 60)])
        self.assertFalse(EG.in_cooldown("ETH/USDT:USDT", cfg=_Cfg(60),
                                        journal=self.jp, now=NOW)[0])

    def test_tat_bang_0_phut(self):
        _write(self.jp, [_close(ts=NOW - 60)])
        self.assertFalse(EG.in_cooldown(PAIR, cfg=_Cfg(0), journal=self.jp, now=NOW)[0])
        self.assertFalse(EG.in_cooldown(PAIR, journal=self.jp, now=NOW, minutes=0)[0])

    def test_lay_moc_THUA_gan_nhat_chu_khong_phai_lan_dau(self):
        _write(self.jp, [_close(ts=NOW - 5 * 3600, r=-1.0),
                         _close(ts=NOW - 120, r=-0.8)])
        rec = EG.last_loss(PAIR, journal=self.jp, now=NOW)
        self.assertAlmostEqual(rec["ts"], NOW - 120)

    def test_journal_hong_khong_lam_bot_dung(self):
        """Dong hong bi bo qua; khong co du lieu ⇒ KHONG chan (fail-open o day la dung)."""
        self.jp.write_text("{hong\n" + json.dumps(_close(ts=NOW - 60)) + "\n", encoding="utf-8")
        EG._LOSS_CACHE.clear()
        self.assertTrue(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])
        self.jp.write_text("", encoding="utf-8")
        EG._LOSS_CACHE.clear()
        self.assertFalse(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])

    def test_doc_thoi_han_tu_cfg_hoac_env(self):
        self.assertEqual(EG.cooldown_minutes(_Cfg(120)), 120.0)
        self.assertEqual(EG.cooldown_minutes(object()), EG.DEFAULT_COOLDOWN_MIN)

    def test_cache_lam_moi_khi_journal_doi(self):
        _write(self.jp, [_close(ts=NOW - 3600 * 10)])          # rat cu
        self.assertFalse(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])
        with open(self.jp, "a", encoding="utf-8") as f:        # ghi them 1 dong moi
            f.write(json.dumps(_close(ts=NOW - 30)) + "\n")
        self.assertTrue(EG.in_cooldown(PAIR, cfg=_Cfg(60), journal=self.jp, now=NOW)[0])


class TestNoiDayVaoVongQuet(unittest.TestCase):
    """Chot NOI DAY: ham dung ma khong duoc goi thi cooldown vo dung (lop loi 'im lang')."""

    def test_turbo_demo_goi_cooldown_truoc_khi_vao_lenh(self):
        src = (ROOT / "turbo_demo.py").read_text(encoding="utf-8")
        call = "entries_gate.in_cooldown(sym, cfg)"
        self.assertIn(call, src, "turbo_demo phai goi cooldown theo cap")
        fetch_next = "fr = fetched.get(sym, {})"
        self.assertLess(src.index(call), src.index(fetch_next),
                        "phai kiem cooldown TRUOC khi doc nen/vao lenh")
        self.assertIn('"status": "COOLDOWN", "reason": _cd_why', src)

    def test_config_co_doc_PAIR_COOLDOWN_MIN(self):
        src = (ROOT / "config.py").read_text(encoding="utf-8")
        self.assertIn('_get_float("PAIR_COOLDOWN_MIN"', src)


if __name__ == "__main__":
    unittest.main()
