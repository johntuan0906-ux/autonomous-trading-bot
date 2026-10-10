"""Tạo 2 cấu hình `.env` để chạy SONG SONG: repo chính = TESTNET, `../atb-live` = LIVE.

    python tools/setup_parallel_env.py            # ghi ca 2 file .env
    python tools/setup_parallel_env.py --dry-run  # chi in se doi gi (khong ghi)

Vì sao phải 2 instance riêng: `logs/journal.jsonl`, `learner.json`, `risk_state.json`,
`managed_state.json`, `heartbeat.json` là file DÙNG CHUNG — chạy 2 chế độ trong cùng thư
mục sẽ ghi đè lẫn nhau ⇒ hỏng số liệu và hỏng cả bằng chứng học. Mỗi instance phải có
`logs/` riêng (đã tách: repo chính + `../atb-live`).

- Repo chính (**TESTNET** — học): demo key, `BINANCE_TESTNET=true`, 7 cặp, `MAX_POSITIONS=4`,
  risk 1.0%, ngưỡng chuẩn `MIN_PF=1.2` / `MIN_TRADES=50`, `AUTO_LIVE_ARMED=false`.
- `../atb-live` (**LIVE** — thực chiến): key THẬT, `BINANCE_TESTNET=false`, `LIVE_CONFIRM=true`,
  5 cặp, `MAX_POSITIONS=2`, risk 0.5%, `MIN_PF=1.05` / `MIN_TRADES=30` (chấp nhận edge mỏng
  khi chạy song song để lấy kinh nghiệm thực tế), `AUTO_LIVE_ARMED=false`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
BAK = ROOT / ".env.bak-live"          # .env truoc khi tu dong sang LIVE (= cau hinh testnet)

# 7 cap cua phien testnet truoc khi sang LIVE (nhieu du lieu hon cho viec hoc)
TEST_SYMS = "BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT"
TEST_EXTRA = "ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT"
LIVE_SYMS = "SOL/USDT:USDT,XRP/USDT:USDT"
LIVE_EXTRA = "ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT"

TESTNET_UPD = {
    "BINANCE_TESTNET": "true", "LIVE_CONFIRM": "false",
    "SYMBOLS": TEST_SYMS, "EXTRA_SYMBOLS": TEST_EXTRA,
    "MAX_POSITIONS": "4", "RISK_PER_TRADE_PCT": "1.0",
    "MIN_PF": "1.2", "MIN_TRADES": "50",
    "AUTO_LIVE_ARMED": "false", "KILL_MONITOR_ONLY": "true",
}
LIVE_UPD = {
    "BINANCE_TESTNET": "false", "LIVE_CONFIRM": "true",
    "SYMBOLS": LIVE_SYMS, "EXTRA_SYMBOLS": LIVE_EXTRA,
    "MAX_POSITIONS": "2", "RISK_PER_TRADE_PCT": "0.5",
    "MIN_PF": "1.05", "MIN_TRADES": "30",
    "AUTO_LIVE_ARMED": "false", "KILL_MONITOR_ONLY": "true",
}


def mask(line: str) -> str:
    if "API_KEY=" in line or "API_SECRET=" in line:
        k, _, v = line.partition("=")
        return "%s=%s" % (k, (v[:6] + "..." + v[-4:]) if len(v) > 12 else "(rong)")
    return line


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tao .env cho 2 instance song song")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    import state_sync as SS   # noqa: E402  (dung lai helper set_env_values)

    cur = (ROOT / ".env").read_text(encoding="utf-8")
    bak = BAK.read_text(encoding="utf-8") if BAK.exists() else cur
    live_env = SS.set_env_values(cur, LIVE_UPD)          # tu ban dang LIVE
    test_env = SS.set_env_values(bak, TESTNET_UPD)       # tu ban testnet truoc flip

    print("--- %s (TESTNET) ---" % (ROOT / ".env"))
    for k in TESTNET_UPD:
        print("  ", mask("%s=%s" % (k, TESTNET_UPD[k])))
    print("--- %s (LIVE) ---" % (LIVE_DIR / ".env"))
    for k in LIVE_UPD:
        print("  ", mask("%s=%s" % (k, LIVE_UPD[k])))
    if args.dry_run:
        print("(dry-run: khong ghi file)")
        return 0
    if not LIVE_DIR.exists():
        print("LOI: chua co %s — copy project truoc" % LIVE_DIR)
        return 2
    (ROOT / ".env").write_text(test_env, encoding="utf-8")
    (LIVE_DIR / ".env").write_text(live_env, encoding="utf-8")
    print("OK: da ghi 2 file .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
