# -*- coding: utf-8 -*-
"""Test `tools/review_due.py` — rà soát lại thay đổi ĐÃ ÁP sau vài ngày, bằng chứng THẬT.

Vì sao (26/10, yêu cầu người vận hành: *"theo dõi tiếp, vài ngày sau xác nhận lại"*):
đổi hình học SL/TP dựa trên **backtest** — backtest chỉ là GIẢ THUYẾT. Tool này phải:
  1. **không kết luận khi `n` nhỏ** (tự hoãn và đo tiếp) — kết luận bằng n nhỏ là kết luận rác;
  2. tính **R THẬT từ giá**, KHÔNG tin trường `r` trong journal (đo thật 26/10: có bản ghi
     `r=793` và `r=+196` cho lệnh lỗ ⇒ dùng `r` sẵn có là rác);
  3. chỉ **hỏi** người vận hành (không tự đổi tham số), và câu hỏi phải vào `ops_queue`.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import harness_ledger as HL     # noqa: E402
import review_due as RD         # noqa: E402

DAY = 86400.0


def _open(ts, pair="X/USDT:USDT", d="LONG", entry=100.0, sl=96.0, tp=112.0, rr=0.0):
    return {"ts": ts, "event": "OPEN", "pair": pair, "direction": d, "entry": entry,
            "sl": sl, "tp": tp, "rr": rr}


def _close(ts, pair="X/USDT:USDT", d="LONG", exit_price=112.0, reason="TP", r=0.0):
    return {"ts": ts, "event": "CLOSE", "pair": pair, "direction": d,
            "exit_price": exit_price, "reason": reason, "r": r}


def _write_journal(path: Path, opens, closes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in list(opens) + list(closes):
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class TestPairTrades(unittest.TestCase):
    """Ghép OPEN→CLOSE và tính R THẬT từ giá (không tin trường `r`)."""

    def test_long_thang_va_lo(self):
        res = RD.pair_trades([_open(1.0, entry=100.0, sl=96.0)],
                             [_close(2.0, exit_price=112.0, reason="TP")])
        self.assertEqual(len(res["trades"]), 1)
        self.assertAlmostEqual(res["trades"][0]["r"], 3.0)
        self.assertTrue(res["trades"][0]["won"])

        res = RD.pair_trades([_open(1.0, entry=100.0, sl=96.0)],
                             [_close(2.0, exit_price=96.0, reason="SL")])
        self.assertAlmostEqual(res["trades"][0]["r"], -1.0)
        self.assertFalse(res["trades"][0]["won"])

    def test_short_doi_dau_dung(self):
        res = RD.pair_trades([_open(1.0, d="SHORT", entry=100.0, sl=104.0, tp=88.0)],
                             [_close(2.0, d="SHORT", exit_price=96.0)])
        self.assertAlmostEqual(res["trades"][0]["r"], 1.0, places=9)

    def test_bo_lenh_khong_ghep_duoc(self):
        res = RD.pair_trades([], [_close(2.0)])
        self.assertEqual(res["trades"], [])
        self.assertEqual(res["n_dropped"], 1)
        self.assertEqual(res["n_closes"], 1)

    def test_bo_R_ngoai_dai_hop_ly(self):
        # exit 1000 voi SL 96 ⇒ r = 225R: ban ghi hong, khong duoc vao mau.
        res = RD.pair_trades([_open(1.0, entry=100.0, sl=96.0)],
                             [_close(2.0, exit_price=1000.0)])
        self.assertEqual(res["trades"], [])
        self.assertEqual(res["n_dropped"], 1)

    def test_ghep_dung_lenh_mo_gan_nhat_chua_dung(self):
        opens = [_open(1.0, entry=100.0, sl=96.0), _open(10.0, entry=200.0, sl=196.0)]
        closes = [_close(5.0, exit_price=104.0), _close(20.0, exit_price=212.0)]
        tr = RD.pair_trades(opens, closes)["trades"]
        self.assertEqual(len(tr), 2)
        self.assertAlmostEqual(tr[0]["r"], 1.0)      # 104 vs SL 96 ⇒ +1R
        self.assertAlmostEqual(tr[1]["r"], 3.0)      # 212 vs SL 196 ⇒ +3R

    def test_rr_tinh_tu_gia_khong_tin_truong_rr(self):
        # Truong `rr` trong ban ghi ghi 99 (rac) nhung gia la 12/6 ⇒ rr = 2.0
        res = RD.pair_trades([_open(1.0, entry=100.0, sl=94.0, tp=112.0, rr=99.0)],
                             [_close(2.0, exit_price=112.0)])
        self.assertAlmostEqual(res["trades"][0]["rr"], 2.0)

    def test_bo_ban_ghi_thieu_gia(self):
        bad = {"ts": 1.0, "event": "OPEN", "pair": "X/USDT:USDT", "direction": "LONG",
               "entry": None, "sl": 96.0, "tp": 112.0}
        res = RD.pair_trades([bad], [_close(2.0)])
        self.assertEqual(res["trades"], [])

    def test_loc_theo_reason_van_giu_duoc_lenh_dust(self):
        # DUST cung la lenh that (r nho) — khong loai theo reason, chi loai theo DAI R.
        res = RD.pair_trades([_open(1.0, entry=100.0, sl=96.0)],
                             [_close(2.0, exit_price=100.4, reason="DUST")])
        self.assertEqual(len(res["trades"]), 1)
        self.assertAlmostEqual(res["trades"][0]["r"], 0.1)


class TestStatsVerdict(unittest.TestCase):
    """Thống kê + KẾT LUẬN CÓ KỶ LUẬT: `n` nhỏ thì KHÔNG kết luận."""

    def test_stats_pf_wr_avgr(self):
        trades = [{"ts": 1.0, "r": 3.0, "won": True}, {"ts": 2.0, "r": -1.0, "won": False},
                  {"ts": 3.0, "r": 2.0, "won": True}, {"ts": 4.0, "r": -1.0, "won": False}]
        s = RD.stats(trades)
        self.assertEqual(s["n"], 4)
        self.assertEqual(s["wins"], 2)
        self.assertAlmostEqual(s["wr"], 0.5)
        self.assertAlmostEqual(s["pf"], 2.5)          # 5R thang / 2R thua
        self.assertAlmostEqual(s["avg_r"], 0.75)

    def test_stats_loc_theo_cua_so(self):
        trades = [{"ts": 1.0, "r": 1.0, "won": True}, {"ts": 100.0, "r": -1.0, "won": False}]
        self.assertEqual(RD.stats(trades, since=50.0)["n"], 1)
        self.assertEqual(RD.stats(trades, since=0.0, until=50.0)["n"], 1)

    def test_stats_cua_so_rong(self):
        s = RD.stats([], since=0.0)
        self.assertEqual(s["n"], 0)
        self.assertEqual(s["pf"], 0.0)

    def test_merge_pf_theo_R_goc_khong_trung_binh_PF(self):
        a = RD.stats([{"ts": 1.0, "r": 1.0, "won": True}])                 # pos 1, neg 0
        b = RD.stats([{"ts": 1.0, "r": -1.0, "won": False}])               # pos 0, neg 1
        m = RD.merge(a, b)
        self.assertEqual(m["n"], 2)
        self.assertAlmostEqual(m["pf"], 1.0)          # (1+0)/(0+1) — khong phai (inf+0)/2

    def test_verdict_chua_du_du_lieu_thi_khong_ket_luan(self):
        base = RD.stats([{"ts": 1.0, "r": 1.0, "won": True}])
        new = RD.stats([{"ts": 1.0, "r": -1.0, "won": False}] * 5)
        v = RD.verdict(base, new, min_n=30)
        self.assertEqual(v["state"], "chua-du")
        self.assertFalse(v["need_human"], "chua du mau thi KHONG hoi nguoi (tranh nhieu)")

    def test_verdict_xau_hon(self):
        base = RD.stats([{"ts": 1.0, "r": 0.10, "won": True}] * 40)
        new = RD.stats([{"ts": 1.0, "r": -0.05, "won": False}] * 40)
        self.assertEqual(RD.verdict(base, new, min_n=30)["state"], "xau-hon")

    def test_verdict_tot_hon(self):
        base = RD.stats([{"ts": 1.0, "r": 0.0, "won": False}] * 40)
        new = RD.stats([{"ts": 1.0, "r": 0.30, "won": True}] * 40)
        self.assertEqual(RD.verdict(base, new, min_n=30)["state"], "tot-hon")

    def test_verdict_trong_nguong_nhieu_la_khong_ro(self):
        base = RD.stats([{"ts": 1.0, "r": 0.10, "won": True}] * 40)
        new = RD.stats([{"ts": 1.0, "r": 0.12, "won": True}] * 40)
        self.assertEqual(RD.verdict(base, new, min_n=30)["state"], "khong-ro")

    def test_verdict_khong_co_cua_so_nen(self):
        base = RD.stats([{"ts": 1.0, "r": 1.0, "won": True}])
        new = RD.stats([{"ts": 1.0, "r": 1.0, "won": True}] * 40)
        v = RD.verdict(base, new, min_n=30)
        self.assertEqual(v["state"], "khong-ro")
        self.assertTrue(v["need_human"])


class TestCauHoiVaChongSpam(unittest.TestCase):
    def test_lua_chon_theo_trang_thai(self):
        rep = {"id": "H-1", "change": "x", "new": {"n": 40, "wr": 0.4, "pf": 0.8,
                                                   "avg_r": -0.1},
               "base": {"n": 40, "wr": 0.5, "pf": 1.1, "avg_r": 0.1},
               "verdict": {"state": "xau-hon", "why": "w", "need_human": True}}
        q, why, opts, prio = RD.question_text(rep)
        self.assertIn("XAU HON", q)
        self.assertIn("ve 14/69 (duong lui)", opts)
        self.assertEqual(prio, "high")

        rep["verdict"] = {"state": "tot-hon", "why": "w", "need_human": True}
        q, _why, opts, prio = RD.question_text(rep)
        self.assertIn("TOT HON", q)
        self.assertEqual(prio, "normal")

    def test_should_push_cooldown_va_doi_trang_thai(self):
        st = {}
        self.assertTrue(RD.should_push(st, "k", now=0.0, cooldown_s=100.0, status="xau-hon"))
        st["pushed"] = {"k": {"ts": 0.0, "status": "xau-hon"}}
        self.assertFalse(RD.should_push(st, "k", now=50.0, cooldown_s=100.0,
                                       status="xau-hon"))
        self.assertTrue(RD.should_push(st, "k", now=50.0, cooldown_s=100.0,
                                      status="tot-hon"),
                        "trang thai DOI thi phai bao lai (khong im lang)")
        self.assertTrue(RD.should_push(st, "k", now=200.0, cooldown_s=100.0,
                                      status="xau-hon"))


class TestRun(unittest.TestCase):
    """Chạy 1 lần: chưa đủ dữ liệu ⇒ TỰ HOÃN; đủ dữ liệu ⇒ HỎI người vận hành (không tự đổi)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.ledger = self.base / "ledger.jsonl"
        self.state = self.base / "state.json"
        self.log = self.base / "review.log"
        self.now = 100 * DAY
        self.applied = self.now - 20 * DAY
        HL.add("risk", "doi hinh hoc SL/TP 14/69 -> 6/12", "backtest 10 cap x 60 ngay",
               decision="adopted", path=self.ledger, now=self.applied)
        self.rid = HL.read_all(self.ledger)[0]["id"]
        HL.schedule(self.rid, -10.0, path=self.ledger, now=self.now)   # dang den han
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def _enqueue(self, q, **kw):
        self.calls.append(dict(kw, question=q))
        return {"ok": True, "id": len(self.calls)}

    def _journal(self, name, opens, closes):
        _write_journal(self.base / name / "logs" / "journal.jsonl", opens, closes)

    def _dirs(self):
        return {"TESTNET": self.base / "tn", "LIVE": self.base / "lv"}

    def _trades(self, n, r, start):
        """n lenh LONG: SL = entry-4 ⇒ exit = entry + 4*r (r dung nhu mong muon)."""
        opens, closes = [], []
        for i in range(n):
            ts = start + i * 60.0
            opens.append(_open(ts, pair="P%d/USDT:USDT" % i))
            closes.append(_close(ts + 30.0, pair="P%d/USDT:USDT" % i,
                                 exit_price=100.0 + 4.0 * r))
        return opens, closes

    def _run(self, **kw):
        kw.setdefault("dirs", self._dirs())
        kw.setdefault("now", self.now)
        kw.setdefault("ledger_path", self.ledger)
        kw.setdefault("state_path", self.state)
        kw.setdefault("log_path", self.log)
        kw.setdefault("enqueue", self._enqueue)
        kw.setdefault("notify", False)
        return RD.run(**kw)

    def _nen(self, r=0.5, n=40):
        self.b_open, self.b_close = self._trades(n, r, self.applied - 13 * DAY)
        self._journal("tn", self.b_open, self.b_close)
        self._journal("lv", [], [])

    def _journal_new(self, opens, closes):
        """Ghi journal cua cua so MOI + giu ca cua so NEN (khong ghi de)."""
        self._journal("tn", list(getattr(self, "b_open", [])) + list(opens),
                      list(getattr(self, "b_close", [])) + list(closes))

    # ---------------------------------------------------------------- hanh vi

    def test_chua_du_du_lieu_thi_tu_hoan_va_khong_hoi(self):
        o, c = self._trades(3, 1.0, self.applied + DAY)      # moi co 3 lenh dong
        self._journal("tn", o, c)
        self._journal("lv", [], [])
        res = self._run(min_n=30)
        self.assertTrue(res["ok"])
        self.assertEqual(res["need_human"], [])
        self.assertEqual(self.calls, [], "chua du mau thi KHONG duoc hoi nguoi van hanh")
        self.assertIn("hoan lai", res["reviews"][0]["action"])
        rec = [r for r in HL.read_all(self.ledger) if r["id"] == self.rid][0]
        self.assertAlmostEqual(rec["review_at"], self.now + 7 * DAY, places=1)
        self.assertTrue(self.state.exists(), "phai ghi vet trang thai (khong im lang)")

    def test_du_du_lieu_xau_hon_thi_hoi_nguoi_van_hanh(self):
        self._nen(r=0.5)
        o, c = self._trades(40, -0.1, self.applied + DAY)    # cua so moi te hon
        self._journal_new(o, c)
        res = self._run(min_n=30)
        self.assertEqual(res["reviews"][0]["verdict"]["state"], "xau-hon")
        self.assertEqual(res["need_human"], [self.rid])
        self.assertEqual(len(self.calls), 2, "hoi CA 2 instance (TESTNET + LIVE)")
        self.assertIn("ve 14/69 (duong lui)", self.calls[0]["options"])
        self.assertEqual(self.calls[0]["priority"], "high")
        self.assertTrue(str(self.calls[0]["open_path"]).endswith("ops_questions.json"))
        rec = [r for r in HL.read_all(self.ledger) if r["id"] == self.rid][0]
        self.assertLess(rec["review_at"], self.now,
                        "co ket luan ⇒ GIU den han (nguoi van hanh phai tra loi)")

    def test_du_du_lieu_tot_hon_thi_hoi_kieu_xac_nhan(self):
        self._nen(r=0.0)
        o, c = self._trades(40, 0.4, self.applied + DAY)
        self._journal_new(o, c)
        res = self._run(min_n=30)
        self.assertEqual(res["reviews"][0]["verdict"]["state"], "tot-hon")
        self.assertIn("giu nguyen (da xac nhan)", self.calls[0]["options"])
        self.assertEqual(self.calls[0]["priority"], "normal")

    def test_khong_hoi_lai_trong_cooldown(self):
        self._nen(r=0.5)
        o, c = self._trades(40, -0.1, self.applied + DAY)
        self._journal_new(o, c)
        self._run(min_n=30)
        self.assertEqual(len(self.calls), 2)
        self.calls.clear()
        res = self._run(min_n=30, cooldown_h=72.0)
        self.assertEqual(self.calls, [], "khong duoc spam lai cung 1 trang thai")
        self.assertEqual(res["need_human"], [])

    def test_dry_run_khong_ghi_gi(self):
        o, c = self._trades(3, 1.0, self.applied + DAY)
        self._journal("tn", o, c)
        res = self._run(min_n=30, dry_run=True)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())
        rec = [r for r in HL.read_all(self.ledger) if r["id"] == self.rid][0]
        self.assertLess(rec["review_at"], self.now, "dry-run khong duoc doi ngay hen")
        self.assertTrue(res["reviews"])

    def test_force_bo_qua_ngay_hen_va_khong_tu_hoan(self):
        HL.schedule(self.rid, 10.0, path=self.ledger, now=self.now)   # chua den han
        o, c = self._trades(2, 1.0, self.applied + DAY)
        self._journal("tn", o, c)
        res = self._run(force=self.rid, min_n=30)
        self.assertEqual(len(res["reviews"]), 1)
        self.assertIn("chua du mau", res["reviews"][0]["action"])
        rec = [r for r in HL.read_all(self.ledger) if r["id"] == self.rid][0]
        self.assertGreater(rec["review_at"], self.now + 9 * DAY,
                           "force khong duoc ghi de ngay hen cua nguoi van hanh")

    def test_force_id_khong_co_thi_bao_loi(self):
        res = self._run(force="H-19990101-001")
        self.assertFalse(res["ok"])
        self.assertIn("khong tim thay", res["err"])

    def test_ban_ghi_rac_bi_loai_truoc_khi_tinh(self):
        # 30 lenh rac (exit 1000 ⇒ 225R) + 40 lenh that ⇒ chi 40 lenh that vao mau.
        ro, rc = [], []
        for i in range(30):
            ts = self.applied + DAY + i * 60.0
            ro.append(_open(ts, pair="R%d/USDT:USDT" % i))
            rc.append(_close(ts + 30.0, pair="R%d/USDT:USDT" % i, exit_price=1000.0))
        self._nen(r=0.5)
        o, c = self._trades(40, -0.1, self.applied + DAY)
        self._journal("tn", ro + o, rc + c)
        res = self._run(min_n=30)
        per = res["reviews"][0]["per"]["TESTNET"]
        self.assertEqual(per["n_trades"], 40)
        self.assertEqual(per["n_dropped"], 30)
        self.assertEqual(res["reviews"][0]["new"]["n"], 40)

    def test_khong_co_muc_den_han_thi_khong_lam_gi(self):
        HL.mark_review(self.rid, "da xac nhan", path=self.ledger, now=self.now)
        res = self._run()
        self.assertEqual(res["n_due"], 0)
        self.assertEqual(res["reviews"], [])


class TestCLI(unittest.TestCase):
    def test_task_command_tro_dung_script_va_target(self):
        cmd = RD.task_command(python_exe="py.exe", script="C:/x/tools/review_due.py",
                              target="both")
        self.assertIn("review_due.py", cmd)
        self.assertIn("--target both", cmd)
        self.assertIn("--quiet", cmd)

    def test_list_khong_can_journal(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            HL.add("risk", "x", "ev", decision="adopted", path=p, now=100.0,
                   review_days=1.0)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = RD.main(["--list", "--ledger", str(p)])
            self.assertEqual(rc, 0)
            self.assertIn("DEN HAN RA SOAT", buf.getvalue())

    def test_check_tra_ve_0_khi_khong_co_muc_den_han(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "l.jsonl"
            p.write_text("", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = RD.main(["--check", "--quiet", "--ledger", str(p)])
            self.assertEqual(rc, 0, "khong co muc den han thi KHONG duoc bao dong")


if __name__ == "__main__":
    unittest.main()
