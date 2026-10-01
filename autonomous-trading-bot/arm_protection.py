"""Trang thai bao ve SL/TP + ARM LAI cho cac vi the dang mo tren DEMO.

Vi sao can: Binance DEMO co luc tra `-4045 Reach max stop order limit` cho MOI lenh
stop (du so lenh treo = 0) -> bot KHONG dat duoc SL/TP tren san. Khi do vi the chi
duoc bao ve bang MONITOR PHAN MEM (bot tu dong khi gia cham SL/TP) — chi an toan khi
bot dang chay. Tien ich nay de:
  1) xem vi the nao dang co/khong co SL-TP tren san;
  2) thu arm lai (khi san cho phep tro lai), lay SL/TP tu logs/managed_state.json.

CHI DOC + arm cho vi the DANG MO tren DEMO. Khong mo them vi the, khong dong vi the.

    python arm_protection.py              # xem trang thai
    python arm_protection.py --arm        # thu arm lai SL/TP
"""
from __future__ import annotations

import argparse
import json
import time

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from config import Settings  # noqa: E402


def _client(cfg):
    import ccxt  # type: ignore
    cli = ccxt.binance({"apiKey": cfg.api_key, "secret": cfg.api_secret,
                        "options": {"defaultType": "future"}, "enableRateLimit": True})
    cli.enable_demo_trading(True)
    cli.options["fetchOpenOrders"] = {"warnWithoutSymbol": False}
    return cli


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bao ve SL/TP tren DEMO")
    ap.add_argument("--arm", action="store_true", help="thu arm lai SL/TP")
    args = ap.parse_args(argv)

    cfg = Settings()
    if not cfg.testnet or not cfg.api_key:
        print("[TU CHOI] chi chay tren DEMO (BINANCE_TESTNET=true + co API key).")
        return 2
    cli = _client(cfg)
    poss = [p for p in cli.fetch_positions() if float(p.get("contracts") or 0) != 0]
    try:
        orders = cli.fetch_open_orders()
    except Exception as e:  # noqa: BLE001
        orders = []
        print("[WARN] khong doc duoc lenh treo:", str(e)[:120])
    per_sym: dict = {}
    for o in orders:
        per_sym.setdefault(o.get("symbol"), []).append(o)

    print(f"VI THE: {len(poss)} | LENH TREO: {len(orders)}")
    missing = []
    for p in poss:
        s = p.get("symbol")
        n = len(per_sym.get(s, []))
        flag = "" if n else "   <-- KHONG co SL/TP tren san"
        if not n:
            missing.append(s)
        print(f"  {s:18} {str(p.get('side')).upper():5} qty={p.get('contracts')} "
              f"lenh treo={n}{flag}")
    if not args.arm:
        if missing:
            print(f"\n{len(missing)} vi the khong co bao ve tren san: {missing}")
            print("Bot van bao ve bang MONITOR phan mem. Thu lai: "
                  "python arm_protection.py --arm")
        return 0

    ms = json.load(open("logs/managed_state.json", encoding="utf-8"))
    trades = ms.get("trades") or {}
    ok = fail = 0
    for p in poss:
        sym = p.get("symbol")
        qty = abs(float(p["contracts"]))
        d = "LONG" if str(p.get("side")).lower() == "long" else "SHORT"
        close_side = "sell" if d == "LONG" else "buy"
        st = trades.get(sym) or {}
        sl, tp = float(st.get("sl") or 0), float(st.get("tp") or 0)
        if sl <= 0 or tp <= 0:
            print(f"  {sym}: khong co sl/tp trong managed_state -> bo qua")
            continue
        for tag, otype, price in (("SL", "STOP_MARKET", sl),
                                  ("TP", "TAKE_PROFIT_MARKET", tp)):
            try:
                o = cli.create_order(sym, otype, close_side, qty,
                                     params={"stopPrice": price, "reduceOnly": True,
                                             "workingType": "CONTRACT_PRICE"})
                print(f"  {sym} {tag} {price} -> OK id={o.get('id')}")
                ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  {sym} {tag} {price} -> LOI: {str(e)[:110]}")
                fail += 1
            time.sleep(1)
    print(f"\n=> dat duoc {ok} lenh, loi {fail}. Kiem tra lai: "
          "python arm_protection.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
