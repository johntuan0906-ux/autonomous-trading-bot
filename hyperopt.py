#!/usr/bin/env python
"""hyperopt.py - tim bo tham so toi uu tu journal (Offline grid search).
Chay: python hyperopt.py"""
from __future__ import annotations
import json, os, sys
from dataclasses import dataclass
from itertools import product

@dataclass
class Params:
    sl_mult: float = 1.5; tp_mult: float = 3.0
    partial_r: float = 1.0; partial_pct: float = 0.5
    be_r: float = 1.0; trail_mult: float = 1.0; min_rr: float = 2.0

@dataclass
class Result:
    params: tuple; n: int = 0; wins: int = 0; wr: float = 0.0
    sum_r: float = 0.0; avg_r: float = 0.0; pf: float = 0.0

def load_journal(path):
    opens, closes = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try: r = json.loads(line)
            except: continue
            if r.get("event") == "OPEN" and r.get("entry") and r.get("sl") and r.get("tp"):
                opens.append(r)
            elif r.get("event") == "CLOSE":
                closes.append(r)
    return opens, closes

def simulate(open_r, closes, p, start_idx=0):
    entry = float(open_r["entry"]); direction = str(open_r.get("direction","")).upper()
    sl = float(open_r["sl"]); tp = float(open_r["tp"])
    atr = abs(sl - entry) / max(p.sl_mult, 0.1)
    sl2 = entry - p.sl_mult * atr if direction == "LONG" else entry + p.sl_mult * atr
    tp2 = entry + p.tp_mult * atr if direction == "LONG" else entry - p.tp_mult * atr
    partial_done = be_done = False
    booked_pnl = 0.0; qty = float(open_r.get("qty",0)); init_qty = qty
    sl_cur = sl2; ts0 = float(open_r.get("ts",0))
    for c in closes:
        if float(c.get("ts",0)) <= ts0: continue
        px = float(c.get("exit_price",0)); reason = str(c.get("reason","")).upper()
        if px <= 0: continue
        dist = (px - entry) if direction == "LONG" else (entry - px)
        r = dist / max(abs(entry - sl2), 1e-12)
        if not partial_done and p.partial_r > 0 and p.partial_pct > 0 and r >= p.partial_r and qty > 0:
            cq = min(qty * p.partial_pct, qty); booked_pnl += cq * abs(px - entry) * 0.999
            qty -= cq; partial_done = be_done = True; sl_cur = entry
        if not be_done and p.be_r > 0 and r >= p.be_r:
            sl_cur = entry; be_done = True
        if p.trail_mult > 0 and atr > 0 and (be_done or partial_done):
            cand = (px - p.trail_mult * atr) if direction == "LONG" else (px + p.trail_mult * atr)
            if (cand > sl_cur) if direction == "LONG" else (cand < sl_cur): sl_cur = cand
        rem = (qty * (px - entry) if direction == "LONG" else qty * (entry - px)) * 0.999
        pnl = booked_pnl + rem; full_r = pnl / max(abs(entry - sl2) * init_qty, 1e-12)
        won = reason in ("TP","TRAIL") or (pnl > 0 and (partial_done or reason == "BE"))
        return full_r, won
    return 0.0, False

def grid():
    return [Params(sl, tp, pr, pp, be, tr) for sl,tp,pr,pp,be,tr in product(
        [1.2,1.5,2.0], [2.5,3.0,4.0], [0.5,1.0,1.5], [0.3,0.5], [0.5,1.0], [0.5,1.0,1.5])]

def run(opens, closes, params_list):
    results = []
    for p in params_list:
        n = wins = sum_r = 0.0
        for o in opens:
            r, w = simulate(o, closes, p)
            n += 1; wins += 1 if w else 0; sum_r += r
        if n: results.append(Result((p.sl_mult,p.tp_mult,p.partial_r,p.partial_pct,p.be_r,p.trail_mult),
            n=n, wins=wins, wr=round(wins/n*100,1), sum_r=round(sum_r,2), avg_r=round(sum_r/n,3)))
    results.sort(key=lambda x: x.avg_r, reverse=True)
    return results

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "logs/journal.jsonl"
    if not os.path.exists(path): print(f"Khong co {path}"); sys.exit(1)
    opens, closes = load_journal(path)
    if not opens: print("Chua co du OPEN"); sys.exit(0)
    pl = grid()
    print(f"Nap {len(opens)} OPEN + {len(closes)} CLOSE. Quet {len(pl)} bo tham so...")
    results = run(opens, closes, pl)
    hdr = f"{'#':>3} {'SLx':>5} {'TPx':>5} {'PR':>5} {'PP%':>5} {'BEx':>5} {'Trx':>5} {'n':>4} {'WR%':>6} {'avgR':>7}"
    print(f"\n{'='*75}\n{hdr}\n{'-'*len(hdr)}")
    for i,r in enumerate(results[:12]):
        sl,tp,pr,pp,be,tr = r.params
        print(f"{i+1:>3} {sl:>5.1f} {tp:>5.1f} {pr:>5.1f} {pp:>4.0%} {be:>5.1f} {tr:>5.1f} {r.n:>4} {r.wr:>5.1f}% {r.avg_r:>7.3f}")
    if results:
        sl,tp,pr,pp,be,tr = results[0].params
        print(f"\nDE XUAT BO #1:")
        cur_sl = float(os.getenv("SL_ATR_MULT",1.5)); cur_tp = float(os.getenv("TP_ATR_MULT",3.0))
        print(f"  SL_ATR_MULT={sl:.1f} (hien: {cur_sl}) | TP_ATR_MULT={tp:.1f} (hien: {cur_tp})")
        print(f"  PARTIAL_AT_R={pr:.1f} | PARTIAL_PCT={pp:.0%} | BE_AT_R={be:.1f} | TRAIL_ATR_MULT={tr:.1f}")
        print(f"  KQ: n={results[0].n} WR={results[0].wr}% avgR={results[0].avg_r}")

if __name__ == "__main__": main()