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

