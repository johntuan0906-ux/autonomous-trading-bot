# -*- coding: utf-8 -*-
"""test_agents.py — tang multi-AI agent Phase 1: co van, offline, fail-open.

Vi sao test nay quan trong:
  1) Agent KHONG duoc co kha nang doi hanh vi trading -> kiem tra module khong
     import risk/portfolio/bot va khong chua lenh dat/huy lenh.
  2) Test suite KHONG duoc cham mang -> dung StubProvider / provider gia lap.
  3) Moi loi (provider, JSON sai, het ngan sach) phai FAIL-OPEN: tra NO_OPINION,
     khong bao gio nem loi ra ngoai (neu nem, vong lap trading se chet).
  4) Guardrail phai hoat dong: cache, tran cuoc goi/ngay, tran tien/ngay,
     circuit breaker khi loi lien tiep, state luu qua file + reset theo ngay.

Chay: python -m unittest tests.test_agents -v
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agents as A  # noqa: E402


class _FixedProvider:
    """Provider gia lap tra ve dung 1 chuoi (khong mang)."""

    name = "fixed"

    def __init__(self, text: str, model: str = "fixed-1"):
        self.text = text
        self.model = model
        self.calls = 0

    def complete(self, system: str, user: str, *, timeout: float = 5.0) -> dict:
        self.calls += 1
        return {"text": self.text, "tokens_in": 100, "tokens_out": 20}


class _BoomProvider:
    """Provider luon loi -> de kiem tra fail-open + circuit breaker."""

    name = "boom"

    def __init__(self, model: str = "boom-1"):
        self.model = model
        self.calls = 0

    def complete(self, system: str, user: str, *, timeout: float = 5.0) -> dict:
        self.calls += 1
        raise RuntimeError("simulated provider error")


def _cfg(**kw):
    base = dict(agents_enabled=True, agents_shadow=True, agent_cache_sec=900,
                agent_timeout_sec=5, agent_max_prompt_tokens=1200,
                agent_daily_calls=50, agent_daily_budget_usd=1.0,
                agent_max_errors=3, agent_provider="stub", agent_model="")
    base.update(kw)
    return SimpleNamespace(**base)


def _layer(provider=None, tmp=None, **kw):
    d = tmp or tempfile.mkdtemp()
    return A.AgentLayer(_cfg(**kw), provider=provider,
                        journal=os.path.join(d, "journal.jsonl"),
                        state_path=os.path.join(d, "state.json"))


class TestParseDecision(unittest.TestCase):
    def test_json_hop_le(self):
        out = A.parse_decision(json.dumps({"action": "VETO", "confidence": 0.8,
                                           "reasons": ["x"], "risk_flags": ["y"]}))
        self.assertEqual(out["action"], "VETO")
        self.assertAlmostEqual(out["confidence"], 0.8)
        self.assertEqual(out["parse"], "ok")

    def test_json_lan_trong_van_ban(self):
        out = A.parse_decision('Day la ket qua:\n{"action":"ALLOW","confidence":1.5}\nhet')
        self.assertEqual(out["action"], "ALLOW")
        self.assertAlmostEqual(out["confidence"], 1.0)   # kep ve 0..1

    def test_rac_fail_open(self):
        self.assertEqual(A.parse_decision("khong phai json")["action"], "NO_OPINION")
        self.assertEqual(A.parse_decision("")["action"], "NO_OPINION")
        self.assertEqual(A.parse_decision(None)["action"], "NO_OPINION")

    def test_dong_nghia_action(self):
        self.assertEqual(A.parse_decision('{"action":"BLOCK"}')["action"], "VETO")
        self.assertEqual(A.parse_decision('{"verdict":"yes"}')["action"], "ALLOW")
        self.assertEqual(A.parse_decision('{"action":"???"}')["action"], "NO_OPINION")


class TestStubProvider(unittest.TestCase):
    def test_tat_dinh_va_dung_rule(self):
        p = A.StubProvider()
        sysp, user = A.build_prompt("critic", {
            "role": "critic", "direction": "SHORT", "rsi": 20.0, "alpha": 0.2,
            "atr_pct": 0.01, "news_score": 0.0, "urgent_bearish": 0})
        d1 = A.parse_decision(p.complete(sysp, user)["text"])
        d2 = A.parse_decision(p.complete(sysp, user)["text"])
        self.assertEqual(d1["action"], "VETO")          # SHORT khi RSI 20
        self.assertEqual(d1, d2)                        # tat dinh
        self.assertEqual(p.calls, 2)

    def test_stub_bat_vi_mo_xau(self):
        p = A.StubProvider()
        sysp, user = A.build_prompt("macro", {
            "role": "macro", "direction": "LONG", "rsi": 55.0, "alpha": 0.3,
            "news_score": -0.7, "urgent_bearish": 25})
        self.assertEqual(A.parse_decision(p.complete(sysp, user)["text"])["action"],
                         "VETO")

    def test_stub_allow_khi_thuan(self):
        p = A.StubProvider()
        sysp, user = A.build_prompt("critic", {
            "role": "critic", "direction": "LONG", "rsi": 60.0, "alpha": 0.30,
            "atr_pct": 0.009, "news_score": 0.4, "urgent_bearish": 0})
        self.assertEqual(A.parse_decision(p.complete(sysp, user)["text"])["action"],
                         "ALLOW")

    def test_stub_review_rut_bai_hoc(self):
        p = A.StubProvider()
        win = A.build_prompt("review", {"role": "review", "r_multiple": 0.74,
                                        "won": True})
        loss = A.build_prompt("review", {"role": "review", "r_multiple": -1.0,
                                         "won": False})
        d_win = A.parse_decision(p.complete(*win)["text"])
        d_loss = A.parse_decision(p.complete(*loss)["text"])
        self.assertEqual(d_win["action"], "ALLOW")
        self.assertEqual(d_loss["action"], "VETO")
        self.assertIn("SL day du", d_loss["reasons"][0])


class TestGuardrails(unittest.TestCase):
    def test_cache_khong_goi_lai_provider(self):
        p = _FixedProvider('{"action":"ALLOW","confidence":0.5}')
        lyr = _layer(provider=p)
        pay = A.setup_payload("BTC/USDT:USDT", "LONG", 0.3, "B_BREAKOUT_RETEST",
                              {"rsi": 60.0}, {"score": 0.2})
        d1 = lyr.vote("critic", pay)
        d2 = lyr.vote("critic", pay)
        self.assertFalse(d1.cache_hit)
        self.assertTrue(d2.cache_hit)
        self.assertEqual(p.calls, 1)              # chi goi 1 lan
        self.assertEqual(d2.action, "ALLOW")

    def test_tran_cuoc_goi_ngay(self):
        p = _FixedProvider('{"action":"ALLOW","confidence":0.5}')
        lyr = _layer(provider=p, agent_daily_calls=1)
        lyr.vote("critic", {"a": 1})
        d2 = lyr.vote("critic", {"a": 2})
        self.assertEqual(p.calls, 1)              # khong goi them
        self.assertEqual(d2.action, "NO_OPINION")
        self.assertIn("tran cuoc goi", d2.note)

    def test_tran_ngan_sach_ngay(self):
        p = _FixedProvider('{"action":"ALLOW","confidence":0.5}')
        lyr = _layer(provider=p, agent_daily_budget_usd=0.0)
        d = lyr.vote("critic", {"a": 1})
        self.assertEqual(p.calls, 0)
        self.assertEqual(d.action, "NO_OPINION")
        self.assertIn("ngan sach", d.note)

    def test_fail_open_khi_provider_loi(self):
        p = _BoomProvider()
        lyr = _layer(provider=p)
        d = lyr.vote("critic", {"a": 1})
        self.assertEqual(d.action, "NO_OPINION")   # khong nem loi
        self.assertIn("loi provider", d.note)
        self.assertEqual(d.confidence, 0.0)

    def test_circuit_breaker_tat_sau_n_lan_loi(self):
        p = _BoomProvider()
        lyr = _layer(provider=p, agent_max_errors=2)
        lyr.vote("critic", {"a": 1})
        lyr.vote("critic", {"a": 2})
        self.assertTrue(lyr.budget.disabled())     # da ngat
        before = p.calls
        d = lyr.vote("critic", {"a": 3})
        self.assertEqual(p.calls, before)          # khong goi nua
        self.assertIn("TAT", d.note)

    def test_json_rac_tu_provider_van_an_toan(self):
        lyr = _layer(provider=_FixedProvider("day khong phai json"))
        d = lyr.vote("critic", {"a": 1})
        self.assertEqual(d.action, "NO_OPINION")
        self.assertEqual(d.risk_flags, [])

    def test_state_luu_file_va_reset_theo_ngay(self):
        tmp = tempfile.mkdtemp()
        st = os.path.join(tmp, "state.json")
        now = [1_700_000_000.0]
        b = A.AgentBudget(st, daily_calls=5, now_fn=lambda: now[0])
        b.note(cost=0.25, ok=True)
        self.assertEqual(b.calls(), 1)
        self.assertAlmostEqual(b.cost(), 0.25)
        b2 = A.AgentBudget(st, daily_calls=5, now_fn=lambda: now[0])
        self.assertEqual(b2.calls(), 1)            # khong reset cung ngay
        now[0] += 86400.0                          # sang ngay moi (UTC)
        b3 = A.AgentBudget(st, daily_calls=5, now_fn=lambda: now[0])
        self.assertEqual(b3.calls(), 0)
        self.assertAlmostEqual(b3.cost(), 0.0)
        self.assertEqual(b3.disabled(), "")

    def test_tat_mac_dinh_khi_cfg_khong_bat(self):
        lyr = _layer(provider=_FixedProvider("{}"), agents_enabled=False)
        self.assertFalse(lyr.enabled())
        d = lyr.vote("critic", {"a": 1})
        self.assertEqual(d.action, "NO_OPINION")
        self.assertEqual(d.note, "agents_enabled=false")


class TestShadowIsolation(unittest.TestCase):
    """Agent chi CO VAN: khong the doi hanh vi trading, khong lo bi mat."""

    def test_shadow_mac_dinh_true(self):
        lyr = _layer(provider=_FixedProvider('{"action":"VETO"}'))  # cfg bat san trong _cfg()
        self.assertTrue(lyr.shadow)
        d = lyr.vote("critic", {"a": 1})
        self.assertTrue(d.shadow)                  # nguoi goi biet la chi tham khao

    def test_module_khong_the_doi_hanh_vi_trading(self):
        """Khong co IMPORT that su toi risk/portfolio/bot + khong lenh dat/huy lenh.

        Chi xet dong import thuc (docstring co the nhac ten module de giai thich).
        """
        import re
        src = inspect.getsource(A)
        import_lines = [ln.strip() for ln in src.splitlines()
                        if re.match(r"\s*(import|from)\s+\w", ln)]
        for ln in import_lines:
            for bad_mod in ("risk", "portfolio", "bot", "turbo_demo"):
                self.assertFalse(
                    re.match(r"(import|from)\s+%s\b" % bad_mod, ln),
                    f"agents.py khong duoc import {bad_mod}: {ln}")
        for bad in ("create_order", "create_market_order", "close_position",
                    "stop_tp_orders", "_flatten", "kill.tripped"):
            self.assertNotIn(bad, src, f"agents.py khong duoc chua {bad}")

    def test_journal_ghi_event_agent_va_dem_duoc(self):
        tmp = tempfile.mkdtemp()
        jp = os.path.join(tmp, "journal.jsonl")
        lyr = A.AgentLayer(_cfg(), provider=_FixedProvider('{"action":"VETO"}'),
                           journal=jp, state_path=os.path.join(tmp, "st.json"))
        dec = lyr.vote("critic", {"a": 1})
        rec = lyr.log_decision(dec, extra={"symbol": "BTC/USDT:USDT", "status": "SETUP"})
        self.assertEqual(rec.get("event"), "AGENT")
        self.assertEqual(rec.get("action"), "VETO")
        self.assertEqual(A.count_agent_events(jp), {"critic:VETO": 1})
        # khong lan vao du lieu lenh: khong co truong entry/order
        self.assertNotIn("entry", rec)

    def test_payload_khong_chua_bi_mat_va_on_dinh_cache(self):
        p = A.setup_payload("SOL/USDT:USDT", "SHORT", 0.123456, "A_TREND_PULLBACK",
                            {"rsi": 47.777, "atr_pct": 0.01234567}, {"score": 0.2})
        self.assertEqual(p["alpha"], 0.123)        # lam tron -> cache hit
        self.assertEqual(p["rsi"], 47.8)
        body = json.dumps(p).lower()
        self.assertNotIn("api", body)
        self.assertNotIn("key", body)
        self.assertNotIn("balance", body)

    def test_build_prompt_cat_theo_ngan_sach(self):
        _sys, user = A.build_prompt("critic", {"big": "x" * 50_000}, max_tokens=200)
        self.assertLessEqual(len(user), 200 * 4 + 200)
        self.assertIn("cat bot", user)

    def test_cost_usd_theo_bang_gia(self):
        self.assertGreater(A.cost_usd("gpt-4o-mini", 1_000_000, 0), 0)
        self.assertAlmostEqual(A.cost_usd("stub-rules", 10 ** 6, 10 ** 6), 0.0)
        # model la -> tinh gia cao cho an toan (khong the vuot tran ngan sach)
        self.assertGreater(A.cost_usd("model-la-hoac", 10 ** 6, 0), 0)

    def test_provider_factory_fallback_stub(self):
        p = A.build_provider(SimpleNamespace(agent_provider="openai", agent_model=""))
        self.assertEqual(p.name, "stub")           # thieu key -> stub, khong crash
        p2 = A.build_provider(SimpleNamespace(agent_provider="khong-ton-tai"))
        self.assertEqual(p2.name, "stub")
        p3 = A.build_provider(None)
        self.assertEqual(p3.name, "stub")

class _FakeRunner:
    """Runner gia lap cho CopilotCliProvider (khong chay subprocess that)."""

    def __init__(self, rc=0, out="", err=""):
        self.rc, self.out, self.err = rc, out, err
        self.calls: list = []

    def __call__(self, cmd, timeout, cwd=None, env=None):
        self.calls.append({"cmd": cmd, "timeout": timeout, "cwd": cwd})
        return self.rc, self.out, self.err

class TestReviewPayload(unittest.TestCase):
    """01/10: review phai gui DU ngu canh, neu khong agent luon tra NO_OPINION."""

    def test_extra_duoc_gui_kem(self):
        p = A.review_payload("SOL/USDT:USDT", "SHORT", -1.02, False, "SL", "NONE",
                             extra={"entry": 117.9, "mfe_r": 0.4, "partial": True,
                                    "pnl": -10.5, "had_feats": True})
        for k in ("entry", "mfe_r", "partial", "pnl", "had_feats"):
            self.assertIn(k, p)
        self.assertEqual(p["strategy"], "NONE")
        self.assertEqual(p["direction"], "SHORT")
        self.assertEqual(p["exit_reason"], "SL")

    def test_khong_extra_van_chay(self):
        p = A.review_payload("BTC/USDT:USDT", "long", 0.5, True, "TP", "NONE")
        self.assertEqual(p["direction"], "LONG")
        self.assertTrue(p["won"])


class _RoleProvider:
    """Provider gia lap tra JSON khac nhau theo VAI TRO (doc tu user message)."""

    name = "rolebot"
    model = "role-1"

    def __init__(self, by_role: dict, default: dict | None = None):
        self.by_role = dict(by_role or {})
        self.default = dict(default or {"action": "NO_OPINION", "confidence": 0.0})
        self.calls = 0
        self.seen = []

    def complete(self, system: str, user: str, *, timeout: float = 5.0) -> dict:
        self.calls += 1
        role = "?"
        for r in ("arbiter", "critic", "macro", "review", "reflect"):
            if f'"role": "{r}"' in user or f'"role":"{r}"' in user:
                role = r
                break
        self.seen.append((role, user))
        payload = {**self.default, **self.by_role.get(role, {})}
        return {"text": json.dumps(payload), "tokens_in": 100, "tokens_out": 20}


class TestCouncil(unittest.TestCase):
    """Hoi dong 2 vong + chu toa (01/10): quy tac quorum TAT DINH + tom tat Telegram."""

    def test_ca_hai_allow_thi_allow_du_arbiter_muon_veto(self):
        p = _RoleProvider({"macro": {"action": "ALLOW", "confidence": 0.6},
                           "critic": {"action": "ALLOW", "confidence": 0.5},
                           "arbiter": {"action": "VETO", "confidence": 0.9}})
        res = A.council_decision(_layer(p), {"symbol": "SOL/USDT:USDT", "direction": "SHORT"})
        self.assertEqual(res["action"], "ALLOW", "dong thuan ALLOW khong bi ghi de")
        self.assertEqual(res["consensus"], "unanimous_allow")
        self.assertEqual(p.calls, 3, "phai goi du 3 vai (macro/critic/arbiter)")

    def test_ca_hai_veto_thi_veto_du_arbiter_allow(self):
        p = _RoleProvider({"macro": {"action": "VETO", "confidence": 0.8},
                           "critic": {"action": "VETO", "confidence": 0.7},
                           "arbiter": {"action": "ALLOW", "confidence": 0.9}})
        res = A.council_decision(_layer(p), {"symbol": "BTC/USDT:USDT", "direction": "LONG"})
        self.assertEqual(res["action"], "VETO", "dong thuan VETO khong the bi ghi de")
        self.assertEqual(res["consensus"], "unanimous_veto")
        self.assertAlmostEqual(res["confidence"], 0.8, places=6)

    def test_chia_phieu_thi_chu_toa_quyet(self):
        p = _RoleProvider({"macro": {"action": "ALLOW", "confidence": 0.6},
                           "critic": {"action": "VETO", "confidence": 0.75},
                           "arbiter": {"action": "ALLOW", "confidence": 0.65}})
        res = A.council_decision(_layer(p), {"symbol": "XRP/USDT:USDT", "direction": "SHORT"})
        self.assertEqual(res["action"], "ALLOW", "chia phieu -> theo chu toa")
        self.assertEqual(res["consensus"], "split")
        p2 = _RoleProvider({"macro": {"action": "ALLOW", "confidence": 0.6},
                            "critic": {"action": "VETO", "confidence": 0.75},
                            "arbiter": {"action": "VETO", "confidence": 0.8}})
        res2 = A.council_decision(_layer(p2), {"symbol": "XRP/USDT:USDT", "direction": "SHORT"})
        self.assertEqual(res2["action"], "VETO")
        self.assertEqual(res2["consensus"], "split")

    def test_critic_nhan_duoc_y_kien_macro(self):
        """Vong 2: critic PHAI doc duoc y kien cua macro (peer)."""
        p = _RoleProvider({"macro": {"action": "VETO", "confidence": 0.9},
                           "critic": {"action": "ALLOW", "confidence": 0.4},
                           "arbiter": {"action": "ALLOW", "confidence": 0.4}})
        A.council_decision(_layer(p), {"symbol": "ADA/USDT:USDT", "direction": "LONG"})
        critic_msgs = [u for r, u in p.seen if r == "critic"]
        self.assertTrue(critic_msgs, "critic phai duoc goi")
        self.assertIn('"peer"', critic_msgs[0], "critic phai nhan y kien macro")
        arb_msgs = [u for r, u in p.seen if r == "arbiter"]
        self.assertIn('"council"', arb_msgs[0], "chu toa phai nhan ca 2 y kien")

    def test_provider_loi_thi_khong_crash(self):
        res = A.council_decision(_layer(_BoomProvider()),
                                 {"symbol": "SOL/USDT:USDT", "direction": "SHORT"})
        self.assertEqual(res["action"], "NO_OPINION")

    def test_quorum_khi_thieu_phieu(self):
        m = SimpleNamespace(action="NO_OPINION", confidence=0.0)
        c = SimpleNamespace(action="NO_OPINION", confidence=0.0)
        a = SimpleNamespace(action="VETO", confidence=0.8)
        act, conf, _why = A._final_from_council(m, c, a)
        self.assertEqual((act, conf), ("VETO", 0.8))
        self.assertEqual(A.consensus_of("NO_OPINION", "NO_OPINION", act, "VETO"),
                         "arbiter_only")

    def test_tom_tat_telegram_ngan_va_du_vai(self):
        p = _RoleProvider({"macro": {"action": "ALLOW", "confidence": 0.6,
                                     "reasons": ["tin trung tinh"]},
                           "critic": {"action": "VETO", "confidence": 0.8,
                                      "reasons": ["RSI qua ban"]},
                           "arbiter": {"action": "VETO", "confidence": 0.8,
                                       "reasons": ["uu tien von"]}})
        res = A.council_decision(_layer(p), {"symbol": "SOL/USDT:USDT", "direction": "SHORT"})
        txt = A.council_summary_text("SOL/USDT:USDT", "SHORT", res)
        self.assertIn("COUNCIL SOL SHORT", txt)
        for role in ("macro", "critic", "arbiter"):
            self.assertIn(role, txt)
        self.assertLessEqual(len(txt), 400)


class _FixedModelProvider:
    """Provider gia lap 1 model that CO THE "treo" (loi) de kiem tra bo qua phieu."""

    name = "fixed_model"

    def __init__(self, model: str, response: dict | None = None, boom: bool = False):
        self.model = model
        self.response = dict(response or {"action": "NO_OPINION", "confidence": 0.0})
        self.boom = boom
        self.calls = 0

    def complete(self, system: str, user: str, *, timeout: float = 5.0) -> dict:
        self.calls += 1
        if self.boom:
            raise RuntimeError("treo/loi mo phong")
        return {"text": json.dumps(self.response), "tokens_in": 50, "tokens_out": 10}


class TestMultiModelCouncil(unittest.TestCase):
    """Hoi dong NHIEU MODEL THAT song song: khong chon 1 model, chi loai phieu trang."""

    def _cfg_mm(self, tmp):
        return _cfg(agent_state_path=os.path.join(tmp, "state.json"))

    def _factory(self, responses: dict, hung: tuple = ()):
        def make(model: str):
            return _FixedModelProvider(model, response=responses.get(model),
                                       boom=model in hung)
        return make

    def test_chay_het_cac_model_va_bo_qua_model_treo(self):
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b", "model-c"]
        factory = self._factory({
            "model-a": {"action": "ALLOW", "confidence": 0.6},
            "model-b": {"action": "ALLOW", "confidence": 0.8},
        }, hung=("model-c",))
        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "BTC/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertEqual(res["action"], "ALLOW")
        self.assertEqual(res["abstained"], ["model-c"], "model treo phai bi loai, khong tinh phieu")
        self.assertEqual(set(res["votes"]), {"model-a", "model-b"})

    def test_khong_co_model_nao_duoc_chon_dai_dien_quorum_quyet_dinh(self):
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b", "model-c"]
        factory = self._factory({
            "model-a": {"action": "VETO", "confidence": 0.7},
            "model-b": {"action": "VETO", "confidence": 0.9},
            "model-c": {"action": "ALLOW", "confidence": 0.5},
        })
        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "ETH/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertEqual(res["action"], "VETO", "2 VETO > 1 ALLOW -> VETO (khong phai 1 model quyet)")
        self.assertEqual(len(res["votes"]), 3, "ca 3 model deu duoc hoi, khong ai bi bo qua khi tra loi")

    def test_hoa_phieu_thi_no_opinion_khong_chan_lenh(self):
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b"]
        factory = self._factory({
            "model-a": {"action": "VETO", "confidence": 0.7},
            "model-b": {"action": "ALLOW", "confidence": 0.7},
        })
        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "SOL/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertEqual(res["action"], "NO_OPINION")

    def test_tat_ca_model_treo_thi_no_opinion_khong_crash(self):
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b"]
        factory = self._factory({}, hung=("model-a", "model-b"))
        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "XRP/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertEqual(res["action"], "NO_OPINION")
        self.assertEqual(set(res["abstained"]), {"model-a", "model-b"})
        self.assertEqual(res["votes"], {})

    def test_van_de_de_khong_ton_them_ngan_sach(self):
        """Dong thuan ro rang, khong model nao treo -> KHONG escalate (giam nhe chi phi)."""
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b", "model-c"]
        factory = self._factory({
            "model-a": {"action": "ALLOW", "confidence": 0.6},
            "model-b": {"action": "ALLOW", "confidence": 0.7},
            "model-c": {"action": "ALLOW", "confidence": 0.8},
        })
        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "BTC/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertFalse(res["escalated"])
        self.assertEqual(res["action"], "ALLOW")

    def test_van_de_kho_tu_hoi_lai_model_treo_voi_ngan_sach_hard(self):
        """Vong 1 hoa phieu (1 ALLOW/1 VETO) + 1 model treo -> tu dong hoi lai model
        treo voi timeout/ngan sach 'hard'; neu lan nay model tra loi -> het hoa phieu."""
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b", "model-c"]
        attempts = {"model-c": 0}

        def factory(model: str):
            if model == "model-a":
                return _FixedModelProvider(model, response={"action": "ALLOW", "confidence": 0.6})
            if model == "model-b":
                return _FixedModelProvider(model, response={"action": "VETO", "confidence": 0.7})
            attempts["model-c"] += 1
            return _FixedModelProvider(model, response={"action": "ALLOW", "confidence": 0.5},
                                       boom=(attempts["model-c"] == 1))

        res = A.multi_model_council(self._cfg_mm(tmp), {"symbol": "XRP/USDT:USDT"},
                                    role="critic", models=models, provider_factory=factory)
        self.assertTrue(res["escalated"], "vong 1 hoa phieu -> phai tu hoi lai model treo")
        self.assertEqual(res["action"], "ALLOW", "model-c tra loi o lan hoi lai -> het hoa phieu")
        self.assertNotIn("model-c", res["abstained"])
        self.assertIn("ngan sach", res["why"])
        self.assertEqual(attempts["model-c"], 2, "model treo phai duoc hoi LAI, khong bi bo luon")

    def test_tat_adaptive_thi_khong_tu_hoi_lai(self):
        tmp = tempfile.mkdtemp()
        models = ["model-a", "model-b", "model-c"]
        cfg = self._cfg_mm(tmp)
        cfg.agent_budget_adaptive = False
        factory = self._factory({
            "model-a": {"action": "ALLOW", "confidence": 0.6},
            "model-b": {"action": "VETO", "confidence": 0.7},
        }, hung=("model-c",))
        res = A.multi_model_council(cfg, {"symbol": "XRP/USDT:USDT"}, role="critic",
                                    models=models, provider_factory=factory)
        self.assertFalse(res["escalated"])
        self.assertEqual(res["action"], "NO_OPINION")
        self.assertIn("model-c", res["abstained"])

    def test_cline_models_ngoi_chung_hoi_dong_voi_copilot(self):
        import unittest.mock as _mock
        cfg = self._cfg_mm(tempfile.mkdtemp())
        cfg.agent_council_cline = "all"
        with _mock.patch.dict(os.environ, {"CLINE_API_KEY": "k", "CLINE_SKIP_MODELS":
                                           "cline-pass/glm-5.3-flash"}):
            names = A._council_models(cfg)
        cline = [m for m in names if m.startswith("cline-pass/")]
        self.assertEqual(len(cline), 13, "14 model tru 1 model bi skip")
        self.assertTrue(set(A.COUNCIL_MULTI_MODELS) <= set(names))
        with _mock.patch.dict(os.environ, {"CLINE_API_KEY": ""}):
            self.assertEqual(A._cline_council_models(cfg), [], "thieu key -> bo qua Cline")

    def test_provider_dinh_tuyen_theo_tien_to_model(self):
        import unittest.mock as _mock
        cfg = self._cfg_mm(tempfile.mkdtemp())
        seen = {}

        def fake_complete(self, system, user, *, timeout=8.0):
            seen[self.name] = self.model
            return {"text": '{"action":"ALLOW","confidence":0.7}', "tokens_in": 1, "tokens_out": 1}
        with _mock.patch.object(A.ClineProvider, "complete", fake_complete), \
             _mock.patch.object(A.CopilotCliProvider, "complete", fake_complete):
            res = A.multi_model_council(cfg, {"symbol": "BTC/USDT:USDT"}, role="critic",
                                        models=["cline-pass/kimi-k3", "kimi-k3"])
        self.assertEqual(seen, {"cline": "cline-pass/kimi-k3", "copilot_cli": "kimi-k3"})
        self.assertEqual(set(res["votes"]), {"cline-pass/kimi-k3", "kimi-k3"})

    def test_agents_enabled_false_thi_khong_goi_model_nao(self):
        tmp = tempfile.mkdtemp()
        cfg = self._cfg_mm(tmp)
        cfg.agents_enabled = False
        called = []
        res = A.multi_model_council(cfg, {}, models=["model-a"],
                                    provider_factory=lambda m: called.append(m))
        self.assertEqual(res["action"], "NO_OPINION")
        self.assertEqual(called, [])

    def test_veto_decision_dung_hoi_dong_nhieu_model_khi_bat_co(self):
        tmp = tempfile.mkdtemp()
        cfg = self._cfg_mm(tmp)
        cfg.agents_council_multi_model = True
        cfg.agent_veto_min_conf = 0.5
        models = ["model-a", "model-b"]
        factory = self._factory({
            "model-a": {"action": "VETO", "confidence": 0.9},
            "model-b": {"action": "VETO", "confidence": 0.8},
        })
        import unittest.mock as _mock
        with _mock.patch.object(A, "_council_models", return_value=models), \
             _mock.patch.object(A, "CopilotCliProvider",
                                side_effect=lambda model=None, **kw: factory(model)):
            res = A.veto_decision(cfg, _layer(A.StubProvider(), tmp=tmp), {"symbol": "BTC/USDT:USDT"})
        self.assertTrue(res["block"], "2 VETO that -> chan lenh")
        self.assertEqual(res["decision"]["action"], "VETO")
        self.assertTrue(res["decision"].get("multi_model"))
        self.assertEqual(set(res["decision"]["votes"]), {"model-a", "model-b"})


class TestCouncilAuthority(unittest.TestCase):
    """Do bang chung RIENG cho hoi dong: status=COUNCIL tach khoi SETUP."""


    def _journal(self, d: str, status: str) -> str:
        jp = os.path.join(d, "j.jsonl")
        rows = []
        now = time.time()
        for i in range(12):
            rows.append({"ts": now - 3600 + i, "event": "AGENT", "role": "arbiter",
                         "status": status, "action": "VETO", "confidence": 0.8,
                         "symbol": "SOL/USDT:USDT", "direction": "SHORT"})
            rows.append({"ts": now - 1800 + i, "event": "CLOSE", "pair": "SOL/USDT:USDT",
                         "direction": "SHORT", "r": -1.0, "won": False})
            rows.append({"ts": now + i, "event": "AGENT", "role": "arbiter",
                         "status": status, "action": "ALLOW", "confidence": 0.6,
                         "symbol": "BTC/USDT:USDT", "direction": "LONG"})
            rows.append({"ts": now + 60 + i, "event": "CLOSE", "pair": "BTC/USDT:USDT",
                         "direction": "LONG", "r": 1.0, "won": True})
        with open(jp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        return jp

    def test_cohort_tach_theo_status(self):
        jp = self._journal(tempfile.mkdtemp(), "COUNCIL")
        council = A.agent_authority(jp, min_n=10, status="COUNCIL")
        setup = A.agent_authority(jp, min_n=10, status="SETUP")
        default = A.agent_authority(jp, min_n=10)          # mac dinh = SETUP
        self.assertEqual(council["veto_n"], 12)
        self.assertTrue(council["granted"], "VETO -1R vs ALLOW +1R -> du bang chung")
        self.assertEqual(setup["veto_n"], 0, "khong duoc lan sang cohort SETUP")
        self.assertEqual(default["status"], "SETUP", "mac dinh van la SETUP (tuong thich cu)")
        self.assertEqual(default["veto_n"], 0)


class TestSplitCmd(unittest.TestCase):
    """AGENT_COPILOT_BIN: duong dan Windows co khoang trang phai duoc cat dung.

    Thuc te 01/10: pythonw (do supervisor spawn) khong co `node` trong PATH ->
    "[WinError 2] The system cannot find the file specified" moi vong, agent luon
    NO_OPINION. Sua bang duong dan tuyet doi -> phai co nhay kep + cat dung.
    """

    def test_chuoi_thuong(self):
        self.assertEqual(A._split_cmd("node C:\\x\\npm-loader.js"),
                         ["node", "C:\\x\\npm-loader.js"])

    def test_duong_dan_co_khoang_trang(self):
        s = '"C:\\Program Files\\nodejs\\node.exe" C:\\Users\\u\\npm-loader.js'
        self.assertEqual(A._split_cmd(s),
                         ["C:\\Program Files\\nodejs\\node.exe",
                          "C:\\Users\\u\\npm-loader.js"])

    def test_rong_va_khoang_trang_thua(self):
        self.assertEqual(A._split_cmd(""), [])
        self.assertEqual(A._split_cmd("  a   b "), ["a", "b"])

    def test_provider_dung_dung_bin(self):
        p = A.CopilotCliProvider(bin_path='"C:\\Program Files\\nodejs\\node.exe" x.js')
        self.assertEqual(p.bin, "C:\\Program Files\\nodejs\\node.exe")
        self.assertEqual(p._base, ["C:\\Program Files\\nodejs\\node.exe", "x.js"])

    def test_resolve_exe_duong_dan_thi_giu_nguyen(self):
        self.assertEqual(A._resolve_exe(r"C:\x\node.exe"), r"C:\x\node.exe")
        self.assertEqual(A._resolve_exe(""), "")

    def test_resolve_exe_tim_qua_PATH(self):
        """pythonw (supervisor spawn) khong co node trong PATH -> phai tu resolve,
        neu khong moi lan goi agent deu WinError 2 -> NO_OPINION mai mai."""
        import os
        import tempfile
        d = tempfile.mkdtemp()
        exe = os.path.join(d, "fakenode.exe")
        with open(exe, "w", encoding="utf-8") as f:
            f.write("x")
        old = os.environ.get("PATH", "")
        os.environ["PATH"] = d + os.pathsep + old
        try:
            # Windows: shutil.which tra ve 'fakenode.EXE' (chu hoa phan mo rong)
            self.assertEqual(os.path.normcase(A._resolve_exe("fakenode")),
                             os.path.normcase(exe))
            self.assertEqual(A._resolve_exe("khong-ton-tai-xyz"), "khong-ton-tai-xyz")
        finally:
            os.environ["PATH"] = old




class TestCopilotCliProvider(unittest.TestCase):
    """Phase 2 duong 'copilot_cli' — dung subscription Copilot, khong can API key."""

    def test_parse_output_va_prompt_duoc_truyen(self):
        r = _FakeRunner(out='{"response":"{\\"action\\":\\"VETO\\",\\"confidence\\":0.7}"}')
        p = A.CopilotCliProvider(model="gpt-5", runner=r)
        res = p.complete("SYS", "USER")
        self.assertIn("-p", r.calls[0]["cmd"])
        self.assertTrue(any("SYS" in str(x) and "USER" in str(x)
                            for x in r.calls[0]["cmd"]))
        self.assertEqual(A.parse_decision(res["text"])["action"], "VETO")
        self.assertIn("--model", r.calls[0]["cmd"])          # model duoc them

    def test_output_text_thuan_van_hoat_dong(self):
        r = _FakeRunner(out='{"action":"ALLOW","confidence":0.9}')
        p = A.CopilotCliProvider(runner=r)
        self.assertEqual(A.parse_decision(p.complete("s", "u")["text"])["action"],
                         "ALLOW")

    def test_shim_bao_loi_ro_khong_treo(self):
        """Truong hop may hien tai: chi co shim hoi 'Install ...? (y/N)'."""
        r = _FakeRunner(rc=1,
                        out="Cannot find GitHub Copilot CLI (https://docs.github.com/)")
        p = A.CopilotCliProvider(runner=r)
        with self.assertRaises(RuntimeError) as ctx:
            p.complete("s", "u")
        self.assertIn("npm install -g @github/copilot", str(ctx.exception))

    def test_rc_khac_0_va_stderr_bao_loi(self):
        r = _FakeRunner(rc=2, out="", err="not authenticated")
        p = A.CopilotCliProvider(runner=r)
        with self.assertRaises(RuntimeError):
            p.complete("s", "u")

    def test_loi_nay_duoc_fail_open_o_tang_layer(self):
        class _Cli:
            name = "copilot_cli"
            model = "gpt-5"

            def complete(self, system, user, *, timeout=20.0):
                raise RuntimeError("chua dang nhap")

        lyr = _layer(provider=_Cli(), agent_provider="copilot_cli")
        d = lyr.vote("critic", {"a": 1})
        self.assertEqual(d.action, "NO_OPINION")            # khong nem ra ngoai
        self.assertIn("loi provider", d.note)

    def test_args_tuy_chinh_chan_tool(self):
        r = _FakeRunner(out='{"action":"ALLOW"}')
        p = A.CopilotCliProvider(
            model="gpt-5", runner=r,
            args=["-p", "{prompt}", "--deny-tool", "write", "--model", "{model}"])
        p.complete("s", "u")
        cmd = " ".join(r.calls[0]["cmd"])
        self.assertIn("--deny-tool write", cmd)
        self.assertEqual(cmd.count("--model"), 1)            # khong them trung

class TestVscodeLmProvider(unittest.TestCase):
    """Phase 2 duong 'vscode_lm' — bridge localhost toi extension dung vscode.lm."""

    def test_post_toi_bridge_va_parse(self):
        import http.server
        import json as _json
        import threading

        seen: dict = {}

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                n = int(self.headers.get("Content-Length", 0))
                seen.update(_json.loads(self.rfile.read(n) or b"{}"))
                seen["auth"] = self.headers.get("Authorization", "")
                body = _json.dumps(
                    {"text": '{"action":"VETO","confidence":0.8}'}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):  # im lang
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = "http://127.0.0.1:%d/complete" % srv.server_port
            p = A.VscodeLmProvider(url=url, token="tok", model="gpt-5")
            res = p.complete("SYS", "USER", timeout=3.0)
            self.assertEqual(A.parse_decision(res["text"])["action"], "VETO")
            self.assertEqual(seen.get("system"), "SYS")
            self.assertEqual(seen.get("prompt"), "USER")
            self.assertEqual(seen.get("auth"), "Bearer tok")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_bridge_tra_rong_thi_loi(self):
        p = A.VscodeLmProvider(http_fn=lambda url, payload, headers, timeout: {})
        with self.assertRaises(RuntimeError):
            p.complete("s", "u")


class TestProviderFactoryPhase2(unittest.TestCase):
    def test_copilot_cli_duoc_tao_tu_cfg(self):
        cfg = SimpleNamespace(agent_provider="copilot_cli", agent_model="gpt-5",
                              agent_copilot_bin="copilot",
                              agent_copilot_args="-p {prompt} --model {model}")
        p = A.build_provider(cfg)
        self.assertEqual(p.name, "copilot_cli")
        self.assertEqual(p.model, "gpt-5")

    def test_vscode_lm_duoc_tao_tu_cfg(self):
        cfg = SimpleNamespace(agent_provider="vscode_lm", agent_model="",
                              agent_vscode_lm_url="http://127.0.0.1:9/complete",
                              agent_vscode_lm_token="")
        p = A.build_provider(cfg)
        self.assertEqual(p.name, "vscode_lm")
        self.assertEqual(p.url, "http://127.0.0.1:9/complete")

    def test_openai_compatible_thieu_cau_hinh_thi_ve_stub(self):
        cfg = SimpleNamespace(agent_provider="openai_compatible", agent_model="")
        self.assertEqual(A.build_provider(cfg).name, "stub")

    def test_stub_khong_cham_mang(self):
        """StubProvider khong duoc goi requests/urlopen (test suite phai offline)."""
        src = inspect.getsource(A.StubProvider)
        self.assertNotIn("requests", src)
        self.assertNotIn("urlopen", src)

    def test_tai_lieu_noi_ro_copilot_khong_can_key(self):
        src = inspect.getsource(A)
        self.assertIn("khong can API key", src)
        self.assertIn("Copilot Requests", src)     # huong dan PAT v2 dung

class TestExtractTextJsonl(unittest.TestCase):
    """Copilot CLI co `--output-format json` = JSONL (moi dong 1 JSON)."""

    def test_jsonl_lay_dong_cuoi_co_van_ban(self):
        raw = ('{"type":"start"}\n'
               '{"type":"delta","text":"phan dau"}\n'
               '{"type":"message","text":"{\\"action\\":\\"VETO\\",\\"confidence\\":0.8}"}\n')
        out = A._extract_text(raw)
        self.assertEqual(A.parse_decision(out)["action"], "VETO")

    def test_jsonl_khong_co_van_ban_thi_rong(self):
        self.assertEqual(A._extract_text('{"type":"start"}\n{"type":"done"}\n'), "")

    def test_van_ban_nhieu_dong_giu_nguyen(self):
        raw = "dong 1\nkhong phai json\ndong 3"
        self.assertEqual(A._extract_text(raw), raw)

    def test_json_quyet_dinh_tra_nguyen_chuoi(self):
        raw = '{"action":"ALLOW","confidence":0.9}'
        self.assertEqual(A._extract_text(raw), raw)

    def test_json_rong_tra_empty(self):
        self.assertEqual(A._extract_text("{}"), "")

    def test_json_de_xuat_phase3_duoc_coi_la_van_ban(self):
        """JSON {"proposals":...} phai duoc tra ve (loi that: bi coi la rong)."""
        raw = ('{"proposals":[{"type":"none","target":"A_TREND_PULLBACK",'
               '"reason":"n=3 qua nho"}],"confidence":0.35}')
        self.assertEqual(A._extract_text(raw), raw)
        parsed = A.parse_proposals(A._extract_text(raw))
        self.assertEqual(parsed["parse"], "ok")
        self.assertEqual(parsed["proposals"][0]["type"], "none")

    def test_jsonl_co_de_xuat_lay_dong_cuoi(self):
        raw = ('{"type":"start"}\n'
               '{"proposals":[{"type":"block_strategy","target":"D_RANGE_REVERSAL"}]}\n')
        parsed = A.parse_proposals(A._extract_text(raw))
        self.assertEqual(parsed["proposals"][0]["target"], "D_RANGE_REVERSAL")


class TestEnableFlag(unittest.TestCase):
    """`agents.py --enable` phai xoa duoc circuit breaker (sau khi da login)."""

    def test_enable_xoa_disabled(self):
        tmp = tempfile.mkdtemp()
        st = os.path.join(tmp, "state.json")
        b = A.AgentBudget(st, max_errors=1)
        b.note(cost=0.0, ok=False, reason="chua dang nhap")
        b.note(cost=0.0, ok=False, reason="chua dang nhap")
        self.assertTrue(b.disabled())
        b2 = A.AgentBudget(st, max_errors=1)
        self.assertTrue(b2.disabled())          # state luu qua file
        b2.enable()
        self.assertEqual(b2.disabled(), "")
        self.assertEqual(A.AgentBudget(st, max_errors=1).disabled(), "")







if __name__ == "__main__":
    unittest.main()



class TestTurboAgentWiring(unittest.TestCase):
    """Glue turbo_demo: vote agent phai CHAY NEN (khong lam cham vong lap trading)."""

    def setUp(self):
        import turbo_demo as T
        self.T = T

    def tearDown(self):
        self.T._AGENTS["layer"] = None

    def test_vote_khong_chan_vong_lap(self):
        import json as _json
        import tempfile as _tf
        import time as _time

        tmp = _tf.mkdtemp()
        jp = os.path.join(tmp, "journal.jsonl")

        class _SlowLayer:
            shadow = True

            def __init__(self):
                self.calls = 0

            def vote(self, role, payload):
                self.calls += 1
                _time.sleep(0.4)                      # gia lap CLI cham
                return A.Decision(role=role, agent=role + "_agent", action="VETO",
                                  confidence=0.5, reasons=["test"], shadow=True)

            def log_decision(self, dec, extra=None):
                with open(jp, "a", encoding="utf-8") as f:
                    f.write(_json.dumps({"event": "AGENT", **dec.to_dict(),
                                         **(extra or {})}) + "\n")
                return dec.to_dict()

        layer = _SlowLayer()
        self.T._AGENTS["layer"] = layer
        cfg = SimpleNamespace(agents_enabled=True, agents_shadow=True)

        t0 = _time.time()
        self.T.agent_vote_setup(cfg, "BTC/USDT:USDT", "LONG", 0.3, "B_BREAKOUT_RETEST",
                                {"rsi": 60.0},
                                SimpleNamespace(score=0.2, urgent_bearish=0), "UPTREND")
        elapsed = _time.time() - t0
        # 2 luot vote x 0.4s neu chay dong bo -> phai tra ve NGAY vi da chay nen
        self.assertLess(elapsed, 0.25, "agent_vote_setup phai tra ve NGAY")

        deadline = _time.time() + 3.0
        while _time.time() < deadline and self.T._AGENTS["pending"] > 0:
            _time.sleep(0.05)
        self.assertEqual(self.T._AGENTS["pending"], 0, "job nen phai chay xong")
        self.assertEqual(layer.calls, 2)               # macro + critic
        events = A.count_agent_events(jp)
        self.assertEqual(events.get("macro:VETO"), 1)
        self.assertEqual(events.get("critic:VETO"), 1)

    def test_hang_doi_day_thi_bo_khong_nghen(self):
        """pending vuot tran -> bo job (dropped), khong xep hang vo han."""
        self.T._AGENTS["layer"] = object()
        self.T._AGENTS["pending"] = self.T._AGENT_MAX_PENDING
        before = self.T._AGENTS["dropped"]
        ok = self.T._agent_submit(lambda: None)
        self.assertFalse(ok)
        self.assertEqual(self.T._AGENTS["dropped"], before + 1)
        self.T._AGENTS["pending"] = 0
        self.T._AGENTS["layer"] = None


class TestSubprocessRunnerEncoding(unittest.TestCase):
    """Runner phai doc duoc UTF-8 (Copilot CLI tra tieng Viet) tren Windows.

    Loi that 01/10/2026: subprocess text=True dung cp1252 -> UnicodeDecodeError
    lam hong 1 luot vote (review). Dung \\u escape de test khong phu thuoc
    encoding cua file nguon.
    """

    def test_doc_utf8_khong_loi(self):
        """CLI that ghi BYTES utf-8 ra stdout -> runner phai decode dung.

        Con ghi thang vao stdout.buffer (khong qua console cp1252) de test dung
        ban chat "CLI tra UTF-8", khong phu thuoc code page cua Windows.
        Dung chr() de file test khong phu thuoc encoding nguon.
        """
        import sys as _sys
        check = chr(0x2713)                        # dau check ✓
        text = "Ki" + chr(0x1ec3) + "m tra " + check
        tmp = tempfile.mkdtemp()
        fp = os.path.join(tmp, "utf8.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write(text)
        rc, out, err = A._subprocess_runner(
            [_sys.executable, "-c",
             "import sys; d=open(sys.argv[1],'rb').read(); "
             "sys.stdout.buffer.write(d)", fp], 30)
        self.assertEqual(rc, 0, err)
        self.assertIn(check, out)              # doc dung UTF-8
        self.assertNotIn(chr(0xfffd), out)     # khong bi thay the
        self.assertEqual(err, "")


class TestPhase3Proposals(unittest.TestCase):
    """Phase 3: de xuat PHAI qua gate tat dinh; khong bao gio tu ap dung."""

    def _digest(self, a_avg=-0.12, a_n=30, blocked=("A_TREND_PULLBACK",)):
        return {"n": 100, "by_strategy": {
            "A_TREND_PULLBACK": {"n": a_n, "wr": 45.0, "avg_r": a_avg,
                                 "sum_r": a_avg * a_n},
            "B_BREAKOUT_RETEST": {"n": 20, "wr": 60.0, "avg_r": 0.12, "sum_r": 2.4}},
            "current_block": list(blocked)}

    def test_parse_proposals_json_va_rac(self):
        ok = A.parse_proposals('{"proposals":[{"type":"block_strategy",'
                               '"target":"c_liq_sweep_reclaim","reason":"x"}],'
                               '"confidence":0.7}')
        self.assertEqual(ok["parse"], "ok")
        self.assertEqual(ok["proposals"][0]["type"], "block_strategy")
        self.assertEqual(ok["proposals"][0]["target"], "C_LIQ_SWEEP_RECLAIM")
        bad = A.parse_proposals("khong phai json")
        self.assertEqual(bad["proposals"], [])
        self.assertEqual(bad["parse"], "fail")

    def test_gate_chap_nhan_khi_du_bang_chung(self):
        props = [{"type": "block_strategy", "target": "B_BREAKOUT_RETEST",
                  "reason": "x"}]
        out = A.validate_proposals(props, self._digest(blocked=()), min_n=20)
        self.assertEqual(out[0]["status"], "REJECTED")   # B dang duong -> khong am
        props2 = [{"type": "block_strategy", "target": "C_LIQ_SWEEP_RECLAIM"}]
        dig = {"n": 40, "by_strategy": {"C_LIQ_SWEEP_RECLAIM": {"n": 25,
                                                               "avg_r": -0.2}},
               "current_block": []}
        out2 = A.validate_proposals(props2, dig, min_n=20)
        self.assertEqual(out2[0]["status"], "ACCEPTED")

    def test_gate_tu_choi_khi_thieu_mau(self):
        props = [{"type": "block_strategy", "target": "A_TREND_PULLBACK"}]
        out = A.validate_proposals(props, self._digest(a_n=5, blocked=()), min_n=20)
        self.assertEqual(out[0]["status"], "REJECTED")
        self.assertIn("chua du mau", out[0]["why"])

    def test_gate_tu_choi_risk_size_sl_tp(self):
        for bad in ("giam risk_per_trade xuong 0.5%", "dat leverage 20",
                    "doi sl_atr_mult thanh 1.5"):
            props = [{"type": "block_strategy", "target": "A_TREND_PULLBACK",
                      "reason": bad}]
            out = A.validate_proposals(props, self._digest(blocked=()), min_n=1)
            self.assertEqual(out[0]["status"], "REJECTED", bad)
            self.assertIn("ngoai pham vi", out[0]["why"])

    def test_gate_tu_choi_type_la(self):
        props = [{"type": "set_leverage", "target": "A_TREND_PULLBACK", "reason": "x"}]
        out = A.validate_proposals(props, self._digest(), min_n=1)
        self.assertEqual(out[0]["status"], "REJECTED")
        self.assertIn("allowlist", out[0]["why"])

    def test_gate_unblock_can_avgR_duong(self):
        good = [{"type": "unblock_strategy", "target": "A_TREND_PULLBACK"}]
        self.assertEqual(A.validate_proposals(good, self._digest(a_avg=0.20),
                                              min_n=20)[0]["status"], "ACCEPTED")
        bad = [{"type": "unblock_strategy", "target": "A_TREND_PULLBACK"}]
        self.assertEqual(A.validate_proposals(bad, self._digest(a_avg=-0.30),
                                              min_n=20)[0]["status"], "REJECTED")

    def test_gate_tran_so_de_xuat(self):
        props = [{"type": "block_strategy", "target": "B_BREAKOUT_RETEST"},
                 {"type": "block_strategy", "target": "D_RANGE_REVERSAL"}]
        dig = {"n": 60, "by_strategy": {
            "B_BREAKOUT_RETEST": {"n": 30, "avg_r": -0.2},
            "D_RANGE_REVERSAL": {"n": 30, "avg_r": -0.2}}, "current_block": []}
        out = A.validate_proposals(props, dig, min_n=20, max_accept=1)
        self.assertEqual([p["status"] for p in out], ["ACCEPTED", "REJECTED"])
        self.assertIn("vuot tran", out[1]["why"])


    def test_stdin_dong_cli_khong_treo(self):
        """stdin=DEVNULL: lenh hoi input se nhan EOF thay vi treo."""
        import sys as _sys
        rc, out, err = A._subprocess_runner(
            [_sys.executable, "-c",
             "import sys; d=sys.stdin.read(); print('EOF_OK' if d=='' else d)"], 30)
        self.assertEqual(rc, 0)
        self.assertIn("EOF_OK", out)




    def test_apply_proposal_dry_run_khong_ghi(self):
        tmp = tempfile.mkdtemp()
        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8", newline="") as f:
            f.write("A=1\r\nSTRATEGY_BLOCK=A_TREND_PULLBACK\r\nB=2\r\n")
        before = open(env, "rb").read()
        res = A.apply_proposal({"type": "block_strategy",
                                "target": "D_RANGE_REVERSAL"},
                               env_path=env, dry_run=True)
        self.assertTrue(res["ok"])
        self.assertEqual(res["after"], ["A_TREND_PULLBACK", "D_RANGE_REVERSAL"])
        self.assertEqual(open(env, "rb").read(), before)      # khong doi file

    def test_apply_proposal_ghi_that_giu_crlf_va_backup(self):
        tmp = tempfile.mkdtemp()
        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8", newline="") as f:
            f.write("A=1\r\nSTRATEGY_BLOCK=A_TREND_PULLBACK\r\nB=2\r\n")
        res = A.apply_proposal({"type": "unblock_strategy",
                                "target": "A_TREND_PULLBACK"}, env_path=env,
                               dry_run=False)
        self.assertTrue(res["ok"] and res["changed"])
        txt = open(env, "rb").read().decode("utf-8")
        self.assertIn("STRATEGY_BLOCK=\r\n", txt)             # giu nguyen CRLF
        self.assertTrue(res["backup"] and os.path.exists(res["backup"]))

    def test_apply_proposal_tu_choi_type_ngoai_pham_vi(self):
        tmp = tempfile.mkdtemp()
        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8") as f:
            f.write("STRATEGY_BLOCK=\n")
        res = A.apply_proposal({"type": "set_leverage",
                                "target": "A_TREND_PULLBACK"},
                               env_path=env, dry_run=False)
        self.assertFalse(res["ok"])
        self.assertIn("khong duoc phep", res["error"])

    def test_reflection_chi_ghi_file_khong_sua_env(self):
        """Chay reflection: ghi proposals file, KHONG dong den .env."""
        tmp = tempfile.mkdtemp()
        env = os.path.join(tmp, ".env")
        with open(env, "w", encoding="utf-8") as f:
            f.write("STRATEGY_BLOCK=\n")
        env_before = open(env, "rb").read()
        props_path = os.path.join(tmp, "proposals.jsonl")
        prov = _FixedProvider(
            '{"proposals":[{"type":"block_strategy","target":"C_LIQ_SWEEP_RECLAIM",'
            '"reason":"n=25 avgR=-0.20 am ro"}],"confidence":0.8}')
        cfg = _cfg(strategy_block=(), reflect_min_n=20)
        layer = A.AgentLayer(cfg, provider=prov,
                             journal=os.path.join(tmp, "j.jsonl"),
                             state_path=os.path.join(tmp, "s.json"))
        orig = A.build_digest
        A.build_digest = lambda *a, **k: {
            "n": 60, "current_block": [],
            "by_strategy": {"C_LIQ_SWEEP_RECLAIM": {"n": 25, "wr": 30.0,
                                                    "avg_r": -0.20}}}
        try:
            rep = A.run_reflection(cfg, layer=layer, proposals_path=props_path)
        finally:
            A.build_digest = orig
        self.assertEqual(len(rep["accepted"]), 1)
        self.assertTrue(os.path.exists(props_path))           # da ghi de xuat
        self.assertEqual(open(env, "rb").read(), env_before)   # .env KHONG sua
        recs = A.list_proposals(props_path, limit=1)
        self.assertEqual(recs[0]["accepted"][0]["target"], "C_LIQ_SWEEP_RECLAIM")





class TestPhase4Authority(unittest.TestCase):
    """Phase 4: quyen veto CHI duoc cap khi shadow chung minh VETO te hon ALLOW."""

    def _journal(self, tmp, n_veto=12, r_veto=-1.0, n_allow=12, r_allow=0.2):
        jp = os.path.join(tmp, "journal.jsonl")
        t0 = 1_700_000_000.0
        with open(jp, "w", encoding="utf-8") as f:
            for i in range(n_veto):
                f.write(json.dumps({"event": "AGENT", "status": "SETUP",
                                    "symbol": "BTC/USDT:USDT", "direction": "LONG",
                                    "action": "VETO", "role": "critic",
                                    "confidence": 0.8, "ts": t0 + i * 100}) + "\n")
                f.write(json.dumps({"event": "CLOSE", "pair": "BTC/USDT:USDT",
                                    "direction": "LONG", "r": r_veto,
                                    "won": r_veto > 0, "pnl": r_veto * 10,
                                    "ts": t0 + i * 100 + 50}) + "\n")
            for i in range(n_allow):
                f.write(json.dumps({"event": "AGENT", "status": "SETUP",
                                    "symbol": "ETH/USDT:USDT", "direction": "SHORT",
                                    "action": "ALLOW", "role": "critic",
                                    "confidence": 0.5, "ts": t0 + i * 100}) + "\n")
                f.write(json.dumps({"event": "CLOSE", "pair": "ETH/USDT:USDT",
                                    "direction": "SHORT", "r": r_allow, "won": True,
                                    "pnl": r_allow * 10, "ts": t0 + i * 100 + 50}) + "\n")
        return jp

    def test_cap_quyen_khi_veto_te_hon_ro(self):
        jp = self._journal(tempfile.mkdtemp())
        auth = A.agent_authority(jp, min_n=10, min_gap=0.15)
        self.assertTrue(auth["granted"], auth)
        self.assertEqual(auth["veto_n"], 12)
        self.assertAlmostEqual(auth["veto_avg_r"], -1.0, places=3)
        self.assertAlmostEqual(auth["allow_avg_r"], 0.2, places=3)

    def test_khong_cap_quyen_khi_gap_nho(self):
        jp = self._journal(tempfile.mkdtemp(), r_allow=-0.5)
        self.assertFalse(A.agent_authority(jp, min_n=10, min_gap=0.8)["granted"])

    def test_khong_cap_quyen_khi_thieu_mau(self):
        jp = self._journal(tempfile.mkdtemp(), n_veto=3)
        self.assertFalse(A.agent_authority(jp, min_n=10, min_gap=0.15)["granted"])

    def test_bo_qua_close_ngoai_horizon(self):
        tmp = tempfile.mkdtemp()
        jp = os.path.join(tmp, "journal.jsonl")
        t0 = 1_700_000_000.0
        with open(jp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"event": "AGENT", "status": "SETUP",
                                "symbol": "BTC/USDT:USDT", "direction": "LONG",
                                "action": "VETO", "ts": t0}) + "\n")
            f.write(json.dumps({"event": "CLOSE", "pair": "BTC/USDT:USDT",
                                "direction": "LONG", "r": -1.0, "won": False,
                                "ts": t0 + 72 * 3600}) + "\n")   # 72h > horizon 48h
        self.assertEqual(A.agent_authority(jp, min_n=1, min_gap=0.1)["veto_n"], 0)

    def test_journal_khong_ton_tai_khong_crash(self):
        auth = A.agent_authority(os.path.join(tempfile.mkdtemp(), "khong-co.jsonl"))


class TestPhase4Veto(unittest.TestCase):
    def test_veto_decision_chan_khi_conf_du(self):
        prov = _FixedProvider('{"action":"VETO","confidence":0.9,"reasons":["xau"]}')
        cfg = _cfg(agent_veto_min_conf=0.7)
        out = A.veto_decision(cfg, _layer(provider=prov), {"a": 1})
        self.assertTrue(out["block"])
        self.assertEqual(out["decision"]["action"], "VETO")

    def test_veto_decision_khong_chan_khi_conf_thap(self):
        prov = _FixedProvider('{"action":"VETO","confidence":0.4}')
        out = A.veto_decision(_cfg(agent_veto_min_conf=0.7), _layer(provider=prov),
                              {"a": 1})
        self.assertFalse(out["block"])

    def test_veto_decision_fail_open_khi_loi(self):
        out = A.veto_decision(_cfg(), _layer(provider=_BoomProvider()), {"a": 1})
        self.assertFalse(out["block"])          # loi -> KHONG chan lenh

    def test_turbo_agent_veto_tat_mac_dinh(self):
        import turbo_demo as T
        cfg = SimpleNamespace(agents_veto_enabled=False)
        out = T.agent_veto(cfg, "BTC/USDT:USDT", "LONG", 0.3, "B_BREAKOUT_RETEST",
                           {}, SimpleNamespace(score=0.0, urgent_bearish=0), "UPTREND")
        self.assertFalse(out["block"])
        self.assertIn("TAT", out["reason"])

    def test_turbo_agent_veto_chua_cap_quyen_thi_khong_chan(self):
        import turbo_demo as T
        T._AGENTS["layer"] = _layer(provider=_FixedProvider(
            '{"action":"VETO","confidence":0.99}'))
        T._AGENT_AUTH["ts"] = time.time()
        T._AGENT_AUTH["res"] = {"granted": False, "reason": "chua du bang chung"}
        try:
            cfg = SimpleNamespace(agents_veto_enabled=True, agents_enabled=True,
                                  agent_veto_min_conf=0.7)
            out = T.agent_veto(cfg, "BTC/USDT:USDT", "LONG", 0.3, "B_BREAKOUT_RETEST",
                               {}, SimpleNamespace(score=0.0, urgent_bearish=0),
                               "UPTREND")
            self.assertFalse(out["block"])
            self.assertIn("chua duoc cap quyen", out["reason"])
        finally:
            T._AGENTS["layer"] = None
            T._AGENT_AUTH["res"] = None

    def test_turbo_agent_veto_da_cap_quyen_thi_chan_va_ghi_journal(self):
        """Duong nguy hiem nhat: da cap quyen + agent VETO -> BO QUA lenh + ghi journal."""
        import turbo_demo as T
        tmp = tempfile.mkdtemp()
        jp = os.path.join(tmp, "j.jsonl")
        lyr = _layer(provider=_FixedProvider(
            '{"action":"VETO","confidence":0.99,"reasons":["tin vi mo xau"]}'))
        lyr.journal = jp
        T._AGENTS["layer"] = lyr
        T._AGENT_AUTH["ts"] = time.time()          # cache con hieu luc (TTL 3600s)
        T._AGENT_AUTH["res"] = {"granted": True, "reason": "du bang chung (test)"}
        try:
            cfg = SimpleNamespace(agents_veto_enabled=True, agents_enabled=True,
                                  agent_veto_min_conf=0.7, agent_cache_sec=0)
            out = T.agent_veto(cfg, "SOL/USDT:USDT", "LONG", 0.3, "B_BREAKOUT_RETEST",
                               {"rsi": 60.0},
                               SimpleNamespace(score=0.1, urgent_bearish=0), "UPTREND")
            self.assertTrue(out["block"])
            self.assertIn("tin vi mo xau", out["reason"])
            events = A.count_agent_events(jp)
            self.assertEqual(events.get("critic:VETO"), 1)
            rec = json.loads(open(jp, encoding="utf-8").read().strip())
            self.assertEqual(rec["status"], "VETO_ENFORCED")   # dau vet de do luong
        finally:
            T._AGENTS["layer"] = None
            T._AGENT_AUTH["res"] = None

    def test_auto_apply_tat_mac_dinh(self):
        self.assertEqual(A.main(["--auto-apply"]), 1)   # can AGENT_AUTO_APPLY=true
        self.assertFalse(bool(getattr(cfg_auto(), "agent_auto_apply", False)))


def cfg_auto():
    """Helper: doc .env hien tai (chi de kiem tra mac dinh AGENT_AUTO_APPLY)."""
    from config import Settings
    return Settings()


class TestTierDifficulty(unittest.TestCase):
    """(05/10) Do kho + tier motel: de -> lite, kho -> pro/max, nang tier khi chia re."""

    def setUp(self):
        import agents as A2
        self.A = A2
        self.A._PROVIDER_BLOCKED.clear()

    def tearDown(self):
        self.A._PROVIDER_BLOCKED.clear()

    def test_lite_flash(self):
        self.assertEqual(self.A.model_tier("cline-pass/mimo-v2.6-flash"), "lite")
        self.assertEqual(self.A.model_tier("claude-haiku-4.5"), "lite")

    def test_hard_pro_max(self):
        self.assertEqual(self.A.model_tier("cline-pass/deepseek-v4-pro"), "hard")
        self.assertEqual(self.A.model_tier("cline-pass/qwen3.8-max"), "hard")
        self.assertEqual(self.A.model_tier("claude-sonnet-5.5"), "hard")

    def test_core_con_lai(self):
        self.assertEqual(self.A.model_tier("cline-pass/glm-5.3"), "core")

    def test_do_kho_de(self):
        s, _ = self.A.council_difficulty({"rsi": 55, "atr_pct": 0.01,
                                          "news_score": 0.1, "alpha": 0.2})
        self.assertLess(s, 0.34, "thong so la -> de")
        self.assertEqual(self.A._tier_for(s), "lite")

    def test_do_kho_cao(self):
        s, _ = self.A.council_difficulty({"rsi": 78, "atr_pct": 0.06,
                                          "news_score": -0.5, "urgent_bearish": 15})
        self.assertGreater(s, 0.66, "bien dong + tin xau + khan cap -> kho")
        self.assertEqual(self.A._tier_for(s), "hard")

    def test_muse_spark_hard(self):
        """muse-spark-* duoc xep hard vi la frontier model."""
        self.assertEqual(self.A.model_tier("muse/muse-spark-1.3"), "hard")
        self.assertEqual(self.A.model_tier("muse/muse-spark-1.3-contributor"), "hard")
        self.assertEqual(self.A.model_tier("muse-spark-1.2"), "hard")

    def test_muse_glimmer_core(self):
        self.assertEqual(self.A.model_tier("muse/muse-glimmer-30b"), "core")

    def test_is_muse_model(self):
        self.assertTrue(self.A._is_muse_model("muse/muse-spark-1.3"))
        self.assertTrue(self.A._is_muse_model("muse/muse-glimmer-30b"))
        self.assertFalse(self.A._is_muse_model("cline-pass/deepseek-v4-pro"))
        self.assertFalse(self.A._is_muse_model("claude-sonnet-5.5"))


class TestMuseProvider(unittest.TestCase):
    """(05/10) Muse: Meta Model API - OpenAI-compatible, MUSE_API_KEY."""

    def setUp(self):
        import agents as A2
        self.A = A2
        self.A._PROVIDER_BLOCKED.clear()

    def tearDown(self):
        self.A._PROVIDER_BLOCKED.clear()

    def test_muse_endpoint_default(self):
        self.assertIn("api.meta.ai", self.A.MUSE_ENDPOINT)

    def test_muse_prefix(self):
        self.assertEqual(self.A.MUSE_PREFIX, "muse/")

    def test_no_key_returns_empty_council(self):
        import os as _os
        from unittest.mock import patch
        with patch.dict(_os.environ, {"MUSE_API_KEY": ""}):
            models = self.A._muse_council_models(_FakeCfg(agent_council_muse="muse-spark-1.3"))
            self.assertEqual(models, [], "khong co key -> rong")

    def test_has_key_returns_prefixed_models(self):
        import os as _os
        from unittest.mock import patch
        with patch.dict(_os.environ, {"MUSE_API_KEY": "sk-test", "MUSE_SKIP_MODELS": ""}):
            models = self.A._muse_council_models(_FakeCfg(agent_council_muse="muse-spark-1.3,muse-spark-1.2"))
            self.assertEqual(models, ["muse/muse-spark-1.3", "muse/muse-spark-1.2"])

    def test_skip_models_respected(self):
        import os as _os
        from unittest.mock import patch
        with patch.dict(_os.environ, {"MUSE_API_KEY": "sk-test",
                                       "MUSE_SKIP_MODELS": "muse-spark-1.2"}):
            models = self.A._muse_council_models(_FakeCfg(agent_council_muse="muse-spark-1.3,muse-spark-1.2"))
            self.assertEqual(models, ["muse/muse-spark-1.3"])


class _FakeCfg:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class TestCouncilProviderFallback(unittest.TestCase):
    """(05/10) Hoi dong het quota 1 ben -> ben con lai tu lam 100%, khong treo."""

    def setUp(self):
        import agents as A2
        self.A = A2
        self.A._PROVIDER_BLOCKED.clear()

    def tearDown(self):
        self.A._PROVIDER_BLOCKED.clear()

    def _cfg(self, **kw):
        from config import Settings
        c = Settings()
        for k, v in kw.items():
            object.__setattr__(c, k, v)
        return c

    def test_date_block_copilot_chi_con_cline(self):
        cfg = self._cfg(agent_council_copilot_until="2999-01-01",
                        agent_council_cline_until="")
        models = self.A._council_models(cfg)
        self.assertTrue(models, "clines van con")
        self.assertTrue(all(m.startswith(self.A.CLINE_PREFIX) for m in models),
                        "Copilot bi chan -> chi con model cline")

    def test_date_block_cline_chi_con_copilot(self):
        cfg = self._cfg(agent_council_cline_until="2999-01-01",
                        agent_council_copilot_until="")
        models = self.A._council_models(cfg)
        self.assertTrue(models)
        self.assertTrue(all(not m.startswith(self.A.CLINE_PREFIX) for m in models),
                        "Cline bi chan -> chi con model copilot")

    def test_ca_hai_deu_chan_van_khong_crash(self):
        cfg = self._cfg(agent_council_copilot_until="2999-01-01",
                        agent_council_cline_until="2999-01-01")
        models = self.A._council_models(cfg)
        self.assertTrue(models, "ca 2 chan van tra danh sach de khong crash")

    def test_session_block_khi_toan_bo_model_cung_provider_abstain(self):
        cfg = self._cfg(agent_council_models="m1,m2,m3")
        decs = {
            "m1": self.A.Decision(role="critic", agent="m1", action="NO_OPINION",
                                   provider="copilot_cli"),
            "m2": self.A.Decision(role="critic", agent="m2", action="NO_OPINION",
                                   provider="copilot_cli"),
            "m3": self.A.Decision(role="critic", agent="m3", action="NO_OPINION",
                                   provider="copilot_cli"),
        }
        self.A._mark_provider_exhausted(decs)
        self.assertIn("copilot", self.A._PROVIDER_BLOCKED,
                      "toan bo copilot abstain -> phai danh dau")
        # sau do _council_models phai bo copilot (session block)
        models = self.A._council_models(self._cfg(agent_council_models="m1,m2,m3",
                                                   agent_council_cline="all"))
        self.assertTrue(all(m.startswith(self.A.CLINE_PREFIX) for m in models))

    def test_khong_block_khi_van_con_model_hoạt_dong(self):
        decs = {
            "m1": self.A.Decision(role="critic", agent="m1", action="NO_OPINION"),
            "m2": self.A.Decision(role="critic", agent="m2", action="VETO"),
        }
        self.A._mark_provider_exhausted(decs)
        self.assertNotIn("copilot", self.A._PROVIDER_BLOCKED)

    def test_khong_block_khi_chi_1_model(self):
        decs = {
            "m1": self.A.Decision(role="critic", agent="m1", action="NO_OPINION"),
        }
        self.A._mark_provider_exhausted(decs)
        self.assertNotIn("copilot", self.A._PROVIDER_BLOCKED,
                         "1 model abstain la false positive, khong block")



class TestRunnerAnCuaSo(unittest.TestCase):
    """(05/10) Bot chay duoi pythonw -> moi lan goi CLI (node/copilot) phai chay NGAM.

    Khong co CREATE_NO_WINDOW: Windows tu mo 1 cua so console cho con -> nguoi dung
    thay "pop-up node" khong noi dung nhay len moi lan co vote hoi dong / review.
    """

    def test_windows_thi_phai_co_creationflags(self):
        from unittest import mock
        import subprocess
        with mock.patch.object(subprocess, "run") as m:
            m.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
            A._subprocess_runner(["cmd"], 10)
        kw = m.call_args.kwargs
        if sys.platform == "win32":
            self.assertEqual(kw.get("creationflags"), subprocess.CREATE_NO_WINDOW,
                             "phai an cua so console cua CLI con")
        else:
            self.assertNotIn("creationflags", kw, "flag nay chi co tren Windows")


