"""Nạp danh sách cặp từ `symbols_all.txt` vào `.env` của (các) instance.

    python tools/apply_symbols.py --dry-run            # xem truoc (khong ghi)
    python tools/apply_symbols.py                      # ghi ca 2 instance (testnet + live)
    python tools/apply_symbols.py --target testnet     # chi 1 ben
    python tools/apply_symbols.py --no-validate        # khong kiem tra voi san (nhanh)

Việc làm:
1. Đọc `symbols_all.txt` (`BTCUSDT,BTCUSDT...`) -> đổi sang định dạng ccxt `BTC/USDT:USDT`.
2. **Kiểm tra hợp lệ** với sàn (public, không cần key): chỉ giữ cặp có thật + đang giao dịch
   (tránh `DATA_FAIL` mỗi vòng do cặp đã huỷ/không phải futures).
3. **Loại cặp đã bị BAN** (`logs/banned_pairs.json` của chính instance — do `pair_audit.py`
   ghi khi cặp thua dài hạn) ⇒ cặp bị loại là **vĩnh viễn**, nạp lại danh sách cũng không quay lại.
4. Ghi `SYMBOLS` (toàn bộ) + `EXTRA_SYMBOLS=` (rỗng) vào `.env`.
5. **Chỉnh thông số quét cho phù hợp số cặp** (`--tune-scan`, mặc định BẬT): 450 cặp mà để
   `POLL_INTERVAL_SEC=30` + 450 luồng sẽ vượt rate-limit của sàn (đo: ~1800 request/vòng).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
LIST = ROOT / "symbols_all.txt"

# Thong so quet an toan cho ~460 cap: cache tang dan (exchange.fetch_ohlcv) cat
# request tu ~1800 xuong ~458/vong; 8 luong × 2 instance = 16 ket noi dong thoi
# (dual-WAN/CGNAT khong chiu duoc 32) -> POLL 5 phut de khong chong vong.
SCAN_TUNE = {
    "POLL_INTERVAL_SEC": "300",      # 5 phut/vong
    "ROUND_TIMEOUT_SEC": "280",
    "SCAN_WORKERS": "8",             # giam tu 16 (SSL EOF khi 32 ket noi dong thoi)
    "COOLDOWN_SEC": "1800",
}


def to_ccxt(raw: str) -> list:
    """`BTCUSDT` -> `BTC/USDT:USDT` (bo hau to USDT roi ghep lai)."""
    out: list = []
    for tok in str(raw).replace("\n", ",").split(","):
        s = tok.strip().upper()
        if not s:
            continue
        base = s[:-4] if s.endswith("USDT") else s
        if not base:
            continue
        out.append("%s/USDT:USDT" % base)
    return out


def load_symbols() -> list:
    txt = LIST.read_text(encoding="utf-8")
    syms = to_ccxt(txt)
    # giu thu tu, bo trung
    seen: set = set()
    uniq = []
    for s in syms:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def banned(target: Path) -> set:
    """Cặp đã bị loại vĩnh viễn (do `pair_audit.py`) của instance `target`."""
    p = target / "logs" / "banned_pairs.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    return set(d.keys()) if isinstance(d, dict) else set()


def validate(syms: list, cfg) -> tuple:
    """Loc theo san: chi giu cap co that + dang giao dich (public, khong can key)."""
    try:
        import ccxt
        import state_sync as SS
        key, secret, _ = SS.key_pair(cfg)
        ex = ccxt.binanceusdm({"apiKey": key, "secret": secret, "enableRateLimit": True,
                               "timeout": 20000})
        if getattr(cfg, "testnet", True):
            try:
                ex.enable_demo_trading(True)
            except Exception:  # noqa: BLE001
                pass
        mk = ex.load_markets()
        ok, bad = [], []
        for s in syms:
            m = mk.get(s)
            if m and m.get("swap") and m.get("active", True):
                ok.append(s)
            else:
                bad.append(s)
        return ok, bad
    except Exception as e:  # noqa: BLE001
        print("CANH BAO: khong kiem tra duoc voi san (%s) -> giu nguyen danh sach" % str(e)[:120])
        return syms, []


def apply_one(target: Path, syms: list, tune: bool, dry_run: bool) -> dict:
    import state_sync as SS
    envp = target / ".env"
    if not envp.exists():
        return {"ok": False, "err": "khong co %s" % envp}
    cur = envp.read_text(encoding="utf-8")
    upd = {"SYMBOLS": ",".join(syms), "EXTRA_SYMBOLS": ""}
    if tune:
        upd.update(SCAN_TUNE)
    new = SS.set_env_values(cur, upd)
    if not dry_run:
        envp.write_text(new, encoding="utf-8")
    return {"ok": True, "env": str(envp), "n": len(syms), "tune": SCAN_TUNE if tune else {}}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Nap danh sach cap vao .env")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-validate", action="store_true")
    ap.add_argument("--no-tune-scan", action="store_true", help="khong doi thong so quet")
    ap.add_argument("--limit", type=int, default=0, help="chi lay N cap dau (de thu)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    sys.path.insert(0, str(ROOT))  # de import state_sync/config ngay ca khi --no-validate
    syms = load_symbols()
    print("doc %s: %d cap" % (LIST.name, len(syms)))
    if args.limit:
        syms = syms[:args.limit]

    targets = []
    if args.target in ("both", "testnet"):
        targets.append(("testnet", ROOT))
    if args.target in ("both", "live"):
        targets.append(("live", LIVE_DIR))

    for name, d in targets:
        ban = banned(d)
        keep = [s for s in syms if s not in ban]
        print("--- %s: ban=%d -> con %d cap" % (name, len(ban), len(keep)))
        if not args.no_validate:
            sys.path.insert(0, str(ROOT))
            from config import Settings
            os.environ["BINANCE_TESTNET"] = "true"        # chi de doc markets (public)
            ok, bad = validate(keep, Settings())
            print("    hop le=%d | loai=%d %s" % (len(ok), len(bad), bad[:8]))
            keep = ok
        res = apply_one(d, keep, tune=not args.no_tune_scan, dry_run=args.dry_run)
        print("    %s n=%s tune=%s%s" % (res.get("env"), res.get("n"), res.get("tune"),
                                         "  (DRY-RUN)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
