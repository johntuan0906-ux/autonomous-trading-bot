"""Test `compare_modes` — so sánh 2 chế độ + chọn phương án (KHÔNG gọi AI)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import compare_modes as CM


def _st(n=0, pf=0.0, wr=0.0, e=0.0, pnl=0.0):
    return {"n": n, "pf_r": pf, "wr": wr, "e_r": e, "pnl": pnl, "err": ""}


class TestDecide(unittest.TestCase):
    def test_mau_it_thi_giu_nguyen(self):
        self.assertEqual(CM.decide(_st(100, 1.3), _st(5, 0.5))[0], "GIU_NGUYEN")

    def test_live_pf_duoi_1_thi_giam_risk(self):
        self.assertEqual(CM.decide(_st(100, 1.3), _st(40, 0.92))[0], "GIAM_RISK_LIVE")

    def test_live_yeu_testnet_manh_thi_chi_testnet(self):
        self.assertEqual(CM.decide(_st(100, 1.25), _st(40, 1.05))[0], "CHI_TESTNET")

    def test_ca_2_manh_thi_tang_risk(self):
        self.assertEqual(CM.decide(_st(100, 1.25), _st(40, 1.22))[0], "TANG_RISK_LIVE")

    def test_mac_dinh_giu_nguyen(self):
        self.assertEqual(CM.decide(_st(100, 1.15), _st(40, 1.15))[0], "GIU_NGUYEN")


class TestApplyPick(unittest.TestCase):
    def _env(self) -> Path:
        d = Path(tempfile.mkdtemp())
        (d / ".env").write_text("RISK_PER_TRADE_PCT=0.5\nMAX_POSITIONS=2\nMIN_PF=1.05\n",
                                encoding="utf-8")
        return d

    def test_giam_risk_ghi_dung(self):
        d = self._env()
        res = CM.apply_pick("GIAM_RISK_LIVE", d)
        txt = (d / ".env").read_text(encoding="utf-8")
        self.assertTrue(res["ok"])
        self.assertIn("RISK_PER_TRADE_PCT=0.25", txt)
        self.assertIn("MAX_POSITIONS=1", txt)

    def test_tang_risk_khong_vuot_tran_cung(self):
        d = self._env()
        CM.apply_pick("TANG_RISK_LIVE", d)
        txt = (d / ".env").read_text(encoding="utf-8")
        self.assertIn("RISK_PER_TRADE_PCT=0.75", txt)      # <= RISK_MAX (1.0)
        self.assertIn("MAX_POSITIONS=3", txt)              # <= MAXPOS_MAX (3)

    def test_giu_nguyen_khong_sua_gi(self):
        d = self._env()
        res = CM.apply_pick("GIU_NGUYEN", d)
        self.assertTrue(res.get("noop"))
        self.assertIn("RISK_PER_TRADE_PCT=0.5", (d / ".env").read_text(encoding="utf-8"))

    def test_thieu_env_thi_bao_loi(self):
        res = CM.apply_pick("GIAM_RISK_LIVE", Path(tempfile.mkdtemp()))
        self.assertFalse(res["ok"])


class TestModeStats(unittest.TestCase):
    def test_journal_khong_ton_tai(self):
        st = CM.mode_stats(Path(tempfile.mkdtemp()) / "khong.jsonl")
        self.assertEqual(st["n"], 0)
        self.assertTrue(st["err"])

    def test_loc_theo_moc_thoi_gian(self):
        p = Path(tempfile.mkdtemp()) / "j.jsonl"
        rows = [{"event": "OPEN", "pair": "A", "ts": 100, "entry": 1.0, "qty": 1.0},
                {"event": "CLOSE", "pair": "A", "ts": 200, "r": 1.0, "won": True, "pnl": 1.0},
                {"event": "OPEN", "pair": "A", "ts": 300, "entry": 1.0, "qty": 1.0},
                {"event": "CLOSE", "pair": "A", "ts": 400, "r": -1.0, "won": False, "pnl": -1.0}]
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        st = CM.mode_stats(p, since=250)
        self.assertEqual(st["n"], 1)
        self.assertAlmostEqual(st["pnl"], -1.0)

    def test_khong_loc_thi_tinh_ca(self):
        p = Path(tempfile.mkdtemp()) / "j.jsonl"
        rows = [{"event": "OPEN", "pair": "A", "ts": 100, "entry": 1.0, "qty": 1.0},
                {"event": "CLOSE", "pair": "A", "ts": 200, "r": 2.0, "won": True, "pnl": 2.0}]
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        self.assertEqual(CM.mode_stats(p)["n"], 1)


if __name__ == "__main__":
    unittest.main()
