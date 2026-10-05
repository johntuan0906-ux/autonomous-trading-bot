"""hyperopt.py - grid search tham so tu journal, offline."""
from __future__ import annotations
import json, os, sys
from dataclasses import dataclass
from itertools import product


@dataclass
class P:
    sl: float = 1.5; tp: float = 3.0
    pr: float = 1.0; pp: float = 0.5
    be: float = 1.0; tr: float = 1.0


def load(path):
    o, c = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try: r = json.loads(line)
            except: continue
            if r.get("event") == "OPEN" and r.get("entry") and r.get("sl") and r.get("tp"):
                o.append(r)
            elif r.get("event") == "CLOSE": c.append(r)
    return o, c


def sim(o, cs, p):
    e, d = float(o["entry"]), str(o.get("direction", "")).upper()
    sl = float(o["sl"]); a = abs(sl - e) / max(p.sl, 0.1)
    s2 = e - p.sl * a if d == "LONG" else e + p.sl * a
    t2 = e + p.tp * a if d == "LONG" else e - p.tp * a
    pd = bd = False; bp = 0.0; q = float(o.get("qty", 0)); iq = q; sc = s2
    t0 = float(o.get("ts", 0))
    for x in cs:
        if float(x.get("ts", 0)) <= t0: continue
        px = float(x.get("exit_price", 0)); rs = str(x.get("reason", "")).upper()
        if px <= 0: continue
        dt = (px - e) if d == "LONG" else (e - px)
        r = dt / max(abs(e - s2), 1e-12)
        if not pd and p.pr > 0 and p.pp > 0 and r >= p.pr and q > 0:
            cq = min(q * p.pp, q); bp += cq * abs(px - e) * 0.999; q -= cq
            pd = bd = True; sc = e
        if not bd and p.be > 0 and r >= p.be: sc = e; bd = True
        if p.tr > 0 and a > 0 and (bd or pd):
            cd = (px - p.tr * a) if d == "LONG" else (px + p.tr * a)
            if (cd > sc) if d == "LONG" else (cd < sc): sc = cd
        rm = (q * (px - e) if d == "LONG" else q * (e - px)) * 0.999
        pnl = bp + rm; fr = pnl / max(abs(e - s2) * iq, 1e-12)
        w = rs in ("TP", "TRAIL") or (pnl > 0 and (pd or rs == "BE"))
        return fr, w
    return 0.0, False


def grid():
    return [P(sl, tp, pr, pp, be, tr) for sl, tp, pr, pp, be, tr in product(
        [1.2, 1.5, 2.0], [2.5, 3.0, 4.0], [0.5, 1.0, 1.5],
        [0.3, 0.5], [0.5, 1.0], [0.5, 1.0, 1.5])]


def run(o, c, pl):
    rs = []
    for p in pl:
        n = w = sr = 0.0
        for x in o:
            r, wn = sim(x, c, p); n += 1; w += 1 if wn else 0; sr += r
        if n: rs.append(((p.sl, p.tp, p.pr, p.pp, p.be, p.tr), n, w, round(sr / n, 3)))
    rs.sort(key=lambda x: x[3], reverse=True)
    return rs


def main():
    p = sys.argv[1] if len(sys.argv) > 1 else "logs/journal.jsonl"
    if not os.path.exists(p): print(f"KO: {p}"); sys.exit(1)
    o, c = load(p)
    if not o: print("KO OPEN"); sys.exit(0)
    pl = grid(); print(f"OPEN={len(o)} CLOSE={len(c)} PARAM={len(pl)}")
    rs = run(o, c, pl)
    print(f"{'#':>3} {'SLx':>5} {'TPx':>5} {'PR':>5} {'PP%':>5} {'BEx':>5} {'Trx':>5} {'n':>4} {'WR%':>6} {'avgR':>7}")
    print("-" * 67)
    for i, (pr, n, w, av) in enumerate(rs[:10]):
        sl, tp, pr2, pp, be, tr = pr
        print(f"{i+1:>3} {sl:>5.1f} {tp:>5.1f} {pr2:>5.1f} {pp:>4.0%} {be:>5.1f} {tr:>5.1f} {n:>4} {w/n*100:>5.1f}% {av:>7.3f}")
    if rs:
        sl, tp, pr2, pp, be, tr = rs[0][0]
        print(f"\nTOP: SL={sl} TP={tp} PARTIAL={pr2}/{pp:.0%} BE={be} TRAIL={tr} avgR={rs[0][3]}")


if __name__ == "__main__":
    main()