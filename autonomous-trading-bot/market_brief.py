"""BẢN TIN thị trường để bạn theo dõi & quyết định (chỉ ĐỌC, KHÔNG đặt lệnh).

    python market_brief.py            # tin tuc + sentiment + boi canh + vi the + vi sao chua vao lenh
    python market_brief.py --no-news  # bo phan tin tuc (nhanh, khong goi RSS)
    python market_brief.py --json     # them 1 dong JSON cho may doc

Gồm 5 phần:
1. TIN TỨC & SENTIMENT  — score -1..1, so bai, tin URGENT, top tieu de (RSS + GDELT, khong can key)
2. BỐI CẢNH THEO CẶP    — gia, ATR%, regime, funding/OI (du lieu that tu san)
3. VỊ THẾ & RỦI RO      — equity that, so vi the, notional, tran risk
4. VÌ SAO CHƯA VÀO LỆNH — doc vong quet cuoi trong logs/turbo_err.log (SKIP_OPEN/SKIP_RISK/BLOCKED_*)
5. BOT HỌC ĐƯỢC GÌ      — logs/learner.json: so cap nhat + trong so lon nhat (dau = uu tien)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ERRLOG = ROOT / "logs" / "turbo_err.log"


def news_section(cfg) -> dict:
    """Tin tức + sentiment (RSS/GDELT; CryptoPanic nếu có token)."""
    out: dict = {"score": None, "n": 0, "urgent": 0, "headlines": [], "err": ""}
    try:
        from sentiment import SentimentCache
        ttl = int(getattr(cfg, "sentiment_cache_sec", 120) or 120)
        tok = str(getattr(cfg, "cryptopanic_token", "") or "")
        r = SentimentCache(ttl_sec=ttl).get(tok)
        out.update(score=float(r.score), n=int(r.n_articles),
                   urgent=int(getattr(r, "urgent_bearish", 0) or 0),
                   headlines=list(getattr(r, "headlines", []) or [])[:6])
    except Exception as e:  # noqa: BLE001
        out["err"] = str(e)[:160]
    return out


def learner_section(path: str | Path = "logs/learner.json", top: int = 6) -> dict:
    """Bot đã học gì: số cập nhật + trọng số lớn nhất (dấu + = có lợi, - = nên tránh)."""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"n": 0, "top": [], "bias": None}
    w = d.get("w") or {}
    items = sorted(w.items(), key=lambda kv: -abs(float(kv[1])))
    return {"n": int(d.get("n") or 0), "bias": round(float(d.get("b") or 0.0), 3),
            "top": [(k, round(float(v), 3)) for k, v in items[:top]]}


def parse_last_round(text: str) -> dict:
    """Lấy vòng quét CUỐI trong log: `round N monitor={...} -> [{'symbol':..,'status':..}]`."""
    rows: list = []
    rnd = 0
    for m in re.finditer(r"round (\d+) monitor=\S* -> (\[.*?\])\s*$", text, re.M):
        rnd = int(m.group(1))
        body = m.group(2)
        rows = []
        for s in re.finditer(r"'symbol': '([^']+)', 'status': '([^']+)'"
                             r"(?:, 'reason': '([^']*)')?", body):
            rows.append({"symbol": s.group(1), "status": s.group(2),
                         "reason": s.group(3) or ""})
    return {"round": rnd, "rows": rows}


def context_rows(cfg, ex, *, with_deriv: bool = True) -> list:
    """Bối cảnh thật theo từng cặp: giá, ATR%, regime (+ funding/OI)."""
    from indicators import atr, market_regime
    syms = list(getattr(cfg, "symbols", ()) or ()) + list(getattr(cfg, "extra_symbols", ()) or ())
    out: list = []
    for sym in syms:
        row: dict = {"symbol": sym, "price": None, "atr_pct": None, "regime": "", "err": ""}
        try:
            import pandas as pd
            raw = ex.fetch_ohlcv(sym, getattr(cfg, "timeframe", "15m"),
                                 limit=int(getattr(cfg, "ohlcv_limit", 200) or 200))
            # ccxt tra list[[ts,o,h,l,c,v]] -> DataFrame (giong exchange.fetch_ohlcv cua bot)
            df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
            px = float(df["close"].iloc[-1])
            row["price"] = px
            row["atr_pct"] = round(float(atr(df, int(getattr(cfg, "atr_period", 14))).iloc[-1])
                                   / max(px, 1e-9), 5)
            row["regime"] = str((market_regime(df) or {}).get("regime", ""))
        except Exception as e:  # noqa: BLE001
            row["err"] = str(e)[:80]
        if with_deriv:
            try:
                from derivatives import fetch_oi_funding
                d = fetch_oi_funding(sym) or {}
                row["funding"] = d.get("funding")
                row["oi_change"] = d.get("oi_change_pct") or d.get("oi_change")
            except Exception:  # noqa: BLE001
                pass
        out.append(row)
    return out


def last_round_from_log(path: str | Path = ERRLOG, tail_bytes: int = 400_000) -> dict:
    """Vòng quét cuối trong `logs/turbo_err.log` (đọc phần đuôi file)."""
    p = Path(path)
    try:
        with open(p, "rb") as f:
            try:
                f.seek(-min(tail_bytes, p.stat().st_size), 2)
            except OSError:
                f.seek(0)
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return {"round": 0, "rows": []}
    return parse_last_round(text)


def positions_section(cfg, ex) -> dict:
    """Vị thế THẬT + rủi ro đang dùng (chỉ đọc)."""
    out: dict = {"equity": None, "positions": [], "notional": 0.0, "err": ""}
    try:
        from state_sync import real_equity_usdt
        out["equity"] = real_equity_usdt(cfg)
    except Exception as e:  # noqa: BLE001
        out["err"] = str(e)[:120]
    try:
        for p in ex.fetch_positions() or []:
            c = abs(float(p.get("contracts") or 0))
            if c <= 0:
                continue
            ntl = abs(float(p.get("notional") or 0))
            out["positions"].append({"symbol": p.get("symbol"), "side": p.get("side"),
                                     "qty": c, "notional": round(ntl, 3),
                                     "uPnL": round(float(p.get("unrealizedPnl") or 0), 4)})
            out["notional"] += ntl
    except Exception as e:  # noqa: BLE001
        out["err"] = (out["err"] + " | " + str(e)[:100]).strip(" |")
    out["notional"] = round(out["notional"], 3)
    return out


def render(rep: dict) -> str:
    L: list = []
    L.append("=" * 78)
    L.append("BAN TIN THI TRUONG | %s | che do=%s"
             % (rep["ts_human"], "TESTNET" if rep["testnet"] else "LIVE"))
    L.append("=" * 78)
    nw = rep.get("news") or {}
    L.append("1) TIN TUC & SENTIMENT")
    if nw.get("err"):
        L.append("   (khong lay duoc tin: %s)" % nw["err"])
    else:
        L.append("   sentiment=%+.3f (-1..1) | so bai=%s | tin URGENT bearish=%s"
                 % (float(nw.get("score") or 0.0), nw.get("n"), nw.get("urgent")))
        for h in (nw.get("headlines") or [])[:5]:
            L.append("   - %s" % str(h)[:110])
    L.append("")
    L.append("2) BOI CANH THEO CAP (du lieu that)")
    for r in rep.get("context") or []:
        if r.get("err"):
            L.append("   %-16s LOI: %s" % (r["symbol"], r["err"]))
            continue
        extra = ""
        if r.get("funding") is not None:
            extra += " funding=%s" % r["funding"]
        if r.get("oi_change") is not None:
            extra += " OI_chg=%s" % r["oi_change"]
        L.append("   %-16s px=%-10s ATR=%.3f%% regime=%-12s%s"
                 % (r["symbol"], r.get("price"), 100.0 * float(r.get("atr_pct") or 0),
                    r.get("regime") or "-", extra))
    L.append("")
    ps = rep.get("positions") or {}
    L.append("3) VI THE & RUI RO")
    L.append("   equity that=%s USDT | vi the mo=%d | tong notional=%.2f | cap risk=%s%%"
             % (ps.get("equity"), len(ps.get("positions") or []),
                float(ps.get("notional") or 0),
                getattr(rep.get("cfg"), "max_total_risk_pct", "?")))
    for p in ps.get("positions") or []:
        L.append("   %-16s %-5s qty=%-10s notional=%-8s uPnL=%+s"
                 % (p["symbol"], p["side"], p["qty"], p["notional"], p["uPnL"]))
    if ps.get("err"):
        L.append("   (canh bao doc vi: %s)" % ps["err"])
    L.append("")
    lr = rep.get("last_round") or {}
    L.append("4) VI SAO CHUA VAO LENH (vong quet cuoi: round %s)" % lr.get("round"))
    if not lr.get("rows"):
        L.append("   (chua doc duoc vong quet trong logs/turbo_err.log)")
    for r in lr.get("rows") or []:
        why = (" — %s" % r["reason"]) if r.get("reason") else ""
        L.append("   %-16s %s%s" % (r["symbol"], r["status"], why[:90]))
    L.append("")
    ln = rep.get("learner") or {}
    L.append("5) BOT HOC DUOC GI (learner n=%s bias=%s)" % (ln.get("n"), ln.get("bias")))
    for k, v in ln.get("top") or []:
        L.append("   %-12s %+0.3f  (%s)" % (k, v,
                 "co loi -> uu tien" if v > 0 else "bat loi -> tranh"))
    L.append("=" * 78)
    return "\n".join(L)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ban tin thi truong (chi doc)")
    ap.add_argument("--no-news", action="store_true", help="bo phan tin tuc (nhanh)")
    ap.add_argument("--no-deriv", action="store_true", help="bo funding/OI")
    ap.add_argument("--json", action="store_true", help="in them 1 dong JSON")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    import time as _t
    from config import Settings
    import restart_when_flat as RWF
    cfg = Settings()
    ex = RWF.make_exchange(cfg)
    rep = {"ts_human": _t.strftime("%d/%m/%Y %H:%M:%S"), "testnet": bool(cfg.testnet),
           "cfg": cfg, "news": {} if args.no_news else news_section(cfg),
           "context": context_rows(cfg, ex, with_deriv=not args.no_deriv),
           "positions": positions_section(cfg, ex), "last_round": last_round_from_log(),
           "learner": learner_section()}
    print(render(rep))
    if args.json:
        small = {k: rep[k] for k in ("ts_human", "testnet", "news", "context", "positions",
                                     "last_round", "learner")}
        print(json.dumps(small, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
