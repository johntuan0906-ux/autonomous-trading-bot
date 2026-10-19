"""TRACE mot lenh tu dau den cuoi — tra loi cau hoi "VI SAO bot mo/dong lenh nay?".

    python tools/trace_trade.py --pair SOL/USDT:USDT          # lenh gan nhat cua cap
    python tools/trace_trade.py --pair SOL --last 3           # 3 lenh gan nhat
    python tools/trace_trade.py --ts 1792386409               # theo moc thoi gian OPEN
    python tools/trace_trade.py --key "B_BREAKOUT_RETEST | BOS_UP | BREAKOUT | LONG"
    python tools/trace_trade.py --pair SOL --json

Chuoi trace (moi muc kem id/thoi diem):
  1. VAO LENH  : feature luc mo (strategy/setup/regime/alpha/score100) + size/risk/SL/TP/leverage
  2. HOI DONG  : phieu cua tung model quanh luc mo (trong cua so `--window-min`)
  3. SETUP/REVIEW: ban ghi `status=SETUP` truoc khi vao, `status=CLOSED` sau khi dong
  4. DONG LENH : r/pnl/reason/mfe_r/thoi gian giu
  5. BAI HOC   : to hop dieu kien (ma `EV-xxxxxx`) + n/avgR/WR/PnL + CO DANG BI CHAN khong
  6. VI THE    : neu con mo — SL/TP/trailing/partial tu `logs/managed_state.json`

Vi sao (19/10, REPO_IDEAS §15.3 — "verification: traceability"): day la MAT XICH THIEU LON
NHAT — he thong co journal, co bang diem model, co lessons, nhung KHONG co cho nao tra loi
duoc "lenh nay vi sao vao, ai dong y, va no thuoc bai hoc nao". Do la cung lop van de da lam
hoi dong "im lang" 48h (he thong chay ma khong ai biet no quyet the nao).

Chi DOC journal/state; khong doi hanh vi trading.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_JOURNAL = "logs/journal.jsonl"
DEFAULT_LESSONS = "logs/lessons.json"
DEFAULT_MANAGED = "logs/managed_state.json"


def read_journal(path) -> list:
    """Doc journal -> list dict (bo qua dong hong; khong nem loi)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        try:
            d = json.loads(ln)
        except (TypeError, ValueError):
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def _f(x, k, d=0.0) -> float:
    try:
        return float((x or {}).get(k) if (x or {}).get(k) is not None else d)
    except (TypeError, ValueError):
        return d


def norm_pair(s: str) -> str:
    """`SOL` -> `SOL/USDT:USDT` (de go ngan cho nhanh)."""
    t = str(s or "").strip().upper()
    return t if "/" in t else "%s/USDT:USDT" % t


def related(rows: list, pair: str, t0: float, t1: float, *, status=None,
            event=None) -> list:
    """Ban ghi cua DUNG cap trong khoang [t0, t1], loc theo `status`/`event`."""
    out = []
    for d in rows or []:
        if str(d.get("symbol") or d.get("pair") or "") != pair:
            continue
        if status is not None and str(d.get("status") or "") != str(status):
            continue
        if event is not None and str(d.get("event") or "") != str(event):
            continue
        ts = _f(d, "ts")
        if t0 <= ts <= t1:
            out.append(d)
    return sorted(out, key=lambda d: _f(d, "ts"))


def find_trades(journal_path, *, pair: str = "", ts: float | None = None,
                last: int = 1, keys=None) -> list:
    """Cac lenh DA DONG khop bo loc, moi nhat truoc.

    Dung `lessons.load_closed` (MOT dinh nghia duy nhat cho "1 lenh" = OPEN ghep CLOSE).
    `pair` nhan ca dang ngan (`SOL`); `ts` khop moc OPEN trong +-300s.
    """
    import lessons as LES
    trades = LES.load_closed(journal_path)
    want = norm_pair(pair) if pair else ""
    if want:
        trades = [t for t in trades if norm_pair(t.get("pair")) == want]
    if ts is not None:
        trades = [t for t in trades if abs(_f(t, "ts") - float(ts)) <= 300.0]
    trades.sort(key=lambda t: -_f(t, "ts_close") if _f(t, "ts_close") else -_f(t, "ts"))
    return trades[:max(1, int(last or 1))]


