"""Debug sau: goi ccxt demo endpoints tung buoc de phan biet key sai vs quyen sai."""
from __future__ import annotations
import ccxt
from config import Settings

c = Settings()
cli = ccxt.binance({
    "apiKey": c.api_key, "secret": c.api_secret,
    "options": {"defaultType": "future"}, "enableRateLimit": True,
})
cli.enable_demo_trading(True)
print("api urls (fapiPrivate):", cli.urls["api"].get("fapiPrivate"))
print("isSandbox:", cli.isSandboxModeEnabled)

for name, fn in [
    ("fetch_time", lambda: cli.fetch_time()),
    ("fetch_balance", lambda: cli.fetch_balance()),
    ("fetch_positions BTC", lambda: cli.fetch_positions(["BTC/USDT:USDT"])),
]:
    try:
        r = fn()
        print(f"[OK] {name}:", str(r)[:200])
    except Exception as e:
        print(f"[FAIL] {name}:", str(e)[:500])
