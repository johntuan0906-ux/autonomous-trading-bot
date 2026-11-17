"""perf_report.py — 8 chi so hieu nang tinh tu JOURNAL THAT (khong tu backtest).

Chay:
  python tools\\perf_report.py                          # instance TESTNET, 30 ngay
  python tools\\perf_report.py --instance live --days 90
  python tools\\perf_report.py --json                   # may doc
  python tools\\perf_report.py --split setup            # tach theo setup_type / market_regime

8 chi so (dung dinh nghia chuan, khong tu nghi):
  CAGR · Sharpe · Sortino · Calmar · Max drawdown · Ulcer index · Profit factor · Expectancy

Vi sao can: `monitor_report.py` tra loi "dang lai/lo bao nhieu" (WR/PF/R), con cai nay tra loi
"hieu nang co TOT theo thoi gian khong" — cung 1 PF nhung drawdown 40% la khac hoan toan
drawdown 8%. Moi chi so tinh tren DUONG EQUITY THEO NGAY (khong phai tung lenh) tru PF/expectancy.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BALANCE = 1000.0
PERIODS = 365.0          # crypto: quy doi nam = 365 ngay


def journal_for(instance: str = "testnet") -> Path:
    """Journal cua instance (`live` nam o thu muc khac — xem `tools/restart_bot.instance_dir`)."""
    inst = str(instance or "testnet").strip().lower()
    if inst in ("testnet", "demo", ""):
        return ROOT / "logs" / "journal.jsonl"
    try:
        import restart_bot as RB       # noqa: WPS433 (tool cung thu muc)
        return Path(RB.instance_dir("LIVE")) / "logs" / "journal.jsonl"
    except Exception:  # noqa: BLE001
        return ROOT.parent / "atb-live" / "logs" / "journal.jsonl"


def rows(path) -> list:
    """Doc journal -> list dict (bo qua dong hong, khong lam hong ca bao cao)."""
    out = []
    p = Path(path)
    if not p.is_file():
        return out
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def closes(all_rows: list) -> list:
    """Ban ghi CLOSE (hoac ban ghi co `won`/`r` khong phai OPEN), sap theo thoi gian."""
    out = [r for r in all_rows
           if str(r.get("event") or "") == "CLOSE"
           or ("won" in r and str(r.get("event") or "") != "OPEN")]
    out.sort(key=lambda r: float(r.get("ts") or 0.0))
    return out


def attach_context(all_rows: list, close_rows: list) -> list:
    """Gan `setup_type` / `market_regime` tu ban ghi OPEN cung cap (FIFO) vao moi CLOSE."""
    pend: dict = {}
    for r in all_rows:
        if "entry" in r and str(r.get("event") or "") == "OPEN":
            key = str(r.get("pair") or r.get("symbol") or "")
            pend.setdefault(key, []).append(r)
    out = []
    for c in close_rows:
        rec = dict(c)
        key = str(rec.get("pair") or rec.get("symbol") or "")
        queue = pend.get(key) or []
        o = queue.pop(0) if queue else {}
        if o:
            rec.setdefault("setup_type", o.get("setup_type"))
            rec.setdefault("market_regime", o.get("market_regime"))
        rec["_bot"] = bool(o)          # (15/11) co OPEN tuong ung => lenh cua BOT (khong phai lenh tay)
        rec["_pair"] = key
        out.append(rec)
    return out


def _pnl(r: dict) -> float:
    try:
        return float(r.get("pnl") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _r(r: dict) -> float:
    try:
        return float(r.get("r") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def daily_pnl(close_rows: list) -> list:
    """[(ngay UTC 'YYYY-MM-DD', tong pnl)] sap tang dan."""
    import datetime as dt
    buckets: dict = {}
    for r in close_rows:
        ts = float(r.get("ts") or 0.0)
        if ts <= 0:
            continue
        day = dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%d")
        buckets[day] = buckets.get(day, 0.0) + _pnl(r)
    return sorted(buckets.items())


def equity_curve(daily: list, start: float) -> list:
    """Duong equity THEO NGAY, **gom ca diem xuat phat** (neu khong, ngay dau lo nang se lam
    `peak` bat dau tu so am ⇒ maxDD = 0 sai — da gap that tren journal TESTNET).
    """
    eq, out = float(start), [float(start)]
    for _day, pnl in daily:
        eq += float(pnl)
        out.append(eq)
    return out


def drawdowns(equity: list) -> list:
    """% drawdown tai tung diem so voi dinh truoc do."""
    peak, out = None, []
    for v in equity:
        peak = v if peak is None else max(peak, v)
        out.append(0.0 if not peak else max(0.0, (peak - v) / peak * 100.0))
    return out


def max_drawdown(equity: list) -> float:
    return max(drawdowns(equity) or [0.0])


def ulcer_index(equity: list) -> float:
    dd = drawdowns(equity)
    return math.sqrt(sum(x * x for x in dd) / len(dd)) if dd else 0.0


def daily_returns(daily: list, start: float) -> list:
    """Loi nhuan theo ngay tren equity DAU NGAY (dung mau so truoc khi cong pnl ngay do)."""
    out, eq = [], float(start)
    for _day, pnl in daily:
        out.append((float(pnl) / eq) if eq else 0.0)
        eq += float(pnl)
    return out


def sharpe(rets: list, periods: float = PERIODS) -> float:
    if len(rets) < 2:
        return 0.0
    sd = statistics.pstdev(rets)
    return 0.0 if sd <= 0 else statistics.fmean(rets) / sd * math.sqrt(periods)


def sortino(rets: list, periods: float = PERIODS) -> float:
    """Sortino: chi phat bien dong AM (downside deviation), khong phat bien dong len.

    (15/11) Can **>= 2 ngay lo** moi in so: voi 1 ngay lo, mau so ~0 nen Sortino nhay len hang
    nghin (do that tren journal LIVE: 1483) — con so do khong dung de so sanh, nen tra 0 va ghi note.
    """
    if not rets:
        return 0.0
    down = [x for x in rets if x < 0]
    if len(down) < 2:
        return 0.0
    dd = math.sqrt(sum(x * x for x in down) / len(rets))
    return 0.0 if dd <= 0 else statistics.fmean(rets) / dd * math.sqrt(periods)


def cagr(start: float, end: float, days: float, periods: float = PERIODS) -> float:
    """% nam (quy doi tu so ngay CO DU LIEU, khong phai tu 1 nam)."""
    if start <= 0 or end <= 0 or days <= 0:
        return 0.0
    return ((end / start) ** (periods / float(days)) - 1.0) * 100.0


def calmar(cagr_pct: float, maxdd_pct: float) -> float:
    """CAGR / MaxDD. MaxDD < 0,05% (lam tron 0,00%) thi tra 0 — khong in so hang nghin."""
    return 0.0 if float(maxdd_pct) < 0.05 else float(cagr_pct) / float(maxdd_pct)


def profit_factor(pnls: list) -> tuple:
    """(PF, tong lai, tong lo duong). PF = ∞ neu khong co lenh lo nao."""
    win = sum(x for x in pnls if x > 0)
    loss = -sum(x for x in pnls if x < 0)
    if loss <= 0:
        return (float("inf") if win > 0 else 0.0), win, loss
    return win / loss, win, loss


def expectancy(rs: list) -> float:
    """R ky vong moi lenh (don vi R, khong phai USDT)."""
    return statistics.fmean(rs) if rs else 0.0


def stats(rs: list, pnls: list) -> dict:
    n = len(pnls)
    wins = [x for x in pnls if x > 0]
    pf, gw, gl = profit_factor(pnls)
    return {"n": n, "winrate": (len(wins) / n * 100.0) if n else 0.0,
            "pnl": sum(pnls), "pf": pf, "gross_win": gw, "gross_loss": gl,
            "exp_r": expectancy(rs), "exp_pnl": (sum(pnls) / n) if n else 0.0}


def _notes(rets: list, maxdd: float) -> list:
    """Ghi ro vi sao mot chi so la 0/khong in — de lan sau khong ai doc nham la 'an toan'."""
    out = []
    if sum(1 for x in rets if x < 0) < 2:
        out.append("Sortino=0 vi < 2 ngay lo (mau so qua nho => so se vo nghia)")
    if float(maxdd) < 0.05:
        out.append("Calmar=0 vi MaxDD < 0,05% (lam tron 0,00%)")
    if len(rets) < 2:
        out.append("Sharpe=0 vi < 2 ngay co lenh")
    return out


def split_by(close_rows: list, key: str) -> dict:
    """Tach theo `setup_type` hoac `market_regime` (FIFO tu OPEN, thieu thi ghi '?' )."""
    groups: dict = {}
    for r in close_rows:
        k = str(r.get(key) or "?")
        groups.setdefault(k, []).append(r)
    return {k: stats([_r(x) for x in v], [_pnl(x) for x in v]) for k, v in groups.items()}


def build(close_rows: list, start_balance: float = DEFAULT_BALANCE,
          days: float = 30.0, now: float = None, bot_only: bool = False) -> dict:
    """Tinh toan bo 8 chi so + tach nhom. `close_rows` da gan context (`attach_context`).

    `bot_only=True` (15/11, RESEARCH_1115): chi tinh lenh co OPEN tuong ung — loai lenh tay.
    """
    import time as _t
    t_now = float(now if now is not None else _t.time())
    if bot_only:
        close_rows = [r for r in close_rows if r.get("_bot")]
    if days and days > 0:
        close_rows = [r for r in close_rows
                      if float(r.get("ts") or 0.0) >= t_now - float(days) * 86400.0]
    daily = daily_pnl(close_rows)
    eq = equity_curve(daily, start_balance)
    rets = daily_returns(daily, start_balance)
    end = eq[-1] if eq else float(start_balance)
    span = len(daily) or 0
    cg = cagr(start_balance, end, span)
    mdd = max_drawdown(eq)
    pnls = [_pnl(r) for r in close_rows]
    rs = [_r(r) for r in close_rows]
    base = stats(rs, pnls)
    insolvent = bool(eq) and min(eq) <= 0.0
    return {
        "days": span, "trades": base["n"], "start_balance": float(start_balance),
        "end_balance": end, "return_pct": (end / start_balance - 1.0) * 100.0
        if start_balance else 0.0,
        "cagr_pct": cg, "sharpe": sharpe(rets), "sortino": sortino(rets),
        "calmar": calmar(cg, mdd), "max_dd_pct": mdd, "ulcer_pct": ulcer_index(eq),
        "pf": base["pf"], "winrate": base["winrate"], "exp_r": base["exp_r"],
        "exp_pnl": base["exp_pnl"], "pnl": base["pnl"],
        # Hai co "so lieu khong dang tin" — bao ra thay vi im lang (dung lop loi B-047/B-050)
        "insolvent": insolvent,
        "r_pnl_mismatch": (base["exp_r"] > 0) != (base["exp_pnl"] > 0) and base["n"] > 0,
        "notes": _notes(rets, mdd),
        "by_setup": split_by(close_rows, "setup_type"),
        "by_regime": split_by(close_rows, "market_regime"),
        "equity": eq, "daily": daily,
    }


def _num(v, nd: int = 2) -> str:
    if isinstance(v, float) and math.isinf(v):
        return "inf"
    return ("%." + str(nd) + "f") % float(v or 0.0)


def render(rep: dict) -> str:
    """Bao cao van xuoi ngan (so lieu lay tu `build`)."""
    L = ["=== PERF | %d ngay | %d lenh | von %.0f -> %.2f USDT (%.2f%%) ==="
         % (rep["days"], rep["trades"], rep["start_balance"], rep["end_balance"],
            rep["return_pct"]),
         "  CAGR %s%% · Sharpe %s · Sortino %s · Calmar %s"
         % (_num(rep["cagr_pct"]), _num(rep["sharpe"]), _num(rep["sortino"]),
            _num(rep["calmar"])),
         "  MaxDD %s%% · Ulcer %s%% · PF %s · WR %s%% · ky vong %sR/lenh (%s USDT)"
         % (_num(rep["max_dd_pct"]), _num(rep["ulcer_pct"]), _num(rep["pf"]),
            _num(rep["winrate"], 1), _num(rep["exp_r"], 3), _num(rep["exp_pnl"], 3))]
    for label, key in (("SETUP", "by_setup"), ("REGIME", "by_regime")):
        rows_ = rep.get(key) or {}
        if not rows_:
            continue
        L.append("  %s:" % label)
        for name, s in sorted(rows_.items(), key=lambda kv: -kv[1]["n"]):
            L.append("    %-22s n=%3d WR=%5.1f%% PF=%6s ky vong=%+.3fR pnl=%+.2f"
                     % (name[:22], s["n"], s["winrate"], _num(s["pf"], 2),
                        s["exp_r"], s["pnl"]))
    if rep.get("r_pnl_mismatch"):
        L.append("  CANH BAO: ky vong R va ky vong USDT NGUOC DAU ⇒ so lieu journal khong dang tin"
                 " (xem `reconcile.py`: lenh tay lan vao journal, B-050)")
    if rep.get("insolvent"):
        L.append("  CANH BAO: von da ve <= 0 trong cua so nay ⇒ %/CAGR/Calmar vo nghia;"
                 " doi `--balance` cho dung von ban dau")
    for n in rep.get("notes") or []:
        L.append("  GHI CHU: %s" % n)
    return "\n".join(L)


def main(argv=None) -> int:
    try:                      # console Windows (cp1252) khong in duoc '⇒'/'·' -> khong duoc no
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="8 chi so hieu nang tu journal that.")
    ap.add_argument("--instance", default="testnet", choices=("testnet", "live"))
    ap.add_argument("--journal", default="", help="duong dan journal (bo qua --instance)")
    ap.add_argument("--days", type=float, default=30.0, help="cua so ngay (0 = tat ca)")
    ap.add_argument("--balance", type=float, default=DEFAULT_BALANCE, help="von ban dau")
    ap.add_argument("--split", default="", choices=("", "setup", "regime"))
    ap.add_argument("--bot-only", action="store_true",
                    help="chi tinh lenh co OPEN tuong ung (loai lenh tay khoi journal)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.journal) if args.journal else journal_for(args.instance)
    all_rows = rows(path)
    close_rows = attach_context(all_rows, closes(all_rows))
    rep = build(close_rows, start_balance=args.balance, days=args.days,
                bot_only=bool(args.bot_only))
    if args.split == "setup":
        rep = {**rep, "by_regime": {}}
    elif args.split == "regime":
        rep = {**rep, "by_setup": {}}
    if args.json:
        print(json.dumps({k: v for k, v in rep.items()
                          if k not in ("equity", "daily")}, ensure_ascii=False, indent=2,
                         default=str))
        return 0
    print(render(rep))
    print("  (journal: %s%s)" % (path, " · CHI LENH BOT" if args.bot_only else " · gop ca lenh tay"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

