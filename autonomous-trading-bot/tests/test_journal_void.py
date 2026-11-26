"""Unit test B-073: OPEN bi ghi TRUNG khi ADOPT chay lai (journal `void` + chan ghi lap)."""
import json
import os
import tempfile
import unittest

import journal
import monitor_report as mr


def _write(recs) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    with f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return f.name


def _open(ts, pair="ETH/USDT:USDT", direction="SHORT", qty=0.016, entry=1708.79, **kw):
    rec = {"ts": ts, "event": "OPEN", "pair": pair, "direction": direction,
           "entry": entry, "qty": qty, "sl": 1777.66, "tp": 1624.58,
           "strategy": "", "adopted": True, "reason": "ADOPT"}
    rec.update(kw)
    return rec


def _close(ts, pair="ETH/USDT:USDT", direction="SHORT", qty=0.016, entry=1708.79,
           exit_=1742.22):
    return {"ts": ts, "event": "CLOSE", "pair": pair, "direction": direction,
            "entry": entry, "qty": qty, "exit_price": exit_, "r": -1.0, "won": False,
            "pnl": -0.53, "reason": "SL"}


class TestFindDuplicateOpens(unittest.TestCase):
    def test_hai_open_cung_gia_va_mot_close_bi_coi_la_trung(self):
        opens = [_open(1000.0), _open(2000.0)]          # adopt ghi 2 lan, cung vi the
        closes = [_close(5000.0)]
        res = journal.find_duplicate_opens(opens, closes)
        self.assertEqual(len(res["dupes"]), 1)
        self.assertEqual(res["dupes"][0]["open"]["ts"], 1000.0)   # giu ban ghi da co CLOSE
        self.assertEqual(res["dupes"][0]["twin"]["ts"], 2000.0)
        self.assertEqual(res["review"], [])

    def test_hai_vi_the_that_khac_gia_khong_bi_danh_dau(self):
        opens = [_open(1000.0, entry=1700.0), _open(2000.0, entry=1710.0)]
        closes = [_close(5000.0, entry=1700.0), _close(6000.0, entry=1710.0)]
        res = journal.find_duplicate_opens(opens, closes)
        self.assertEqual(res["dupes"], [])
        self.assertEqual(res["review"], [])

    def test_vi_the_con_mo_chi_giu_ban_ghi_cu(self):
        opens = [_open(1000.0), _open(2000.0)]
        res = journal.find_duplicate_opens(opens, [])   # chua co CLOSE nao
        self.assertEqual(len(res["dupes"]), 1)
        self.assertEqual(res["dupes"][0]["open"]["ts"], 2000.0)   # void ban ghi SAU
        self.assertEqual(res["dupes"][0]["twin"]["ts"], 1000.0)   # giu ban ghi CU
        self.assertEqual(res["review"], [])

    def test_mot_vi_the_mot_open_khong_bi_danh_dau(self):
        res = journal.find_duplicate_opens([_open(1000.0)], [])
        self.assertEqual(res["dupes"], [])
        self.assertEqual(res["review"], [])

    def test_hai_ban_ghi_sat_nhau_duoi_30s_khong_bi_coi_la_trung(self):
        opens = [_open(1000.0), _open(1005.0)]
        res = journal.find_duplicate_opens(opens, [])
        self.assertEqual(res["dupes"], [])


class TestVoidRecords(unittest.TestCase):
    def test_void_ghi_co_void_va_load_journal_bo_qua(self):
        path = _write([_open(1000.0), _open(2000.0), _close(5000.0)])
        bak = []
        try:
            opens, closes = mr.load_journal(path)
            res = journal.find_duplicate_opens(opens, closes)
            rep = journal.void_records(path, [d["open"] for d in res["dupes"]], apply=True)
            self.assertEqual(rep["matched"], 1)
            self.assertTrue(rep["applied"])
            self.assertTrue(rep["backup"] and os.path.exists(rep["backup"]))
            bak.append(rep["backup"])
            o2, c2 = mr.load_journal(path)
            self.assertEqual((len(o2), len(c2)), (1, 1))   # OPEN trung bien mat khoi bo dem
            _pairs, still = mr.match_pairs(o2, c2)
            self.assertEqual(still, [])
            with open(path, "r", encoding="utf-8") as f:
                raw = [json.loads(line) for line in f if line.strip()]
            self.assertEqual(len(raw), 3)                  # lich su goc van con
            self.assertEqual(sum(1 for r in raw if r.get("void") is True), 1)
        finally:
            os.unlink(path)
            for b in bak:
                if b and os.path.exists(b):
                    os.unlink(b)

    def test_dry_run_khong_sua_file(self):
        path = _write([_open(1000.0), _open(2000.0), _close(5000.0)])
        try:
            with open(path, "r", encoding="utf-8") as f:
                before = f.read()
            rep = journal.void_records(path, [_open(1000.0)], apply=False)
            self.assertEqual(rep["matched"], 1)
            self.assertFalse(rep["applied"])
            with open(path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), before)
        finally:
            os.unlink(path)


class TestPendingKeys(unittest.TestCase):
    def test_pending_chi_gom_vi_the_chua_dong(self):
        path = _write([_open(1000.0),
                       _open(2000.0, pair="BTC/USDT:USDT", qty=0.031, entry=84100.0),
                       _close(5000.0)])
        try:
            keys = journal.pending_keys(path)
            self.assertIn(journal.rec_key(pair="BTC/USDT:USDT", direction="SHORT",
                                          qty=0.031, entry=84100.0), keys)
            self.assertNotIn(journal.rec_key(pair="ETH/USDT:USDT", direction="SHORT",
                                             qty=0.016, entry=1708.79), keys)
        finally:
            os.unlink(path)

    def test_ban_ghi_void_khong_duoc_tinh(self):
        path = _write([_open(1000.0), _open(2000.0, void=True), _close(5000.0)])
        try:
            self.assertEqual(journal.pending_keys(path), set())
        finally:
            os.unlink(path)


class TestAdoptKhongGhiLap(unittest.TestCase):
    """`position_sync.adopt`: co `unclosed_fn` bao da co OPEN ⇒ khong ghi them."""

    class _Ex:
        def fetch_protection(self, sym):
            return {"sl": 1777.66, "tp": 1624.58}

        def stop_tp_orders(self, *a, **kw):
            return {"ok": True}

    class _Bot:
        def __init__(self):
            self.exchange = TestAdoptKhongGhiLap._Ex()
            self.portfolio = type("P", (), {"positions": {}})()
            self.managed = {}

    def _rows(self):
        return [{"symbol": "ETH/USDT:USDT", "side": "short", "contracts": 0.016,
                 "entryPrice": 1708.79, "markPrice": 1710.0}]

    def test_khi_da_co_open_thi_khong_ghi_them(self):
        import position_sync as ps
        calls = []
        rep = ps.adopt(self._Bot(), self._rows(),
                       journal_fn=lambda **kw: calls.append(kw),
                       unclosed_fn=lambda **kw: True)
        self.assertEqual(rep["adopted"], ["ETH/USDT:USDT"])
        self.assertEqual(rep["journal_skip"], ["ETH/USDT:USDT"])
        self.assertEqual(calls, [])

    def test_chua_co_open_thi_van_ghi(self):
        import position_sync as ps
        calls = []
        rep = ps.adopt(self._Bot(), self._rows(),
                       journal_fn=lambda **kw: calls.append(kw),
                       unclosed_fn=lambda **kw: False)
        self.assertEqual(rep["journal_skip"], [])
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["adopted"])


if __name__ == "__main__":
    unittest.main()


