# -*- coding: utf-8 -*-
"""test_glow_signals.py — kiem thu lop "tin hieu truy xuat AI" dung chung.

Bao phu 4 thu nguoi dung yeu cau:
  1. NHIEU model agent cung chay chien luoc rieng (toc do / token / depth).
  2. Do THAT: do tre ms, token tra ve vs token neu doc nguyen file, cache, $.
  3. Dong bo tuyet doi 2 ban do: lib + CSS nhung y het, cung signature du lieu.
  4. Tin hieu hien tren bieu do (HUD) + server live day SSE / reload.

Chay:  python -m unittest tests.test_glow_signals -v
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import glow_retrieval as R                                                  # noqa: E402

GLOW2D = ROOT / "glow_map.html"
GLOW3D = ROOT / "glow_map_webgl.html"
NODE = shutil.which("node")

# ── Fixture tat dinh (khong phu thuoc file repo -> so duoc voi JS) ───────────
FIX_RAW = [
    ("risk.py::check_drawdown", "check drawdown limit", "function", "risk.py"),
    ("risk.py::stop_loss", "apply stop loss on position", "function", "risk.py"),
    ("strategy.py::rsi_signal", "rsi oversold signal", "function", "strategy.py"),
    ("glow_map_webgl_engine.js::buildLayout", "layout 3d positions",
     "function", "glow_map_webgl_engine.js"),
    ("glow_retrieval.py::Index_search", "bm25 retrieval index search",
     "function", "glow_retrieval.py"),
    ("memory_agent.py::MemoryAgent", "memory agent recall", "class",
     "memory_agent.py"),
    ("backtest.py::run_backtest", "backtest pnl summary", "function",
     "backtest.py"),
    ("glow_signals.js::GS_search", "signals retrieval search", "function",
     "glow_signals.js"),
    ("risk.py", "risk module file", "file", "risk.py"),
    ("note://no-file", "note without file on disk", "note", None),
]
FIX_EDGES = [(0, 1), (0, 8), (1, 8), (2, 6), (3, 7), (4, 7), (5, 9), (2, 0), (3, 4)]
FIX_FTOK = {"risk.py": 900, "strategy.py": 700, "backtest.py": 1200,
            "glow_retrieval.py": 5200, "glow_signals.js": 3400,
            "memory_agent.py": 1500, "glow_map_webgl_engine.js": 14000}
FIX_QUERIES = ["stop_loss drawdown", "layout 3d", "retrieval index",
               "mem", "zzz khong ton tai"]
FIX_STRATEGIES = ["fast", "code", "hybrid", "deep", "semantic"]


def fix_docs():
    docs = []
    for nid, label, kind, f in FIX_RAW:
        docs.append({"id": nid, "label": label, "kind": kind, "file": f, "deg": 0,
                     "tokens": max(R.MIN_DOC_TOKENS,
                                   R.estimate_tokens(nid + " " + label))})
    for s, t in FIX_EDGES:
        docs[s]["deg"] += 1
        docs[t]["deg"] += 1
    return docs


def fix_index():
    return R.Index(fix_docs(), FIX_EDGES, dict(FIX_FTOK), name="fixture")


def fix_agent(**kw):
    a = {"id": "tester", "label": "Tester", "model": "unit-test-model",
         "provider": "test", "color": "#fff", "tier": "test", "strategy": "fast",
         "k": 6, "beam": 1, "ms_budget": 40, "token_budget": 10 ** 9,
         "cache_ttl_ms": 100_000, "price_in": 1.0, "price_out": 3.0}
    a.update(kw)
    return a


def rounded(obj, nd=4):
    """So sanh lien ngon ngu: lam tron float (JS/Python khac nhau o ulp cuoi)."""
    if isinstance(obj, float):
        return round(obj, nd)
    if obj is None or isinstance(obj, (bool, str, int)):
        return obj
    if isinstance(obj, dict):
        return {k: rounded(v, nd) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [rounded(v, nd) for v in obj]
    return obj


class TestTokenizer(unittest.TestCase):
    def test_estimate_tokens_floor(self):
        self.assertEqual(R.estimate_tokens(""), 1)
        self.assertEqual(R.estimate_tokens("a" * 8), 2)
        self.assertEqual(R.estimate_tokens("a" * 9), 3)

    def test_snake_case_split_and_kept(self):
        toks = R.tokenize("memory_graph")
        self.assertIn("memory", toks)
        self.assertIn("graph", toks)
        self.assertIn("memory_graph", toks)

    def test_camel_case_split(self):
        toks = R.tokenize("buildLayout")
        self.assertIn("build", toks)
        self.assertIn("layout", toks)

    def test_identifier_parts_kept(self):
        toks = R.tokenize("risk.py::stop_loss")
        self.assertIn("risk", toks)
        self.assertIn("stop", toks)
        self.assertIn("loss", toks)

    def test_norm_query_is_order_insensitive(self):
        self.assertEqual(R.norm_query("stop loss drawdown"),
                         R.norm_query("drawdown loss stop"))

    def test_norm_query_keeps_compound_tokens(self):
        # "Stop_Loss" van giu cum ghep -> cac ban do cache duoc key on dinh
        self.assertEqual(R.norm_query("Stop_Loss"),
                         " ".join(sorted(set(R.tokenize("Stop_Loss")))))
        self.assertIn("stop_loss", R.norm_query("Stop_Loss"))

    def test_norm_query_falls_back_to_raw_text_when_no_tokens(self):
        self.assertEqual(R.norm_query("b a c"), "b a c")

    def test_pct_linear(self):
        self.assertEqual(R.pct([10], 95), 10.0)
        self.assertEqual(R.pct([0, 10], 50), 5.0)
        self.assertAlmostEqual(R.pct([0, 10, 20], 95), 19.0, places=6)


class TestIndex(unittest.TestCase):
    def setUp(self):
        self.ix = fix_index()

    def test_index_shape(self):
        self.assertEqual(self.ix.n, len(FIX_RAW))
        self.assertGreater(len(self.ix.post), 10)
        self.assertIn(1, self.ix.adj[0])

    def test_search_finds_stop_loss_first(self):
        r = self.ix.search("stop_loss drawdown", k=5, strategy="fast")
        self.assertGreaterEqual(len(r["hits"]), 1)
        self.assertIn("stop_loss", r["hits"][0]["id"])

    def test_scores_positive_and_sorted(self):
        scores = [h["score"] for h in self.ix.search("retrieval index", k=5)["hits"]]
        self.assertTrue(all(s > 0 for s in scores))
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_unknown_query_has_no_hits(self):
        r = self.ix.search("zzz-khong-ton-tai", k=5)
        self.assertEqual(r["hits"], [])
        self.assertEqual(r["cost"]["returned"], 0)

    def test_semantic_strategy_widens_recall(self):
        base = self.ix.search("mem", k=10, strategy="fast")["scored"]
        wide = self.ix.search("mem", k=10, strategy="semantic")["scored"]
        self.assertGreaterEqual(wide, base)

    def test_deep_strategy_adds_two_hop(self):
        fast = {h["id"] for h in self.ix.search("stop_loss", 10, "fast")["hits"]}
        deep = {h["id"] for h in self.ix.search("stop_loss", 10, "deep")["hits"]}
        self.assertTrue(fast.issubset(deep))
        self.assertGreater(len(deep), len(fast))

    def test_cost_saves_tokens_vs_reading_whole_files(self):
        c = self.ix.search("risk stop_loss drawdown", k=3)["cost"]
        self.assertGreater(c["baseline"], c["returned"])
        self.assertEqual(c["baseline"] - c["returned"], c["saved"])
        self.assertGreater(c["pct"], 50.0)
        self.assertGreaterEqual(c["files"], 1)

    def test_same_file_counted_once_in_baseline(self):
        r = self.ix.search("risk drawdown stop loss", k=4)
        files = {h["file"] for h in r["hits"] if h["file"]}
        self.assertEqual(r["cost"]["files"], len(files))

    def test_docs_without_file_use_record_baseline(self):
        self.assertEqual(self.ix.baseline_of(9), R.RECORD_TOKENS)
        self.assertEqual(self.ix.baseline_of(0), FIX_FTOK["risk.py"])


class TestCacheAndTuner(unittest.TestCase):
    def test_cache_miss_then_hit(self):
        c = R.Cache()
        self.assertIsNone(c.get("k", 1000))
        c.put("k", {"v": 1}, 1000, 500)
        self.assertEqual(c.get("k", 1200), {"v": 1})
        self.assertEqual(c.stats()["hits"], 1)
        self.assertEqual(c.stats()["misses"], 1)

    def test_cache_ttl_expires(self):
        c = R.Cache()
        c.put("k", {"v": 1}, 1000, 500)
        self.assertIsNone(c.get("k", 1501))

    def test_cache_is_lru_bounded(self):
        c = R.Cache(maxsize=2)
        c.put("a", 1, 0, 9999)
        c.put("b", 2, 0, 9999)
        c.put("c", 3, 0, 9999)
        self.assertIsNone(c.get("a", 0))
        self.assertEqual(c.get("c", 0), 3)
        self.assertEqual(c.stats()["size"], 2)

    def test_cache_hit_rate_rounds(self):
        c = R.Cache()
        c.put("k", 1, 0, 9999)
        c.get("k", 0)
        c.get("k", 0)
        c.get("x", 0)
        self.assertEqual(c.stats()["hit_pct"], 66.7)

    def test_tuner_needs_warmup(self):
        t = R.Tuner()
        a = fix_agent(k=12)
        for _ in range(3):
            self.assertEqual(t.adapt(a, 500.0, False)[:2], (12, 1))

    def test_tuner_cuts_k_when_too_slow(self):
        t = R.Tuner()
        a = fix_agent(k=12, ms_budget=40)
        for _ in range(6):
            k, beam, done = t.adapt(a, 300.0, False)
        self.assertLess(k, 12)
        self.assertGreaterEqual(k, 4)
        self.assertGreaterEqual(beam, 1)
        self.assertTrue(t.snapshot()["tester"]["tuned"] >= 1)

    def test_tuner_restores_k_when_fast_and_cached(self):
        t = R.Tuner()
        a = fix_agent(k=8, ms_budget=100)
        for _ in range(6):
            t.adapt(a, 900.0, False)          # pha cho k giam xuong 4
        low = t.state["tester"]["k"]
        self.assertLess(low, 8)
        # lich su cham bi day khoi cua so (window=12) -> p95 thap -> tang lai
        for _ in range(24):
            t.adapt(a, 1.0, True)
        self.assertGreater(t.state["tester"]["k"], low)
        self.assertEqual(t.state["tester"]["k"], 8)

    def test_tuner_stable_when_within_budget(self):
        t = R.Tuner()
        a = fix_agent(k=10, ms_budget=100)
        for _ in range(10):
            k, beam, done = t.adapt(a, 30.0, False)
        self.assertEqual((k, beam), (10, 1))
        self.assertFalse(done)


class TestAgentRuns(unittest.TestCase):
    def setUp(self):
        self.ix = fix_index()
        self.cache = R.Cache()
        self.tuner = R.Tuner()

    def test_event_has_all_chart_fields(self):
        e = R.run_agent(self.ix, fix_agent(), "stop_loss drawdown",
                        self.cache, self.tuner, "fixture", rund=1, now=1000.0)
        for key in ("t", "agent", "model", "query", "dataset", "round", "k",
                    "beam", "strategy", "hits", "n_hits", "scored",
                    "latency_ms", "cache", "tokens_returned", "tokens_baseline",
                    "tokens_saved", "saved_pct", "files_touched", "cost_usd",
                    "truncated", "tuned", "k_after", "beam_after", "ok"):
            self.assertIn(key, e, "event thieu %s -> HUD/thieu cot" % key)
        self.assertTrue(e["ok"])
        self.assertGreater(e["n_hits"], 0)
        self.assertGreater(e["tokens_saved"], 0)

    def test_second_run_is_cache_hit_and_faster(self):
        a, q = fix_agent(), "retrieval index"
        e1 = R.run_agent(self.ix, a, q, self.cache, self.tuner, "fixture",
                         rund=1, now=1000.0, force_miss=True)
        e2 = R.run_agent(self.ix, a, q, self.cache, self.tuner, "fixture",
                         rund=2, now=1000.0)
        self.assertFalse(e1["cache"])
        self.assertTrue(e2["cache"])
        self.assertEqual(e1["hits"], e2["hits"])
        self.assertLessEqual(e2["latency_ms"], e1["latency_ms"] + 0.5)
        self.assertEqual(self.cache.stats()["hits"], 1)

    def test_different_queries_do_not_share_cache(self):
        R.run_agent(self.ix, fix_agent(), "stop_loss", self.cache, self.tuner,
                    "fixture", now=1000.0)
        e = R.run_agent(self.ix, fix_agent(), "layout 3d", self.cache,
                        self.tuner, "fixture", now=1000.0)
        self.assertFalse(e["cache"])

    def test_token_budget_truncates_hits(self):
        a = fix_agent(k=6, token_budget=40)
        e = R.run_agent(self.ix, a, "risk layout retrieval memory backtest",
                        self.cache, self.tuner, "fixture", now=1000.0)
        self.assertTrue(e["truncated"])
        self.assertLessEqual(e["tokens_returned"], 40)

    def test_cost_usd_uses_agent_price(self):
        a = fix_agent(price_in=2.0, price_out=4.0)
        e = R.run_agent(self.ix, a, "stop_loss", self.cache, self.tuner,
                        "fixture", now=1000.0)
        expect = round(e["tokens_returned"] / 1e6 * 3.0, 6)
        self.assertAlmostEqual(e["cost_usd"], expect, places=6)

    def test_five_agents_shipped_with_distinct_policies(self):
        self.assertEqual([a["id"] for a in R.AGENTS],
                         ["scout", "analyst", "coder", "auditor", "oracle"])
        self.assertEqual(len({a["model"] for a in R.AGENTS}), 5)
        self.assertEqual(len({a["strategy"] for a in R.AGENTS}), 5)
        for a in R.AGENTS:
            self.assertGreater(a["token_budget"], 0)
            self.assertGreater(a["ms_budget"], 0)
            self.assertIn(a["strategy"], ("fast", "code", "hybrid", "deep",
                                          "semantic"))

    def test_all_agents_run_on_same_data(self):
        cache, tuner = R.Cache(), R.Tuner()
        evs = [R.run_agent(self.ix, R.AGENT_BY_ID[i], "risk layout retrieval",
                           cache, tuner, "fixture", rund=1, now=1000.0)
               for i in ("scout", "analyst", "coder", "auditor", "oracle")]
        self.assertEqual(len(evs), 5)
        for e in evs:
            self.assertTrue(e["ok"])
            self.assertGreaterEqual(e["n_hits"], 1)
        # agent "deep" (analyst) phai lay rong hon agent "fast" (scout)
        self.assertGreaterEqual(len({h["id"] for h in
                                     evs[1]["hits"]}), 1)


class TestMetrics(unittest.TestCase):
    def _ev(self, agent="scout", ms=10.0, ret=100, base=500, cache=False,
            trunc=False, tuned=False, model="gpt-4o-mini"):
        return {"agent": agent, "model": model, "ok": True, "latency_ms": ms,
                "tokens_returned": ret, "tokens_baseline": base,
                "tokens_saved": max(0, base - ret), "cache": cache,
                "cost_usd": 0.001, "truncated": trunc, "tuned": tuned,
                "n_hits": 3}

    def test_empty_events_safe(self):
        m = R.metrics([])
        self.assertEqual(m["byAgent"], {})
        self.assertEqual(m["totals"]["runs"], 0)
        self.assertEqual(m["totals"]["saved_pct"], 0.0)

    def test_failed_events_ignored(self):
        e = self._ev()
        e["ok"] = False
        self.assertEqual(R.metrics([e])["totals"]["runs"], 0)

    def test_percentiles_and_savings(self):
        evs = [self._ev(ms=v) for v in (2, 4, 6, 8, 10)]
        a = R.metrics(evs)["byAgent"]["scout"]
        self.assertEqual(a["runs"], 5)
        self.assertEqual(a["p50_ms"], 6.0)
        self.assertEqual(a["tokens_returned"], 500)
        self.assertEqual(a["tokens_baseline"], 2500)
        self.assertEqual(a["saved_pct"], 80.0)
        self.assertGreaterEqual(a["speed"], 1)

    def test_cache_hit_percentage(self):
        evs = [self._ev(cache=True), self._ev(cache=False)]
        self.assertEqual(R.metrics(evs)["byAgent"]["scout"]["cache_hit_pct"],
                         50.0)

    def test_totals_across_agents(self):
        evs = [self._ev("scout"), self._ev("analyst", model="claude")]
        t = R.metrics(evs)["totals"]
        self.assertEqual(t["runs"], 2)
        self.assertEqual(t["ret"], 200)
        self.assertEqual(len(R.metrics(evs)["byAgent"]), 2)


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="glow_sig_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_append_and_read_roundtrip(self):
        p = self.tmp / "log.jsonl"
        ix, cache, tuner = fix_index(), R.Cache(), R.Tuner()
        for i, q in enumerate(FIX_QUERIES[:3]):
            R.append_event(p, R.run_agent(ix, fix_agent(), q, cache, tuner,
                                          "fixture", rund=1, now=1000.0 + i))
        evs = R.read_events(p)
        self.assertEqual(len(evs), 3)
        self.assertEqual([e["query"] for e in evs], FIX_QUERIES[:3])

    def test_read_events_skips_broken_lines(self):
        p = self.tmp / "log.jsonl"
        p.write_text('{"ok": true, "agent": "a"}\nRAC RU\n\n{"ok": true}\n',
                     encoding="utf-8")
        self.assertEqual(len(R.read_events(p)), 2)

    def test_read_events_missing_file_is_empty(self):
        self.assertEqual(R.read_events(self.tmp / "khong.png"), [])

    def test_read_events_keeps_tail_and_survives_corruption(self):
        p = self.tmp / "log.jsonl"
        with open(p, "w", encoding="utf-8") as f:
            for i in range(50):
                f.write(json.dumps({"i": i}) + "\n")
            f.write("{cat\ncuoi\n")
        evs = R.read_events(p, limit=10)
        self.assertEqual(len(evs), 10)
        self.assertEqual(evs[-1]["i"], 49)

    def test_fingerprint_stable_and_sensitive(self):
        a = {"X": ([{"id": "a", "deg": 1}], [(0, 1)]),
             "Y": ([{"id": "b", "deg": 0}], [])}
        b = {"X": ([{"id": "a", "deg": 1}], [(0, 1)]),
             "Y": ([{"id": "b", "deg": 0}], [])}
        self.assertEqual(R.fingerprint(a), R.fingerprint(b))
        self.assertEqual(len(R.fingerprint(a)), 12)
        b["Y"][0].append({"id": "c", "deg": 0})
        self.assertNotEqual(R.fingerprint(a), R.fingerprint(b))

    def test_snapshot_shape_matches_hud_contract(self):
        ix, cache, tuner = fix_index(), R.Cache(), R.Tuner()
        evs = [R.run_agent(ix, R.AGENT_BY_ID["scout"], q, cache, tuner,
                           "fixture", rund=1, now=1000.0)
               for q in FIX_QUERIES]
        snap = R.snapshot(evs, [fix_agent()], [{"name": "fixture", "nodes": 10,
                                               "edges": 9, "tokens": 1234}],
                          "abc123def456", queries=FIX_QUERIES, cache=cache,
                          tuner=tuner)
        for key in ("lib", "generated", "signature", "agents", "datasets",
                    "queries", "metrics", "events", "cache", "tuning"):
            self.assertIn(key, snap)
        self.assertEqual(snap["signature"], "abc123def456")
        self.assertEqual(snap["metrics"]["totals"]["runs"], len(FIX_QUERIES))
        self.assertEqual(len(snap["events"]), len(FIX_QUERIES))
        self.assertIn("fixture", [d["name"] for d in snap["datasets"]])
        self.assertTrue(json.dumps(snap) is not None)   # JSON-safe

    def test_snapshot_caps_events_at_120(self):
        evs = [{"agent": "scout", "ok": True, "latency_ms": 1, "n_hits": 0,
                "tokens_returned": 0, "tokens_baseline": 0,
                "tokens_saved": 0} for _ in range(300)]
        self.assertEqual(len(R.snapshot(evs, [], [], "s")["events"]), 120)

    def test_load_all_docs_reads_real_maps(self):
        docs = R.load_all_docs(ROOT)
        self.assertGreaterEqual(len(docs), 1, "can co it nhat 1 dataset ban do")
        for name, (d, l, ft) in docs.items():
            self.assertGreater(len(d), 50, "%s qua it node" % name)
            self.assertGreater(len(l), 10, "%s qua it edge" % name)
            self.assertTrue(all("id" in x and "label" in x for x in d))
            self.assertTrue(all(x["tokens"] >= R.MIN_DOC_TOKENS for x in d))
            self.assertTrue(all(0 <= i < len(d) and 0 <= j < len(d)
                                for i, j in l))

    def test_build_payload_signature_uses_same_fingerprint(self):
        """build_glow.py + serve_glow.py + test dung DUNG 1 cach tinh chu ky."""
        docs = R.load_all_docs(ROOT)
        sig = R.fingerprint({n: (d, l) for n, (d, l, _f) in docs.items()})
        sig2 = R.fingerprint({n: (d, l) for n, (d, l, _f)
                              in R.load_all_docs(ROOT).items()})
        self.assertEqual(sig, sig2)
        self.assertRegex(sig, r"^[0-9a-f]{12}$")


# ── Parity Python <-> JS: 2 ban do nhung JS, nen JS phai TRA CUNG ket qua ───
FIX_EVENTS = [
    {"agent": "scout", "model": "gpt-4o-mini", "ok": True, "latency_ms": 12.5,
     "tokens_returned": 240, "tokens_baseline": 4000, "tokens_saved": 3760,
     "cache": False, "cost_usd": 0.0003, "truncated": False, "tuned": False,
     "n_hits": 4},
    {"agent": "scout", "model": "gpt-4o-mini", "ok": True, "latency_ms": 3.0,
     "tokens_returned": 240, "tokens_baseline": 4000, "tokens_saved": 3760,
     "cache": True, "cost_usd": 0.0003, "truncated": False, "tuned": True,
     "n_hits": 4},
    {"agent": "analyst", "model": "claude-3.5-sonnet", "ok": True,
     "latency_ms": 90.0, "tokens_returned": 900, "tokens_baseline": 9000,
     "tokens_saved": 8100, "cache": False, "cost_usd": 0.0069,
     "truncated": True, "tuned": False, "n_hits": 7},
]


class TestPythonJsParity(unittest.TestCase):
    """Cung 1 truy van -> Python (sinh snapshot) va JS (nhung trong 2 ban do)
    phai tra ve CUNG xep hang, cung token, cung so lieu HUD."""

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise unittest.SkipTest("khong co node -> bo qua parity")
        cls.tmp = Path(tempfile.mkdtemp(prefix="glow_parity_"))
        docs = fix_docs()
        flat = []
        for s, t in FIX_EDGES:
            flat += [s, t, 0, 1]
        runs = [{"query": q, "round": i, "at": 0} for i, q in
                enumerate(FIX_QUERIES + FIX_QUERIES)]
        inp = {
            "texts": ["memory_graph", "buildLayout", "risk.py::stop_loss",
                      "12345", "x", "MemoryAgent_recall", ""],
            "queries": FIX_QUERIES,
            "pcts": [{"xs": [0, 10, 20, 30, 40], "p": 50},
                     {"xs": [10], "p": 95},
                     {"xs": [0, 5], "p": 95},
                     {"xs": [3, 1, 2], "p": 25}],
            "docs": docs, "flatEdges": flat, "fileTokens": FIX_FTOK,
            "search": [{"query": q, "k": 6, "strategy": s}
                       for q in FIX_QUERIES for s in FIX_STRATEGIES],
            "cacheSeq": [{"key": "a", "at": 0, "put": 1, "ttl": 500},
                         {"key": "a", "at": 100},
                         {"key": "a", "at": 600},
                         {"key": "b", "at": 700, "put": 2, "ttl": 5000},
                         {"key": "a", "at": 800, "put": 3, "ttl": 5000}],
            "tunerSeq": [{"id": "tester", "k": 12, "beam": 2,
                          "ms_budget": 40, "ms": 300.0, "hit": False},
                         {"id": "tester", "k": 12, "beam": 2,
                          "ms_budget": 40, "ms": 300.0, "hit": False}],
            "runs": runs, "agent": fix_agent(k=6), "events": FIX_EVENTS,
        }
        cls.inp = inp
        in_json = cls.tmp / "in.json"
        out_json = cls.tmp / "out.json"
        in_json.write_text(json.dumps(inp, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([NODE, str(Path(__file__).with_name("_js_parity.js")),
                            str(in_json), str(out_json)],
                           capture_output=True, text=True, cwd=str(ROOT),
                           timeout=120)
        if r.returncode != 0:
            raise AssertionError("node parity loi: %s\n%s" % (r.stdout, r.stderr))
        cls.js = json.loads(out_json.read_text(encoding="utf-8"))
        cls.py = cls._python_side(inp)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "tmp", None):
            shutil.rmtree(cls.tmp, True)

    @classmethod
    def _python_side(cls, inp):
        out = {"V": R.LIB_VERSION, "K1": R.K1}
        out["defaultAgents"] = [
            {k: v for k, v in a.items() if k not in ("note", "on")}
            for a in R.AGENTS]
        out["tokenize"] = [R.tokenize(s) for s in inp["texts"]]
        out["normQuery"] = [R.norm_query(q) for q in inp["queries"]]
        out["pct"] = [R.pct(p["xs"], p["p"]) for p in inp["pcts"]]

        ix = fix_index()
        out["index"] = {"n": ix.n, "terms": len(ix.post)}
        out["search"] = []
        for s in inp["search"]:
            out["search"].append(ix.search(s["query"], k=s["k"],
                                           strategy=s["strategy"]))

        cache = R.Cache(maxsize=4)
        seq = []
        for c in inp["cacheSeq"]:
            got = cache.get(c["key"], 1000 + c["at"])
            seq.append([None if got is None else got["v"], cache.stats()])
            if c.get("put"):
                cache.put(c["key"], {"v": c["put"]}, 1000 + c["at"], c["ttl"])
        out["cacheSeq"] = seq
        out["cacheStats"] = cache.stats()

        tuner = R.Tuner()
        out["tuner"] = []
        for t in inp["tunerSeq"]:
            ag = {"id": t["id"], "k": t["k"], "beam": t["beam"],
                  "ms_budget": t["ms_budget"]}
            k, beam, done = tuner.adapt(ag, t["ms"], t["hit"])
            out["tuner"].append([k, beam, done])
        out["tunerSnapshot"] = tuner.snapshot()

        ix2, cache2 = fix_index(), R.Cache(maxsize=256)
        out["runs"] = []
        for rr in inp["runs"]:
            e = R.run_agent(ix2, inp["agent"], rr["query"], cache2, R.Tuner(),
                            "fixture", rund=rr["round"], now=1000.0 + rr["at"])
            out["runs"].append({k: v for k, v in e.items() if k != "latency_ms"})
        out["metrics"] = R.metrics(inp["events"])
        return out

    def _cmp(self, js_key, py_key=None):
        self.assertEqual(rounded(self.js[js_key]),
                         rounded(self.py[py_key or js_key]),
                         "lech JS<->Python o %s" % js_key)

    def test_tokenize_parity(self):
        self._cmp("tokenize")

    def test_norm_query_parity(self):
        self._cmp("normQuery")

    def test_percentile_parity(self):
        self._cmp("pct")

    def test_agent_roster_parity(self):
        self.assertEqual([a["id"] for a in self.js["defaultAgents"]],
                         [a["id"] for a in self.py["defaultAgents"]])

    def test_index_parity(self):
        self._cmp("index")

    def test_search_ranking_parity_all_strategies(self):
        self.assertEqual(len(self.js["search"]), len(self.py["search"]))
        for i, (a, b) in enumerate(zip(self.js["search"], self.py["search"])):
            self.assertEqual([h["id"] for h in a["hits"]],
                             [h["id"] for h in b["hits"]],
                             "xep hang lech o query #%d" % i)
            self.assertEqual(a["scored"], b["scored"])
            self.assertEqual(a["cost"], b["cost"], "chi phi token lech")

    def test_cache_ttl_and_lru_parity(self):
        self._cmp("cacheSeq")
        self._cmp("cacheStats")

    def test_tuner_parity(self):
        self._cmp("tuner")
        self._cmp("tunerSnapshot")

    def test_agent_run_parity(self):
        self.assertEqual(len(self.js["runs"]), len(self.py["runs"]))
        for i, (a, b) in enumerate(zip(self.js["runs"], self.py["runs"])):
            self.assertEqual(a["agent"], b["agent"])
            self.assertEqual([h["id"] for h in a["hits"]],
                             [h["id"] for h in b["hits"]],
                             "hits lech o lan chay #%d" % i)
            for f in ("n_hits", "scored", "cache", "tokens_returned",
                      "tokens_baseline", "tokens_saved", "saved_pct",
                      "cost_usd", "truncated"):
                self.assertEqual(rounded(a[f]), rounded(b[f]),
                                 "%s lech o lan chay #%d" % (f, i))

    def test_metrics_parity(self):
        self._cmp("metrics")


# ── 2 bản đồ phải chạy CÙNG 1 lớp tín hiệu (nhúng nguyên văn) ───────────────
def _payload(html: str) -> dict:
    line = html.split("const DATA = ", 1)[1].split("\n", 1)[0]
    if line.endswith(";"):
        line = line[:-1]
    return json.loads(line.replace("<\\/", "</"))


class TestMapsAreInSync(unittest.TestCase):
    """Cả 2 bản đồ (canvas2d + webgl) nhúng y hệt lib/CSS/cùng snapshot."""

    @classmethod
    def setUpClass(cls):
        if not GLOW2D.exists() or not GLOW3D.exists():
            raise unittest.SkipTest("chua build glow_map(.html / _webgl.html)")
        cls.h2 = GLOW2D.read_text(encoding="utf-8")
        cls.h3 = GLOW3D.read_text(encoding="utf-8")
        cls.d2 = _payload(cls.h2)
        cls.d3 = _payload(cls.h3)

    def test_no_placeholder_left(self):
        for h, name in ((self.h2, "canvas2d"), (self.h3, "webgl")):
            for ph in ("__GLOW_PAYLOAD__", "__GLOW_SIGNALS_LIB__",
                       "/*__GLOW_SIGNALS_CSS__*/"):
                self.assertNotIn(ph, h, "%s con placeholder %s" % (name, ph))

    def test_embedded_lib_matches_source_files(self):
        src = ((ROOT / "glow_signals.js").read_text(encoding="utf-8") + "\n" +
               (ROOT / "glow_signals_lib.js").read_text(encoding="utf-8")).strip()
        self.assertIn("window.__GSL", src, "bus __GSL phai co trong nguon")
        for h, name in ((self.h2, "canvas2d"), (self.h3, "webgl")):
            self.assertEqual(h.count(src), 1,
                             "%s phai nhung DUNG NGUYEN VAN lib 1 lan" % name)

    def test_embedded_css_matches_source(self):
        css = (ROOT / "glow_signals.css").read_text(encoding="utf-8")
        for h, name in ((self.h2, "canvas2d"), (self.h3, "webgl")):
            self.assertEqual(h.count(css), 1,
                             "%s phai nhung DUNG NGUYEN VAN css" % name)

    def test_both_maps_share_identical_signals_blob(self):
        s2, s3 = self.d2.get("signals"), self.d3.get("signals")
        self.assertIsNotNone(s2, "glow_map.html thieu DATA.signals")
        self.assertIsNotNone(s3, "glow_map_webgl.html thieu DATA.signals")
        self.assertEqual(json.dumps(s2, sort_keys=True),
                         json.dumps(s3, sort_keys=True),
                         "2 ban do trung snapshot tin hieu KHAC nhau")

    def test_both_maps_share_data_signature(self):
        self.assertEqual(self.d2["signature"], self.d3["signature"],
                         "du lieu 2 ban do lech -> chay build lai")
        self.assertRegex(self.d2["signature"], r"^[0-9a-f]{12}$")
        sig_now = R.fingerprint({n: (d, l) for n, (d, l, _f)
                                 in R.load_all_docs(ROOT).items()})
        self.assertEqual(self.d2["signals"]["signature"], sig_now,
                         "snapshot trong ban do da cu so voi du lieu hien tai")

    def test_signals_snapshot_contract(self):
        for h, name in ((self.d2["signals"], "canvas2d"),
                        (self.d3["signals"], "webgl")):
            for key in ("lib", "generated", "signature", "agents", "datasets",
                        "metrics", "events", "cache", "tuning"):
                self.assertIn(key, h, "%s thieu %s" % (name, key))
            self.assertEqual(h["lib"], R.LIB_VERSION)
            self.assertEqual(len(h["agents"]), len(R.AGENTS))
            self.assertIn("byAgent", h["metrics"])
            self.assertIn("totals", h["metrics"])
            self.assertLessEqual(len(h["events"]), 120)

    def test_hud_elements_present_in_both_templates(self):
        """HUD markup nam trong TEMPLATE; webgl goi __GSL.boot tu ENGINE."""
        for tpl in (ROOT / "glow_map_template.html",
                    ROOT / "glow_map_webgl_template.html"):
            t = tpl.read_text(encoding="utf-8")
            for el in ("sigPanel", "sigAgents", "sigStats", "sigEvents",
                       "fxSignals"):
                self.assertIn(el, t, "%s thieu %s" % (tpl.name, el))
        boots = ((ROOT / "glow_map_template.html").read_text(encoding="utf-8"),
                 (ROOT / "glow_map_webgl_engine.js").read_text(encoding="utf-8"))
        self.assertTrue(all("__GSL.boot" in b for b in boots),
                        "ca 2 engine deu phai goi __GSL.boot")

    def test_fx_signals_toggle_wired_in_both_maps(self):
        for h, name in ((self.h2, "canvas2d"), (self.h3, "webgl")):
            self.assertIn('id="fxSignals"', h, "%s thieu toggle" % name)
            self.assertIn("__GSL", h, "%s thieu bus" % name)

    def test_log_events_agree_with_snapshot(self):
        """Snapshot nhung phai phan anh day du log truy xuat cuoi."""
        evs = R.read_events(ROOT / "retrieval_log.jsonl")
        if not evs:
            self.skipTest("chua co retrieval_log.jsonl")
        embedded = self.d2["signals"]["events"]
        self.assertEqual(len(embedded), min(len(evs), 120))
        self.assertEqual(embedded[-1]["query"], evs[-1]["query"])
        self.assertEqual(embedded[-1]["agent"], evs[-1]["agent"])


# ── Cong cu chay agent dong bo + hook cho BAT KY AI ──────────────────────────
class TestToolCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="glow_cli_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "retrieval_log.jsonl"

    def _run(self, *args):
        return subprocess.run([sys.executable, *args], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=180)

    def test_glow_agents_writes_events_and_snapshot(self):
        exp = self.tmp / "glow_signals.json"
        r = self._run("glow_agents.py", "--agents", "scout,analyst",
                      "--queries", "risk stop loss", "--rounds", "2",
                      "--log", str(self.log), "--export", str(exp))
        self.assertEqual(r.returncode, 0, r.stderr)
        evs = R.read_events(self.log)
        self.assertEqual(len(evs), 4, "2 agent x 1 query x 2 vong")
        self.assertEqual({e["agent"] for e in evs}, {"scout", "analyst"})
        for e in evs:
            self.assertTrue(e["ok"])
            self.assertGreaterEqual(e["n_hits"], 1)
            self.assertGreater(e["tokens_saved"], 0)
        self.assertTrue(exp.exists(), "phai xuat snapshot cho cac ban do")
        snap = json.loads(exp.read_text(encoding="utf-8"))
        self.assertEqual(snap["metrics"]["totals"]["runs"], 4)
        self.assertGreater(snap["metrics"]["totals"]["saved"], 0)
        self.assertEqual(snap["signature"],
                         R.fingerprint({n: (d, l) for n, (d, l, _f)
                                        in R.load_all_docs(ROOT).items()}))
        self.assertTrue(any(e["cache"] for e in evs), "khong co cache hit")

    def test_glow_agents_custom_agent_from_cli(self):
        exp = self.tmp / "snap.json"
        r = self._run("glow_agents.py", "--agents", "",
                      "--agent", "mine:my-model:#ff0000:9:code",
                      "--queries", "layout 3d", "--rounds", "1",
                      "--log", str(self.log), "--export", str(exp))
        self.assertEqual(r.returncode, 0, r.stderr)
        evs = R.read_events(self.log)
        self.assertEqual(evs[0]["agent"], "mine")
        self.assertEqual(evs[0]["model"], "my-model")
        self.assertEqual(evs[0]["strategy"], "code")

    def test_glow_agents_rejects_bad_strategy(self):
        r = self._run("glow_agents.py", "--agent", "x:m:#fff:5:sai")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("strategy", (r.stderr or "") + (r.stdout or ""))

    def test_any_ai_hook_records_an_event(self):
        r = self._run("retrieval_hook.py", "--agent", "cline",
                      "--model", "test-model", "--query", "tim kiem rule risk",
                      "--hits", "risk.py::stop_loss,strategy.py::rsi_signal",
                      "--ms", "42.5", "--tokens", "300", "--baseline", "4000",
                      "--log", str(self.log))
        self.assertEqual(r.returncode, 0, r.stderr)
        evs = R.read_events(self.log)
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual(e["agent"], "cline")
        self.assertEqual(e["n_hits"], 2)
        self.assertEqual(e["tokens_saved"], 3700)
        self.assertEqual(e["saved_pct"], 92.5)
        self.assertEqual(e["latency_ms"], 42.5)

    def test_hook_dry_writes_nothing(self):
        r = self._run("retrieval_hook.py", "--agent", "gpt", "--query", "x",
                      "--dry", "--log", str(self.log))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.log.exists())
        self.assertIn('"ok": true', r.stdout)


class TestServeGlow(unittest.TestCase):
    """Server live: day tin hieu bang SSE + tu rebuild khi du lieu doi."""

    @classmethod
    def setUpClass(cls):
        import serve_glow as S
        cls.S = S

    def test_broadcast_reaches_every_subscriber(self):
        import queue
        S = self.S
        q = queue.Queue()
        S.SUBS.append(q)
        try:
            S.broadcast("snapshot", {"hello": "world"})
            msg = q.get(timeout=2)
        finally:
            S.SUBS.remove(q)
        self.assertIn("event: snapshot", msg)
        self.assertIn('"hello"', msg)

    def test_dead_subscriber_is_dropped(self):
        import queue
        S = self.S
        q = queue.Queue(maxsize=1)
        S.SUBS.append(q)
        try:
            S.broadcast("a", {"n": 1})
            S.broadcast("b", {"n": 2})          # day day queue -> bi loai
            S.broadcast("c", {"n": 3})
            self.assertNotIn(q, S.SUBS)
        finally:
            if q in S.SUBS:
                S.SUBS.remove(q)

    def test_file_tokens_counts_real_sizes(self):
        ft = self.S.file_tokens(["risk.py"])
        self.assertEqual(ft["risk.py"],
                         max(1, int((ROOT / "risk.py").stat().st_size
                                    * R.TOKENS_PER_CHAR)))
        self.assertNotIn("khong-ton-tai.py",
                         self.S.file_tokens(["khong-ton-tai.py"]))

    def test_build_snapshot_matches_maps_contract(self):
        """Snapshot tu server phai cung contract voi snapshot nhung trong ban do."""
        S = self.S
        tmp = Path(tempfile.mkdtemp(prefix="glow_snap_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        orig = R.SNAPSHOT_PATH
        R.SNAPSHOT_PATH = tmp / "glow_signals.json"
        try:
            snap = S.build_snapshot()
        finally:
            R.SNAPSHOT_PATH = orig
        self.assertEqual(snap["signature"],
                         R.fingerprint({n: (d, l) for n, (d, l, _f)
                                        in R.load_all_docs(ROOT).items()}))
        self.assertEqual(len(snap["agents"]), len(R.AGENTS))
        self.assertIn("byAgent", snap["metrics"])
        self.assertTrue((tmp / "glow_signals.json").exists())
        self.assertEqual(S.STATE["signature"], snap["signature"])

    def test_watch_files_cover_data_and_source(self):
        for name in ("graph_memory.json", "memory_map_data.json",
                     "retrieval_log.jsonl", "glow_retrieval.py"):
            self.assertIn(name, self.S.WATCH_FILES,
                          "thieu %s -> server khong tai tai lieu" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)









