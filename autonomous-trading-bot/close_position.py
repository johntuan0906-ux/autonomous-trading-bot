"""Dong vi the MO TAY tren tai khoan DEMO (testnet) — vi du BTC dang short 0.1812.

An toan:
  - TU CHOI chay neu BINANCE_TESTNET != true (khong bao gio dong lenh tien that
    bang script nay).
  - Market + reduceOnly, qty cat theo precision cua san (amount_to_precision).
  - --dry: chi in ke hoach, KHONG dat lenh.

Chay:
    python close_position.py --pair BTC/USDT:USDT          # dong that (demo)
    python close_position.py --pair BTC/USDT:USDT --dry    # xem truoc
"""
from __future__ import annotations

import argparse
import sys

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from config import Settings  # noqa: E402

SYM = "BTC/USDT:USDT"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dong vi the mo tay tren DEMO")
    ap.add_argument("--pair", default=SYM)
    ap.add_argument("--dry", action="store_true", help="chi in, khong dat lenh")
    args = ap.parse_args(argv)

    cfg = Settings()
    if not cfg.testnet or not cfg.api_key:
        print("[TU CHOI] chi chay tren DEMO: can BINANCE_TESTNET=true + co API key.")
        return 2
    import ccxt  # type: ignore

    cli = ccxt.binance({"apiKey": cfg.api_key, "secret": cfg.api_secret,
                        "options": {"defaultType": "future"}, "enableRateLimit": True})
    cli.enable_demo_trading(True)

    poss = [p for p in cli.fetch_positions([args.pair])
            if float(p.get("contracts") or 0) != 0]
    if not poss:
        print(f"khong co vi the nao dang mo tren {args.pair} — khong can dong.")
        return 0
    p = poss[0]
    qty = abs(float(p["contracts"]))
    side = "buy" if str(p.get("side")) == "short" else "sell"
    m = cli.market(args.pair)
    dec = (m.get("precision") or {}).get("amount")
    lim = (m.get("limits") or {})
    q = float(cli.amount_to_precision(args.pair, qty))
    print(f"vi the : {str(p.get('side')).upper()} qty={qty} entry={p.get('entryPrice')} "
          f"mark={p.get('markPrice')} uPnL={p.get('unrealizedPnl')}")
    print(f"market : stepPrecision={dec} minAmount={(lim.get('amount') or {}).get('min')} "
          f"minNotional={(lim.get('cost') or {}).get('min')}")
    print(f"ke hoach: {side.upper()} MARKET qty={q} reduceOnly=True")
    if q <= 0 or q < float(((lim.get("amount") or {}).get("min") or 0)):
        print("[DUNG] qty sau khi cat < minAmount — khong the dong bang lenh.")
        return 3
    if args.dry:
        print("[dry] chua dat lenh.")
        return 0

    o = cli.create_order(args.pair, "market", side, q, None, {"reduceOnly": True})
    print("order  :", {k: o.get(k) for k in ("id", "status", "filled", "average",
                                             "clientOrderId")})
    left = [x for x in cli.fetch_positions([args.pair])
            if float(x.get("contracts") or 0) != 0]
    if left:
        print(f"[CON LAI] {left[0]['side']} qty={abs(float(left[0]['contracts']))} "
              "(duoi 1 step cua san nen khong the dong bang lenh)")
    else:
        print("[XONG] da dong het vi the", args.pair)
    return 0


if __name__ == "__main__":
    sys.exit(main())
