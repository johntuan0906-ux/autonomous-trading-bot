"""Kiem tra ket noi Binance Futures TESTNET (che do 2: paper-trading).
Chay: python check_testnet.py
- Doc .env (BINANCE_API_KEY/SECRET, BINANCE_TESTNET, DRY_RUN)
- Test public (khong can key) + test private (can key testnet)
"""
from __future__ import annotations
import sys

from config import Settings


def mask(s: str) -> str:
    s = s or ""
    if not s:
        return "(TRONG)"
    return s[:4] + "**** (dai %d ky tu)" % len(s)


def main() -> int:
    cfg = Settings()
    print("=== Cau hinh hien tai (.env) ===")
    print(f"BINANCE_API_KEY    = {mask(cfg.api_key)}")
    print(f"BINANCE_API_SECRET = {mask(cfg.api_secret)}")
    print(f"BINANCE_TESTNET    = {cfg.testnet}")
    print(f"DRY_RUN            = {cfg.dry_run}")
    print(f"BALANCE_USDT       = {cfg.balance_usdt} | LEVERAGE={cfg.leverage} "
          f"| RISK={cfg.risk_per_trade_pct}% | TF={cfg.timeframe}")

    # 1) Public (khong can key)
    try:
        import ccxt
        pub = ccxt.binance({"options": {"defaultType": "future"}, "enableRateLimit": True})
        px = pub.fetch_ticker("BTC/USDT:USDT")["last"]
        print(f"\n[OK] Public Binance: BTC/USDT:USDT = {px}")
    except Exception as e:
        print(f"\n[FAIL] Public Binance loi: {e}")
        return 1

    # 2) Private testnet (can key)
    if not cfg.api_key or not cfg.api_secret:
        print("\n[CANH BAO] Chua co BINANCE_API_KEY/SECRET trong .env.")
        print("  -> Lay key free tai https://demo.binance.com (xem huong dan o duoi).")
        return 2
    try:
        import ccxt
        cli = ccxt.binance({
            "apiKey": cfg.api_key, "secret": cfg.api_secret,
            "options": {"defaultType": "future"}, "enableRateLimit": True,
        })
        # Paper-trading moi cua Binance: Demo Trading (demo.binance.com).
        # Key phai tao tu demo.binance.com -> My Settings -> API Management.
        try:
            cli.enable_demo_trading(True)
            print("[OK] Da bat Demo Trading mode (demo.binance.com).")
        except Exception as e:
            print(f"[WARN] enable_demo_trading loi (thu sandbox cu): {e}")
            cli.set_sandbox_mode(True)

        bal = cli.fetch_balance()
        usdt = (bal.get("USDT") or {})
        print(f"[OK] Testnet auth thanh cong. USDT free = {usdt.get('free')}, total = {usdt.get('total')}")
        # thu doc vi the futures hien tai
        try:
            poss = cli.fetch_positions(list(cfg.symbols))
            openp = [p for p in poss if float(p.get("contracts") or 0) != 0]
            print(f"[OK] Vi the dang mo tren testnet: {len(openp)}")
            for p in openp:
                print("   ", p.get("symbol"), p.get("side"), p.get("contracts"))
        except Exception as e:
            print(f"[WARN] Khong doc duoc positions (co the chua co quyen futures): {e}")
        print("\n=> San sang chay: python main.py --once  (voi DRY_RUN=false)")
        return 0
    except Exception as e:
        print(f"\n[FAIL] Testnet auth that bai: {e}")
        print("  -> Kiem tra: key tao tu testnet.binancefuture.com, chua het han, "
              "da bat quyen Futures, dong ho may chuan (time sync).")
        return 3


if __name__ == "__main__":
    sys.exit(main())
