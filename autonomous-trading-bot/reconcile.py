"""P0-reconcile: doi chieu journal voi FILL THAT tren san de ghi bu CLOSE bi thieu.

Van de (phat hien 2026-09-30): journal co 53 OPEN nhung chi 35 CLOSE. Khi bot
(khong phai lenh treo) dung/chet trong luc dang mo vi the, san van dong vi the
bang SL/TP -> khong ai ghi CLOSE -> monitor_report thieu lenh (n / WR / PF /
LONG-SHORT) => gate LIVE bi lech, co the "de" hon thuc te.

VI SAO KHONG DUNG FIFO CUA monitor_report: FIFO ghep CLOSE voi OPEN cu nhat.
Khi mot vai lenh dong KHONG duoc ghi (bot tat), moi CLOSE sau do bi lech mot nhip
-> OPEN nao "mo coi" theo FIFO KHONG phai la OPEN thieu ghi (kiem chung 30/09:
11/16 OPEN "mo coi" thuc ra DA CO CLOSE ghi, chi la bi ghep lech). Vi vay phai
lay FILL THAT lam chuan:

    1) Tai tao lai tung VONG LENH (position round-trip) tu fill san: di theo
       khoi luong co dau (+ mua / - ban), moi khi vi the ve 0 -> 1 vong lenh
       gom entry/exit/qty/thoi gian/PnL THAT (FIFO lot accounting).
    2) Ghep vong lenh do voi OPEN trong journal (symbol, huong, gia vao, qty,
       thoi gian trong sai so cho phep). Khong ghep duoc -> la lenh KHONG do bot
       mo (vi du lenh tay cua nguoi) -> BO QUA, khong dua vao thong ke.
    3) Vong lenh nao da co CLOSE trong journal (gia thoat + thoi gian khop) ->
       da ghi, bo qua. Con lai = ghi bu CLOSE.

Cong thuc R/PnL dung lai trade_mgmt.trade_result (cac leg dong truoc leg cuoi
vao booked_pnl nhu partial) -> so lieu ghi bu KHOP dinh dang bot ghi that.

Nguyen tac an toan:
- CHI ghi log. KHONG sua risk_state/kill-switch, KHONG gui lenh len san.
- Khong co fill -> khong ghi (khong bao gio suy dien ket qua).
- Vi the con MO tren san -> bo qua (chua dong thi khong ghi).
- Ban ghi ghi bu duoc danh dau reconciled=true + recon_src=exchange -> loc duoc.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from journal import log_trade
from monitor_report import load_journal
from trade_mgmt import FEE_ROUNDTRIP_PCT, ManagedTrade, trade_result

LOOKBACK_DAYS = 7                 # Binance chi tra userTrades toi da 7 ngay/lan
BINANCE_WINDOW_MS = 7 * 86400 * 1000
ENTRY_TOL_PCT = 0.003             # gia vao vong lenh vs OPEN: lech toi da 0.3%
QTY_TOL = 0.02                    # khoi luong lech toi da 2%
OPEN_TS_TOL_MS = 600_000          # ts OPEN (gio local) vs fill: lech toi da 10 phut
CLOSE_TS_TOL_MS = 30 * 60 * 1000  # da co CLOSE trong +/-30 phut => coi nhu da ghi
EXIT_TOL_PCT = 0.005              # gia thoat lech toi da 0.5% (bot ghi gia quan sat)
DEDUPE_TS_MS = 60_000             # cung symbol/huong/qty + thoat lech <= 60s = da ghi
STATE_PATH = "logs/reconcile_state.json"


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def journal_records(path: str = "logs/journal.jsonl") -> tuple:
    """(opens, closes) — dung lai quy uoc cua monitor_report."""
    return load_journal(path)


def orphan_opens(path: str = "logs/journal.jsonl") -> list:
    """CHAN DOAN: OPEN chua ghep duoc CLOSE theo FIFO (khong dung de ghi bu).

    Con so nay chi de so sanh voi ket qua doi chieu fill (ben duoi) — neu hai
    con so lech nhau nhieu thi journal da bi lech thoi diem ghi CLOSE.
    """
    from monitor_report import match_pairs
    opens, closes = load_journal(path)
    _pairs, still = match_pairs(opens, closes)
    return sorted(still, key=lambda o: float(o.get("ts") or 0))


def norm_fills(rows) -> list:
    """Chuan hoa fetch_my_trades (ccxt + info) -> list fill de tai tao vong lenh."""
    out: list = []
    for r in rows or []:
        info = r.get("info") or {}
        try:
            qty = float(r.get("amount") or info.get("qty") or 0)
            price = float(r.get("price") or info.get("price") or 0)
            ts = int(r.get("timestamp") or info.get("time") or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0 or price <= 0 or ts <= 0:
            continue
        fee = r.get("fee") or {}
        out.append({
            "symbol": r.get("symbol") or info.get("symbol"),
            "side": str(r.get("side") or info.get("side") or "").upper(),
            "qty": qty, "price": price, "ts": ts,
            "order_id": str(r.get("order") or info.get("orderId") or ""),
            "pnl_exchange": _f(info.get("realizedPnl")),
            "fee": _f(fee.get("cost") if isinstance(fee, dict) else None)
                   or _f(info.get("commission")),
        })
    return sorted(out, key=lambda f: f["ts"])


def fetch_fills(ex, symbols, days: int = LOOKBACK_DAYS, log=None) -> list:
    """Fill THAT tu san cho cac symbol (chia cua so 7 ngay vi Binance gioi han)."""
    client = getattr(ex, "_client", None)
    if client is None or not symbols:
        return []
    out: list = []
    now_ms = int(time.time() * 1000)
    for sym in symbols:
        s = now_ms - int(days * 86400 * 1000)
        while s < now_ms:
            end = min(s + BINANCE_WINDOW_MS, now_ms)
            try:
                rows = client.fetch_my_trades(sym, s, 1000)
            except Exception as e:  # noqa: BLE001
                if log:
                    log.warning("reconcile: fetch_my_trades %s loi: %s", sym,
                                str(e)[:160])
                break
            if not rows:
                break
            out.extend(norm_fills(rows))
            if end - s < BINANCE_WINDOW_MS:
                break
            s = end
    return sorted(out, key=lambda f: f["ts"])


def _episode(sym: str, side: int, entry_legs: list, exit_legs: list) -> dict:
    """Gop cac leg thanh 1 vong lenh (gia vao/ra binh quan theo khoi luong)."""
    q_in = sum(f["qty"] for f in entry_legs) or 1e-12
    q_out = sum(f["qty"] for f in exit_legs) or 1e-12
    return {
        "symbol": sym, "direction": "LONG" if side > 0 else "SHORT",
        "qty": q_in,
        "entry_px": sum(f["price"] * f["qty"] for f in entry_legs) / q_in,
        "exit_px": sum(f["price"] * f["qty"] for f in exit_legs) / q_out,
        "open_ts": min(f["ts"] for f in entry_legs),
        "close_ts": max(f["ts"] for f in exit_legs),
        "exit_qty": q_out,
        "realized_pnl": sum(f["pnl_exchange"] for f in exit_legs),
        "entry_legs": list(entry_legs), "exit_legs": list(exit_legs),
    }


def build_episodes(fills, symbols=None) -> tuple:
    """Tai tao cac vong lenh da dong tu fill -> (episodes, vi_the_con_mo).

    Di theo khoi luong CO DAU (+ mua / - ban, FIFO lot). Moi khi vi the ve 0 ->
    1 vong lenh hoan tat. Phan con lai = vi the dang mo (tra rieng, khong ghi bu).

    Luu y: neu cua so fill bat dau GIUA mot vi the (mo truoc do), vong lenh dau
    tien cua symbol do se bi lech va gan nhu chac chan KHONG khop OPEN nao ->
    roi vao `unmatched` -> bi bo qua (an toan).
    """
    by_sym: dict = {}
    for f in sorted(fills, key=lambda x: x["ts"]):
        if symbols is None or f["symbol"] in symbols:
            by_sym.setdefault(f["symbol"], []).append(f)
    episodes: list = []
    still_open: list = []
    for sym, fs in by_sym.items():
        side = 0
        lots: list = []           # [qty, price, ts] dang mo
        entry_legs: list = []
        exit_legs: list = []
        for f in fs:
            signed = f["qty"] if f["side"] == "BUY" else -f["qty"]
            if side == 0:
                side = 1 if signed > 0 else -1
            if (signed > 0) == (side > 0):      # mo them / dao chieu (khong xay ra voi bot)
                lots.append([f["qty"], f["price"], f["ts"]])
                entry_legs.append(f)
                continue
            rem = f["qty"]                        # dong bot vi the (FIFO)
            while rem > 1e-12 and lots:
                take = min(lots[0][0], rem)
                lots[0][0] -= take
                rem -= take
                if lots[0][0] <= 1e-12:
                    lots.pop(0)
            exit_legs.append(f)
            if not lots:
                episodes.append(_episode(sym, side, entry_legs, exit_legs))
                side, entry_legs, exit_legs = 0, [], []
        if lots:
            q = sum(l[0] for l in lots) or 1e-12
            still_open.append({
                "symbol": sym, "direction": "LONG" if side > 0 else "SHORT",
                "qty": q, "entry_px": sum(l[1] * l[0] for l in lots) / q,
                "open_ts": min(l[2] for l in lots),
            })
    episodes.sort(key=lambda e: e["close_ts"])
    return episodes, still_open



def pair_episodes_to_opens(episodes: list, opens: list) -> tuple:
    """Ghep vong lenh (tu san) voi OPEN trong journal -> (matched, unmatched).

    Dieu kien khop: cung symbol + huong, qty lech <= 2%, gia vao lech <= 0.3%,
    thoi gian mo lenh lech <= 10 phut. Moi OPEN chi dung 1 lan (chon sat nhat).
    """
    used: set = set()
    matched: list = []
    unmatched: list = []
    for ep in sorted(episodes, key=lambda e: e["open_ts"]):
        best, best_d = None, None
        for i, o in enumerate(opens):
            if i in used:
                continue
            if str(o.get("pair") or o.get("symbol")) != ep["symbol"]:
                continue
            if str(o.get("direction") or "").upper() != ep["direction"]:
                continue
            q = _f(o.get("qty"))
            if q <= 0 or abs(q - ep["qty"]) / q > QTY_TOL:
                continue
            e0 = _f(o.get("entry"))
            if e0 <= 0 or abs(e0 - ep["entry_px"]) / e0 > ENTRY_TOL_PCT:
                continue
            d = abs(int(_f(o.get("ts")) * 1000) - ep["open_ts"])
            if d > OPEN_TS_TOL_MS:
                continue
            if best_d is None or d < best_d:
                best, best_d = i, d
        if best is None:
            unmatched.append(ep)
        else:
            used.add(best)
            matched.append((opens[best], ep))
    return matched, unmatched


def already_recorded(ep: dict, closes: list) -> bool:
    """Vong lenh nay da co ban ghi CLOSE trong journal chua (gia + thoi gian)?

    So theo GIA LEG CUOI: bot ghi `exit_price` = gia no quan sat tai thoi diem
    thoat (khong phai gia binh quan cua vong lenh), nen so voi gia binh quan se
    truot -> chay lai se ghi trung. Them nhanh chong trung chat (cung symbol +
    huong + qty, thoi gian lech <= 60s) de `reconcile --apply` IDEMPOTENT.
    """
    last_px = _f(ep["exit_legs"][-1]["price"]) if ep.get("exit_legs") else 0.0
    for c in closes:
        if str(c.get("pair") or c.get("symbol")) != ep["symbol"]:
            continue
        if str(c.get("direction") or "").upper() != ep["direction"]:
            continue
        d_ts = abs(int(_f(c.get("ts")) * 1000) - ep["close_ts"])
        q = _f(c.get("qty"))
        if d_ts <= DEDUPE_TS_MS and q > 0 and abs(q - ep["qty"]) / q <= QTY_TOL:
            return True
        if d_ts > CLOSE_TS_TOL_MS:
            continue
        x = _f(c.get("exit_price"))
        if x > 0 and last_px > 0 and abs(x - last_px) / last_px <= EXIT_TOL_PCT:
            return True
    return False


def build_close(op: dict, legs: list, now: float | None = None) -> dict:
    """Ban ghi CLOSE ghi bu cho 1 OPEN (legs = fill dong, da sort theo ts).

    Dung lai trade_result: cac leg truoc leg cuoi vao `booked_pnl` (nhu partial),
    leg cuoi la lenh thoat -> R/PnL tinh y het bot ghi that.
    """
    direction = str(op.get("direction") or "").upper()
    entry = _f(op.get("entry"))
    init_qty = _f(op.get("qty"))
    sl = _f(op.get("sl"))
    tp = _f(op.get("tp"))
    sign = 1.0 if direction == "LONG" else -1.0
    booked = sum(sign * (f["price"] - entry) * f["qty"] * (1.0 - FEE_ROUNDTRIP_PCT)
                 for f in legs[:-1])
    last = legs[-1]
    mt = ManagedTrade(symbol=str(op.get("pair") or op.get("symbol") or "?"),
                      direction=direction, entry=entry, qty=last["qty"], sl=sl, tp=tp,
                      initial_sl=sl, init_qty=init_qty, partial_done=len(legs) > 1,
                      booked_pnl=booked, mfe_r=0.0)
    reason = infer_reason(op, last["price"])
    res = trade_result(mt, reason, last["price"])
    return {
        "ts": last["ts"] / 1000.0, "event": "CLOSE",
        "pair": op.get("pair") or op.get("symbol"), "direction": direction,
        "timeframe": op.get("timeframe"), "entry": entry, "qty": init_qty,
        "exit_price": last["price"], "r": res["r"], "won": bool(res["won"]),
        "pnl": res["pnl"], "reason": reason, "partial": bool(res["partial_done"]),
        "mfe_r": None,
        # ---- dau vet ghi bu (loc duoc khi can so lieu "sach") ----
        "reconciled": True, "recon_src": "exchange", "recon_legs": len(legs),
        "recon_filled_qty": round(sum(f["qty"] for f in legs), 10),
        "recon_pnl_exchange": round(sum(f["pnl_exchange"] for f in legs), 6),
        "recon_at": now or time.time(),
    }


def infer_reason(op: dict, exit_price: float, tol_pct: float = 0.002) -> str:
    """Doan SL/TP tu gia thoat (chi de hien thi; 'won'/R luon tinh tu pnl)."""
    sl = _f(op.get("sl"))
    tp = _f(op.get("tp"))
    if tp > 0 and abs(exit_price - tp) <= abs(tp) * tol_pct:
        return "TP"
    if sl > 0 and abs(exit_price - sl) <= abs(sl) * tol_pct:
        return "SL"
    return "CLOSE"


def plan_backfill(opens: list, closes: list, fills: list, now: float | None = None) -> dict:
    """Doi chieu fill voi journal -> ke hoach ghi bu (KHONG ghi gi o day)."""
    episodes, still_open = build_episodes(fills)
    matched, unmatched = pair_episodes_to_opens(episodes, opens)
    todo, done = [], []
    for o, ep in matched:
        (done if already_recorded(ep, closes) else todo).append((o, ep))
    todo.sort(key=lambda x: x[1]["close_ts"])
    return {
        "episodes": len(episodes), "open_positions": still_open,
        "matched": len(matched), "already": len(done),
        "unmatched_episodes": unmatched,          # khong co OPEN -> bo qua
        "closes": [build_close(o, ep["exit_legs"], now=now) for o, ep in todo],
        "todo_pairs": todo,
    }


def apply_closes(path: str, closes: list, backup: bool = True) -> dict:
    """Ghi bu cac ban ghi CLOSE vao journal (backup 1 lan truoc khi ghi)."""
    if not closes:
        return {"written": 0, "backup": None}
    bak = None
    if backup and os.path.exists(path):
        bak = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        try:
            with open(path, "r", encoding="utf-8") as src, \
                    open(bak, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        except Exception:  # noqa: BLE001
            bak = None
    n = 0
    for rec in closes:
        log_trade(path, **rec)  # 'ts' trong rec thang time.time() cua log_trade
        n += 1
    return {"written": n, "backup": bak}


def _load_state(path: str = STATE_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _save_state(state: dict, path: str = STATE_PATH) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except Exception:  # noqa: BLE001
        pass


def reconcile(cfg, ex, log=None, apply: bool = True, now: float | None = None,
              fills: list | None = None, state_path: str | None = None) -> dict:
    """Chay 1 lan doi chieu + ghi bu. Tra summary (KHONG bao gio nem loi ra ngoai).

    Throttle: bo qua neu lan chay truoc cach day < cfg.reconcile_min_interval_sec
    (supervisor spawn lai nhieu lan -> khong goi API lien tuc).
    """
    now = now or time.time()
    path = getattr(cfg, "journal_path", "logs/journal.jsonl")
    st_path = state_path or STATE_PATH
    every = int(getattr(cfg, "reconcile_min_interval_sec", 3600) or 0)
    last = _f(_load_state(st_path).get("last_run"))
    if every > 0 and last and (now - last) < every:
        return {"skipped": "vua chay %.0fs truoc" % (now - last), "written": 0}
    opens, closes = journal_records(path)
    if not opens:
        return {"orphans": 0, "episodes": 0, "written": 0}
    days = int(getattr(cfg, "reconcile_days", LOOKBACK_DAYS) or LOOKBACK_DAYS)
    syms = sorted({str(o.get("pair") or o.get("symbol")) for o in opens})
    if fills is None:
        fills = fetch_fills(ex, syms, days=days, log=log)
    plan = plan_backfill(opens, closes, fills, now=now)
    # Vi the con MO tren san thi khong the co fill dong -> bo qua cho chac
    try:
        open_qty = {p.get("symbol"): abs(_f(p.get("contracts")))
                    for p in ex.fetch_positions(syms)}
    except Exception:  # noqa: BLE001
        open_qty = {}
    todo = [(o, ep) for o, ep in plan["todo_pairs"]
            if _f(open_qty.get(ep["symbol"])) <= 0]
    rep = {"orphans": len(orphan_opens(path)), "episodes": plan["episodes"],
           "matched": plan["matched"], "already": plan["already"],
           "unmatched": len(plan["unmatched_episodes"]),
           "fills": len(fills), "matched_open": len(todo), "written": 0}
    if apply and todo:
        rep.update(apply_closes(path, [build_close(o, ep["exit_legs"], now=now)
                                       for o, ep in todo]))
    _save_state({"last_run": now, "episodes": rep["episodes"],
                 "written": rep["written"], "matched": rep["matched_open"]}, st_path)
    if log:
        log.warning("RECONCILE: %d fill -> %d vong lenh | khop OPEN=%d | da ghi=%d | "
                    "ghi bu=%d | bo qua=%d%s", rep["fills"], rep["episodes"],
                    rep["matched"], rep["already"], rep["matched_open"],
                    rep["unmatched"], "" if apply else " [DRY-RUN]")
        for ep in plan["unmatched_episodes"][:5]:
            log.info("  reconcile: vong lenh khong co OPEN trong journal: %s %s qty=%.6g "
                     "entry=%.6g luc %s -> bo qua", ep["symbol"], ep["direction"],
                     ep["qty"], ep["entry_px"],
                     time.strftime("%Y-%m-%d %H:%M", time.gmtime(ep["open_ts"] / 1000)))
    return {**plan, **rep}


def active_symbols(cfg) -> tuple:
    """Danh sach cap dang quet (uy quyen cho turbo_demo.active_symbols)."""
    try:
        from turbo_demo import active_symbols as _a
        return _a(cfg)
    except Exception:  # noqa: BLE001
        return tuple(getattr(cfg, "symbols", ()) or ())


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Doi chieu journal voi fill san, ghi bu CLOSE bi thieu")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--apply", action="store_true",
                    help="ghi that (mac dinh chi xem truoc, KHONG sua gi)")
    ap.add_argument("--days", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--json", default="", help="ghi bao cao JSON ra file")
    args = ap.parse_args(argv)

    from config import Settings
    from exchange import BinanceFutures
    cfg = Settings()
    ex = BinanceFutures(cfg.api_key, cfg.api_secret, cfg.testnet, dry_run=False)
    opens, closes = journal_records(args.journal)
    print("=" * 94)
    print(f"RECONCILE | journal={args.journal} | OPEN={len(opens)} CLOSE={len(closes)} | "
          f"OPEN mo coi (FIFO, chan doan)={len(orphan_opens(args.journal))} | "
          f"apply={args.apply} | days={args.days}")
    print("=" * 94)
    if not cfg.api_key or not cfg.api_secret:
        print("Thieu BINANCE_API_KEY/SECRET trong .env -> khong doc duoc fill.")
        return 2
    syms = sorted({str(o.get("pair") or o.get("symbol")) for o in opens})
    fills = fetch_fills(ex, syms, days=args.days)
    plan = plan_backfill(opens, closes, fills)
    print(f"fill doc duoc={len(fills)} | vong lenh tai tao={plan['episodes']} | "
          f"khop OPEN={plan['matched']} | da co CLOSE={plan['already']} | "
          f"can ghi bu={len(plan['closes'])}")
    for c in plan["closes"]:
        print("  + %s %-14s %-5s entry=%-12.6g exit=%-12.6g qty=%-10.6g R=%+7.4f "
              "pnl=%+9.4f won=%-5s legs=%d (san: %+.4f)"
              % (time.strftime("%Y-%m-%d %H:%M", time.gmtime(c["ts"])), c["pair"],
                 c["direction"], c["entry"], c["exit_price"], c["qty"], c["r"],
                 c["pnl"], c["won"], c["recon_legs"], c["recon_pnl_exchange"]))
    for ep in plan["unmatched_episodes"]:
        print("  - vong lenh KHONG co OPEN trong journal (lenh tay / ngoai cua so): "
              "%s %-5s qty=%.6g entry=%.6g %s -> bo qua"
              % (ep["symbol"], ep["direction"], ep["qty"], ep["entry_px"],
                 time.strftime("%Y-%m-%d %H:%M", time.gmtime(ep["open_ts"] / 1000))))
    for p in plan["open_positions"]:
        print("  - vi the con MO (khong ghi): %s %s qty=%.6g entry=%.6g"
              % (p["symbol"], p["direction"], p["qty"], p["entry_px"]))
    if args.apply and plan["closes"]:
        rep = apply_closes(args.journal, plan["closes"])
        print(f"\nDA GHI {rep['written']} ban ghi CLOSE (backup: {rep['backup']})")
        print("Chay lai `python monitor_report.py` de xem n/PF/LONG-SHORT moi.")
    elif plan["closes"]:
        print("\n(chua ghi gi — them --apply de ghi that)")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"closes": plan["closes"],
                       "unmatched": plan["unmatched_episodes"],
                       "open_positions": plan["open_positions"],
                       "fills": len(fills)}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


