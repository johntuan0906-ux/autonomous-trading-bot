# -*- coding: utf-8 -*-
"""bench_retrieval.py - do toc do TIM KIEM / TRUY XUAT du lieu cua cac ban do.

Do 3 tang cung 1 bo truy van, cung payload glow_map.html:
  py     - glow_retrieval.py  (Python: tooling, build_glow, serve_glow, CLI)
  node   - glow_signals.js    (JS kernel nhung trong CA 2 ban do, chay Node/V8)
  chrome - cung glow_signals.js + bench_core.js tren Chrome THAT (Web page)

Muc do:
  payload parse / docs build / index build (live + offline)
  search p50/p95/max + QPS theo tung chien luoc (fast, code, hybrid, deep, semantic)
  cache hit vs miss (us/op)
  1 vong 5 agent x 7 query: cold / warm + token tiet kiem, cache hit %
  sidebar Search (substring, cham 500 hit)

Chay:  python bench_retrieval.py [--iters 200] [--json out.json] [--no-browser]
"""
from __future__ import annotations

import argparse
import base64
import html as html_mod
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import glow_retrieval as R                                                  # noqa: E402

STRATEGIES = ["fast", "code", "hybrid", "deep", "semantic"]
K_TOP = 12
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def pct(xs, p):
    return R.pct(xs, p)


def stats(xs):
    s = sorted(xs)
    mean = (sum(s) / len(s)) if s else 0.0
    return {"n": len(s), "p50": round(pct(s, 50), 3),
            "p95": round(pct(s, 95), 3),
            "max": round(s[-1], 3) if s else 0.0,
            "mean": round(mean, 3),
            "qps": round(1000.0 / mean, 1) if mean > 0 else 0.0}


def queries():
    from glow_agents import DEFAULT_QUERIES
    return list(DEFAULT_QUERIES)


def load_payload_text(path: Path | None = None) -> str:
    """Chinh payload `const DATA = ...` da nhung trong glow_map.html."""
    p = path or (ROOT / "glow_map.html")
    html = p.read_text(encoding="utf-8")
    line = html.split("const DATA = ", 1)[1].split("\n", 1)[0]
    return line[:-1] if line.endswith(";") else line


def docs_from_payload(ds: dict):
    """Mirror glow_signals_lib.js docsFromDs: id/label/deg/file/kind/tokens."""
    ids = ds.get("id") or []
    labels = ds.get("label") or []
    degs = ds.get("deg") or []
    kinds = ds.get("kinds") or []
    kind = ds.get("kind") or []
    clusters = ds.get("clusters") or []
    cluster = ds.get("cluster") or []
    docs, files, seen = [], [], set()
    for i, nid in enumerate(ids):
        nid = str(nid)
        label = str(labels[i]) if i < len(labels) and labels[i] is not None else nid
        f = ""
        if i < len(cluster) and cluster[i] is not None:
            ci = cluster[i]
            if ci < len(clusters) and clusters[ci] is not None:
                f = str(clusters[ci])
        kk = ""
        if i < len(kind) and kind[i] is not None:
            ki = kind[i]
            if ki < len(kinds) and kinds[ki] and kinds[ki][0] is not None:
                kk = str(kinds[ki][0])
        deg = int(degs[i]) if i < len(degs) and degs[i] else 0
        docs.append({"id": nid, "label": label, "deg": deg, "file": f, "kind": kk,
                     "tokens": max(R.MIN_DOC_TOKENS,
                                   R.estimate_tokens(nid + " " + label))})
        if f and f not in seen:
            seen.add(f)
            files.append(f)
    edges = ds.get("edges") or []
    n = len(ids)
    links = [(edges[i], edges[i + 1]) for i in range(0, len(edges) - 3, 4)
             if 0 <= edges[i] < n and 0 <= edges[i + 1] < n]
    return docs, links, files


def sidebar_scan(docs, q: str):
    """Giong o Search sidebar: lower + substring, cham khi du 500 hit."""
    ql = q.lower()
    hit = 0
    for d in docs:
        if ql in d["label"].lower() or ql in d["id"].lower():
            hit += 1
            if hit >= 500:
                break
    return hit


