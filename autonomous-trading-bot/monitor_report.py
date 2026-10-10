"""Phan tich hieu qua testnet: journal.jsonl (OPEN/CLOSE) + log round (BLOCKED/KILL).

Chay:
    python monitor_report.py
    python monitor_report.py --log logs/turbo_run_err.log --out logs/monitor_report.json

Muc dich: theo doi testnet >= 1 tuan truoc khi LIVE (README) — can >= 50 lenh dong
va PF >= 1.2; chu y BLOCKED_LEARN/BLOCKED_URGENT neu bot qua it lenh.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import time
from collections import Counter, defaultdict, deque

try:  # doc CUNG .env VOI runtime (config.py) -> STRAT_MIN_N/STRATEGY_BLOCK khop bot
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

STATUS_RE = re.compile(r"['\"]status['\"]:\s*['\"]([A-Z_]+)['\"]")
KILL_RE = re.compile(r"['\"]reason['\"]:\s*['\"]([^'\"]*(?:loss|error|volatility)[^'\"]*)['\"]", re.I)
STOPPED_RE = re.compile(r"STOPPED:\s*(.+)")
LOG_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?")
MIN_TRADES = int(os.getenv("MIN_TRADES", "50") or 50)
# (11/10) Nguong PF cho phep (configurable): chay SONG SONG testnet + live thi moi
# instance can nguong rieng (vd instance LIVE dat MIN_PF=1.05 khi chap nhan edge mong).
MIN_PF = float(os.getenv("MIN_PF", "1.2") or 1.2)
MIN_SAMPLE_DAYS = 3            # mau CLOSE phai phan chia tren it nhat 3 ngay
DIRECTIONS_REQUIRED = ("LONG", "SHORT")
MIN_DIRECTION_TRADES = 5       # moi huong LONG/SHORT can >=5 lenh trong toan bo mau
# Strategy gate — DOC CUNG ENV VOI RUNTIME (turbo_demo/strategy.gate_check) de
# monitor va bot cung mot bo nguong (mac dinh 10 / -0.10; doi qua .env).
STRAT_MIN_N = int(float(os.getenv("STRAT_MIN_N", "10")) or 10)
STRAT_AVG_R = float(os.getenv("STRAT_AVG_R", "0.10") or 0.10)
STRATEGY_GATE = (os.getenv("STRATEGY_GATE", "true").strip().lower()
                 in ("1", "true", "yes", "y", "on"))
# Blocklist chu dong (cung .env voi runtime) — xem strategy.gate_check.
STRATEGY_BLOCK = tuple(s.strip() for s in
                       os.getenv("STRATEGY_BLOCK", "").split(",") if s.strip())
MIN_RECENT_BLOCKED_LEARN = 10  # so BLOCKED_LEARN toi thieu moi bat dau de danh gia


def load_journal(path: str) -> tuple:
    """Tra (opens, closes). Close = event=CLOSE hoac co 'won' khong phai OPEN."""
    opens: list = []
    closes: list = []
    if not os.path.exists(path):
        return opens, closes
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("event") == "CLOSE" or ("won" in rec and rec.get("event") != "OPEN"):
                closes.append(rec)
            elif "entry" in rec:
                opens.append(rec)
    return opens, closes


def match_pairs(opens: list, closes: list) -> tuple:
    """Gan tung CLOSE voi OPEN cung pair som nhat chua gan (FIFO)."""
    pending: dict = defaultdict(deque)
    for o in opens:
        pending[o.get("pair") or o.get("symbol", "?")].append(o)
    pairs = []
    for c in closes:
        key = c.get("pair") or c.get("symbol", "?")
        o = pending[key].popleft() if pending.get(key) else None
        pairs.append((o, c))
    still = [o for q in pending.values() for o in q]
    return pairs, still


def _group(rows: list, key_fn) -> dict:
    g: dict = {}
    for r in rows:
        g.setdefault(key_fn(r) or "?", []).append(r)
    out = {}
    for k, rs in g.items():
        n = len(rs)
        wins = sum(1 for r in rs if r.get("won"))
        avg_r = sum(float(r.get("r") or 0.0) for r in rs) / n
        out[str(k)] = {"n": n, "wr": round(100.0 * wins / n, 1), "avg_r": round(avg_r, 3)}
    return out


def stats(pairs: list) -> dict:
    """WR/PF/E(R) tu cac cap (OPEN, CLOSE) da ghep."""
    closes = [c for _, c in pairs]
    n = len(closes)
    if n == 0:
        return {"n": 0, "wins": 0, "wr": 0.0, "pf_r": 0.0, "pf_pnl": 0.0,
                "e_r": 0.0, "pnl": 0.0, "avg_hold_min": None,
                "by_pair": {}, "by_direction": {}, "by_strategy": {}}
    rs = [float(c.get("r") or 0.0) for c in closes]
    pnls = [float(c.get("pnl") or 0.0) for c in closes]
    wins = sum(1 for c in closes if c.get("won"))
    win_r = sum(r for r in rs if r > 0)
    loss_r = abs(sum(r for r in rs if r < 0))
    win_p = sum(p for p in pnls if p > 0)
    loss_p = abs(sum(p for p in pnls if p < 0))
    st = {
        "n": n, "wins": wins, "wr": round(100.0 * wins / n, 2),
        "pf_r": round(win_r / loss_r, 3) if loss_r > 1e-9 else (999.0 if win_r > 0 else 0.0),
        "pf_pnl": round(win_p / loss_p, 3) if loss_p > 1e-9 else (999.0 if win_p > 0 else 0.0),
        "e_r": round(sum(rs) / n, 4), "pnl": round(sum(pnls), 2),
        "avg_hold_min": None,
    }
    holds = [(float(c.get("ts") or 0) - float(o.get("ts") or 0)) / 60.0
             for o, c in pairs if o and o.get("ts") and c.get("ts")]
    if holds:
        st["avg_hold_min"] = round(sum(holds) / len(holds), 1)
    st["by_pair"] = _group(closes, lambda r: r.get("pair"))
    st["by_direction"] = _group(closes, lambda r: r.get("direction"))
    strat_rows = [{"won": c.get("won"), "r": c.get("r"),
                   "strategy": (o or {}).get("strategy")} for o, c in pairs]
    st["by_strategy"] = _group(strat_rows, lambda r: r.get("strategy"))
    return st


# ---- Journal CLOSE helpers -> WR/PF report (python monitor_report.py) ----
def scan_text(text: str) -> Counter:
    """Dem status (OPENED/BLOCKED_*/KILLED/...) trong log round."""
    return Counter(STATUS_RE.findall(text))


def log_line_ts(line: str) -> float | None:
    """Timestamp UTC tu dau dong dang 'YYYY-MM-DD HH:MM[:SS]'; None neu khong co."""
    m = LOG_TS_RE.match(line or "")
    if not m:
        return None
    try:
        from datetime import datetime, timezone
        day = m.group(1)
        hh = int(m.group(2))
        mm = int(m.group(3))
        ss = int(m.group(4) or 0)
        dt = datetime.strptime(f"{day} {hh:02d}:{mm:02d}:{ss:02d}",
                               "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def scan_text_since(text: str, cutoff_ts: float) -> Counter:
    """Chi dem status tu nhung dong log moi hon cutoff (bo lich su cu)."""
    found: list = []
    for line in (text or "").splitlines():
        ts = log_line_ts(line)
        if ts is None or ts >= cutoff_ts:
            found.extend(STATUS_RE.findall(line))
    return Counter(found)


def scan_logs(patterns: list, recent_ts: float | None = None) -> tuple:
    """Tra (Counter status toan bo, Counter status gan day, kill_reasons, files).

    - Counter toan bo: hien thi LOG STATUS (khong quen lich su).
    - Counter gan day (dong co timestamp >= recent_ts): dung cho gate
      BLOCKED_LEARN — so cu truoc khi sua label P0-7 (778 lan) khong duoc
      chan gate moi, nhung van bat duoc phan hoi learner hien tai.
    - KILL/STOPPED: LUON quet toan bo file (an toan — kill-switch khong bi quen).
    """
    files: list = []
    for p in patterns:
        files.extend(glob.glob(p) if any(ch in p for ch in "*?[") else [p])
    files = sorted({f for f in files if os.path.isfile(f)})
    counter: Counter = Counter()
    recent: Counter = Counter()
    kills: list = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception:
            continue
        counter.update(scan_text(text))
        if recent_ts is not None:
            recent.update(scan_text_since(text, recent_ts))
        kills += KILL_RE.findall(text)
        kills += STOPPED_RE.findall(text)
    return counter, recent, [k.strip() for k in kills], files


def verdict(st: dict, statuses: Counter, closes: list | None = None,
            recent_statuses: Counter | None = None, window_days: float = 0.0,
            strict: bool = False, strategy_gate: dict | None = None,
            runtime_blocked: set | None = None) -> dict:
    """Quyet dinh LIVE chua:
    - Trade-level (toan bo lich su): >= 50 lenh dong, PF >= 1.2, khong KILL.
    - Chat luong mau (toan bo lich su, bat buoc): mau phan chia >= 3 ngay +
      du ca LONG va SHORT (>= MIN_DIRECTION_TRADES moi huong). Mau 100% SHORT
      thi PF khong co gia tri quyet dinh cho he thong 2 chieu.
    - Strategy gate (toan bo lich su, bat buoc neu truyen strategy_gate): strategy
      nao du mau (>= STRAT_MIN_N) ma avgR am ro (<= -STRAT_AVG_R) thi CHAN LIVE —
      khong cho mot nhom setup keo PF xuong qua cua. Chua du mau -> CANH BAO.
    - Van hanh (cua so window_days gan day, neu co recent_statuses):
      BLOCKED_LEARN vuot OPENED -> CANH BAO (khong chan LIVE). Ly do: block chi
      lam GIAM so lenh nen khong tao rui ro tien; chieu nguy hiem (learner dao
      nguoc -> mo lenh toi) da bi gate PF >= 1.2 bat. --strict de nang lenh thanh
      ly do chan LIVE (dung khi nghi learner bi nhiem doc weight cu).
    """
    reasons: list = []
    warns: list = []
    if st["n"] < MIN_TRADES:
        reasons.append(f"n={st['n']} < {MIN_TRADES} lenh dong — tiep tuc testnet")
    if st["pf_r"] < MIN_PF:
        reasons.append(f"PF={st['pf_r']} < {MIN_PF} — chay lai sweep.py truoc khi LIVE")
    if statuses.get("KILLED", 0) or statuses.get("KILL", 0):
        reasons.append("co KILL trong log — xem lai MAX_DAILY_LOSS_PCT/loi API")
    rows = closes or []
    if rows:
        days = {time.strftime("%Y-%m-%d", time.gmtime(float(c.get("ts") or 0)))
                for c in rows if c.get("ts")}
        if len(days) < MIN_SAMPLE_DAYS:
            reasons.append(f"mau moi phu {len(days)} ngay (<{MIN_SAMPLE_DAYS} "
                           "ngay) — can them ngay giao dich de tranh mau 1 phien")
        by_dir = Counter(str(c.get("direction") or "?").upper() for c in rows)
        missing = [d for d in DIRECTIONS_REQUIRED
                   if by_dir.get(d, 0) < MIN_DIRECTION_TRADES]
        if missing:
            have = ", ".join(f"{d}={by_dir.get(d, 0)}" for d in DIRECTIONS_REQUIRED)
            reasons.append(f"thieu mau chieu ({have}) — can >= {MIN_DIRECTION_TRADES} "
                           f"lenh moi huong trong toan bo {len(rows)} lenh dong")
    if recent_statuses is not None:
        bl = int(recent_statuses.get("BLOCKED_LEARN", 0))
        op = int(recent_statuses.get("OPENED", 0))
        if bl >= MIN_RECENT_BLOCKED_LEARN and bl > op:
            msg = (f"BLOCKED_LEARN={bl} > OPENED={op} trong {window_days:g} ngay gan nhat "
                   "- learner chan gan moi setup (kiem tra label P0-7 / LEARN_MIN_EDGE"
                   " / weight cu trong logs/learner.json)")
            (reasons if strict else warns).append(msg)
    for _code, _g in (strategy_gate or {}).items():
        _n = int(_g.get("n", 0) or 0)
        _a = float(_g.get("avg_r", 0.0) or 0.0)
        # Runtime da chan nhom nay (STRATEGY_BLOCK hoac auto-gate) -> khong dem lai
        # ly do chan LIVE (bot da khong mo lenh moi nua) nhung van in de ro rang.
        if runtime_blocked and _code in runtime_blocked:
            warns.append(f"strategy {_code} dang am (n={_n}, avgR={_a:+.2f}) - "
                         "DA BI STRATEGY GATE chan o runtime")
            continue
        if _n >= STRAT_MIN_N and _a <= -STRAT_AVG_R:
            reasons.append(f"strategy {_code} dang am (n={_n}, avgR={_a:+.2f}) - "
                           "khong cho LIVE voi nhom setup keo PF xuong")
        elif _n >= STRAT_MIN_N // 2:
            warns.append(f"strategy {_code} yeu (n={_n}, avgR={_a:+.2f}) - can them mau")
    return {"ready_for_live": not reasons, "reasons": reasons, "warnings": warns}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Testnet monitor: journal + log -> WR/PF verdict")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--log", nargs="*", default=["logs/*.log"],
                    help="log file(s) scan BLOCKED/KILL (mac dinh logs/*.log)")
    ap.add_argument("--out", default="logs/monitor_report.json")
    ap.add_argument("--days", type=float, default=0.0, help="chi tinh lenh trong N ngay qua (0 = tat ca)")
    ap.add_argument("--ops-days", type=float, default=3.0,
                    help="cua so ngay gan nhat cho gate BLOCKED_LEARN + LOG STATUS gan day "
                         "(KILL van quet toan bo lich su)")
    ap.add_argument("--strict", action="store_true",
                    help="nang canh bao van hanh (BLOCKED_LEARN > OPENED) thanh ly do chan LIVE")
    args = ap.parse_args(argv)

    opens, closes = load_journal(args.journal)
    if args.days > 0:
        cut = time.time() - args.days * 86400.0
        opens = [o for o in opens if float(o.get("ts") or 0) >= cut]
        closes = [c for c in closes if float(c.get("ts") or 0) >= cut]
    pairs, still = match_pairs(opens, closes)
    st = stats(pairs)
    recent_ts = (time.time() - float(args.ops_days) * 86400.0
                 if args.ops_days > 0 else None)
    statuses, recent, kills, files = scan_logs(args.log, recent_ts=recent_ts)
    # Strategy gate: thong ke theo strategy trong journal -> chan nhom setup am.
    # Lay strategy tu OPEN cua cap (OPEN, CLOSE) da ghep (FIFO) de strategy dung
    # voi lenh do (ban ghi CLOSE ghi bu khong co strategy rieng — xem reconcile.py).
    # Khong ghep duoc (NONE / ?) -> bo qua, khong phat cho strategy do.
    strat_gate: dict = {}
    try:
        _acc: dict = {}
        for o, c in pairs:
            _s = str((o or {}).get("strategy") or c.get("strategy") or "?").upper()
            if _s in ("NONE", "?"):
                continue
            _a = _acc.setdefault(_s, {"n": 0, "w": 0, "r": 0.0})
            _a["n"] += 1
            _a["w"] += 1 if c.get("won") else 0
            _a["r"] += float(c.get("r") or 0.0)
        for _code, _g in _acc.items():
            strat_gate[_code] = {"n": _g["n"], "wr": round(100.0 * _g["w"] / _g["n"], 1),
                                 "avg_r": round(_g["r"] / _g["n"], 3)}
    except Exception:  # noqa: BLE001
        strat_gate = {}
    vd = verdict(st, statuses, closes=[c for _, c in pairs],
                 recent_statuses=recent if args.ops_days > 0 else None,
                 window_days=args.ops_days, strict=args.strict,
                 strategy_gate=strat_gate,
                 runtime_blocked=({_c for _c, _g in strat_gate.items()
                                   if int(_g.get("n", 0)) >= STRAT_MIN_N
                                   and float(_g.get("avg_r", 0.0)) <= -STRAT_AVG_R}
                                  | (set(STRATEGY_BLOCK) if STRATEGY_GATE else set())
                                  if STRATEGY_GATE else set()))

    print("=" * 92)
    print(f"TESTNET MONITOR | journal={args.journal} | opens={len(opens)} closes={len(closes)} "
          f"journal-open(chua ghep)={len(still)} | log files={len(files)}")
    print("=" * 92)
    if st["n"]:
        print(f"TRADES: n={st['n']}  WR={st['wr']:.1f}%  PF(R)={st['pf_r']:.3f}  "
              f"PF($)={st['pf_pnl']:.3f}  E(R)={st['e_r']:+.4f}  PnL={st['pnl']:+.2f}$  "
              f"hold={st['avg_hold_min']}m")
        for title, key in (("BY_PAIR", "by_pair"), ("BY_DIR", "by_direction"),
                           ("BY_STRAT", "by_strategy")):
            if st.get(key):
                det = " | ".join(f"{k}: n={v['n']} WR={v['wr']:.0f}% avgR={v['avg_r']:+.2f}"
                                 for k, v in sorted(st[key].items()))
                print(f"  {title}: {det}")
    else:
        print("TRADES: chua co lenh dong nao trong journal (van cho lenh OPEN dau tien)")
    if statuses:
        top = ", ".join(f"{k}={v}" for k, v in statuses.most_common(10))
        print(f"LOG STATUS: {top}")
    if still:
        print(f"  ! {len(still)} OPEN chua ghep CLOSE la LICH SU GHI CHEP (khong phai vi "
              f"the dang mo). Vi the that: python positions.py")
    if recent:
        top_r = ", ".join(f"{k}={v}" for k, v in recent.most_common(8))
        print(f"LOG STATUS ({args.ops_days:g} ngay gan nhat): {top_r}")
    for kr in kills[:5]:
        print(f"  KILL: {kr}")
    print("-" * 92)
    print(f"VERDICT: {'READY FOR LIVE' if vd['ready_for_live'] else 'CHUA — GIU TESTNET'}")
    for r in vd["reasons"]:
        print(f"  - {r}")
    for w in vd.get("warnings", []):
        print(f"  ! CANH BAO: {w}")
    try:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"stats": st, "log_status": dict(statuses), "kill_reasons": kills,
                       "verdict": vd, "open_positions": [o.get("pair") for o in still],
                       "generated_at": time.time()},
                      f, ensure_ascii=False, indent=1)
        print(f"[OK] da luu {args.out}")
    except Exception as exc:
        print(f"[WARN] khong luu duoc report: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())