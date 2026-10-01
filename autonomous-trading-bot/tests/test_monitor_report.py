"""Unit test cho monitor_report (journal OPEN/CLOSE pairing + WR/PF + verdict)."""
import json
import os
import tempfile
import unittest

import monitor_report as mr


class TestJournalLoad(unittest.TestCase):
    def test_open_close_split_and_pairing(self):
        recs = [
            {"event": "OPEN", "pair": "SOL/USDT:USDT", "entry": 100.0, "ts": 1.0},
            {"pair": "XRP/USDT:USDT", "entry": 1.0, "ts": 2.0},  # legacy OPEN (khong event)
            {"event": "CLOSE", "pair": "SOL/USDT:USDT", "won": True, "r": 2.0, "ts": 3.0},
            {"event": "CLOSE", "pair": "XRP/USDT:USDT", "won": False, "r": -1.0, "ts": 4.0},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                         encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
            path = f.name
        try:
            opens, closes = mr.load_journal(path)
            self.assertEqual(len(opens), 2)
            self.assertEqual(len(closes), 2)
            pairs, still = mr.match_pairs(opens, closes)
            self.assertEqual(len(pairs), 2)
            self.assertEqual(len(still), 0)
            st = mr.stats(pairs)
            self.assertEqual(st["n"], 2)
            self.assertEqual(st["wins"], 1)
            self.assertAlmostEqual(st["wr"], 50.0)
            self.assertAlmostEqual(st["e_r"], 0.5)  # (2.0 + -1.0) / 2
        finally:
            os.unlink(path)

    def test_stats_empty_and_pf(self):
        st = mr.stats([])
        self.assertEqual(st["n"], 0)
        self.assertAlmostEqual(st["pf_r"], 0.0)
        # 2 win +1R/+3R, 1 loss -1R -> PF = 4.0
        pairs = [({"pair": "A"}, {"won": True, "r": 1.0, "pnl": 10.0}),
                 ({"pair": "A"}, {"won": True, "r": 3.0, "pnl": 30.0}),
                 ({"pair": "B"}, {"won": False, "r": -1.0, "pnl": -10.0})]
        st2 = mr.stats(pairs)
        self.assertAlmostEqual(st2["pf_r"], 4.0)
        self.assertAlmostEqual(st2["pf_pnl"], 4.0)

    def test_verdict_gate(self):
        from collections import Counter
        bad = mr.verdict({"n": 0, "pf_r": 0.0}, Counter())
        self.assertFalse(bad["ready_for_live"])
        self.assertTrue(any("testnet" in r for r in bad["reasons"]))
        killed = mr.verdict({"n": 60, "pf_r": 1.5}, Counter({"KILLED": 1}))
        self.assertFalse(killed["ready_for_live"])
        good = mr.verdict({"n": 60, "pf_r": 1.5}, Counter())
        self.assertTrue(good["ready_for_live"])

    def test_scan_text_counts(self):
        from collections import Counter
        text = ("round 1 ... [{'symbol': 'BTC', 'status': 'BLOCKED_URGENT'}] "
                "[{'status': 'BLOCKED_LEARN'}] {'status': 'KILLED', 'reason': 'daily loss 2%'}")
        c = mr.scan_text(text)
        self.assertEqual(c["BLOCKED_URGENT"], 1)
        self.assertEqual(c["BLOCKED_LEARN"], 1)
        self.assertEqual(c["KILLED"], 1)
        self.assertIsInstance(c, Counter)

    def test_scan_logs_since_bo_lich_su_cu(self):
        import time
        old = ("2026-09-20 10:00:00 INFO x [{'status': 'BLOCKED_LEARN'}]\n"
               "garbage line without ts [{'status': 'BLOCKED_LEARN'}]\n")
        new = ("2026-09-29 10:00:00 INFO y [{'status': 'OPENED'}]\n"
               "{'status': 'KILLED', 'reason': 'daily loss 2%'}\n")
        now = time.time()
        self.assertEqual(mr.scan_text_since(old + new, now - 3 * 86400)["BLOCKED_LEARN"], 1)
        self.assertEqual(mr.scan_text_since(old + new, now - 3 * 86400)["OPENED"], 1)

    def test_log_line_ts(self):
        import time
        ts = mr.log_line_ts("2026-09-29 13:42:35,595 WARNING ADOPT ...")
        self.assertIsNotNone(ts)
        self.assertAlmostEqual(ts, time.time(), delta=30 * 86400)
        self.assertIsNone(mr.log_line_ts("khong co timestamp o day"))
        self.assertIsNone(mr.log_line_ts(""))

    def test_verdict_can_chat_luong_mau(self):
        import time
        from collections import Counter
        now = time.time()
        closes = [{"direction": "SHORT", "ts": now - i * 100.0} for i in range(60)]
        st = {"n": 60, "pf_r": 2.0}
        vd = mr.verdict(st, Counter(), closes=closes, window_days=3.0)
        self.assertFalse(vd["ready_for_live"])
        self.assertTrue(any("chieu" in r for r in vd["reasons"]))

    def test_verdict_du_2_chieu_va_3_ngay(self):
        import time
        from collections import Counter
        now = time.time()
        closes = ([{"direction": "SHORT", "ts": now - i * 3600.0} for i in range(5, 45)]
                  + [{"direction": "LONG", "ts": now - 2 * 86400 - i * 3600.0}
                     for i in range(5, 20)])
        vd = mr.verdict({"n": 55, "pf_r": 1.5}, Counter(), closes=closes, window_days=3.0)
        self.assertTrue(vd["ready_for_live"], vd["reasons"])

    def _closes_2_chieu(self):
        import time
        now = time.time()
        return ([{"direction": "SHORT", "ts": now - i * 3600.0} for i in range(5, 45)]
                + [{"direction": "LONG", "ts": now - 2 * 86400 - i * 3600.0}
                   for i in range(5, 20)])

    def test_verdict_blocked_learn_gan_day(self):
        """BLOCKED_LEARN chi tinh cua so gan day; mac dinh = CANH BAO, --strict moi chan."""
        from collections import Counter
        closes = self._closes_2_chieu()
        st = {"n": 55, "pf_r": 1.5}
        # Hoc dao lai (giong loi P0-7 cu): nhieu block hon OPENED trong 3 ngay
        soft = mr.verdict(st, Counter(), closes=closes,
                          recent_statuses=Counter({"BLOCKED_LEARN": 50, "OPENED": 3}),
                          window_days=3.0)
        self.assertTrue(soft["ready_for_live"], soft["reasons"])   # khong chan LIVE
        self.assertTrue(any("BLOCKED_LEARN" in w for w in soft["warnings"]), soft["warnings"])
        hard = mr.verdict(st, Counter(), closes=closes,
                          recent_statuses=Counter({"BLOCKED_LEARN": 50, "OPENED": 3}),
                          window_days=3.0, strict=True)
        self.assertFalse(hard["ready_for_live"])
        self.assertTrue(any("BLOCKED_LEARN" in r for r in hard["reasons"]), hard["reasons"])
        self.assertEqual(hard["warnings"], [])
        # Learner khoe: it block, mo lenh van chay -> khong co canh bao
        ok = mr.verdict(st, Counter(), closes=closes,
                        recent_statuses=Counter({"BLOCKED_LEARN": 4, "OPENED": 7}),
                        window_days=3.0)
        self.assertTrue(ok["ready_for_live"], ok["reasons"])
        self.assertEqual(ok["warnings"], [])
        # Duoi nguong nhieu (10) thi im lang — tranh mot vet block le keo canh bao
        qua_it = mr.verdict(st, Counter(), closes=closes,
                            recent_statuses=Counter({"BLOCKED_LEARN": 3, "OPENED": 0}),
                            window_days=3.0)
        self.assertEqual(qua_it["warnings"], [])
        # Khong truyen recent (mode cu) -> khong sinh canh bao gia tao
        legacy = mr.verdict(st, Counter(), closes=closes)
        self.assertEqual(legacy["warnings"], [])

    def test_scan_logs_tra_2_counter(self):
        import time
        txt = ("2026-09-20 10:00:00 cu [{'status': 'BLOCKED_LEARN'}]\n"
               "2026-09-29 10:00:00 moi [{'status': 'BLOCKED_LEARN'}]\n"
               "{'status': 'KILLED', 'reason': 'daily loss 2%'}\n")
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                         encoding="utf-8") as f:
            f.write(txt)
            path = f.name
        try:
            full, recent, kills, files = mr.scan_logs(
                [path], recent_ts=time.time() - 3 * 86400.0)
            self.assertEqual(full["BLOCKED_LEARN"], 2)   # toan bo lich su
            self.assertEqual(recent["BLOCKED_LEARN"], 1)  # dong 2026-09-20 bi loai
            self.assertEqual(recent["OPENED"], 0)
            self.assertTrue(files)
            # KILL LUON quet toan bo — khong do vao cua so
            self.assertEqual(len(kills), 1)
        finally:
            os.unlink(path)

    def test_scan_dem_blocked_strat(self):
        """Status BLOCKED_STRAT cua strategy gate duoc dem rieng (khong lan voi WAIT)."""
        from collections import Counter
        text = ("round 1 ... [{'status': 'BLOCKED_STRAT', 'strategy': 'A_TREND_PULLBACK'}] "
                "[{'status': 'WAIT'}] {'status': 'KILLED', 'reason': 'daily loss 2%'}")
        c = mr.scan_text(text)
        self.assertEqual(c["BLOCKED_STRAT"], 1)
        self.assertEqual(c["WAIT"], 1)
        self.assertEqual(c["KILLED"], 1)
        self.assertIsInstance(c, Counter)

    def test_verdict_strategy_gate_chua_du_mau(self):
        """Gate strategy: chua du mau -> chi CANH BAO, khong chan LIVE."""
        import time
        from collections import Counter
        now = time.time()
        closes = ([{"direction": "SHORT", "ts": now - i * 3600.0} for i in range(5, 45)]
                  + [{"direction": "LONG", "ts": now - 2 * 86400 - i * 3600.0}
                     for i in range(5, 20)])
        st = {"n": 55, "pf_r": 1.5}
        sg = {"A_TREND_PULLBACK": {"n": 6, "avg_r": -0.30}}
        ok = mr.verdict(st, Counter(), closes=closes, strategy_gate=sg,
                        window_days=3.0)
        self.assertTrue(ok["ready_for_live"], ok["reasons"])
        self.assertTrue(any("A_TREND_PULLBACK" in w for w in ok["warnings"]),
                        ok["warnings"])

    def test_verdict_strategy_gate_du_mau_chan_live(self):
        """Gate strategy: du mau + avgR am -> CHAN LIVE nhu PF thap."""
        import time
        from collections import Counter
        now = time.time()
        closes = ([{"direction": "SHORT", "ts": now - i * 3600.0} for i in range(5, 45)]
                  + [{"direction": "LONG", "ts": now - 2 * 86400 - i * 3600.0}
                     for i in range(5, 20)])
        st = {"n": 55, "pf_r": 1.5}
        sg = {"A_TREND_PULLBACK": {"n": 30, "avg_r": -0.39}}
        vd = mr.verdict(st, Counter(), closes=closes, strategy_gate=sg,
                        window_days=3.0)
        self.assertFalse(vd["ready_for_live"])
        self.assertTrue(any("A_TREND_PULLBACK" in r for r in vd["reasons"]),
                        vd["reasons"])

    def test_verdict_da_bi_runtime_chan_khong_dem_la_ly_do(self):
        """Neu runtime da chan nhom am -> khong chan LIVE vi no (da khong vao lenh)."""
        import time
        from collections import Counter
        now = time.time()
        closes = ([{"direction": "SHORT", "ts": now - i * 3600.0} for i in range(5, 45)]
                  + [{"direction": "LONG", "ts": now - 2 * 86400 - i * 3600.0}
                     for i in range(5, 20)])
        st = {"n": 55, "pf_r": 1.5}
        sg = {"A_TREND_PULLBACK": {"n": 30, "avg_r": -0.39}}
        vd = mr.verdict(st, Counter(), closes=closes, strategy_gate=sg,
                        window_days=3.0, runtime_blocked={"A_TREND_PULLBACK"})
        self.assertTrue(vd["ready_for_live"], vd["reasons"])
        self.assertTrue(any("DA BI STRATEGY GATE" in w for w in vd["warnings"]),
                        vd["warnings"])




if __name__ == "__main__":
    unittest.main()