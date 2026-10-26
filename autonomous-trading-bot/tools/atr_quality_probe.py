"""Do CHAT LUONG proxy bien dong (ATR) bang du lieu THAT cua chinh bot (26/10).

Y tuong lay tu Kronos (foundation model K-line, §21 REPO_IDEAS): **truoc khi nghi toi model
nang (torch + weight 25-100M), phai tra loi cau hoi RE HON**: *"ATR(15m) — thu ta dang dung
de dat SL/TP — co phan anh dung bien dong that cua gia khong?"*
Neu ATR da tot ⇒ khong can model; neu do ⇒ co SO LIEU de mo lai de xuat Kronos.

Do duoc (KHONG can mang):
  1) `sl_pct`  = |entry - sl| / entry           (khoang cach ke hoach, % gia)
  2) `mfe_r`   = bien do THUAN dat duoc (bot tu ghi trong CLOSE)  ⇒ tinh bang R
  3) `mfe_pct` = mfe_r x sl_pct                  (bien do thuan that, % gia)
  4) `cost_r`  = (2 x (phi + slippage) x notional) / risk_usdt   (chi phi quy ra R)
⇒ Cau hoi cot loi: **bien do thuan that (mfe_r) co vuot chi phi (cost_r) va co cham toi
muc tieu ke hoach khong?** Neu mfe_r p90 << 1R thi SL/TP dat theo ATR dang RONG hon nhieu
so voi bien do gia thuc su di.

Them `--with-exchange --sample N`: lay OHLCV 15m tu san, tinh ATR(14) TAI thoi diem vao lenh
cho N lenh mau ⇒ do tuong quan hang (Spearman) giua `atr_pct` va `mfe_pct` + ty le
`mfe_pct / atr_pct`. Ty le ~1 ⇒ ATR phan anh dung bien do; << 1 ⇒ ATR phong dai.

Chay:
    python tools/atr_quality_probe.py                      # TESTNET, offline
    python tools/atr_quality_probe.py --target live        # LIVE (atb-live/logs/journal.jsonl)
    python tools/atr_quality_probe.py --with-exchange --sample 40
    python tools/atr_quality_probe.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

FEE_PCT = 0.0005      # 0.05%/chieu (taker) => 0.10% khu hoi
SLIP_PCT = 0.0002     # 0.02%/chieu — gia dinh truot gia market order


def load_journal(path: Path) -> tuple:
    """(opens, closes) tu journal.jsonl — dung convention cua `monitor_report`."""
    opens: list = []
    closes: list = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rec = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "OPEN":
                    opens.append(rec)
                elif rec.get("event") == "CLOSE":
                    closes.append(rec)
    except OSError:
        return [], []
    return opens, closes


def match_pairs(opens: list, closes: list) -> list:
    """Ghep OPEN<->CLOSE theo FIFO cung cap (giong `monitor_report.match_pairs`)."""
    pool: dict = {}
    for o in opens:
        pool.setdefault(str(o.get("pair")), []).append(o)
    pairs: list = []
    for c in closes:
        sym = str(c.get("pair"))
        q = pool.get(sym) or []
        pairs.append((q.pop(0) if q else {}, c))
    return pairs


def sl_pct(open_rec: dict) -> float:
    """Khoang cach SL ke hoach tinh theo % gia vao lenh."""
    try:
        e = float(open_rec.get("entry") or 0.0)
        s = float(open_rec.get("sl") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return abs(e - s) / e if e > 0 and s > 0 else 0.0


def mfe_pct(open_rec: dict, close_rec: dict) -> float:
    """Bien do THUAN that (% gia) = mfe_r x khoang cach SL ke hoach."""
    try:
        m = float(close_rec.get("mfe_r") or 0.0)
    except (TypeError, ValueError):
        m = 0.0
    return max(0.0, m) * sl_pct(open_rec)


def cost_r(open_rec: dict, *, fee_pct: float = FEE_PCT, slip_pct: float = SLIP_PCT) -> float:
    """Chi phi (phi + slippage 2 chieu) quy ra R: cost / risk_usdt.

    Dung `risk_usdt` neu OPEN co ghi; khong thi tinh lai = |entry - sl| x qty.
    """
    try:
        qty = float(open_rec.get("qty") or 0.0)
        entry = float(open_rec.get("entry") or 0.0)
    except (TypeError, ValueError):
        return 0.0
    notional = qty * entry
    if notional <= 0:
        return 0.0
    try:
        risk = float(open_rec.get("risk_usdt") or 0.0)
    except (TypeError, ValueError):
        risk = 0.0
    if risk <= 0:
        risk = abs(entry - float(open_rec.get("sl") or 0.0)) * qty
    if risk <= 0:
        return 0.0
    return 2.0 * (float(fee_pct) + float(slip_pct)) * notional / risk


def _rank(xs: list) -> list:
    """Hang (trung binh cho gia tri bang nhau) — de tinh Spearman khong can scipy."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: list, ys: list) -> float:
    """Tuong quan hang Spearman (0.0 neu khong du mau / phuong sai = 0)."""
    pairs = [(float(x), float(y)) for x, y in zip(xs or [], ys or [])
             if x is not None and y is not None]
    n = len(pairs)
    if n < 3:
        return 0.0
    a = _rank([p[0] for p in pairs])
    b = _rank([p[1] for p in pairs])
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return round(num / (da * db), 4) if da > 0 and db > 0 else 0.0


