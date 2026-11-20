"""Tests for dashboard_server.py — security, redaction, B-031 accuracy, caching, read-only."""
from __future__ import annotations

import ast
import concurrent.futures
import http.client
import json
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import dashboard_server as DS  # noqa: E402
import monitor_report as MR  # noqa: E402


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestStaticSecurityInvariants(unittest.TestCase):
    """AST & static code assertions: read-only, no dangerous sinks, zero innerHTML/eval in JS."""

    def test_server_ast_has_no_writes_or_dangerous_sinks(self):
        src = (ROOT / "dashboard_server.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_calls = {"eval", "exec", "os.system", "pickle.load", "yaml.load", "os.remove", "os.unlink", "shutil.rmtree"}
        forbidden_imports = {"subprocess", "ccxt", "requests", "risk", "bot", "exchange", "portfolio", "turbo_demo"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_imports, f"dashboard_server must not import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_imports, f"dashboard_server must not import from {node.module}")
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        name = f"{node.func.value.id}.{node.func.attr}"
                    else:
                        name = node.func.attr
                self.assertNotIn(name, forbidden_calls, f"Forbidden call {name} at line {node.lineno}")
                self.assertNotIn(name, {"write_text", "write_bytes"}, f"File write {name} forbidden in dashboard_server")
                if name in {"open", "Path.open"} or (isinstance(node.func, ast.Attribute) and node.func.attr == "open"):
                    # Verify mode argument is read-only if specified
                    for arg in node.args[1:2]:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            self.assertFalse(any(c in arg.value for c in "wax+"), f"Writable open mode {arg.value!r}")
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                            self.assertFalse(any(c in kw.value.value for c in "wax+"), f"Writable open mode {kw.value.value!r}")

    def test_frontend_js_has_no_xss_sinks(self):
        js_src = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(forbidden, js_src, f"XSS/code sink {forbidden!r} found in dashboard/app.js")

    def test_non_loopback_bind_rejected(self):
        with self.assertRaises(ValueError):
            DS.create_server(port=0, host="0.0.0.0")
        with self.assertRaises(ValueError):
            DS.create_server(port=0, host="192.168.1.5")


class TestRedactionAndPathSafety(unittest.TestCase):
    def test_redact_nested_secrets(self):
        canary = {
            "ping": "https://hc-ping.com/65ccac3a-3ee5-4ccf-be87-a34233135f23",
            "tg_url": "https://api.telegram.org/bot123456789:AAH_abcdefghijklmnopqrstuvwxyz12345/sendMessage",
            "tg_raw": "987654321:BBH_abcdefghijklmnopqrstuvwxyz123456",
            "ip_pub": "IP(222.253.53.82) banned; local 127.0.0.1 ok",
            "userinfo": "https://user:supersecret@example.com/hook",
            "kv": "BINANCE_API_KEY=abcdef1234567890 secret=myTopSecretValue123",
            "long_hex": "a" * 64,
            "nested": [{"msg": "Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature"}],
        }
        out = json.dumps(DS.redact_obj(canary))
        for leak in (
            "65ccac3a-3ee5-4ccf-be87-a34233135f23",
            "AAH_abcdefghijklmnopqrstuvwxyz12345",
            "BBH_abcdefghijklmnopqrstuvwxyz123456",
            "222.253.53.82",
            "user:supersecret",
            "abcdef1234567890",
            "myTopSecretValue123",
            "a" * 48,
            "eyJhbGciOiJIUzI1NiJ9",
        ):
            self.assertNotIn(leak, out, f"Secret leaked after redaction: {leak}")
        self.assertIn("127.0.0.1", out)

    def test_suspicious_paths_blocked(self):
        bad_paths = (
            "/.env",
            "/.env.bak-2026",
            "/../.env",
            "/%2e%2e/.env",
            "/..%5c.env",
            "/index.html::$DATA",
            "/CON",
            "/NUL.txt",
            "/logs/journal.jsonl",
            "/.git/config",
            "/dashboard/../../.env",
            "/id_rsa",
            "/foo\x00bar",
        )
        for p in bad_paths:
            self.assertTrue(DS.is_suspicious_path(p), f"Should block suspicious path: {p}")


class TestDashboardEndToEnd(unittest.TestCase):
    """Spin up real loopback server over isolated temp TESTNET + LIVE fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.testnet = base / "autonomous-trading-bot"
        cls.live = base / "atb-live"
        (cls.testnet / "logs").mkdir(parents=True)
        (cls.testnet / "security").mkdir(parents=True)
        (cls.testnet / "golden").mkdir(parents=True)
        (cls.live / "logs").mkdir(parents=True)

        now = time.time()
        # Write realistic fixtures with canary secrets & XSS payloads & B-031 bad R
        _write_json(cls.testnet / "logs" / "heartbeat.json", {
            "ts": now - 12.0, "pid": 1111, "round": 42, "phase": "end", "equity": 1025.5,
        })
        _write_json(cls.testnet / "logs" / "risk_state.json", {
            "max_daily_loss_pct": 2.0, "start_balance": 1000.0, "start_equity": 1020.0,
            "peak_balance": 1040.0, "errors": 0, "max_errors": 5, "tripped": False,
            "reason": "", "consec_losses": 1, "max_consec_losses": 5, "day": "2026-11-20", "mode": "demo",
        })
        _write_json(cls.testnet / "logs" / "state_snapshot.json", {
            "ts": now - 30.0, "git_head": "abc1234",
            "bot": {"pid": 1111, "round": 42, "phase": "end", "watchdog_sec": 360, "alive": True},
            "equity_demo": 1025.5,
            "config": {"testnet": True, "dry_run": False, "live_confirm": False, "risk_pct": 0.4,
                       "max_total_risk_pct": 1.6, "leverage": 8, "max_positions": 4},
            "live_ready": {"ok": False, "verdict": "CHUA HOAN THANH", "blockers": ["PF < 1.2"]},
            "live_guard": {"ok": True, "live": False, "blockers": []},
            "council": {"models": ["auto", "cline-pass/mimo-v2.6-pro"]},
        })
        _write_json(cls.testnet / "logs" / "managed_state.json", {
            "saved_ts": now - 12.0,
            "trades": {
                "ADA/USDT:USDT": {
                    "entry": 0.5, "qty": 100.0, "sl": 0.52, "tp": 0.46, "initial_sl": 0.52,
                    "init_qty": 100.0, "partial_done": False, "be_done": False, "booked_pnl": 0.0,
                    "mfe_r": 0.45, "direction": "SHORT", "strategy": "B_BREAKOUT_RETEST",
                    "prot_ids": {"sl": "s1", "tp": "t1"},
                }
            },
        })
        _write_json(cls.testnet / "logs" / "orders_snapshot.json", {
            "orders": 2, "positions": 1, "protect_orders": 2, "orphans": 0,
            "orphan_symbols": [], "dupes": {}, "naked": [], "dust": [],
            "per_symbol": {"ADA/USDT:USDT": 2},
        })
        _write_json(cls.testnet / "logs" / "deadman.json", {
            "ok": True, "reason": "OK", "ts": now - 40.0, "muted": False,
            "instances": [{"name": "TESTNET", "round": 42, "hb_age_s": 12.0, "supervisor_pid": 999, "kill_tripped": False, "errors_win": {}}],
            "pings": [{"ok": True, "status": 200, "instance": "testnet", "url": "https://hc-ping.com/secret-uuid-999999"}],
        })
        _write_json(cls.testnet / "security" / "findings.json", {
            "audited_at": "15/11/2026", "scope": "test", "findings": [], "controls": [], "validations": [],
        })
        _write_json(cls.testnet / "golden" / "bug_manifest.json", {
            "n_classes": 68, "n_tests": 267, "digest": "0123456789abcdef" * 4, "files": ["test_a.py"],
        })
        (cls.testnet / ".env").write_text("BINANCE_API_SECRET=SHOULD_NEVER_LEAK_12345\n", encoding="utf-8")
        (cls.testnet / "STATE.md").write_text("# STATE\nIP 222.253.53.82 test\n", encoding="utf-8")

        # Journal with valid BOT trades + B-031 garbage R + manual trade + XSS reason + truncated trailing line
        t0 = now - 3 * 86400
        journal_lines = [
            json.dumps({"ts": t0, "event": "OPEN", "pair": "ADA/USDT:USDT", "direction": "SHORT", "entry": 0.5, "strategy": "B_BREAKOUT_RETEST", "setup_type": "BOS", "market_regime": "DOWNTREND"}),
            json.dumps({"ts": t0 + 3600, "event": "CLOSE", "pair": "ADA/USDT:USDT", "direction": "SHORT", "exit": 0.48, "r": 1.5, "pnl": 15.0, "won": True, "reason": "TP"}),
            json.dumps({"ts": t0 + 7200, "event": "OPEN", "pair": "SOL/USDT:USDT", "direction": "LONG", "entry": 100.0, "strategy": "B_BREAKOUT_RETEST", "setup_type": "BOS", "market_regime": "UPTREND"}),
            json.dumps({"ts": t0 + 10800, "event": "CLOSE", "pair": "SOL/USDT:USDT", "direction": "LONG", "exit": 98.0, "r": -1.0, "pnl": -10.0, "won": False, "reason": "SL"}),
            # B-031 garbage R record (r=793.07) must be dropped!
            json.dumps({"ts": t0 + 14400, "event": "OPEN", "pair": "XRP/USDT:USDT", "direction": "LONG", "entry": 1.0, "strategy": "B_BREAKOUT_RETEST"}),
            json.dumps({"ts": t0 + 18000, "event": "CLOSE", "pair": "XRP/USDT:USDT", "direction": "LONG", "exit": 0.99, "r": 793.07, "pnl": -5.0, "won": False, "reason": "SL"}),
            # Manual close (no OPEN)
            json.dumps({"ts": t0 + 21600, "event": "CLOSE", "pair": "DOGE/USDT:USDT", "direction": "LONG", "r": -0.8, "pnl": -8.0, "won": False, "reason": "MANUAL"}),
            # Agent vote with XSS payload and secret canary
            json.dumps({"ts": t0 + 22000, "event": "AGENT", "role": "critic", "model": "cline-pass/mimo", "action": "VETO", "confidence": 0.8, "symbol": "ADA/USDT:USDT", "direction": "SHORT", "reasons": ["<script>alert(1)</script> https://hc-ping.com/leak-uuid-111"]}),
        ]
        # Append incomplete trailing JSON line (no newline) to verify safe handling
        cls.journal_path = cls.testnet / "logs" / "journal.jsonl"
        cls.journal_path.write_text("\n".join(journal_lines) + "\n{\"ts\": 123, \"event\": \"OPEN\", \"broken", encoding="utf-8")

        # LIVE intentionally missing heartbeat to verify UNKNOWN / STALE (never fake 0 / ALIVE)
        _write_json(cls.live / "logs" / "risk_state.json", {
            "max_daily_loss_pct": 2.0, "start_balance": 50.0, "start_equity": 40.0,
            "tripped": True, "reason": "daily loss exceeded", "errors": 0, "max_errors": 5,
            "consec_losses": 3, "max_consec_losses": 5, "day": "2026-11-20", "mode": "live",
        })

        cls.live_snapshot_mtimes = {
            p.name: p.stat().st_mtime_ns for p in (cls.live / "logs").iterdir()
        }

        cls.store = DS.DataStore(testnet_root=cls.testnet, live_root=cls.live)
        cls.srv = DS.create_server(port=0, store=cls.store, static_dir=ROOT / "dashboard")
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def _req(self, method: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, headers=headers or {})
            resp = conn.getresponse()
            body = resp.read()
            hdrs = {k.lower(): v for k, v in resp.getheaders()}
            return resp.status, hdrs, body
        finally:
            conn.close()

    def test_security_headers_and_methods(self):
        status, hdrs, _ = self._req("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertIn("default-src 'none'", hdrs.get("content-security-policy", ""))
        self.assertEqual(hdrs.get("x-content-type-options"), "nosniff")
        self.assertEqual(hdrs.get("cache-control"), "no-store")

        for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
            st, h, _ = self._req(method, "/api/overview")
            self.assertEqual(st, 405, f"{method} should return 405")
            self.assertEqual(h.get("allow"), "GET, HEAD")

        st_head, _, body_head = self._req("HEAD", "/api/health")
        self.assertEqual(st_head, 200)
        self.assertEqual(body_head, b"")

    def test_host_and_origin_validation(self):
        # Evil host, wrong port, empty Host
        st, _, _ = self._req("GET", "/api/health", headers={"Host": "evil.attacker.com"})
        self.assertEqual(st, 403)
        st, _, _ = self._req("GET", "/api/health", headers={"Host": "127.0.0.1:9999"})
        self.assertEqual(st, 403)
        self.assertFalse(DS._is_allowed_host("", self.port))
        self.assertFalse(DS._is_allowed_host("127.0.0.1", self.port))
        self.assertTrue(DS._is_allowed_host(f"127.0.0.1:{self.port}", self.port))
        self.assertTrue(DS._is_allowed_host(f"localhost:{self.port}", self.port))
        # Evil origin and Origin: null
        st, _, _ = self._req("GET", "/api/health", headers={"Origin": "http://evil.attacker.com"})
        self.assertEqual(st, 403)
        st, _, _ = self._req("GET", "/api/health", headers={"Origin": "null"})
        self.assertEqual(st, 403)
        st, _, _ = self._req("GET", "/api/health", headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(st, 200)

    def test_traversal_and_secret_files_rejected(self):
        for p in (
            "/.env",
            "/../.env",
            "/%2e%2e/.env",
            "/..%2f.env",
            "/..%5c.env",
            "/index.html%00.png",
            "/C:/Windows/win.ini",
            "/logs/journal.jsonl",
            "/index.html::$DATA",
            "/dashboard_server.py",
        ):
            st, _, body = self._req("GET", p)
            self.assertIn(st, (403, 404), f"Path {p} returned {st}")
            self.assertNotIn(b"SHOULD_NEVER_LEAK", body)

    def test_symlink_static_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            sd = Path(td) / "dash"
            sd.mkdir()
            secret = Path(td) / "secret.txt"
            secret.write_text("TOP_SECRET", encoding="utf-8")
            link = sd / "index.html"
            try:
                link.symlink_to(secret)
            except OSError:
                self.skipTest("Symlink privilege unavailable on this Windows session")
            self.assertIsNone(DS.resolve_static_file(sd, "/index.html"))

    def test_static_whitelist_works(self):
        for p in ("/", "/index.html", "/styles.css", "/app.js", "/favicon.svg"):
            st, _, body = self._req("GET", p)
            self.assertEqual(st, 200, f"Static {p} failed with {st}")
            self.assertGreater(len(body), 20)

    def test_etag_304_caching(self):
        st1, h1, _ = self._req("GET", "/api/overview?t=testnet")
        self.assertEqual(st1, 200)
        etag = h1.get("etag")
        self.assertTrue(etag)
        st2, _, body2 = self._req("GET", "/api/overview?t=testnet", headers={"If-None-Match": etag})
        self.assertEqual(st2, 304)
        self.assertEqual(body2, b"")

    def test_missing_live_files_report_unknown_not_fake_zero(self):
        st, _, body = self._req("GET", "/api/overview?t=both")
        self.assertEqual(st, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["testnet"]["bot"]["status"], "ALIVE")
        self.assertEqual(data["live"]["bot"]["status"], "UNKNOWN")
        self.assertTrue(data["live"]["stale"])
        self.assertEqual(data["live"]["kill_switch"]["status"], "TRIPPED")
        # Deadman ping URL must be absent
        self.assertNotIn("secret-uuid-999999", body.decode("utf-8"))
        self.assertNotIn("hc-ping.com", body.decode("utf-8"))

    def test_b031_filtered_and_matches_monitor_report(self):
        st, _, body = self._req("GET", "/api/performance?t=testnet&days=30&bot_only=1")
        self.assertEqual(st, 200)
        perf = json.loads(body.decode("utf-8"))
        self.assertEqual(perf["counts"]["n_dropped_b031"], 1)
        self.assertEqual(perf["counts"]["window_valid"], 2)
        self.assertEqual(perf["counts"]["manual_closed"], 1)
        # Cross-check directly with monitor_report.stats
        opens, closes = MR.load_journal(str(self.journal_path))
        pairs, _ = MR.match_pairs(opens, closes)
        bot_only_pairs = [(o, c) for o, c in pairs if o is not None]
        expected = MR.stats(bot_only_pairs)
        self.assertEqual(perf["metrics"]["trades"], expected["n"])
        self.assertAlmostEqual(perf["metrics"]["pf_r"], expected["pf_r"], places=3)
        self.assertAlmostEqual(perf["metrics"]["exp_r"], expected["e_r"], places=4)

    def test_xss_preserved_as_plain_string_and_secrets_redacted_in_council(self):
        st, _, body = self._req("GET", "/api/council?t=testnet")
        self.assertEqual(st, 200)
        text = body.decode("utf-8")
        self.assertNotIn("leak-uuid-111", text)
        data = json.loads(text)
        reasons = data["recent_votes"][0]["reasons"][0]
        self.assertIn("<script>alert(1)</script>", reasons)
        self.assertIn("https://hc-ping.com/<redacted>", reasons)

    def test_docs_whitelist_and_redaction(self):
        st, _, body = self._req("GET", "/api/docs/state")
        self.assertEqual(st, 200)
        text = body.decode("utf-8")
        self.assertNotIn("222.253.53.82", text)
        self.assertIn("<ip_redacted>", text)

        st_bad, _, _ = self._req("GET", "/api/docs/.env")
        self.assertIn(st_bad, (403, 404))
        st_unknown, _, _ = self._req("GET", "/api/docs/nonexistent")
        self.assertEqual(st_unknown, 404)

    def test_invalid_query_params_rejected(self):
        for bad in (
            "/api/overview?t=prod",
            "/api/positions?t=both",
            "/api/performance?t=testnet&days=999",
            "/api/trades?t=testnet&limit=5000",
            "/api/trades?t=testnet&offset=-1",
            "/api/trades?t=testnet&outcome=hack",
        ):
            st, _, _ = self._req("GET", bad)
            self.assertEqual(st, 400, f"Expected 400 for {bad}, got {st}")

    def test_incremental_journal_append_and_rotation(self):
        with tempfile.TemporaryDirectory() as td:
            jpath = Path(td) / "journal.jsonl"
            now = time.time()
            r1 = json.dumps({"ts": now - 200, "event": "OPEN", "pair": "BTC/USDT:USDT", "entry": 100.0})
            r2 = json.dumps({"ts": now - 100, "event": "CLOSE", "pair": "BTC/USDT:USDT", "r": 1.2, "pnl": 12.0, "won": True})
            jpath.write_text(r1 + "\n" + r2 + "\n", encoding="utf-8")

            js = DS._JournalState(jpath)
            js.sync()
            p1, _, _ = js.get_paired()
            self.assertEqual(len(p1), 1)

            # Append another trade incrementally
            r3 = json.dumps({"ts": now - 50, "event": "OPEN", "pair": "ETH/USDT:USDT", "entry": 50.0})
            r4 = json.dumps({"ts": now - 10, "event": "CLOSE", "pair": "ETH/USDT:USDT", "r": -0.5, "pnl": -5.0, "won": False})
            with jpath.open("a", encoding="utf-8") as fh:
                fh.write(r3 + "\n" + r4 + "\n")
            js.sync()
            p2, _, _ = js.get_paired()
            self.assertEqual(len(p2), 2)

            # Truncate/rotate file to smaller size -> cache must rebuild cleanly
            jpath.write_text(r1 + "\n", encoding="utf-8")
            js.sync()
            p3, _, _ = js.get_paired()
            self.assertEqual(len(p3), 0)

    def test_concurrent_requests_and_live_dir_untouched(self):
        urls = [
            "/api/overview?t=both",
            "/api/positions?t=testnet",
            "/api/performance?t=testnet&days=30&bot_only=1",
            "/api/trades?t=testnet&limit=20",
            "/api/council?t=testnet",
            "/api/harness?t=testnet",
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(self._req, "GET", u) for u in urls * 2]
            statuses = [f.result()[0] for f in futs]
        self.assertTrue(all(s == 200 for s in statuses), statuses)

        # Verify LIVE directory mtimes did NOT change (strictly read-only)
        after_mtimes = {
            p.name: p.stat().st_mtime_ns for p in (self.live / "logs").iterdir()
        }
        self.assertEqual(after_mtimes, self.live_snapshot_mtimes)


if __name__ == "__main__":
    unittest.main()
