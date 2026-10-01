# -*- coding: utf-8 -*-
"""retrieval_hook.py - BAT KY agent AI nao cung ghi duoc 1 su kien truy xuat.

Dung cho Cline / GPT / Claude / Qwen / DeepSeek / tool ngoai: sau moi lan tim
kiem du lieu du an, goi hook nay de tin hieu hien tren CA HAI ban do
(qua retrieval_log.jsonl -> glow_signals.json -> build_glow.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import glow_retrieval as R


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ghi 1 su kien truy xuat vao log dung chung.")
    ap.add_argument("--agent", required=True, help="id agent (cline, gpt, claude, qwen, ...)")
    ap.add_argument("--model", default="", help="ten model (vd claude-sonnet-4.5)")
    ap.add_argument("--query", required=True)
    ap.add_argument("--hits", default="", help="id node cach nhau dau phay (vd a.py::f,b.py)")
    ap.add_argument("--dataset", default="Graph Memory")
    ap.add_argument("--ms", type=float, default=0.0, help="do tre do duoc (ms)")
    ap.add_argument("--tokens", type=int, default=0, help="token da doc (tra ve)")
    ap.add_argument("--baseline", type=int, default=0, help="token neu doc nguyen file")
    ap.add_argument("--cache", action="store_true", help="lan nay trung cache")
    ap.add_argument("--round", type=int, default=0)
    ap.add_argument("--strategy", default="fast")
    ap.add_argument("--log", default=str(R.LOG_PATH))
    ap.add_argument("--dry", action="store_true", help="chi in, khong ghi")
    args = ap.parse_args(argv)

    ids = [h.strip() for h in args.hits.split(",") if h.strip()]
    saved = max(0, args.baseline - args.tokens)
    ev = {"t": round(time.time(), 3), "agent": args.agent, "model": args.model,
          "query": args.query, "dataset": args.dataset, "round": args.round,
          "k": len(ids), "beam": 1, "strategy": args.strategy,
          "hits": [{"id": h, "file": h.split("::")[0], "score": 1.0} for h in ids],
          "n_hits": len(ids), "scored": len(ids),
          "latency_ms": round(args.ms, 2), "cache": bool(args.cache),
          "tokens_returned": args.tokens, "tokens_baseline": args.baseline,
          "tokens_saved": saved,
          "saved_pct": round(100.0 * saved / args.baseline, 1) if args.baseline else 0.0,
          "files_touched": len({h.split("::")[0] for h in ids}),
          "cost_usd": 0.0, "truncated": False, "tuned": False,
          "k_after": len(ids), "beam_after": 1, "ok": True}
    line = json.dumps(ev, ensure_ascii=False)
    if args.dry:
        print(line)
        return 0
    with open(args.log, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("[hook] %s/%s q=%r hits=%d saved=%d tok -> %s" % (
        args.agent, args.model or "-", args.query, len(ids), saved, args.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