def pct(vals: list, q: float) -> float:
    """Phan vi (q trong [0,1]) — tra 0.0 neu rong."""
    xs = sorted(float(v) for v in (vals or []) if v is not None)
    if not xs:
        return 0.0
    i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
    return round(xs[i], 4)


def atr_from_ohlcv(ohlcv: list, period: int = 14) -> list:
    """ATR Wilder tren chuoi OHLCV [[ts, o, h, l, c, v], ...] -> list ATR cung do dai."""
    out: list = []
    prev_close = None
    atr = None
    for row in ohlcv or []:
        try:
            h, l, c = float(row[2]), float(row[3]), float(row[4])
        except (IndexError, TypeError, ValueError):
            out.append(atr or 0.0)
            continue
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        atr = tr if atr is None else (atr * (period - 1) + tr) / period
        out.append(round(float(atr), 8))
        prev_close = c
    return out


def atr_pct_at(ohlcv: list, ts: float, *, period: int = 14) -> float:
    """ATR(period) tai (hoac ngay truoc) moc `ts`, quy ve % gia dong cua cung nen."""
    if not ohlcv:
        return 0.0
    idx = 0
    for i, row in enumerate(ohlcv):
        try:
            if float(row[0]) / 1000.0 <= float(ts):
                idx = i
        except (IndexError, TypeError, ValueError):
            continue
    atrs = atr_from_ohlcv(ohlcv[: idx + 1], period)
    if not atrs:
        return 0.0
    try:
        close = float(ohlcv[idx][4])
    except (IndexError, TypeError, ValueError):
        return 0.0
    a = float(atrs[-1] or 0.0)
    return round(a / close, 6) if close > 0 and a > 0 else 0.0


def summarize(pairs: list, *, fee_pct: float = FEE_PCT, slip_pct: float = SLIP_PCT,
              atr_pcts: list | None = None) -> dict:
    """Tong hop so lieu: khoang cach SL, bien do thuan, chi phi (quy ra R)."""
    sls, mfes, costs, moves = [], [], [], []
    for o, c in pairs:
        s = sl_pct(o)
        if s <= 0:
            continue
        sls.append(s)
        mfes.append(float(c.get("mfe_r") or 0.0))
        costs.append(cost_r(o, fee_pct=fee_pct, slip_pct=slip_pct))
        moves.append(mfe_pct(o, c))
    out = {
        "n": len(sls),
        "sl_pct_med": pct(sls, 0.5), "sl_pct_p90": pct(sls, 0.9),
        "mfe_r_med": pct(mfes, 0.5), "mfe_r_p90": pct(mfes, 0.9),
        "mfe_r_p10": pct(mfes, 0.1),
        "mfe_pct_med": pct(moves, 0.5),
        "cost_r_med": pct(costs, 0.5), "cost_r_p90": pct(costs, 0.9),
        "fee_pct": fee_pct, "slip_pct": slip_pct,
    }
    if atr_pcts:
        usable = [a for a in atr_pcts if a and a > 0]
        out["n_atr"] = len(usable)
        out["atr_pct_med"] = pct(usable, 0.5)
        if len(usable) == len(moves):
            out["spearman_atr_vs_mfe"] = spearman(usable, moves)
            ratio = [m / a for m, a in zip(moves, usable) if a > 0]
            out["mfe_over_atr_med"] = pct(ratio, 0.5)
            out["mfe_over_atr_p90"] = pct(ratio, 0.9)
    return out


def verdict(s: dict) -> str:
    """1 dong ket luan: ATR/proxy co dung khong, SL co rong qua khong."""
    n = int(s.get("n") or 0)
    if n < 20:
        return "chua du mau (n=%d < 20) -> chay tiep" % n
    med, p90 = float(s["mfe_r_med"]), float(s["mfe_r_p90"])
    cost = float(s["cost_r_med"])
    parts = []
    if p90 < 1.0:
        parts.append("bien do THUAN p90 chi %.2fR < 1R => muc tieu/SL dang RONG hon bien do gia "
                     "thuc su di (bot gan nhu khong bao gio cham TP ke hoach)" % p90)
    if med < cost * 3:
        parts.append("bien do thuan TRUNG VI %.2fR chi ~%.1fx chi phi (%.3fR) => bien do "
                     "khong du day de tra chi phi + dat loi nhuan" % (med, med / cost if cost else 0, cost))
    if s.get("mfe_over_atr_med"):
        r = float(s["mfe_over_atr_med"])
        parts.append("mfe/ATR trung vi %.2f (%s)"
                     % (r, "ATR phan anh dung bien do" if r >= 0.8 else
                        "ATR PHONG DAI bien do thuc (nen xem lai SL/TP theo ATR)"))
    if s.get("spearman_atr_vs_mfe") is not None:
        parts.append("Spearman(ATR%% vs bien do thuan)=%.2f" % float(s["spearman_atr_vs_mfe"]))
    return " | ".join(parts) if parts else "khong thay bat thuong ro rang"


