# -*- coding: utf-8 -*-
"""glow_agents.py - chay dong loat nhieu "model agent" tren du lieu that cua ban do.

Moi agent co model + chien luoc + ngan sach ms/token rieng (xem AGENTS trong
glow_retrieval.py). Ket qua duoc do THAT (ms, token tra ve/tiet kiem, cache hit,
$) va ghi ra retrieval_log.jsonl -> 2 ban do hien thi cung tin hieu.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time

import glow_retrieval as R

DEFAULT_QUERIES = ["risk stop loss", "layout 3d", "memory agent", "rsi signal",
                   "backtest pnl", "satellite cross link", "bloom pass"]


def parse_custom_agent(spec):
    """name:model:color:k:strategy -> agent dict (them agent/model moi tu CLI)."""
    parts = str(spec).split(":")
    if len(parts) != 5:
        raise ValueError("agent dang name:model:color:k:strategy, nhan: %r" % spec)
    name, model, color, k, strategy = parts
    if strategy not in ("fast", "code", "hybrid", "deep", "semantic"):
        raise ValueError("strategy khong hop le: %r" % strategy)
    return {"id": name, "label": name.capitalize(), "model": model, "provider": "custom",
            "color": color, "tier": "custom", "strategy": strategy, "k": int(k), "beam": 1,
            "ms_budget": 80, "token_budget": 1600, "cache_ttl_ms": 120_000,
            "price_in": 0.5, "price_out": 2.0,
            "note": "agent tuy chinh tu CLI"}


def print_row(e):
    print("  %-8s %-18s q=%-22.22s ms=%7.2f %s hits=%2d ret=%5d base=%7d "
          "saved=%6.1f%% $%.6f%s%s" % (
              e["agent"], e["model"], e["query"], e["latency_ms"],
              "HIT " if e["cache"] else "miss", e["n_hits"],
              e["tokens_returned"], e["tokens_baseline"], e["saved_pct"],
              e["cost_usd"],
              " TRUNC" if e["truncated"] else "",
              " TUNED->k%d" % e["k_after"] if e["tuned"] else ""))


def run_once(indices, agents, queries, cache, tuner, dataset, rund, log_path):
    evs = []
    for ag in agents:
        for q in queries:
            if dataset not in indices:
                continue
            e = R.run_agent(indices[dataset], ag, q, cache, tuner, dataset, rund=rund)
            evs.append(e)
            if log_path:
                R.append_event(log_path, e)
            print_row(e)
    return evs


def export_snapshot(log_path, out_path, queries):
    events = R.read_events(log_path)
    all_docs = R.load_all_docs()
    sig = R.fingerprint({n: (d, l) for n, (d, l, _f) in all_docs.items()})
    info = [{"name": n, "nodes": len(d), "edges": len(l),
             "tokens": sum(max(R.MIN_DOC_TOKENS, x["tokens"]) for x in d)}
            for n, (d, l, _f) in all_docs.items()]
    snap = R.snapshot(events, copy.deepcopy(R.AGENTS), info, sig, queries=queries)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    m = snap["metrics"]["totals"]
    print("[export] %s: %d events, saved=%d tok (%.1f%%), cache=%s%%, cost=$%s" % (
        out_path, m["runs"], m["saved"], m["saved_pct"], m["cache_hit_pct"], m["cost"]))
    return snap

def main(argv=None):
    ap = argparse.ArgumentParser(description="Chay dong loat cac agent AI tren du lieu ban do.")
    ap.add_argument("--agents", default=",".join(a["id"] for a in R.AGENTS))
    ap.add_argument("--agent", action="append", default=[],
                    help="agent tuy chinh name:model:color:k:strategy")
    ap.add_argument("--queries", default=",".join(DEFAULT_QUERIES))
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--dataset", default="Graph Memory")
    ap.add_argument("--log", default=str(R.LOG_PATH))
    ap.add_argument("--no-log", action="store_true")
    ap.add_argument("--export", nargs="?", const=str(R.SNAPSHOT_PATH), default=None)
    ap.add_argument("--watch", type=int, default=0, help="lap lai moi N giay (0 = 1 lan)")
    args = ap.parse_args(argv)

    agents = [a for a in copy.deepcopy(R.AGENTS) if a["id"] in args.agents.split(",")]
    for spec in args.agent:
        agents.append(parse_custom_agent(spec))
    if not agents:
        print("khong co agent nao hop le", file=sys.stderr)
        return 2
    queries = [q.strip() for q in args.queries.split(",") if q.strip()]
    print("== nap du lieu that (%d agent x %d query) ==" % (len(agents), len(queries)))
    all_docs = R.load_all_docs()
    indices = R.build_indices(all_docs)
    if args.dataset not in indices:
        print("dataset khong ton tai: %r (co: %s)" % (args.dataset, sorted(indices)),
              file=sys.stderr)
        return 2
    print("  " + ", ".join("%s=%dn/%de" % (n, len(d), len(l))
                            for n, (d, l, _f) in all_docs.items()))
    log_path = None if args.no_log else args.log
    cache, tuner = R.Cache(), R.Tuner()
    for rund in range(1, args.rounds + 1):
        print("== vong %d ==" % rund)
        run_once(indices, agents, queries, cache, tuner, args.dataset, rund, log_path)
        cs = cache.stats()
        print("  cache: %d hit / %d miss (%.1f%%), tuning: %s" % (
            cs["hits"], cs["misses"], cs["hit_pct"],
            ", ".join("%s:k%d" % (a, s["k"]) for a, s in tuner.snapshot().items())))
        if args.export:
            export_snapshot(log_path or args.log, args.export, queries)
        if args.watch and rund < args.rounds:
            time.sleep(args.watch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
