"""B-075 / B-076: gia vao THAT va so khop MEM khi ADOPT.

B-075 â€” `ManagedTrade.entry` (goc cua moi moc R/BE/partial va cot `r` trong journal)
        truoc day lay gia KE HOACH, trong khi vi the khop gia khac (do that LIVE: MOG
        state `0.07926` vs san `0.07963` = 0,47%).
B-076 â€” `unclosed_fn` cua turbo_demo goi `_open_keys(cfg)` â€” ham KHONG TON TAI â‡’
        `NameError` bi `adopt` nuot â‡’ B-073 khong co tac dung tren ban that; va ca khi
        ton tai thi `rec_key` so khop TUYET DOI (ca qty) nen gia ke hoach/partial lai
        sinh OPEN lap.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import journal  # noqa: E402
import position_sync as ps  # noqa: E402


def _open(ts: float, **kw) -> dict:
    rec = {"ts": ts, "event": "OPEN", "pair": "ETH/USDT:USDT", "direction": "SHORT",
           "qty": 0.016, "entry": 1708.79}
    rec.update(kw)
    return rec


def _close(ts: float, **kw) -> dict:
    rec = {"ts": ts, "event": "CLOSE", "pair": "ETH/USDT:USDT", "direction": "SHORT",
           "qty": 0.016, "entry": 1708.79, "exit_price": 1624.0, "r": 2.0, "won": True}
    rec.update(kw)
    return rec


def _write(recs: list) -> str:
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return path


class _Mt:
    """ManagedTrade toi thieu (khong keo ca module trade_mgmt vao test nay)."""

    def __init__(self, entry: float, initial_sl: float = 1600.0):
        self.entry = entry
        self.initial_sl = initial_sl
        self.init_qty = 0.016
        self.qty = 0.016


class TestFillEntry(unittest.TestCase):
    def test_lay_average_truoc(self):
        self.assertEqual(ps.fill_entry({"average": 1708.5, "price": 1709.0}), 1708.5)

    def test_thieu_average_thi_lay_avgprice(self):
        self.assertEqual(ps.fill_entry({"average": None, "avgPrice": 1707.25}), 1707.25)

    def test_thieu_het_thi_lay_price(self):
        self.assertEqual(ps.fill_entry({"price": 1706.0}), 1706.0)

    def test_response_rong_tra_0(self):
        self.assertEqual(ps.fill_entry({}), 0.0)
        self.assertEqual(ps.fill_entry(None), 0.0)
        self.assertEqual(ps.fill_entry({"average": "abc"}), 0.0)


class TestSyncEntry(unittest.TestCase):
    def test_lech_lon_thi_dong_bo_va_giu_initial_sl(self):
        mt = _Mt(0.07926, initial_sl=0.0755)
        self.assertTrue(ps.sync_entry(mt, 0.07963))
        self.assertAlmostEqual(mt.entry, 0.07963)
        self.assertAlmostEqual(mt.initial_sl, 0.0755)   # moc rui ro KHONG bi doi

    def test_lech_duoi_nguong_thi_khong_sua(self):
        mt = _Mt(1000.0)
        self.assertFalse(ps.sync_entry(mt, 1000.5))     # 0,05% < 0,2%
        self.assertAlmostEqual(mt.entry, 1000.0)

    def test_gia_khong_doc_duoc_thi_bo_qua(self):
        mt = _Mt(1000.0)
        self.assertFalse(ps.sync_entry(mt, 0.0))
        self.assertFalse(ps.sync_entry(mt, None))
        self.assertAlmostEqual(mt.entry, 1000.0)

    def test_entry_cu_bang_0_thi_gan_moi(self):
        mt = _Mt(0.0)
        self.assertTrue(ps.sync_entry(mt, 5.0))
        self.assertAlmostEqual(mt.entry, 5.0)


class _Ex:
    def fetch_protection(self, sym):
        return {"sl": 1600.0, "tp": 1500.0}

    def stop_tp_orders(self, *a, **kw):
        return {"ok": True}


class _Bot:
    def __init__(self):
        self.exchange = _Ex()
        self.portfolio = type("P", (), {"positions": {}})()
        self.managed = {}


class TestAdoptDongBoEntry(unittest.TestCase):
    """`position_sync.adopt` phai lay `entryPrice` THAT tu san lam goc R (B-075)."""

    def _rows(self, entry: float):
        return [{"symbol": "MOG/USDT:USDT", "side": "long", "contracts": 64.7,
                 "entryPrice": entry, "markPrice": entry}]

    def _state(self, entry: float):
        return {"trades": {"MOG/USDT:USDT": {
            "symbol": "MOG/USDT:USDT", "direction": "LONG", "entry": entry,
            "qty": 64.7, "sl": 0.0755, "tp": 0.0805, "initial_sl": 0.0755,
            "init_qty": 64.7, "partial_done": False, "be_done": False,
            "booked_pnl": 0.0, "mfe_r": 0.0, "strategy": "B_BREAKOUT_RETEST"}}}

    def test_state_lech_thi_dong_bo_theo_san(self):
        bot = _Bot()
        rep = ps.adopt(bot, self._rows(0.07963), managed=self._state(0.07926)["trades"])
        self.assertEqual(rep["entry_fix"], ["MOG/USDT:USDT"])
        mt = bot.managed["MOG/USDT:USDT"]
        self.assertAlmostEqual(mt.entry, 0.07963)
        self.assertAlmostEqual(mt.initial_sl, 0.0755)
        self.assertAlmostEqual(bot.portfolio.positions["MOG/USDT:USDT"].entry, 0.07963)

    def test_state_khop_thi_khong_dong_bo(self):
        bot = _Bot()
        rep = ps.adopt(bot, self._rows(0.07930), managed=self._state(0.07926)["trades"])
        self.assertEqual(rep["entry_fix"], [])
        self.assertAlmostEqual(bot.managed["MOG/USDT:USDT"].entry, 0.07926)

    def test_chien_luoc_van_song_qua_adopt(self):
        bot = _Bot()
        ps.adopt(bot, self._rows(0.07963), managed=self._state(0.07926)["trades"])
        self.assertEqual(bot.managed["MOG/USDT:USDT"].strategy, "B_BREAKOUT_RETEST")


class TestPendingPositions(unittest.TestCase):
    def test_chi_gom_open_chua_close(self):
        path = _write([_open(1000.0),
                       _open(2000.0, pair="BTC/USDT:USDT", direction="SHORT",
                             qty=0.031, entry=84100.0),
                       _close(5000.0)])
        try:
            rows = journal.pending_positions(path)
            self.assertEqual([(p, d) for p, d, _e in rows], [("BTC/USDT:USDT", "SHORT")])
        finally:
            os.unlink(path)

    def test_ban_ghi_void_khong_tinh(self):
        path = _write([_open(1000.0), _open(2000.0, void=True), _close(5000.0)])
        try:
            self.assertEqual(journal.pending_positions(path), [])
        finally:
            os.unlink(path)


class TestMatchesPending(unittest.TestCase):
    """So khop MEM: cap + huong + gia vao Â±0,5%, BO qty (partial lam qty giam)."""

    rows = [("ETH/USDT:USDT", "SHORT", 1708.79)]

    def test_gia_ke_hoach_lech_nhe_van_khop(self):
        self.assertTrue(journal.matches_pending(self.rows, pair="ETH/USDT:USDT",
                                                direction="SHORT", qty=0.008,
                                                entry=1712.0))   # +0,19%

    def test_qty_da_giam_sau_partial_van_khop(self):
        self.assertTrue(journal.matches_pending(self.rows, pair="ETH/USDT:USDT",
                                                direction="SHORT", qty=0.008,
                                                entry=1708.79))

    def test_lech_qua_nguong_thi_khong_khop(self):
        self.assertFalse(journal.matches_pending(self.rows, pair="ETH/USDT:USDT",
                                                 direction="SHORT", entry=1750.0))

    def test_khac_huong_thi_khong_khop(self):
        self.assertFalse(journal.matches_pending(self.rows, pair="ETH/USDT:USDT",
                                                 direction="LONG", entry=1708.79))

    def test_khac_cap_thi_khong_khop(self):
        self.assertFalse(journal.matches_pending(self.rows, pair="BTC/USDT:USDT",
                                                 direction="SHORT", entry=1708.79))

    def test_gia_vao_khong_ro_thi_coi_la_khop(self):
        self.assertTrue(journal.matches_pending(self.rows, pair="ETH/USDT:USDT",
                                                direction="SHORT", entry=0.0))

    def test_rong_thi_khong_khop(self):
        self.assertFalse(journal.matches_pending([], pair="ETH/USDT:USDT",
                                                 direction="SHORT", entry=1708.79))


class TestPendingKhongDemTho(unittest.TestCase):
    """B-078: bo dem `so OPEN - so CLOSE` theo cap+huong am ⇒ vi the DANG MO bi coi la da
    dong ⇒ ADOPT ghi `OPEN` lap. Phai ghep theo (cap, huong, GIA VAO) tung ban ghi.

    Do that LIVE 27/11 11:12: ETH `1705.46` / XRP `0.9621` / SOL `70.11` bi ghi lai OPEN
    dung luc vi the van mo, chi vi lich su cap do co nhieu CLOSE hon OPEN.
    """

    def test_close_thua_khong_keo_open_that_xuong(self):
        """3 CLOSE nhung chi 2 OPEN: CLOSE thua KHONG duoc "an" vi the con mo."""
        path = _write([
            _open(1000.0, entry=1630.78),
            _close(2000.0, entry=1630.78),
            _open(3000.0, entry=1691.89),
            _close(4000.0, entry=1691.89),
            _open(5000.0, entry=1705.46),          # vi the DANG MO (khong co CLOSE)
            _close(5500.0, entry=1500.00),         # CLOSE ghi bu / dong tay cap do khac
            _close(6000.0, entry=1500.00),         # tiep: tong CLOSE > OPEN
        ])
        try:
            rows = journal.pending_positions(path)
            self.assertEqual([(p, d, e) for p, d, e in rows],
                             [("ETH/USDT:USDT", "SHORT", 1705.46)])
            self.assertTrue(journal.matches_pending(rows, pair="ETH/USDT:USDT",
                                                    direction="SHORT", entry=1705.46))
        finally:
            os.unlink(path)

    def test_close_cung_gia_vao_moi_khep_open(self):
        path = _write([_open(1000.0, entry=1705.46), _close(2000.0, entry=1705.46)])
        try:
            self.assertEqual(journal.pending_positions(path), [])
        finally:
            os.unlink(path)

    def test_close_truoc_open_khong_khep(self):
        path = _write([_close(1000.0, entry=1705.46), _open(2000.0, entry=1705.46)])
        try:
            self.assertEqual(len(journal.pending_positions(path)), 1)
        finally:
            os.unlink(path)

    def test_pending_keys_cung_khong_dem_tho(self):
        path = _write([
            _open(1000.0, entry=1705.46),
            _close(2000.0, entry=1500.00),
            _close(3000.0, entry=1500.00),
        ])
        try:
            keys = journal.pending_keys(path)
            self.assertIn(journal.rec_key(pair="ETH/USDT:USDT", direction="SHORT",
                                          qty=0.016, entry=1705.46), keys)
        finally:
            os.unlink(path)

    def test_open_cu_qua_lau_khong_ghep_close_moi(self):
        """OPEN 40 ngay truoc mot CLOSE cung gia ⇒ khong phai cung vi the (lag > 30 ngay)."""
        old = 1000.0
        path = _write([_open(old, entry=1705.46),
                       _close(old + journal.CLOSE_MAX_LAG_SEC + 60.0, entry=1705.46)])
        try:
            self.assertEqual(len(journal.pending_positions(path)), 1)
        finally:
            os.unlink(path)


class TestTurboDemoWiring(unittest.TestCase):
    """B-076: `_pending_rows` phai TON TAI va tra du lieu that (truoc day NameError)."""

    def test_pending_rows_ton_tai_va_goi_duoc(self):
        import turbo_demo as td
        self.assertTrue(callable(getattr(td, "_pending_rows", None)))

    def test_pending_rows_doc_theo_cwd_va_cache_tu_lam_moi(self):
        import turbo_demo as td
        cwd = os.getcwd()
        tmp = tempfile.mkdtemp()
        jp = os.path.join(tmp, "logs", "journal.jsonl")
        try:
            os.makedirs(os.path.join(tmp, "logs"), exist_ok=True)
            with open(jp, "w", encoding="utf-8") as f:
                f.write(json.dumps(_open(1000.0, pair="SOL/USDT:USDT", direction="LONG",
                                         qty=0.09, entry=71.82)) + "\n")
            os.chdir(tmp)
            td._PENDING_CACHE.clear()
            rows = td._pending_rows()
            self.assertEqual([(p, d) for p, d, _e in rows], [("SOL/USDT:USDT", "LONG")])
            self.assertTrue(journal.matches_pending(rows, pair="SOL/USDT:USDT",
                                                    direction="LONG", qty=0.09,
                                                    entry=71.9))
            # mtime doi (bot ghi them ban ghi) â‡’ cache phai tu lam moi
            with open(jp, "a", encoding="utf-8") as f:
                f.write(json.dumps(_open(2000.0, pair="ADA/USDT:USDT", direction="SHORT",
                                         qty=550, entry=0.150449)) + "\n")
            os.utime(jp, (time.time() + 5, time.time() + 5))
            self.assertEqual(len(td._pending_rows()), 2)
        finally:
            os.chdir(cwd)
            td._PENDING_CACHE.clear()
            try:
                os.unlink(jp)
                os.rmdir(os.path.join(tmp, "logs"))
                os.rmdir(tmp)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()