def round_bench(ix, agents, qs, ds_name):
    """3 lan chay (cold / warm / metrics) giong bench_core.js roundBench."""
    cache, tuner = R.Cache(256), R.Tuner()
    per, t0 = [], time.perf_counter()
    for a in agents:
        a0 = time.perf_counter()
        for q in qs:
            R.run_agent(ix, a, q, cache, tuner, ds_name, rund=1)
        per.append({"id": a["id"],
                    "coldMs": round((time.perf_counter() - a0) * 1000, 2)})
    cold = round((time.perf_counter() - t0) * 1000, 2)
    warm_evs, t1 = [], time.perf_counter()
    for a in agents:
        for q in qs:
            warm_evs.append(R.run_agent(ix, a, q, cache, tuner, ds_name, rund=2))
    warm = round((time.perf_counter() - t1) * 1000, 2)
    # metrics tinh tren vong WARM de chi so cache_hit% / tiet kiem that su
    return {"agents": len(agents), "queries": len(qs), "coldMs": cold,
            "warmMs": warm, "perAgent": per,
            "totals": R.metrics(warm_evs)["totals"]}


def bench_python(payload_text: str, qs, iters: int) -> dict:
    """Tang Python: parse payload -> docs -> index -> search/cache/round."""
    t0 = time.perf_counter()
    payload = json.loads(payload_text)
    res = {"engine": "py", "ver": R.LIB_VERSION,
           "payloadMs": round((time.perf_counter() - t0) * 1000, 2),
           "datasets": []}
    all_files = {}
    for ds in payload["datasets"]:
        tD = time.perf_counter()
        docs, links, files = docs_from_payload(ds)
        docsMs = round((time.perf_counter() - tD) * 1000, 2)
        for f in files:
            if f not in all_files:
                all_files[f] = R._file_tokens(ROOT, f)
        ft = {f: all_files[f] for f in files if all_files[f]}
        tL = time.perf_counter()
        ix_live = R.Index(docs, links, dict(ft), name=ds.get("name", "ds"))
        idxLiveMs = round((time.perf_counter() - tL) * 1000, 2)
        tO = time.perf_counter()
        ix_off = R.Index(docs, links, {}, name=ds.get("name", "ds"))
        idxOffMs = round((time.perf_counter() - tO) * 1000, 2)
        d_out = {"name": ds.get("name"), "nodes": len(docs), "edges": len(links),
                 "docsMs": docsMs, "idxLiveMs": idxLiveMs, "idxOffMs": idxOffMs,
                 "search": {}}
        for st in STRATEGIES:
            lat, hits = [], 0
            B = 10   # do theo LO de khong bi anh huong do phan giai timer
            for i in range(iters):
                q = qs[i % len(qs)]
                a = time.perf_counter()
                for _ in range(B):
                    r = ix_live.search(q, k=K_TOP, strategy=st)
                lat.append((time.perf_counter() - a) * 1000 / B)
                hits += len(r["hits"])
            s_live = ix_live.search(qs[0], k=K_TOP, strategy=st)["cost"]
            s_off = ix_off.search(qs[0], k=K_TOP, strategy=st)["cost"]
            d_out["search"][st] = stats(lat)
            d_out["search"][st]["hitsAvg"] = round(hits / iters, 2)
            d_out["search"][st]["savedLivePct"] = s_live["pct"]
            d_out["search"][st]["savedOffPct"] = s_off["pct"]
        c = R.Cache(64)
        tM = time.perf_counter()
        for i in range(2000):
            c.get("absent|%d" % (i & 31), 1000)
        miss_us = (time.perf_counter() - tM) * 1e6 / 2000
        c.put("ck", {"v": 1}, 1000, 10 ** 9)
        tH = time.perf_counter()
        for i in range(2000):
            c.get("ck", 1000)
        hit_us = (time.perf_counter() - tH) * 1e6 / 2000
        d_out["cache"] = {"missUs": round(miss_us, 2), "hitUs": round(hit_us, 2)}
        d_out["round"] = round_bench(ix_live, [dict(a) for a in R.AGENTS], qs,
                                     ds.get("name", "ds"))
        s_lat = []
        for i in range(min(iters, 300)):
            qy = qs[i % len(qs)].split(" ")[0].lower()
            if len(qy) < 2:
                qy = "mem"
            b = time.perf_counter()
            sidebar_scan(docs, qy)
            s_lat.append((time.perf_counter() - b) * 1000)
        d_out["sidebar"] = stats(s_lat)
        res["datasets"].append(d_out)
    return res