def report_text(s: dict, label: str) -> str:
    lines = [
        "=== CHAT LUONG ATR / BIEN DONG | %s | n=%d ===" % (label, s.get("n", 0)),
        "  khoang cach SL ke hoach : trung vi %.2f%% | p90 %.2f%%"
        % (float(s["sl_pct_med"]) * 100, float(s["sl_pct_p90"]) * 100),
        "  bien do THUAN (R)       : p10 %.2f | trung vi %.2f | p90 %.2f"
        % (s["mfe_r_p10"], s["mfe_r_med"], s["mfe_r_p90"]),
        "  bien do thuan (%% gia)   : trung vi %.2f%%" % (float(s["mfe_pct_med"]) * 100),
        "  chi phi quy ra R        : trung vi %.3f | p90 %.3f  (phi %.2f%% + slippage %.2f%%/chieu)"
        % (s["cost_r_med"], s["cost_r_p90"], float(s["fee_pct"]) * 100,
           float(s["slip_pct"]) * 100),
    ]
    if s.get("n_atr"):
        lines.append("  ATR(14,15m) tai entry   : trung vi %.3f%% (n=%d) | Spearman=%.2f | mfe/ATR=%.2f"
                     % (float(s["atr_pct_med"]) * 100, s["n_atr"],
                        float(s.get("spearman_atr_vs_mfe") or 0.0),
                        float(s.get("mfe_over_atr_med") or 0.0)))
    lines.append("  KET LUAN: %s" % verdict(s))
    return "\n".join(lines)


def fetch_atr_pcts(pairs: list, fetch, *, period: int = 14, lookback: int = 200,
                   cache: dict | None = None) -> list:
    """ATR% tai entry cho tung cap (o, c). `fetch(symbol, since_ms, limit)` tiem duoc (test).

    Cache theo (symbol, gio) — nhieu lenh cung cap trong cung gio thi dung lai 1 lan goi.
    """
    out: list = []
    cache = {} if cache is None else cache
    for o, c in pairs:
        sym = str(o.get("pair") or c.get("pair") or "")
        try:
            ts = float(o.get("ts") or 0.0)
        except (TypeError, ValueError):
            ts = 0.0
        if not sym or ts <= 0:
            out.append(0.0)
            continue
        key = (sym, int(ts // 3600))
        if key not in cache:
            since = int((ts - lookback * 900) * 1000)
            try:
                cache[key] = fetch(sym, since, lookback + period + 5) or []
            except Exception:  # noqa: BLE001
                cache[key] = []
        out.append(atr_pct_at(cache[key], ts, period=period))
    return out


def exchange_fetch(base: Path):
    """Ham `fetch(symbol, since_ms, limit)` bang client ccxt cua instance (CHI DOC san)."""
    import orders_audit as OA
    env = OA.read_env(Path(base) / ".env")
    live = str(env.get("BINANCE_TESTNET", "true")).lower() in ("false", "0", "no")
    cli = OA.build_client(env, live)

    def fetch(symbol, since_ms, limit):
        return cli.fetch_ohlcv(str(symbol), "15m", since=int(since_ms), limit=int(limit))
    return fetch


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="Do chat luong ATR/bien dong bang du lieu THAT cua bot (chi doc)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--journal", default="", help="mac dinh: logs/journal.jsonl cua instance")
    ap.add_argument("--limit", type=int, default=0, help="chi lay N lenh GAN NHAT (0 = het)")
    ap.add_argument("--fee-pct", type=float, default=FEE_PCT, help="phi moi chieu (0.0005)")
    ap.add_argument("--slip-pct", type=float, default=SLIP_PCT, help="slippage moi chieu")
    ap.add_argument("--with-exchange", action="store_true",
                    help="lay ATR(14,15m) THAT tai entry (goi san, cham hon)")
    ap.add_argument("--sample", type=int, default=40,
                    help="so lenh lay ATR that (chi khi --with-exchange)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    base = ROOT if args.target == "testnet" else LIVE_DIR
    jp = Path(args.journal) if args.journal else (base / "logs" / "journal.jsonl")
    opens, closes = load_journal(jp)
    pairs = [(o, c) for o, c in match_pairs(opens, closes) if sl_pct(o) > 0]
    if args.limit:
        pairs = pairs[-args.limit:]

    atr_pcts = None
    if args.with_exchange and pairs:
        pairs = pairs[-max(1, int(args.sample)):]
        try:
            atr_pcts = fetch_atr_pcts(pairs, exchange_fetch(base))
        except Exception as e:  # noqa: BLE001
            print("[WARN] khong lay duoc ATR tu san: %s" % str(e)[:120])

    s = summarize(pairs, fee_pct=args.fee_pct, slip_pct=args.slip_pct, atr_pcts=atr_pcts)
    s.update({"target": args.target, "journal": str(jp)})
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    else:
        print(report_text(s, "%s | %s" % (args.target.upper(), jp.name)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
