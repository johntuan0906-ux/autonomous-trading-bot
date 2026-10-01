# -*- coding: utf-8 -*-
"""glow_retrieval.py - loi truy xuat + do luong token cho cac "agent AI" tren ban do.

Vai tro trong he thong (dung chung cho CA hai ban do Canvas2D + WebGL):
  - Xay chi muc nghich (inverted index) tu du lieu THAT cua cac ban do
    (graph_memory.json / memory_map_data.json).
  - Chay truy xuat theo nhieu "model agent" khac nhau (scout/analyst/coder/auditor/
    oracle - moi agent 1 model, 1 chien luoc, 1 ngan sach ms/token rieng).
  - Do THAT: thoi gian (ms), so token tra ve, token TIET KIEM so voi doc nguyen file,
    ty le cache hit, chi phi $. Bo dieu chinh (Tuner) tu ha `k`/`beam` khi p95 vuot
    ngan sach -> "toi uu toc do" co so lieu chu khong phai khau hieu.
  - Ghi moi lan truy xuat = 1 dong JSONL (`retrieval_log.jsonl`) -> moi agent/IDE/tool
    (Cline, GPT, Claude, Qwen, DeepSeek...) deu ghi/cham vao cung mot dong su kien.
  - Xuat `glow_signals.json` (snapshot) de build_glow.py nhung vao CA HAI ban do,
    nen 2 ban do luon hien dung cung mot tin hieu (dong bo).

Khong dung thu vien ngoai (chi stdlib) -> chay duoc o moi may, khong CDN.
Quy uoc token: 1 token ~ 4 ky tu (uoc luong chuan cho code/van ban tieng Anh).

Vi du:
  python glow_agents.py --rounds 2 --queries "risk,layout,memory"        # chay agent
  python glow_agents.py --export glow_signals.json                       # xuat snapshot
  python retrieval_hook.py --agent cline --model claude-sonnet-4.5 ^
         --query "stop loss" --hits risk.py::check --ms 320 --tokens 900
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TOKENS_PER_CHAR = 0.25          # 1 token ~ 4 ky tu
RECORD_TOKENS = 140             # 1 ban ghi ky uc (khong co file tren dia)
MIN_DOC_TOKENS = 8              # san chi phi cho 1 snippet tra ve
SNIPPET_CHARS = 160             # do dai snippet agent doc duoc

LOG_PATH = ROOT / "retrieval_log.jsonl"
SNAPSHOT_PATH = ROOT / "glow_signals.json"
LIB_VERSION = "1.0"

DATASETS = [
    ("Graph Memory", ROOT / "graph_memory.json"),
    ("Memory Map", ROOT / "memory_map_data.json"),
]

# ── Doi agent: moi model 1 chien luoc + ngan sach rieng (chinh duoc tu CLI/UI) ──
AGENTS = [
    {"id": "scout", "label": "Scout", "model": "gpt-4o-mini", "provider": "OpenAI",
     "color": "#22d3ee", "tier": "fast", "strategy": "fast", "k": 8, "beam": 1,
     "ms_budget": 45, "token_budget": 900, "cache_ttl_ms": 90_000,
     "price_in": 0.15, "price_out": 0.60,
     "note": "quet nhanh, top-K nho, uu tien do tre thap"},
    {"id": "analyst", "label": "Analyst", "model": "claude-3.5-sonnet", "provider": "Anthropic",
     "color": "#a855f7", "tier": "deep", "strategy": "deep", "k": 20, "beam": 2,
     "ms_budget": 120, "token_budget": 2600, "cache_ttl_ms": 180_000,
     "price_in": 3.0, "price_out": 15.0,
     "note": "2 buoc lan can (2-hop), doc sau, dat token hon"},
    {"id": "coder", "label": "Coder", "model": "qwen3-coder", "provider": "Alibaba",
     "color": "#fbbf24", "tier": "code", "strategy": "code", "k": 12, "beam": 1,
     "ms_budget": 70, "token_budget": 1500, "cache_ttl_ms": 120_000,
     "price_in": 0.30, "price_out": 1.20,
     "note": "tach identifier (snake/camel), khop tien to ten ham/bien"},
    {"id": "auditor", "label": "Auditor", "model": "deepseek-v3", "provider": "DeepSeek",
     "color": "#34d399", "tier": "verify", "strategy": "hybrid", "k": 16, "beam": 1,
     "ms_budget": 100, "token_budget": 2000, "cache_ttl_ms": 150_000,
     "price_in": 0.27, "price_out": 1.10,
     "note": "1 buoc lan can (1-hop) de doi chieu bang chung"},
    {"id": "oracle", "label": "Oracle", "model": "bge-m3-embed", "provider": "local",
     "color": "#e2e8f0", "tier": "index", "strategy": "semantic", "k": 24, "beam": 1,
     "ms_budget": 60, "token_budget": 3200, "cache_ttl_ms": 300_000,
     "price_in": 0.02, "price_out": 0.02,
     "note": "khop mo (tien to/chuoi con) - thay cho embedding, chay offline"},
]
AGENT_BY_ID = {a["id"]: a for a in AGENTS}

# ── Token / tokenize (giong het ban JS: glow_signals.js) ────────────────────
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def estimate_tokens(text: str) -> int:
    """Uoc luong token = ceil(len/4), toi thieu 1."""
    return max(1, int(math.ceil(len(str(text)) * TOKENS_PER_CHAR)))


def tokenize(text: str) -> list[str]:
    """Tach tu kieu code: snake_case, camelCase, so, va giu ca token ghep."""
    out: list[str] = []
    for raw in _WORD.findall(str(text)):
        bits: list[str] = []
        for seg in raw.split("_"):
            if seg:
                bits.extend(_CAMEL.split(seg))
        for b in bits:
            b = b.lower()
            if len(b) >= 2 or b.isdigit():
                out.append(b)
        if len(bits) > 1:
            out.append(raw.lower())        # "memory_graph" -> giu lai ca cum
    return out


def norm_query(q: str) -> str:
    """Chuan hoa query de lam key cache (on dinh giua cac lan goi)."""
    return " ".join(sorted(set(tokenize(q)))) or str(q).strip().lower()


# ── Nguon du lieu: doc node/edge that tu JSON cua ban do ───────────────────
def _file_tokens(root: Path, rel) -> int:
    if not rel:
        return 0
    p = Path(str(rel))
    if not p.is_absolute():
        p = root / str(rel)
    try:
        if p.is_file():
            return max(1, int(math.ceil(p.stat().st_size * TOKENS_PER_CHAR)))
    except OSError:
        pass
    return 0


def load_docs(path, root=None):
    """Doc 1 file du lieu ban do -> (docs, links) voi deg + chi phi token tung node."""
    root = root or ROOT
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_nodes = data.get("nodes", [])
    idx_of = {}
    docs = []
    for nd in raw_nodes:
        nid = str(nd.get("id"))
        if nid in idx_of:
            continue
        idx_of[nid] = len(docs)
        label = str(nd.get("label") or nid)
        docs.append({"id": nid, "label": label,
                     "kind": str(nd.get("type") or nd.get("kind") or "unknown"),
                     "file": nd.get("file"),
                     "deg": 0,
                     "tokens": max(MIN_DOC_TOKENS, estimate_tokens(nid + " " + label))})
    links = []
    for l in data.get("links") or data.get("edges") or []:
        si = idx_of.get(str(l.get("source")))
        ti = idx_of.get(str(l.get("target")))
        if si is None or ti is None or si == ti:
            continue
        links.append((si, ti))
        docs[si]["deg"] += 1
        docs[ti]["deg"] += 1
    ftok = {}
    for d in docs:
        f = d["file"]
        if f and f not in ftok:
            ftok[f] = _file_tokens(root, f) or RECORD_TOKENS
    return docs, links, ftok



# ── Chi muc nghich + BM25-lite (khong phu thuoc model ngoai) ───────────────
K1, B_LEN = 1.2, 0.3


class Index:
    """Inverted index + BM25-lite cho 1 dataset cua ban do."""

    def __init__(self, docs, links=None, file_tokens=None, name="dataset"):
        self.name = name
        self.docs = docs
        self.n = len(docs)
        self.file_tokens = file_tokens or {}
        self.df = Counter()
        self.post = {}
        self.tlen = []
        self.ltoks = []
        self.adj = [[] for _ in range(self.n)]
        for i, d in enumerate(docs):
            toks = tokenize(d["id"]) + tokenize(d["label"])
            tf = Counter(toks)
            self.tlen.append(max(1, len(toks)))
            self.ltoks.append(set(tokenize(d["label"])))
            for t, c in tf.items():
                self.df[t] += 1
                self.post.setdefault(t, []).append((i, c))
        self.avg_len = (sum(self.tlen) / self.n) if self.n else 1.0
        for s, t in (links or []):
            self.adj[s].append(t)
            self.adj[t].append(s)

    def idf(self, t):
        df = self.df.get(t, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def baseline_of(self, i):
        """Token phai doc neu 'doc nguyen file' (naive)."""
        d = self.docs[i]
        f = d.get("file")
        if f:
            return self.file_tokens.get(f) or RECORD_TOKENS
        return RECORD_TOKENS

    def _expand(self, t, strategy, cand):
        """[(doc, tf, he so)]: khop truc tiep / tien to / chuoi con."""
        if strategy == "code" and len(t) >= 3:
            out = [(i, c, 1.0) for i, c in cand]
            for tok, lst in self.post.items():
                if tok != t and tok.startswith(t):
                    out += [(i, c, 0.6) for i, c in lst]
            return out
        if strategy == "semantic" and len(t) >= 4:
            out = [(i, c, 1.0) for i, c in cand]
            for tok, lst in self.post.items():
                if tok != t and t in tok:
                    out += [(i, c, 0.5) for i, c in lst]
            return out
        return [(i, c, 1.0) for i, c in cand]

    def search(self, query, k=10, strategy="fast"):
        """Truy xuat top-K -> dict co hits + chi phi token (that, do tu DL)."""
        scored = {}
        qtoks = tokenize(query)
        for t in qtoks:
            cand = self.post.get(t)
            if not cand:
                continue
            idf = self.idf(t)
            for i, tf, mul in self._expand(t, strategy, cand):
                dl = self.tlen[i]
                bm = (tf * (K1 + 1)) / (tf + K1 * (1 - B_LEN + B_LEN * dl / self.avg_len))
                s = idf * bm * mul
                if t in self.ltoks[i]:
                    s *= 1.6
                s *= 1 + 0.12 * math.log1p(self.docs[i]["deg"])
                scored[i] = scored.get(i, 0.0) + s
        if strategy in ("hybrid", "deep") and scored:
            base = dict(scored)
            seeds = sorted(base, key=lambda i: -base[i])[:8]
            for s in seeds:
                for t in self.adj[s]:
                    if t not in scored:
                        scored[t] = base[s] * 0.35
            if strategy == "deep":
                seeds2 = sorted(scored, key=lambda i: -scored[i])[:12]
                for s in seeds2:
                    for t in self.adj[s]:
                        if t not in scored:
                            scored[t] = scored[s] * 0.15
        order = sorted(scored.items(),
                       key=lambda kv: (-kv[1], -self.docs[kv[0]]["deg"],
                                       self.docs[kv[0]]["id"]))
        hits = order[:max(1, k)]
        out = [{"i": i, "id": self.docs[i]["id"], "label": self.docs[i]["label"],
                "file": self.docs[i].get("file") or "", "deg": self.docs[i]["deg"],
                "score": round(float(s), 4)} for i, s in hits]
        return {"hits": out, "scored": len(scored), "qtokens": len(qtoks),
                "cost": cost_of(self, out)}

    def __repr__(self):
        return "<Index %s n=%d terms=%d>" % (self.name, self.n, len(self.post))


def cost_of(ix, hits):
    """(token tra ve, token khi doc nguyen file, token tiet kiem)."""
    returned = sum(max(MIN_DOC_TOKENS, ix.docs[h["i"]]["tokens"]) for h in hits)
    files, baseline = set(), 0
    for h in hits:
        key = h.get("file") or ("mem:" + h["id"])
        if key in files:
            continue
        files.add(key)
        baseline += ix.baseline_of(h["i"])
    saved = max(0, baseline - returned)
    return {"returned": returned, "baseline": baseline, "saved": saved,
            "pct": (round(100.0 * saved / baseline, 1) if baseline else 0.0),
            "files": len(files)}




def load_all_docs(root=None):
    """Nap tat ca dataset ban do -> {name: (docs, links, fileTokens)}."""
    root = root or ROOT
    out = {}
    for name, path in DATASETS:
        p = Path(path)
        if p.exists():
            docs, links, ftok = load_docs(p, root)
            out[name] = (docs, links, ftok)
    return out


def build_indices(all_docs):
    """{name: Index} san sang truy xuat."""
    return {name: Index(docs, links, ftok, name=name)
            for name, (docs, links, ftok) in all_docs.items()}


# ── Cache LRU + TTL: "truy xuat nhanh" (lan 2 ~0 ms) ───────────────────────
class Cache:
    def __init__(self, maxsize=256):
        self.store = OrderedDict()
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def get(self, key, now_ms):
        ent = self.store.get(key)
        if not ent:
            self.misses += 1
            return None
        if ent["exp"] < now_ms:
            del self.store[key]
            self.misses += 1
            return None
        self.store.move_to_end(key)
        self.hits += 1
        return ent["val"]

    def put(self, key, val, now_ms, ttl_ms):
        self.store[key] = {"val": val, "exp": now_ms + ttl_ms}
        self.store.move_to_end(key)
        while len(self.store) > self.maxsize:
            self.store.popitem(last=False)

    def stats(self):
        tot = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "size": len(self.store),
                "hit_pct": round(100.0 * self.hits / tot, 1) if tot else 0.0}

    def clear(self):
        self.store.clear()
        self.hits = self.misses = 0


# ── Tuner: tu ha k/beam khi p95 vuot ngan sach ms ("toi uu toc do") ─────────
class Tuner:
    def __init__(self, window=12):
        self.window = window
        self.state = {}       # agent_id -> {k, beam, hist:[ms], tuned:int}

    def init(self, agent):
        st = self.state.get(agent["id"])
        if not st:
            st = {"k": agent["k"], "beam": agent["beam"], "hist": [], "tuned": 0}
            self.state[agent["id"]] = st
        return st

    def adapt(self, agent, ms, cache_hit):
        """Tra ve (k_moi, beam_moi, da_dieu_chinh). Quy tac on dinh, khong dao dong."""
        st = self.init(agent)
        st["hist"].append(float(ms))
        st["hist"] = st["hist"][-self.window:]
        if len(st["hist"]) < 4:
            return st["k"], st["beam"], False
        p95 = pct(st["hist"], 95)
        top = agent.get("ms_budget", 60)
        kk, bb = st["k"], st["beam"]
        if p95 > top and kk > 4:
            kk = max(4, kk - 2)
            bb = max(1, bb - 1)
        elif p95 < 0.5 * top and cache_hit and kk < agent["k"]:
            kk = min(agent["k"], kk + 1)
        done = (kk, bb) != (st["k"], st["beam"])
        if done:
            st["k"], st["beam"] = kk, bb
            st["tuned"] += 1
        return kk, bb, done

    def snapshot(self):
        return {aid: {"k": s["k"], "beam": s["beam"], "tuned": s["tuned"],
                      "p95_ms": round(pct(s["hist"], 95), 2) if s["hist"] else 0.0}
                for aid, s in self.state.items()}


def pct(xs, p):
    """Percentile tuyen tinh, xs khong rong."""
    s = sorted(xs)
    if len(s) == 1:
        return float(s[0])
    r = (len(s) - 1) * (p / 100.0)
    lo, hi = int(r), min(len(s) - 1, int(r) + 1)
    return float(s[lo] + (s[hi] - s[lo]) * (r - lo))


def run_agent(ix, agent, query, cache, tuner, dataset, rund=1, now=None,
              force_miss=False):
    """Chay 1 luot truy xuat THAT -> event dict (ghi duoc ra JSONL)."""
    now = time.time() if now is None else now
    t0 = time.perf_counter()
    st = tuner.init(agent)
    key = "%s|%s|%s|%d" % (agent["id"], dataset, norm_query(query), st["k"])
    hit = None if force_miss else cache.get(key, _ms(now))
    if hit is not None:
        res, cached = dict(hit), True
    else:
        res = ix.search(query, k=st["k"], strategy=agent.get("strategy", "fast"))
        cached = False
        cache.put(key, res, _ms(now), agent.get("cache_ttl_ms", 120_000))
    # ngan sach token cua agent: cat bot hits vuot budget (that, thay duoc)
    kept, used = [], 0
    for h in res["hits"]:
        c = max(MIN_DOC_TOKENS, ix.docs[h["i"]]["tokens"])
        if used + c > agent.get("token_budget", 10 ** 9):
            break
        kept.append(h)
        used += c
    trunc = len(kept) < len(res["hits"])
    res2 = dict(res, hits=kept)
    res2["cost"] = cost_of(ix, kept)
    ms = (time.perf_counter() - t0) * 1000.0
    k2, beam2, tuned = tuner.adapt(agent, ms, cached)
    tok_in = res2["cost"]["returned"]
    cost = tok_in / 1e6 * (agent.get("price_in", 0) + agent.get("price_out", 0)) / 2
    return {"t": round(now, 3), "agent": agent["id"], "model": agent["model"],
            "query": query, "dataset": dataset, "round": rund,
            "k": st["k"], "beam": st["beam"], "strategy": agent.get("strategy", "fast"),
            "hits": [{"id": h["id"], "file": h["file"], "score": h["score"]} for h in kept],
            "n_hits": len(kept), "scored": res["scored"],
            "latency_ms": round(ms, 2), "cache": cached,
            "tokens_returned": res2["cost"]["returned"],
            "tokens_baseline": res2["cost"]["baseline"],
            "tokens_saved": res2["cost"]["saved"], "saved_pct": res2["cost"]["pct"],
            "files_touched": res2["cost"]["files"],
            "cost_usd": round(cost, 6), "truncated": trunc,
            "tuned": tuned, "k_after": k2, "beam_after": beam2, "ok": True}


def _ms(t):
    return t * 1000.0



# ── Do luong tong hop: p50/p95, token tiet kiem, cache, $ ("chuyen nghiep") ─
def metrics(events):
    """events (list event dict) -> {byAgent, totals}."""
    by = {}
    for e in events:
        if not e.get("ok", True):
            continue
        a = by.setdefault(e["agent"], {"ms": [], "ret": 0, "base": 0, "saved": 0,
                                       "cache": 0, "runs": 0, "cost": 0.0,
                                       "tuned": 0, "trunc": 0, "hits": 0,
                                       "model": e.get("model", "")})
        a["ms"].append(float(e.get("latency_ms", 0)))
        a["ret"] += e.get("tokens_returned", 0)
        a["base"] += e.get("tokens_baseline", 0)
        a["saved"] += e.get("tokens_saved", 0)
        a["cache"] += 1 if e.get("cache") else 0
        a["runs"] += 1
        a["cost"] += e.get("cost_usd", 0)
        a["tuned"] += 1 if e.get("tuned") else 0
        a["trunc"] += 1 if e.get("truncated") else 0
        a["hits"] += e.get("n_hits", 0)
    out = {}
    for aid, a in by.items():
        ms = a["ms"] or [0.0]
        bud = AGENT_BY_ID.get(aid, {}).get("ms_budget", 60)
        p95 = pct(ms, 95)
        out[aid] = {"model": a["model"], "runs": a["runs"],
                    "p50_ms": round(pct(ms, 50), 2), "p95_ms": round(p95, 2),
                    "ms_budget": bud,
                    "speed": min(200, round(100 * bud / max(p95, 0.05))),
                    "tokens_returned": a["ret"], "tokens_baseline": a["base"],
                    "tokens_saved": a["saved"],
                    "saved_pct": round(100.0 * a["saved"] / a["base"], 1) if a["base"] else 0.0,
                    "cache_hit_pct": round(100.0 * a["cache"] / a["runs"], 1),
                    "cost_usd": round(a["cost"], 6), "tuned": a["tuned"],
                    "truncated": a["trunc"], "hits": a["hits"]}
    tot = {"runs": 0, "ret": 0, "base": 0, "saved": 0, "cost": 0.0, "cache": 0}
    for a in by.values():
        tot["runs"] += a["runs"]
        tot["ret"] += a["ret"]
        tot["base"] += a["base"]
        tot["saved"] += a["saved"]
        tot["cost"] += a["cost"]
        tot["cache"] += a["cache"]
    tot["cost"] = round(tot["cost"], 6)
    tot["saved_pct"] = round(100.0 * tot["saved"] / tot["base"], 1) if tot["base"] else 0.0
    tot["cache_hit_pct"] = round(100.0 * tot["cache"] / tot["runs"], 1) if tot["runs"] else 0.0
    return {"byAgent": out, "totals": tot}


# ── Chu ky du lieu (2 ban do dong bo theo signature) ────────────────────────
def fingerprint(all_docs):
    """all_docs = {name: (docs, links)} -> chuoi ngan duy nhat cho bo du lieu."""
    h = hashlib.sha1()
    for name in sorted(all_docs):
        docs, links = all_docs[name][0], all_docs[name][1]
        h.update(("%s|%d|%d|" % (name, len(docs), len(links))).encode())
        h.update("|".join(d["id"] for d in docs[:2000]).encode("utf-8", "ignore"))
        h.update(str(sum(d["deg"] for d in docs)).encode())
    return h.hexdigest()[:12]


def append_event(path, ev):
    """Ghi 1 event vao log JSONL (thread/process-safe o muc append)."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def read_events(path, limit=400):
    """Doc N event cuoi (bo dong loi, khong chet ca ham)."""
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return out[-limit:] if limit else out


def snapshot(events, agents, datasets_info, sig, queries=None, cache=None, tuner=None):
    """Goi snapshot nhung vao CA HAI ban do (dong bo tin hieu)."""
    m = metrics(events)
    return {"lib": LIB_VERSION, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                           time.gmtime()),
            "signature": sig, "agents": agents, "datasets": datasets_info,
            "queries": queries or [], "metrics": m,
            "events": events[-120:],
            "cache": (cache.stats() if cache else {}),
            "tuning": (tuner.snapshot() if tuner else {})}
