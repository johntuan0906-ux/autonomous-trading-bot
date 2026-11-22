"""`tools/close_dust.py` — dong vi the BUI (B-054? khong: day la cong cu cho skill close-dust).

Chot: (a) chi chon vi the < minNotional; (b) DRY-RUN KHONG dat lenh nao; (c) khi apply thi
nang CUNG CHIEU roi dong TOAN BO va doc lai; (d) LIVE phai co --yes-live.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import close_dust as CD      # noqa: E402


class FakeEx:
    def __init__(self, price=2.0, step=1.0, left=0.0, boom=False, qty=1.0):
        self.price, self.step, self.left, self.boom = price, step, left, boom
        self.qty = float(qty)
        self.calls: list = []

    def last_price(self, sym):
        return self.price

    def quantize_qty(self, sym, qty):
        if self.step <= 0:
            return 0.0
        return int(max(0.0, qty) // self.step) * self.step

    def market_entry(self, sym, direction, qty):
        if self.boom:
            raise RuntimeError("-2019 Margin is insufficient")
        self.calls.append(("entry", sym, direction, qty))
        self.qty += float(qty)                      # vi the TANG (cung chieu)
        return {"ok": True}

    def position_qty(self, sym, direction=None):
        return self.qty

    def close_position(self, sym, direction, qty):
        self.calls.append(("close", sym, direction, qty))
        self.qty = float(self.left)                 # dong xong con lai bao nhieu (0 = sach)
        return {"ok": True}



def _pos(notional, symbol="ACE/USDT:USDT", direction="LONG", qty=1.0):
    return {"symbol": symbol, "direction": direction, "qty": qty,
            "notional": notional, "in_skip": True}


class TestChonBui(unittest.TestCase):
    def test_plan_nang(self):
        self.assertAlmostEqual(CD.plan_raise(1.0), 5.0)      # 6 - 1
        self.assertAlmostEqual(CD.plan_raise(4.9, 5.0, 6.0), 1.1)
        self.assertEqual(CD.plan_raise(5.0), 0.0)            # dung bang nguong => khong phai bui
        self.assertEqual(CD.plan_raise(0.0), 0.0)
        self.assertEqual(CD.plan_raise(0.0, 5.0, 100.0), 0.0)

    def test_lenh_nang_phai_dat_min_notional(self):
        # (20/11, B-070) do that: NEAR bui 2.87, "can them 3.13" ⇒ -4164 vi lenh nang < 5
        self.assertAlmostEqual(CD.add_order_usdt(3.13, 5.0), 5.0)
        self.assertAlmostEqual(CD.add_order_usdt(5.0, 5.0), 5.0)
        self.assertAlmostEqual(CD.add_order_usdt(6.0, 5.0), 6.0)   # need lon hon thi giu
        self.assertAlmostEqual(CD.add_order_usdt(0.0, 5.0), 5.0)

    def test_loc_vi_the_bui(self):
        poss = [
            {"symbol": "A/USDT:USDT", "contracts": 1, "notional": 0.8, "side": "long"},
            {"symbol": "B/USDT:USDT", "contracts": 1, "notional": 12.0, "side": "short"},
            {"symbol": "C/USDT:USDT", "contracts": 0, "notional": 0.0, "side": "long"},
            {"symbol": "D/USDT:USDT", "contracts": 2, "markPrice": 1.0, "side": "short"},
        ]
        got = CD.dust_positions(poss, dust={"A/USDT:USDT"})
        self.assertEqual([d["symbol"] for d in got], ["A/USDT:USDT", "D/USDT:USDT"])
        self.assertEqual(got[0]["direction"], "LONG")
        self.assertEqual(got[1]["direction"], "SHORT")
        self.assertAlmostEqual(got[1]["notional"], 2.0)
        self.assertTrue(got[0]["in_skip"])
        self.assertFalse(got[1]["in_skip"])


class TestDongMotViThe(unittest.TestCase):
    def test_dry_run_khong_dat_lenh(self):
        ex = FakeEx()
        r = CD.close_one(ex, _pos(1.0), apply=False, log=lambda *_: None)
        self.assertFalse(r["ok"])
        self.assertIn("DRY-RUN", r["why"])
        self.assertEqual(ex.calls, [])

    def test_apply_nang_roi_dong_toan_bo(self):
        ex = FakeEx(price=2.0, step=1.0, left=0.0, qty=1.0)
        r = CD.close_one(ex, _pos(1.0, qty=1.0), apply=True, log=lambda *_: None)
        self.assertTrue(r["ok"], r)
        kinds = [c[0] for c in ex.calls]
        self.assertEqual(kinds, ["entry", "close"])
        entry = ex.calls[0]
        self.assertEqual(entry[2], "LONG", "phai nang CUNG CHIEU")
        # (20/11, B-070) need 5 USDT ⇒ 2.5 => quantize 2.0 => chi 4.0 USDT < 5 ⇒ nang 1 buoc
        self.assertAlmostEqual(entry[3], 3.0, msg="lenh nang phai >= minNotional 5 USDT")
        self.assertGreaterEqual(entry[3] * 2.0, 5.0)
        self.assertAlmostEqual(ex.calls[1][3], 4.0,
                               msg="dong TOAN BO (1 cu + 3 nang) chu khong chi phan nang")

    def test_bui_sat_nguong_van_dong_duoc(self):
        # (20/11, B-070) dung ca NEAR that: bui 2.87 USDT, gia 3.13 ⇒ cu "nang 3.13" bi -4164
        ex = FakeEx(price=3.13, step=1.0, left=0.0, qty=1.0)
        r = CD.close_one(ex, _pos(2.87, symbol="NEAR/USDT:USDT", qty=1.0), apply=True,
                         log=lambda *_: None)
        self.assertTrue(r["ok"], r)
        entry = ex.calls[0]
        self.assertGreaterEqual(entry[3] * 3.13, 5.0, "lenh nang phai qua minNotional")
        self.assertAlmostEqual(ex.calls[1][3], 3.0, msg="1 cu + 2 nang = 3, dong toan bo")

    def test_step_qua_lon_thi_bao_ro_chu_khong_dat_lenh(self):
        class KhoEx(FakeEx):
            def quantize_qty(self, sym, qty):
                return 1.0 if qty > 0 else 0.0      # buoc nhay qua tho: 1 x 4.5 = 4.5 < 5

        ex = KhoEx(price=4.5, step=1.0, left=0.0, qty=1.0)
        r = CD.close_one(ex, _pos(1.0), apply=True, log=lambda *_: None)
        self.assertFalse(r["ok"])
        self.assertIn("minNotional", r["why"])
        self.assertEqual(ex.calls, [], "khong duoc dat lenh nao khi khong qua duoc minNotional")

    def test_con_lai_thi_bao_loi_chu_khong_bao_ok(self):
        ex = FakeEx(price=2.0, step=1.0, left=0.5)
        r = CD.close_one(ex, _pos(1.0), apply=True, log=lambda *_: None)
        self.assertFalse(r["ok"])
        self.assertIn("con", r["why"])

    def test_loi_san_thi_tra_why(self):
        ex = FakeEx(boom=True)
        r = CD.close_one(ex, _pos(1.0), apply=True, log=lambda *_: None)
        self.assertFalse(r["ok"])
        self.assertIn("-2019", r["why"])

    def test_qty_nang_0_thi_dung_lai(self):
        ex = FakeEx(price=1000.0, step=1.0)      # 5 USDT / 1000 = 0.005 => quantize 0
        r = CD.close_one(ex, _pos(1.0), apply=True, log=lambda *_: None)
        self.assertFalse(r["ok"])
        self.assertIn("qty nang = 0", r["why"])
        self.assertEqual(ex.calls, [])


class TestClearSkip(unittest.TestCase):
    def test_xoa_symbol_da_dong(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "logs").mkdir()
            p = base / "logs" / "dust_skip.json"
            p.write_text(json.dumps({"symbols": ["A/USDT:USDT", "B/USDT:USDT"]}),
                         encoding="utf-8")
            self.assertEqual(CD.clear_skip(base, ["A/USDT:USDT"]), 1)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["symbols"],
                             ["B/USDT:USDT"])
            self.assertEqual(CD.clear_skip(base, ["KHONG-CO"]), 0)

    def test_file_hong_khong_no(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(CD.clear_skip(Path(td), ["A"]), 0)


class TestPruneSkip(unittest.TestCase):
    def test_chi_giu_bui_hien_tai(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "logs").mkdir()
            p = base / "logs" / "dust_skip.json"
            p.write_text(json.dumps({"symbols": ["A", "B", "C"], "note": "x"}), encoding="utf-8")
            old, new = CD.prune_skip(base, ["C"])
            self.assertEqual(old, ["A", "B", "C"])
            self.assertEqual(new, ["C"])
            d = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(d["symbols"], ["C"])
            self.assertEqual(d.get("note"), "x", "giu cac truong khac")

    def test_danh_sach_rong_van_ghi(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            (base / "logs").mkdir()
            old, new = CD.prune_skip(base, [])
            self.assertEqual((old, new), ([], []))


class TestAnToanLive(unittest.TestCase):
    def test_live_apply_phai_co_yes_live(self):
        self.assertEqual(CD.main(["--target", "live", "--apply"]), 2)


if __name__ == "__main__":
    unittest.main()
