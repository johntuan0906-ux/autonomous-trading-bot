"""Kiểm tra cặp KEY LIVE đã điền trong .env (đọc số dư THẬT, chỉ ĐỌC).

    python check_live_key.py            # kiem tra + in so du that + muc rui ro
    python check_live_key.py --json     # them dong JSON de may doc

Dung khi: ban vua tao key tren Binance THAT va dan vao .env
    BINANCE_LIVE_API_KEY=...
    BINANCE_LIVE_API_SECRET=...
(2 dong nay KHONG dung den key demo dang chay testnet.)

Ket qua: exit 0 = key OK va du dieu kien tu sang LIVE (>= AUTO_LIVE_MIN_EQUITY),
         exit 2 = chua OK (thieu key / khong doc duoc / so du thap).
"""
from __future__ import annotations

import argparse
import json
import sys


def mask(s: str) -> str:
    s = str(s or "")
    return (s[:6] + "…" + s[-4:]) if len(s) > 12 else ("(rong)" if not s else "***")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kiem tra KEY LIVE trong .env")
    ap.add_argument("--json", action="store_true", help="in them JSON")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    from config import Settings
    import risk_tier
    import state_sync as SS

    cfg = Settings()
    key, secret, src = SS.key_pair(cfg)
    min_eq = float(getattr(cfg, "auto_live_min_equity", 10.0) or 10.0)
    print("=" * 74)
    print("KIEM TRA KEY LIVE | nguon dang dung = %s" % src)
    print("=" * 74)
    print("  BINANCE_LIVE_API_KEY      : %s" % mask(getattr(cfg, "live_api_key", "")))
    print("  BINANCE_LIVE_API_SECRET   : %s" % mask(getattr(cfg, "live_api_secret", "")))
    print("  BINANCE_API_KEY (demo)    : %s" % mask(getattr(cfg, "api_key", "")))
    if src != "live":
        print("\n-> CHUA dien key LIVE (dang dung key demo/API chung).")
        print("   Dien 2 dong BINANCE_LIVE_API_KEY / BINANCE_LIVE_API_SECRET vao .env")
        print("   (huong dan tao key: README muc 16). Testnet KHONG bi anh huong.")
        return 2

    eq = SS.real_equity_usdt(cfg)
    tier = risk_tier.tier_for(eq)
    ok_eq = eq is not None and float(eq) >= min_eq
    print("\n  So du USDT THAT           : %s" % ("?" if eq is None else "%.2f" % eq))
    print("  Nguong toi thieu          : %.2f USDT (AUTO_LIVE_MIN_EQUITY)" % min_eq)
    print("  Muc rui ro se ap dung     : %s (%s) — risk %s%% · %s vi the"
          % (tier["name"], tier["label"], tier["risk_pct"], tier["max_positions"]))
    print("  Cap se giao dich          : %s" % (tier["symbols"] + " + " + tier["extra_symbols"]
                                                if tier["feasible_any"] else "(khong co)"))
    if eq is None:
        print("\n-> KHONG doc duoc so du: kiem tra key co bat quyen FUTURES chua, hoac")
        print("   key co bi gioi han IP khac khong.")
    elif not ok_eq:
        print("\n-> So du %.2f < %.2f USDT: nap them USDT vao vi Futures (USDT-M)." % (eq, min_eq))
    else:
        print("\n-> OK: key LIVE doc duoc, so du du dieu kien => chot 4 se qua khi cong LIVE dat.")
    if args.json:
        print(json.dumps({"source": src, "equity": eq, "min_equity": min_eq,
                          "tier": tier["name"], "ok": bool(ok_eq)}, ensure_ascii=False))
    return 0 if ok_eq else 2


if __name__ == "__main__":
    raise SystemExit(main())