def managed_position(symbol: str, managed_path=DEFAULT_MANAGED) -> dict:
    """Vi the dang mo cua cap trong `managed_state.json` (neu con) — de xem SL/TP/trailing."""
    try:
        d = json.loads(Path(managed_path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    trades = d.get("trades") if isinstance(d, dict) else {}
    return dict((trades or {}).get(str(symbol)) or {})


def trace(journal_path, trade: dict, *, window_min: float = 20.0,
          rows: list | None = None, managed_path=DEFAULT_MANAGED) -> dict:
    """Chuoi trace day du cho 1 lenh (dict). Thuan tuy (doc file)."""
    rows = read_journal(journal_path) if rows is None else rows
    pair = norm_pair(trade.get("pair"))
    t_open = _f(trade, "ts")
    t_close = _f(trade, "ts_close") or (time.time() if trade else 0.0)
    win = max(1.0, float(window_min)) * 60.0
    return {
        "pair": pair,
        "open": trade,
        "votes": related(rows, pair, t_open - win, t_open + 120.0, status="COUNCIL"),
        "setups": related(rows, pair, t_open - win, t_open + 60.0, status="SETUP"),
        "reviews": related(rows, pair, t_close - 60.0, t_close + win, status="CLOSED"),
        "position": managed_position(pair, managed_path) if not t_close else {},
    }


def bucket_of(trade: dict, lessons_path=DEFAULT_LESSONS, *, keys=None) -> dict:
    """To hop dieu kien cua lenh + so lieu + CO DANG BI CHAN khong (tu `logs/lessons.json`)."""
    import lessons as LES
    key = LES.key_of(trade, keys or LES.KEYS_DEFAULT)
    out = {"key": key, "code": LES.evidence_code(key), "n": 0, "avg_r": None,
           "wr": None, "pnl": None, "gated": False, "gate_min_n": None}
    try:
        les = json.loads(Path(lessons_path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return out
    b = (les.get("buckets") or {}).get(key) or {}
    if b:
        out.update({"n": b.get("n"), "avg_r": b.get("avg_r"), "wr": b.get("wr"),
                    "pnl": b.get("pnl")})
    gkeys = {g.get("key") for g in (les.get("gates") or [])}
    out["gated"] = key in gkeys
    for g in (les.get("gates") or []):
        if g.get("key") == key:
            out["gate"] = g
    return out



def _t(ts) -> str:
    try:
        return time.strftime("%d/%m %H:%M:%S", time.localtime(float(ts)))
    except Exception:  # noqa: BLE001
        return "?"


def fmt_trace(tr: dict, bucket: dict | None = None) -> list:
    """In chuoi trace (list dong) — du de doc trong terminal/Telegram."""
    o = tr.get("open") or {}
    out = ["=== TRACE LENH | %s | OPEN %s ===" % (tr.get("pair"), _t(o.get("ts")))]
    out.append("1) VAO LENH  %s  %s %s  entry=%s sl=%s tp=%s  rr=%s  lev=%s"
               % (_t(o.get("ts")), o.get("direction"), o.get("timeframe"),
                  o.get("entry"), o.get("sl"), o.get("tp"), o.get("rr"), o.get("leverage")))
    out.append("   size/risk : qty=%s risk=%s%% (~%s USDT) kelly=%s"
               % (o.get("qty"), o.get("risk_pct"), o.get("risk_usdt"),
                  o.get("kelly_size_mult")))
    out.append("   tin hieu  : strategy=%s setup=%s regime=%s htf=%s alpha=%s score=%s"
               % (o.get("strategy"), o.get("setup_type"), o.get("market_regime"),
                  o.get("htf_bias"), o.get("alpha"), o.get("score100")))
    vts = tr.get("votes") or []
    out.append("2) HOI DONG (%d phieu quanh luc vao):" % len(vts))
    for v in vts:
        rs = v.get("reasons") or []
        out.append("   %-30s %-6s %s  %s"
                   % (str(v.get("model"))[:30], v.get("action"),
                      v.get("confidence"), str(rs[0] if rs else "")[:80]))
    st = tr.get("setups") or []
    if st:
        out.append("   tang SETUP (%d): %s" % (len(st), str(st[-1].get("note") or "")[:90]))
    rv = tr.get("reviews") or []
    out.append("3) REVIEW SAU KHI DONG (%d):" % len(rv))
    for r in rv[:3]:
        rs = r.get("reasons") or []
        out.append("   %-30s %-6s %s  %s"
                   % (str(r.get("model"))[:30], r.get("action"), r.get("confidence"),
                      str(rs[0] if rs else "")[:80]))
    if o.get("ts_close"):
        dur = max(0.0, _f(o, "ts_close") - _f(o, "ts"))
        out.append("4) DONG LENH %s  r=%s pnl=%s won=%s reason=%s mfe_r=%s partial=%s (giu %.0f phut)"
                   % (_t(o.get("ts_close")), o.get("r"), o.get("pnl"), o.get("won"),
                      o.get("reason"), o.get("mfe_r"), o.get("partial"), dur / 60.0))
    pos = tr.get("position") or {}
    if pos:
        out.append("4b) DANG MO: sl=%s tp=%s be_done=%s partial_done=%s mfe_r=%s"
                   % (pos.get("sl"), pos.get("tp"), pos.get("be_done"),
                      pos.get("partial_done"), pos.get("mfe_r")))
    if bucket:
        out.append("5) BAI HOC: to hop `%s` (%s) n=%s avgR=%s WR=%s pnl=%s -> %s"
                   % (bucket.get("key"), bucket.get("code"), bucket.get("n"),
                      bucket.get("avg_r"), bucket.get("wr"), bucket.get("pnl"),
                      "DANG CHAN (lessons gate)" if bucket.get("gated") else "chua bi chan"))
        if bucket.get("gated"):
            out.append("   LUU Y: lenh nay thuoc to hop DANG BI CHAN — neu no van duoc mo,"
                       " kiem tra luc do da du mau (n>=20) chua.")
        out.append("   Truy nguoc bang chung: `python tools/trace_trade.py --key \"%s\"`"
                   % bucket.get("key"))
    return out



def fmt_evidence(ev: dict) -> list:
    """In bang chung cua 1 to hop (n/avgR/moc thoi gian + mau lenh te nhat & tot nhat)."""
    out = ["=== BANG CHUNG TO HOP | %s ===" % ev.get("key"),
           "  ma: %s | n=%s (thang %s / thua %s) | avgR=%s | pnl=%s"
           % (ev.get("code"), ev.get("n"), ev.get("wins"), ev.get("losses"),
              ev.get("avg_r"), ev.get("pnl")),
           "  thoi gian: %s -> %s (%.1f ngay)"
           % (_t(ev.get("first_ts")), _t(ev.get("last_ts")), _f(ev, "span_days"))]
    for label, rows in (("TE NHAT", ev.get("worst") or []), ("TOT NHAT", ev.get("best") or [])):
        if rows:
            out.append("  %s:" % label)
            for r in rows:
                out.append("    %s r=%+.3f pnl=%+.3f won=%s reason=%s"
                           % (_t(r.get("ts")), _f(r, "r"), _f(r, "pnl"),
                              r.get("won"), r.get("reason")))
    return out


def main(argv: list | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Trace 1 lenh: vi sao vao/dong, ai dong y, bai hoc nao")
    ap.add_argument("--pair", default="", help="cap (SOL hoac SOL/USDT:USDT)")
    ap.add_argument("--ts", type=float, default=None, help="moc OPEN (khop +-300s)")
    ap.add_argument("--key", default="", help="to hop dieu kien -> in bang chung (khong trace lenh)")
    ap.add_argument("--last", type=int, default=1, help="so lenh gan nhat (mac dinh 1)")
    ap.add_argument("--window-min", type=float, default=20.0,
                    help="cua so gom phieu hoi dong quanh luc mo lenh (phut)")
    ap.add_argument("--journal", default=DEFAULT_JOURNAL)
    ap.add_argument("--lessons", default=DEFAULT_LESSONS)
    ap.add_argument("--managed", default=DEFAULT_MANAGED)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.key:
        import lessons as LES
        ev = LES.evidence(args.journal, args.key)
        if args.json:
            print(json.dumps(ev, ensure_ascii=False, indent=1))
            return 0 if ev.get("n") else 2
        print("\n".join(fmt_evidence(ev)))
        if not ev.get("n"):
            print("  (khong co lenh nao khop to hop nay trong journal)")
            return 2
        return 0

    if not args.pair and args.ts is None:
        ap.error("can --pair hoac --ts (hoac --key)")
    trades = find_trades(args.journal, pair=args.pair, ts=args.ts, last=args.last)
    if not trades:
        print("khong tim thay lenh nao khop (pair=%r ts=%s)" % (args.pair, args.ts))
        return 2
    out_all = []
    for t in trades:
        tr = trace(args.journal, t, window_min=args.window_min, managed_path=args.managed)
        bk = bucket_of(t, args.lessons)
        if args.json:
            out_all.append({"pair": tr["pair"], "open": tr["open"],
                            "votes": tr["votes"], "setups": tr["setups"],
                            "reviews": tr["reviews"], "position": tr["position"],
                            "bucket": bk})
        else:
            out_all += fmt_trace(tr, bk) + [""]
    if args.json:
        print(json.dumps(out_all, ensure_ascii=False, indent=1))
    else:
        print("\n".join(out_all).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