def bench_tooling(qs) -> dict:
    """Startup cua tooling Python: doc 2 file JSON du lieu + dung chi muc."""
    t0 = time.perf_counter()
    all_docs = R.load_all_docs(ROOT)
    load_ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    indices = R.build_indices(all_docs)
    build_ms = (time.perf_counter() - t1) * 1000
    lat = []
    for _ in range(50):
        a = time.perf_counter()
        for ix in indices.values():
            ix.search(qs[0], k=K_TOP, strategy="fast")
        lat.append((time.perf_counter() - a) * 1000)
    return {"loadDocsMs": round(load_ms, 2), "buildIdxMs": round(build_ms, 2),
            "bothIdxSearchMs": stats(lat),
            "datasets": {n: {"nodes": len(d), "edges": len(l)}
                         for n, (d, l, _f) in all_docs.items()}}


def bench_input(payload_text: str, qs, iters: int) -> dict:
    """Dau vao giong nhau cho node + chrome."""
    payload = json.loads(payload_text)
    files = set()
    for ds in payload["datasets"]:
        _, _, fs = docs_from_payload(ds)
        files.update(fs)
    ft = {f: R._file_tokens(ROOT, f) for f in sorted(files)}
    ft = {f: v for f, v in ft.items() if v}
    return {"payloadText": payload_text, "queries": qs,
            "strategies": STRATEGIES, "iters": iters, "fileTokens": ft}


NODE_RUNNER = r"""
'use strict';
const fs = require('fs');
const path = require('path');
const GS = require(path.join(__dirname, 'glow_signals.js'));
const GB = require(path.join(__dirname, 'bench_core.js'));
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = GB.run(input);
fs.writeFileSync(process.argv[3], JSON.stringify(out));
"""


def bench_node(payload_text: str, qs, iters: int) -> dict | None:
    """Chay kernel JS dung nhu 2 ban do dang nhung (Node/V8)."""
    if not shutil.which("node"):
        return None
    tmp = Path(tempfile.mkdtemp(prefix="glow_bench_"))
    try:
        for name in ("glow_signals.js", "bench_core.js"):
            shutil.copy(ROOT / name, tmp / name)
        (tmp / "_run.js").write_text(NODE_RUNNER, encoding="utf-8")
        inp = tmp / "in.json"
        out = tmp / "out.json"
        inp.write_text(json.dumps(bench_input(payload_text, qs, iters),
                                  ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(["node", str(tmp / "_run.js"), str(inp), str(out)],
                           capture_output=True, text=True, cwd=str(tmp),
                           timeout=300)
        if r.returncode != 0 or not out.exists():
            print("[warn] node bench loi: %s" % (r.stderr or r.stdout)[:500])
            return None
        j = json.loads(out.read_text(encoding="utf-8"))
        j["engine"] = "node"
        return j
    finally:
        shutil.rmtree(tmp, True)


BROWSER_RUNNER_TMPL = r"""<!doctype html>
<meta charset="utf-8"><title>BENCH_RUNNING</title>
<script>__GS__</script>
<script>__GB__</script>
<pre id="out" style="white-space:pre-wrap"></pre>
<script>
(function(){
  var input = __INPUT__;
  try {
    var res = GB.run(input);
    res.engine = 'chrome';
    document.getElementById('out').textContent =
      'BENCH_B64:' + btoa(unescape(encodeURIComponent(JSON.stringify(res))));
    document.title = 'BENCH_DONE';
  } catch (e){
    document.getElementById('out').textContent = 'BENCH_ERR: ' + (e && e.message);
    document.title = 'BENCH_ERR';
  }
})();
</script>
"""


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return shutil.which("chrome") or shutil.which("msedge")


def bench_chrome(payload_text: str, qs, iters: int) -> dict | None:
    """Chay CUNG kernel + payload tren Chrome that (Web page), doc ket qua."""
    exe = find_chrome()
    if not exe:
        return None
    tmp = Path(tempfile.mkdtemp(prefix="glow_bench_web_"))
    try:
        page = (BROWSER_RUNNER_TMPL
                .replace("__GS__", (ROOT / "glow_signals.js").read_text(encoding="utf-8"))
                .replace("__GB__", (ROOT / "bench_core.js").read_text(encoding="utf-8"))
                .replace("__INPUT__",
                         json.dumps(bench_input(payload_text, qs, iters),
                                    ensure_ascii=False)))
        page_path = tmp / "bench.html"
        page_path.write_text(page, encoding="utf-8")
        r = subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--no-sandbox",
             "--allow-file-access-from-files", "--enable-precise-timer-info",
             "--virtual-time-budget=20000", "--dump-dom",
             page_path.as_uri()],
            capture_output=True, text=True, timeout=120, cwd=str(tmp))
        dom = r.stdout or ""
        m_pre = re.search(r'<pre id="out"[^>]*>([\s\S]*?)</pre>', dom)
        content = html_mod.unescape(m_pre.group(1)).strip() if m_pre else ""
        if content.startswith("BENCH_ERR"):
            print("[warn] chrome bench loi: %s" % content[:200])
            return None
        m = re.match(r"BENCH_B64:([A-Za-z0-9+/=]+)", content)
        if not m:
            mt = re.search(r"<title>([^<]*)</title>", dom)
            print("[warn] chrome khong tra ve ket qua; title=%s; pre=%.120s"
                  % (mt.group(1) if mt else "?", content or "(trang)"))
            return None
        raw = base64.b64decode(m.group(1)).decode("utf-8")
        j = json.loads(raw)
        j["engine"] = "chrome"
        return j
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        print("[warn] chrome bench that bai: %s" % e)
        return None
    finally:
        shutil.rmtree(tmp, True)


