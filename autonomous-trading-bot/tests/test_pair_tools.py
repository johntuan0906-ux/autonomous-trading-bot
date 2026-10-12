"""Test `pair_audit` (loại cặp thua dài hạn) + `tools/apply_symbols` (đổi định dạng + lọc)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import apply_symbols as AS      # noqa: E402
import pair_audit as PA         # noqa: E402


class TestToCcxt(unittest.TestCase):
    def test_doi_dinh_dang(self):
        self.assertEqual(AS.to_ccxt("BTCUSDT,1000PEPEUSDT,1INCHUSDT"),
                         ["BTC/USDT:USDT", "1000PEPE/USDT:USDT", "1INCH/USDT:USDT"])

    def test_bo_khoang_trang_va_xuong_dong(self):
        self.assertEqual(AS.to_ccxt(" BTCUSDT \nETHUSDT "),
                         ["BTC/USDT:USDT", "ETH/USDT:USDT"])

    def test_rong_hoac_chi_co_USDT(self):
        self.assertEqual(AS.to_ccxt(""), [])
        self.assertEqual(AS.to_ccxt("USDT"), [])


class TestPairStats(unittest.TestCase):
    def test_thong_ke_theo_cap(self):
        st = PA.pair_stats([{"pair": "A", "r": 2.0}, {"pair": "A", "r": -1.0},
                            {"pair": "B", "r": -1.0}])
        self.assertEqual(st["A"]["n"], 2)
        self.assertAlmostEqual(st["A"]["avg_r"], 0.5)
        self.assertAlmostEqual(st["A"]["pf_r"], 2.0)
        self.assertAlmostEqual(st["B"]["pf_r"], 0.0)

    def test_bo_qua_ban_ghi_khong_co_r(self):
        self.assertEqual(PA.pair_stats([{"pair": "A"}, {"pair": "B", "r": None}]), {})


class TestDecideBans(unittest.TestCase):
    def _st(self, n, avg_r, pf):
        return {"n": n, "avg_r": avg_r, "pf_r": pf, "wins": 1, "wr": 50.0, "total_r": avg_r * n}

    def test_ban_khi_du_mau_va_thua_rong(self):
        bans = PA.decide_bans({"X": self._st(40, -0.05, 0.9)}, min_n=30)
        self.assertEqual([b[0] for b in bans], ["X"])
        self.assertIn("avgR", bans[0][1])

    def test_khong_ban_khi_chua_du_mau(self):
        self.assertEqual(PA.decide_bans({"X": self._st(10, -0.5, 0.5)}, min_n=30), [])

    def test_khong_ban_khi_avgR_duong(self):
        self.assertEqual(PA.decide_bans({"X": self._st(50, 0.05, 0.9)}, min_n=30), [])

    def test_khong_ban_khi_pf_tot(self):
        self.assertEqual(PA.decide_bans({"X": self._st(50, -0.01, 1.3)}, min_n=30), [])

    def test_bo_qua_cap_khong_ten(self):
        self.assertEqual(PA.decide_bans({"?": self._st(50, -1.0, 0.1)}, min_n=30), [])


class TestStripFromEnv(unittest.TestCase):
    def test_go_cap_bi_ban_khoi_env(self):
        d = Path(tempfile.mkdtemp())
        (d / ".env").write_text("SYMBOLS=A/USDT:USDT,B/USDT:USDT\nEXTRA_SYMBOLS=C/USDT:USDT\n",
                                encoding="utf-8")
        res = PA.strip_from_env(d, {"B/USDT:USDT"})
        txt = (d / ".env").read_text(encoding="utf-8")
        self.assertTrue(res["ok"])
        self.assertIn("A/USDT:USDT,C/USDT:USDT", txt)
        self.assertNotIn("B/USDT:USDT", txt)

    def test_khong_co_ban_thi_bao_loi(self):
        d = Path(tempfile.mkdtemp())
        (d / ".env").write_text("SYMBOLS=A/USDT:USDT\n", encoding="utf-8")
        self.assertFalse(PA.strip_from_env(d, set())["ok"])


class TestAuditOne(unittest.TestCase):
    def test_ban_va_ghi_file_kem_bang_chung(self):
        d = Path(tempfile.mkdtemp())
        (d / "logs").mkdir()
        (d / ".env").write_text("SYMBOLS=X/USDT:USDT,Y/USDT:USDT\nEXTRA_SYMBOLS=\n",
                                encoding="utf-8")
        rows = [{"event": "CLOSE", "pair": "X/USDT:USDT", "r": -1.0, "ts": 1} for _ in range(40)]
        rows += [{"event": "CLOSE", "pair": "Y/USDT:USDT", "r": 1.0, "ts": 1} for _ in range(5)]
        (d / "logs" / "journal.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        res = PA.audit_one("T", d, days=0, min_n=30, max_avgr=0.0, max_pf=1.0, dry_run=False)
        self.assertIn("X/USDT:USDT", res["ban_moi"])
        ban = json.loads((d / "logs" / "banned_pairs.json").read_text(encoding="utf-8"))
        self.assertIn("X/USDT:USDT", ban)
        self.assertEqual(ban["X/USDT:USDT"]["n"], 40)
        self.assertNotIn("X/USDT:USDT", (d / ".env").read_text(encoding="utf-8"))
        self.assertIn("Y/USDT:USDT", (d / ".env").read_text(encoding="utf-8"))

    def test_dry_run_khong_ghi(self):
        d = Path(tempfile.mkdtemp())
        (d / "logs").mkdir()
        (d / ".env").write_text("SYMBOLS=X/USDT:USDT\n", encoding="utf-8")
        rows = [{"event": "CLOSE", "pair": "X/USDT:USDT", "r": -1.0, "ts": 1} for _ in range(40)]
        (d / "logs" / "journal.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        res = PA.audit_one("T", d, days=0, min_n=30, max_avgr=0.0, max_pf=1.0, dry_run=True)
        self.assertIn("X/USDT:USDT", res["ban_moi"])
        self.assertFalse((d / "logs" / "banned_pairs.json").exists())
        self.assertIn("X/USDT:USDT", (d / ".env").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
