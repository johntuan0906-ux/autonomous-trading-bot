"""close_dust.py — dong vi the BUI (notional < 5 USDT) theo quy trinh DA DO that.

Chay:
  python tools\\close_dust.py                      # TESTNET, DRY-RUN (chi in ke hoach)
  python tools\\close_dust.py --apply              # TESTNET, dong that
  python tools\\close_dust.py --target live --apply --yes-live

Quy trinh (lay tu `skills/close-dust/SKILL.md`, do that 11/11 tren AXS):
  1. `reduceOnly` bi tu choi `-2022`; market khong reduceOnly bi tu choi `-4164` (notional < 5)
  2. **Nang vi the cung chieu len >= 6 USDT** (du bien so voi muc 5), roi
  3. **Dong TOAN BO** qua `exchange.close_position` (ham nay tu xu ly `-2022` bang `_close_exact`)
  4. Doc lai: vi the phai ve 0; neu khong thi ghi ro ma loi, KHONG thu lai vo han.

Vi sao co tool thay vi lam tay: lam tay 7 vi the = 7 lan tinh qty + 7 lan doc lai, va cai sai
o buoc "nang" se TAO them vi the. Tool nay: mac dinh DRY-RUN, `--limit`, va voi LIVE phai them
`--yes-live` (2 lop xac nhan).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import orders_audit as OA           # noqa: E402  (read_env / load_dust / build_client)

MIN_NOTIONAL = 5.0
RAISE_TO = 6.0                      # nang len 6 USDT: du bien so voi 5, phi khong dang ke


def plan_raise(notional: float, min_notional: float = MIN_NOTIONAL,
               target: float = RAISE_TO) -> float:
    """So USDT can THEM de vuot minNotional (0 = khong phai bui / khong can nang)."""
    n = float(notional or 0.0)
    if n <= 0 or n >= float(min_notional):
        return 0.0
    return max(0.0, float(target) - n)


def add_order_usdt(need: float, min_notional: float = MIN_NOTIONAL) -> float:
    """(20/11, B-070) USDT cho CHINH lenh NANG — phai >= minNotional.

    Binance kiem tra notional cua **tung lenh**, khong chi cua vi the sau khi nang. Do that
    TESTNET 21/11: NEAR 2.87 USDT, can them 3.13 (len 6) ⇒ `-4164 Order's notional must be no
    smaller than 5` ⇒ vi the bui khong bao gio dong duoc. Nay lenh nang >= 5 USDT.
    """
    return max(float(need or 0.0), float(min_notional))


def dust_positions(positions: list, dust=None,
                   min_notional: float = MIN_NOTIONAL) -> list:
    """Loc ra vi the BUI (0 < notional < minNotional). `dust` = tap symbol da ghi dust_skip."""
    known = {str(s) for s in (dust or set())}
    out = []
    for p in positions or []:
        try:
            qty = abs(float(p.get("contracts") or 0))
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        try:
            notional = abs(float(p.get("notional") or 0))
        except (TypeError, ValueError):
            notional = 0.0
        if notional <= 0:
            try:
                px = float(p.get("markPrice") or p.get("entryPrice") or 0)
            except (TypeError, ValueError):
                px = 0.0
            notional = qty * px
        if notional <= 0 or notional >= float(min_notional):
            continue
        side = str(p.get("side") or "").lower()
        direction = "LONG" if side in ("long", "buy") else "SHORT"
        out.append({"symbol": str(p.get("symbol") or ""), "direction": direction,
                    "qty": qty, "notional": round(notional, 4),
                    "in_skip": str(p.get("symbol")) in known})
    out.sort(key=lambda r: r["notional"])
    return out


def close_one(ex, pos: dict, *, apply: bool = False,
              min_notional: float = MIN_NOTIONAL, target: float = RAISE_TO,
              log=print) -> dict:
    """Nang roi dong 1 vi the bui. Tra {symbol, ok, added, qty_total, left, why}."""
    sym, direction = pos["symbol"], pos["direction"]
    res = {"symbol": sym, "ok": False, "added": 0.0, "qty_total": pos.get("qty"),
           "left": None, "why": ""}
    need = plan_raise(pos.get("notional"), min_notional, target)
    if need <= 0:
        res["why"] = "khong phai bui (notional >= %.2f)" % float(min_notional)
        return res
    try:
        price = float(ex.last_price(sym))
    except Exception as e:  # noqa: BLE001
        res["why"] = "khong lay duoc gia: %s" % str(e)[:120]
        return res
    if price <= 0:
        res["why"] = "gia = 0"
        return res
    try:
        add_qty = float(ex.quantize_qty(sym, add_order_usdt(need, min_notional) / price))
    except Exception as e:  # noqa: BLE001
        res["why"] = "khong quantize duoc: %s" % str(e)[:120]
        return res
    # (20/11, B-070) sau khi lam tron, notional cua lenh nang van phai >= minNotional
    _usdt = add_order_usdt(need, min_notional)
    for _ in range(3):
        if add_qty <= 0 or add_qty * price >= float(min_notional):
            break
        _usdt *= 1.5
        try:
            add_qty = float(ex.quantize_qty(sym, _usdt / price))
        except Exception:  # noqa: BLE001
            break
    res["added"] = add_qty
    if add_qty <= 0:
        res["why"] = "qty nang = 0 (step qua lon so voi von can bu)"
        return res
    if add_qty * price < float(min_notional):
        res["why"] = ("lenh nang %.8f (~%.2f USDT) van duoi minNotional %.2f "
                      "— step qua lon, phai dong tay" % (add_qty, add_qty * price,
                                                         min_notional))
        return res
    plan = ("%s %s: bui %.2f USDT -> nang +%.8f (~%.2f USDT) roi dong toan bo"
            % (sym, direction, pos.get("notional") or 0.0, add_qty, add_qty * price))
    if not apply:
        res["why"] = "DRY-RUN: " + plan
        log("  [DRY] " + plan)
        return res
    try:
        ex.market_entry(sym, direction, add_qty)           # cung chieu ⇒ tang vi the
        qty_now = ex.position_qty(sym, direction)
        total = float(qty_now) if qty_now else float(pos.get("qty") or 0) + add_qty
        res["qty_total"] = total
        ex.close_position(sym, direction, total)           # dong TOAN BO (tu xu ly -2022)
        left = ex.position_qty(sym, direction)
        res["left"] = left
        res["ok"] = left is None or abs(float(left)) < 1e-12
        res["why"] = plan if res["ok"] else "van con %.8f sau khi dong" % float(left or 0)
    except Exception as e:  # noqa: BLE001
        res["why"] = "loi: %s" % str(e)[:160]
    log("  [%s] %s: %s" % ("OK" if res["ok"] else "LOI", sym, res["why"]))
    return res


def clear_skip(base: Path, symbols) -> int:
    """Xoa cac symbol da dong khoi `logs/dust_skip.json`. Tra so symbol da xoa."""
    drop = {str(s) for s in symbols or []}
    if not drop:
        return 0
    p = Path(base) / "logs" / "dust_skip.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return 0
    rows = (d.get("symbols") if isinstance(d, dict) else d) or []
    keep = [s for s in rows if str(s) not in drop]
    if len(keep) == len(rows):
        return 0
    out = ({**d, "symbols": keep} if isinstance(d, dict) else keep)
    try:
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        return 0
    return len(rows) - len(keep)


def prune_skip(base: Path, dust_symbols) -> list:
    """Ghi lai `dust_skip.json` = DUNG cac symbol dang la bui. Tra (truoc, sau).

    Vi sao (15/11): danh sach nay tich luy theo thoi gian; symbol da het bui (hoac da dong)
    van nam trong do ⇒ `orders_audit` in nhan "BUI" cho vi the TRẦN that ⇒ nguoi van hanh
    bo qua canh bao that. Prune = chi giu su that hien tai.
    """
    p = Path(base) / "logs" / "dust_skip.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        d = {"symbols": []}
    old = [str(s) for s in ((d.get("symbols") if isinstance(d, dict) else d) or [])]
    new = sorted({str(s) for s in (dust_symbols or [])})
    out = ({**d, "symbols": new} if isinstance(d, dict) else new)
    try:
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        return old, old
    return old, new


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Dong vi the BUI (notional < 5 USDT).")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--apply", action="store_true", help="dong THAT (mac dinh chi in)")
    ap.add_argument("--yes-live", action="store_true",
                    help="bat buoc khi --target live --apply")
    ap.add_argument("--min-notional", type=float, default=MIN_NOTIONAL)
    ap.add_argument("--raise-to", type=float, default=RAISE_TO)
    ap.add_argument("--limit", type=int, default=0, help="chi lam N vi the dau (0 = het)")
    ap.add_argument("--clear-skip", action="store_true",
                    help="sau khi dong, xoa symbol khoi logs/dust_skip.json")
    ap.add_argument("--prune-skip", action="store_true",
                    help="ghi lai dust_skip.json = dung cac symbol dang la bui (lam sach danh sach cu)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.target == "live" and args.apply and not args.yes_live:
        print("[TU CHOI] --target live --apply phai kem --yes-live (2 lop xac nhan)")
        return 2
    base = ROOT if args.target == "testnet" else LIVE_DIR
    env = OA.read_env(base / ".env")
    key = env.get("BINANCE_API_KEY") or ""
    sec = env.get("BINANCE_API_SECRET") or ""
    if not (key and sec):
        print("[LOI] thieu API key trong %s/.env" % base)
        return 2
    live = str(env.get("BINANCE_TESTNET", "true")).lower() in ("false", "0", "no")
    if (args.target == "live") != live:
        print("[CANH BAO] --target %s nhung .env ghi BINANCE_TESTNET=%s"
              % (args.target, env.get("BINANCE_TESTNET")))

    from exchange import BinanceFutures
    ex = BinanceFutures(api_key=key, api_secret=sec, testnet=not live, dry_run=False)
    try:
        raw = [p for p in ex.fetch_positions() if float(p.get("contracts") or 0) != 0]
    except Exception as e:  # noqa: BLE001
        print("[LOI] fetch_positions: %s" % str(e)[:150])
        return 1
    todo = dust_positions(raw, OA.load_dust(base), args.min_notional)
    if args.limit and args.limit > 0:
        todo = todo[:args.limit]
    print("=== DONG BUI | %s | %s | %d vi the bui (trong dust_skip: %d) ==="
          % (args.target.upper(), "APPLY" if args.apply else "DRY-RUN", len(todo),
             sum(1 for d in todo if d["in_skip"])))
    if args.prune_skip:
        old, new = prune_skip(base, [d["symbol"] for d in
                                     dust_positions(raw, None, args.min_notional)])
        print("  dust_skip: %d -> %d symbol (bo %d muc cu)"
              % (len(old), len(new), len(set(old) - set(new))))
    if not todo:
        print("  KET LUAN: khong co vi the bui")
        return 0
    done, ok = [], 0
    for pos in todo:
        r = close_one(ex, pos, apply=args.apply, min_notional=args.min_notional,
                      target=args.raise_to)
        done.append(r)
        ok += 1 if r["ok"] else 0
    if args.apply and args.clear_skip:
        n = clear_skip(base, [r["symbol"] for r in done if r["ok"]])
        print("  da xoa %d symbol khoi dust_skip.json" % n)
    if args.json:
        print(json.dumps(done, ensure_ascii=False, indent=1))
    planned = sum(1 for r in done if float(r.get("added") or 0) > 0)
    print("  KET LUAN: %s %d/%d"
          % ("dong duoc" if args.apply else "se dong duoc (co ke hoach)",
             ok if args.apply else planned, len(todo)))
    return 0 if ok == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main())
