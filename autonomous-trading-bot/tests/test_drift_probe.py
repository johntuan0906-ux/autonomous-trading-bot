# -*- coding: utf-8 -*-
"""Test `tools/drift_probe.py` — đo lệch KHAI BÁO vs THỰC TẾ và lệch phân phối đầu vào.

Vì sao (26/10, hội đồng 4 ALLOW / 0 VETO): B-031 là bằng chứng mạnh nhất — journal có 3342 bản
ghi CLOSE mà trường `r` SAI hoàn toàn (r=793), không ai phát hiện nhiều tuần, và nó làm mọi báo
cáo (kể cả STATE.md: PF(R)=5.345 trong khi thật 1.013) thành RÁC. Phép đo này phải:
  1. so `.env` (ý định) với journal (giá trị bot ĐANG CHẠY) — bắt "sửa .env nhưng chưa restart";
  2. tính R/`rr` TỪ GIÁ, không tin trường sẵn có;
  3. **n nhỏ ⇒ KHÔNG kết luận**; chỉ HỎI khi vượt ngưỡng và câu hỏi phải kèm số đo được.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

import drift_probe as DP      # noqa: E402


def _open(ts, *, entry=100.0, sl=96.0, tp=112.0, lev=8, risk=1.2, pair="X/USDT:USDT",
          regime="TREND_UP", score=60.0, vol=1.0):
    return {"ts": ts, "event": "OPEN", "pair": pair, "direction": "LONG", "entry": entry,
            "sl": sl, "tp": tp, "leverage": lev, "risk_pct": risk, "risk_usdt": 12.0,
            "market_regime": regime, "score100": score, "volume_ratio": vol,
            "setup_type": "BOS_UP", "strategy": "A_TREND_PULLBACK", "htf_bias": "LONG",
            "btc_regime": "UP", "alpha": 0.1, "funding": 0.0001, "oi_chg": 0.02,
            "news_score": 0.0, "ls_ratio": 1.1}


class TestKhaiBao(unittest.TestCase):
    def test_declared_tinh_rr_tu_sl_tp_atr(self):
        d = DP.declared({"SL_ATR_MULT": "6", "TP_ATR_MULT": "12", "RISK_PER_TRADE_PCT": "1.2",
                         "LEVERAGE": "8", "PARTIAL_AT_R": "1.0", "MAX_POSITIONS": "6"})
        self.assertAlmostEqual(d["rr"], 2.0)
        self.assertEqual(d["leverage"], 8)
        self.assertAlmostEqual(d["risk_pct"], 1.2)
        self.assertEqual(d["max_positions"], 6)

    def test_declared_thieu_hoac_sai_thi_None(self):
        d = DP.declared({"SL_ATR_MULT": "", "TP_ATR_MULT": "bua"})
        self.assertIsNone(d["rr"])
        self.assertIsNone(d["tp_atr"])

    def test_read_env_bo_qua_comment(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / ".env"
            p.write_text("# SL_ATR_MULT=99\nSL_ATR_MULT=6\nTP_ATR_MULT=\"12\"\n",
                         encoding="utf-8")
            env = DP.read_env(p)
            self.assertEqual(env["SL_ATR_MULT"], "6")
            self.assertEqual(env["TP_ATR_MULT"], "12")

    def test_rr_va_sl_pct_tinh_tu_gia(self):
        rec = _open(1.0, entry=100.0, sl=96.0, tp=112.0)
        self.assertAlmostEqual(DP.rr_of(rec), 3.0)
        self.assertAlmostEqual(DP.sl_pct_of(rec), 4.0)

    def test_rr_khong_tin_truong_rr_san_co(self):
        rec = _open(1.0, entry=100.0, sl=94.0, tp=112.0)
        rec["rr"] = 999.0                      # truong rac (B-031)
        self.assertAlmostEqual(DP.rr_of(rec), 2.0)

    def test_cv_phat_hien_SL_co_dinh(self):
        self.assertAlmostEqual(DP._cv([4.0, 4.0, 4.0]), 0.0, places=6)
        self.assertGreater(DP._cv([2.0, 4.0, 6.0]), 0.3)


class TestThucTe(unittest.TestCase):
    def test_actual_chi_lay_trong_cua_so(self):
        opens = [_open(100.0), _open(1000.0)]
        a = DP.actual(opens, since=500.0)
        self.assertEqual(a["n"], 1)

    def test_actual_median_rr_sl_lev_risk(self):
        opens = [_open(1.0, entry=100.0, sl=94.0, tp=112.0),
                 _open(2.0, entry=100.0, sl=94.0, tp=112.0, lev=5, risk=0.5),
                 _open(3.0, entry=100.0, sl=94.0, tp=112.0)]
        a = DP.actual(opens, since=0.0)
        self.assertEqual(a["n"], 3)
        self.assertAlmostEqual(a["rr"], 2.0)
        self.assertEqual(a["leverage"], 8)
        self.assertAlmostEqual(a["risk_pct"], 1.2)

    def test_compare_ok_khi_khop(self):
        decl = DP.declared({"SL_ATR_MULT": "6", "TP_ATR_MULT": "12", "RISK_PER_TRADE_PCT": "1.2",
                            "LEVERAGE": "8"})
        # sl_pct BIEN THIEN (nhu ATR thay doi) va rr luon = 2.0 (TP = 12/6 x SL)
        opens = []
        for i in range(12):
            sd = 3.0 + 0.2 * i
            opens.append(_open(float(i), sl=100.0 - sd, tp=100.0 + 2 * sd))
        r = DP.compare_declared(decl, DP.actual(opens, since=0.0), min_n=10)
        self.assertTrue(r["ok"], r["findings"])

    def test_compare_bat_rr_lech(self):
        decl = DP.declared({"SL_ATR_MULT": "14", "TP_ATR_MULT": "69"})     # rr 4.93
        opens = [_open(float(i), sl=96.0, tp=112.0) for i in range(12)]    # rr 3.0
        r = DP.compare_declared(decl, DP.actual(opens, since=0.0), min_n=10)
        self.assertFalse(r["ok"])
        self.assertIn("rr", r["findings"][0]["field"])

    def test_compare_bat_env_chua_restart(self):
        decl = DP.declared({"RISK_PER_TRADE_PCT": "1.2", "LEVERAGE": "8"})
        opens = [_open(float(i), risk=0.25) for i in range(12)]            # bot dang chay 0.25%
        r = DP.compare_declared(decl, DP.actual(opens, since=0.0), min_n=10)
        self.assertFalse(r["ok"])
        self.assertTrue(any("risk" in f["field"] for f in r["findings"]))
        self.assertIn("chua restart", r["findings"][0]["why"])

    def test_compare_bat_SL_khong_theo_ATR(self):
        decl = DP.declared({"SL_ATR_MULT": "6", "TP_ATR_MULT": "12"})
        opens = [_open(float(i), sl=96.0, tp=112.0) for i in range(12)]    # sl_pct = 4% MOI lenh
        r = DP.compare_declared(decl, DP.actual(opens, since=0.0), min_n=10)
        self.assertFalse(r["ok"])
        self.assertTrue(any("ATR" in f["field"] for f in r["findings"]))

    def test_compare_khong_ket_luan_khi_n_nho(self):
        decl = DP.declared({"SL_ATR_MULT": "14", "TP_ATR_MULT": "69"})
        opens = [_open(float(i), sl=96.0, tp=112.0) for i in range(3)]
        r = DP.compare_declared(decl, DP.actual(opens, since=0.0), min_n=10)
        self.assertTrue(r["ok"])
        self.assertEqual(r["findings"], [])
        self.assertIn("CHUA ket luan", r["skipped"])


class TestPSI(unittest.TestCase):
    def test_psi_giong_nhau_thi_gan_0(self):
        v = [float(i) for i in range(40)]
        self.assertLess(DP.psi_numeric(v, v), 0.05)

    def test_psi_dich_chuyen_lon_thi_cao(self):
        base = [float(i) for i in range(40)]
        recent = [float(i) + 100 for i in range(40)]
        self.assertGreater(DP.psi_numeric(base, recent), DP.PSI_ALERT)

    def test_psi_thieu_mau_thi_tra_am(self):
        self.assertEqual(DP.psi_numeric([1.0, 2.0], [1.0, 2.0]), -1.0)
        self.assertEqual(DP.psi_categorical(["A"], ["B"]), -1.0)

    def test_psi_phan_loai_doi_ti_le(self):
        base = ["UP"] * 30 + ["DOWN"] * 10
        recent = ["UP"] * 10 + ["DOWN"] * 30
        self.assertGreater(DP.psi_categorical(base, recent), 0.5)

    def test_input_drift_lay_dac_trung_va_xep_hang(self):
        base = [_open(float(i), score=60.0) for i in range(20)]
        recent = [_open(1e6 + i, score=90.0) for i in range(20)]
        d = DP.input_drift(base + recent, since=1e5, baseline_since=0.0, baseline_until=1e5)
        feats = {x["feature"]: x["psi"] for x in d["items"]}
        self.assertIn("score100", feats)
        self.assertGreater(feats["score100"], DP.PSI_ALERT)
        self.assertEqual(d["worst"]["feature"], "score100")
        self.assertTrue(d["alert"])

    def test_input_drift_khong_co_gi_thi_items_rong(self):
        d = DP.input_drift([], since=0.0, baseline_since=0.0)
        self.assertEqual(d["items"], [])
        self.assertIsNone(d["worst"])


class TestCauHoiVaChongSpam(unittest.TestCase):
    def _rep(self, findings, alert=None):
        return {"name": "TESTNET", "dir": "x", "actual": {"n": 12, "hours": 24.0},
                "compare": {"ok": not findings, "findings": findings, "skipped": ""},
                "drift": {"alert": alert or [], "items": alert or [],
                          "worst": (alert or [None])[0]}}

    def test_khong_vuot_nguong_thi_khong_hoi(self):
        self.assertIsNone(DP.question_for(self._rep([])))

    def test_lech_cau_hinh_thi_hoi_uu_tien_cao_va_kem_so(self):
        f = {"field": "risk_per_trade_pct", "declared": 1.2, "actual": 0.25, "ok": False,
             "why": "lech 79%"}
        q = DP.question_for(self._rep([f]))
        self.assertIn("KHONG KHOP", q[0])
        self.assertIn("1.2", q[1])
        self.assertIn("restart de ap .env", q[2])
        self.assertEqual(q[3], "high")

    def test_lech_dau_vao_thi_hoi_muc_thuong(self):
        q = DP.question_for(self._rep([], alert=[{"feature": "score100", "psi": 0.4,
                                                  "n_base": 100, "n_recent": 20}]))
        self.assertIn("DICH CHUYEN", q[0])
        self.assertIn("0.40", q[0])
        self.assertEqual(q[3], "normal")

    def test_cooldown(self):
        st = {}
        self.assertTrue(DP._cooldown_ok(st, "k", now=0.0, hours=24.0))
        st["notified"] = {"k": {"ts": 0.0}}
        self.assertFalse(DP._cooldown_ok(st, "k", now=3600.0, hours=24.0))
        self.assertTrue(DP._cooldown_ok(st, "k", now=25 * 3600.0, hours=24.0))


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.state = self.base / "state.json"
        self.log = self.base / "drift.log"
        self.now = 10 ** 7.0
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def _mk(self, name, opens, env=None):
        d = self.base / name
        (d / "logs").mkdir(parents=True, exist_ok=True)
        # Moc thoi gian phai NAM TRONG cua so do (now - hours) — neu khong thi n=0 va tool
        # dung ket luan "chua du mau" (dung thiet ke, nhung test se hieu sai).
        recs = [dict(r, ts=self.now - 1000.0 + i) for i, r in enumerate(opens)]
        (d / "logs" / "journal.jsonl").write_text(
            "\n".join(DP.json.dumps(r) for r in recs), encoding="utf-8")
        (d / ".env").write_text("\n".join("%s=%s" % kv for kv in (env or {}).items()),
                                encoding="utf-8")
        return d

    def _enqueue(self, q, **kw):
        self.calls.append(dict(kw, question=q))
        return {"ok": True, "id": len(self.calls)}

    def _run(self, **kw):
        kw.setdefault("dirs", {"TESTNET": self.base / "tn"})
        kw.setdefault("now", self.now)
        kw.setdefault("state_path", self.state)
        kw.setdefault("log_path", self.log)
        kw.setdefault("enqueue", self._enqueue)
        kw.setdefault("notify", False)
        return DP.run(**kw)

    def test_lech_cau_hinh_thi_day_cau_hoi_vao_hang_doi(self):
        self._mk("tn", [_open(float(i), sl=96.0, tp=112.0) for i in range(12)],
                 env={"SL_ATR_MULT": "14", "TP_ATR_MULT": "69", "RISK_PER_TRADE_PCT": "1.2",
                      "LEVERAGE": "8"})
        res = self._run(min_n=10)
        self.assertFalse(res["ok"])
        self.assertEqual(res["need_human"], ["TESTNET/cau_hinh"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["priority"], "high")
        self.assertTrue(str(self.calls[0]["open_path"]).endswith("ops_questions.json"))
        self.assertTrue(self.state.exists())

    def test_khong_hoi_lai_trong_cooldown(self):
        self._mk("tn", [_open(float(i), sl=96.0, tp=112.0) for i in range(12)],
                 env={"SL_ATR_MULT": "14", "TP_ATR_MULT": "69"})
        self._run(min_n=10)
        self.calls.clear()
        res = self._run(min_n=10, cooldown_h=24.0)
        self.assertEqual(self.calls, [])
        self.assertEqual(res["need_human"], [])

    def test_khop_thi_khong_hoi_gi(self):
        opens = []
        for i in range(12):
            sd = 3.0 + 0.2 * i
            opens.append(_open(float(i), sl=100.0 - sd, tp=100.0 + 2 * sd))
        self._mk("tn", opens,
                 env={"SL_ATR_MULT": "6", "TP_ATR_MULT": "12", "RISK_PER_TRADE_PCT": "1.2",
                      "LEVERAGE": "8"})
        res = self._run(min_n=10)
        self.assertTrue(res["ok"])
        self.assertEqual(self.calls, [])

    def test_dry_run_khong_ghi_gi(self):
        self._mk("tn", [_open(float(i), sl=96.0, tp=112.0) for i in range(12)],
                 env={"SL_ATR_MULT": "14", "TP_ATR_MULT": "69"})
        self._run(min_n=10, dry_run=True)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())

    def test_n_nho_thi_khong_hoi(self):
        self._mk("tn", [_open(float(i), sl=96.0, tp=112.0) for i in range(3)],
                 env={"SL_ATR_MULT": "14", "TP_ATR_MULT": "69"})
        res = self._run(min_n=10)
        self.assertTrue(res["ok"])
        self.assertEqual(self.calls, [])

    def test_task_command_tro_dung_script(self):
        cmd = DP.task_command(python_exe="py.exe", script="C:/x/tools/drift_probe.py",
                              target="both")
        self.assertIn("drift_probe.py", cmd)
        self.assertIn("--target both", cmd)
        self.assertIn("--quiet", cmd)


if __name__ == "__main__":
    unittest.main()
