"""Xem tien trinh bot realtime: tien trinh + log tail + vi the san + learner.

Chay: python status.py [--tail N]
"""
from __future__ import annotations

import subprocess
import sys

TAIL = int(sys.argv[sys.argv.index("--tail") + 1]) if "--tail" in sys.argv else 5

print("=== 1) TIEN TRINH BOT ===")
try:
    for exe in ("python.exe", "pythonw.exe"):
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "TABLE"],
                             capture_output=True, text=True, timeout=10)
        body = out.stdout.strip()
        print(f"[{exe}]\n{body or '(khong co)'}")
except Exception as e:  # noqa: BLE001
    print("khong doc duoc tasklist:", e)
try:
    lock = open("logs/.supervisor.lock", encoding="utf-8").read().strip()
    print(f"supervisor lock pid={lock}")
except Exception:  # noqa: BLE001
    print("supervisor chua chay (khong co logs/.supervisor.lock)")

print("\n=== 2) LOG MOI NHAT (logs/turbo_err.log) ===")
try:
    with open("logs/turbo_err.log", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"(tong {len(lines)} dong) 5 dong cuoi:")
    for ln in lines[-TAIL:]:
        print(" ", ln.rstrip()[:300])
except Exception as e:  # noqa: BLE001
    print("khong doc duoc log:", e)

print("\n=== 3) VI THE + WALLET DEMO ===")
try:
    import ccxt  # type: ignore
    from config import Settings
    c = Settings()
    cli = ccxt.binance({"apiKey": c.api_key, "secret": c.api_secret,
                        "options": {"defaultType": "future"}})
    cli.enable_demo_trading(True)
    b = cli.fetch_balance()["info"]
    print("wallet:", round(float(b.get("totalWalletBalance") or 0), 2),
          "| uPnL:", round(float(b.get("totalUnrealizedProfit") or 0), 2))
    for p in cli.fetch_positions():
        if float(p.get("contracts") or 0) != 0:
            print(f" - {p['symbol']} {p['side']} {p.get('contracts')} "
                  f"entry={round(float(p.get('entryPrice') or 0), 4)} "
                  f"upnl={round(float(p.get('unrealizedPnl') or 0), 2)}")
except Exception as e:  # noqa: BLE001
    print("khong doc duoc san:", str(e)[:200])

print("\n=== 4) LEARNER (tri nho AI) ===")
try:
    import json
    with open("logs/learner.json") as f:
        d = json.load(f)
    print(f"n_updates={d.get('n')} b={round(float(d.get('b', 0)), 3)}")
    print("w =", {k: round(v, 3) for k, v in d.get("w", {}).items()})
except Exception:
    print("(chua co logs/learner.json — learner chua hoc close nao)")