# ── Bao cao ─────────────────────────────────────────────────────────────────
def _fmt(v, nd=2):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def print_report(meta, tooling, results, qs, iters):
    W = 96
    print("=" * W)
    print("BENCH TRUY XUAT DU LIEU BAN DO  |  %d iters/strategy  |  %d queries  "
          "|  k=%d" % (iters, len(qs), K_TOP))
    print("=" * W)
    print("Queries: " + ", ".join(qs))
    engs = [e for e in ("py", "node", "chrome") if results.get(e)]
    print("Engine : " + ", ".join(
        "%s(%s)" % (e, results[e].get("ver", "?")) for e in engs))

    print("\n-- STARTUP TOOLING PYTHON (glow_agents / serve_glow / build_glow) --")
    print("  nap du lieu 2 file JSON : %8.2f ms" % tooling["loadDocsMs"])
    print("  dung chi muc nghich      : %8.2f ms" % tooling["buildIdxMs"])
    for n, d in tooling["datasets"].items():
        print("    %-14s %4d nodes / %5d edges" % (n, d["nodes"], d["edges"]))

    print("\n-- PARSE + DUNG INDEX (payload nhung trong ban do) --")
    hdr = "%-16s %-11s %10s %10s %10s %10s"
    print(hdr % ("dataset", "engine", "parseMs", "docsMs", "idxLiveMs", "idxOffMs"))
    n_ds = len(results[engs[0]]["datasets"]) if engs else 0
    for di in range(n_ds):
        for e in engs:
            d = results[e]["datasets"][di]
            print(hdr % (d["name"] if e == engs[0] else "", e,
                         _fmt(results[e]["payloadMs"]),
                         _fmt(d["docsMs"]), _fmt(d["idxLiveMs"]),
                         _fmt(d["idxOffMs"])))
        print()

    print("-- TIM KIEM (search) p50/p95 ms [QPS] + hit TB + token tiet kiem --")
    hdr2 = "%-16s %-8s %18s %18s %18s  %6s %7s"
    print(hdr2 % ("dataset", "strategy", "py p50/p95 [QPS]", "node p50/p95 [QPS]",
                  "chrome p50/p95 [QPS]", "hits", "saved%"))
    fixed = [e for e in ("py", "node", "chrome") if results.get(e)]
    for di in range(n_ds):
        name = results[engs[0]]["datasets"][di]["name"]
        for st in STRATEGIES:
            cells = []
            for e in ("py", "node", "chrome"):
                s = (results[e]["datasets"][di]["search"].get(st)
                     if results.get(e) else None)
                cells.append("%s/%s [%s]" % (_fmt(s["p50"], 3), _fmt(s["p95"], 3),
                                             _fmt(s["qps"], 0)) if s else "-")
            ref = results[engs[0]]["datasets"][di]["search"].get(st, {})
            print(hdr2 % (name if st == STRATEGIES[0] else "", st,
                          *(cells + [_fmt(ref.get("hitsAvg")),
                                     _fmt(ref.get("savedLivePct"), 1)])))
        print()

    print("-- CACHE LRU+TTL (us/op) + SIDEBAR SEARCH (o Search) --")
    hdr3 = "%-16s %-8s %12s %12s %14s %14s"
    print(hdr3 % ("dataset", "engine", "missUs", "hitUs", "sidebar p50ms",
                  "sidebar QPS"))
    for di in range(n_ds):
        for e in engs:
            d = results[e]["datasets"][di]
            print(hdr3 % (d["name"] if e == engs[0] else "", e,
                          _fmt(d["cache"]["missUs"]), _fmt(d["cache"]["hitUs"]),
                          _fmt(d["sidebar"]["p50"], 3),
                          _fmt(d["sidebar"]["qps"], 0)))
        print()

    print("-- 1 VONG 5 AGENT x %d QUERY (nhan Q trong ban do) --" % len(qs))
    hdr4 = "%-16s %-8s %10s %10s %11s %11s %10s"
    print(hdr4 % ("dataset", "engine", "coldMs", "warmMs", "tietKiem%",
                  "cacheHit%", "savedTok"))
    for di in range(n_ds):
        for e in engs:
            d = results[e]["datasets"][di]
            r = d["round"]
            t = r["totals"]
            print(hdr4 % (d["name"] if e == engs[0] else "", e,
                          _fmt(r["coldMs"]), _fmt(r["warmMs"]),
                          _fmt(t.get("saved_pct"), 1),
                          _fmt(t.get("cache_hit_pct"), 1), _fmt(t.get("saved"))))
        print()

    print("-- 5 AGENT RIENG (chi tang %s, cold) --" % engs[0])
    for di in range(n_ds):
        d = results[engs[0]]["datasets"][di]
        print("  %s:" % d["name"])
        for pa in d["round"]["perAgent"]:
            ag = next((a for a in R.AGENTS if a["id"] == pa["id"]), {})
            print("    %-8s %8.2f ms / %d query  (ngan sach %s ms)"
                  % (pa["id"], pa["coldMs"], len(qs), ag.get("ms_budget", "?")))
        print()

    print("-- CHI PHI TOKEN TRA VE vs DOC NGUYEN FILE (query %r) --" % qs[0])
    hdr5 = "%-16s %-10s %10s %10s %12s"
    print(hdr5 % ("dataset", "strategy", "live%", "offline%", "hits"))
    for di in range(n_ds):
        d = results[engs[0]]["datasets"][di]
        for st in STRATEGIES:
            s = d["search"][st]
            print(hdr5 % (d["name"] if st == STRATEGIES[0] else "", st,
                          _fmt(s["savedLivePct"], 1), _fmt(s["savedOffPct"], 1),
                          _fmt(s["hitsAvg"])))
        print()
    print("=" * W)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Do toc do tim kiem/truy xuat ban do.")
    ap.add_argument("--iters", type=int, default=200,
                    help="so lan search moi chien luoc (mac dinh 200)")
    ap.add_argument("--json", default="", help="ghi ket qua JSON ra file")
    ap.add_argument("--no-browser", action="store_true",
                    help="khong chay Chrome headless")
    ap.add_argument("--no-node", action="store_true", help="khong chay Node")
    args = ap.parse_args(argv)

    qs = queries()
    payload_text = load_payload_text()
    print("[1/4] bench Python ...", flush=True)
    py_res = bench_python(payload_text, qs, args.iters)
    tooling = bench_tooling(qs)
    results = {"py": py_res, "node": None, "chrome": None}
    if not args.no_node:
        print("[2/4] bench Node (kernel JS nhung trong ban do) ...", flush=True)
        results["node"] = bench_node(payload_text, qs, args.iters)
    if not args.no_browser:
        print("[3/4] bench Chrome headless (web that) ...", flush=True)
        results["chrome"] = bench_chrome(payload_text, qs, args.iters)
    print("[4/4] bao cao\n", flush=True)

    meta = {"iters": args.iters, "queries": qs, "k": K_TOP,
            "strategies": STRATEGIES,
            "engines": [e for e in results if results[e]]}
    print_report(meta, tooling, results, qs, args.iters)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"meta": meta, "tooling": tooling, "results": results},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("[out] %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





