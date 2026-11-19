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
from pathlib import Path

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from config import Settings  # noqa: E402

# (19/11, B-061) Truoc day cong cu nay chi chay DEMO. Do that 19/11: LIVE co **3 vi the
# KHONG co lenh bao ve nao tren san** (BTC/SOL/XRP) va khong co cach nao dat lai tu dong
# ngoai viec cho bot tu re-arm (bi chan IP thi bot cung khong goi duoc). Them `--target`.
LIVE_DIR = Path(__file__).resolve().parent.parent / "atb-live"


def read_env(path: Path) -> dict:
    """Doc `.env` thanh dict (KHONG ghi de os.environ cua instance khac)."""
    out: dict = {}
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:  # noqa: BLE001
        return {}
    return out


def _client(cfg):
    import ccxt  # type: ignore
    cli = ccxt.binance({"apiKey": cfg.api_key, "secret": cfg.api_secret,
                        "options": {"defaultType": "future"}, "enableRateLimit": True})
    cli.enable_demo_trading(True)
    cli.options["fetchOpenOrders"] = {"warnWithoutSymbol": False}
    return cli


def _client_keys(key: str, sec: str, live: bool):
    import ccxt  # type: ignore
    cli = ccxt.binance({"apiKey": key, "secret": sec,
                        "options": {"defaultType": "future"}, "enableRateLimit": True})
    if not live:
        cli.enable_demo_trading(True)
    cli.options["fetchOpenOrders"] = {"warnWithoutSymbol": False}
    return cli


def _ban_left(base: Path) -> float:
    """So giay con bi san chan IP (doc `logs/api_ban.json`, B-044/B-059). 0 = khong."""
    try:
        d = json.loads((Path(base) / "logs" / "api_ban.json").read_text(encoding="utf-8"))
        return max(0.0, float(d.get("until") or 0.0) - time.time())
    except Exception:  # noqa: BLE001
        return 0.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bao ve SL/TP (DEMO hoac LIVE)")
    ap.add_argument("--arm", action="store_true", help="thu arm lai SL/TP")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--yes-live", action="store_true",
                    help="bat buoc khi --target live --arm (dat lenh THAT)")
    ap.add_argument("--default-sl-pct", type=float, default=0.0,
                    help="vi the MO TAY (khong co trong state): dat SL cach entry N%% (0 = bo qua)")
    ap.add_argument("--default-tp-pct", type=float, default=0.0,
                    help="vi the MO TAY: dat TP cach entry N%% (0 = khong dat)")
    args = ap.parse_args(argv)

    if args.target == "live":
        if args.arm and not args.yes_live:
            print("[TU CHOI] --target live --arm dat lenh THAT: them --yes-live.")
            return 2
        base = LIVE_DIR
        env = read_env(base / ".env")
        if not (env.get("BINANCE_API_KEY") and env.get("BINANCE_API_SECRET")):
            print("[LOI] thieu API key trong %s" % (base / ".env"))
            return 2
        _ban = _ban_left(base)
        if _ban > 0:
            print("[CHO] san chan IP (B-044): con %.0f phut (toi %s) -> KHONG goi API"
                  % (_ban / 60.0,
                     time.strftime("%H:%M:%S", time.localtime(time.time() + _ban))))
            return 3
        cli = _client_keys(env["BINANCE_API_KEY"], env["BINANCE_API_SECRET"], True)
        ms_path = base / "logs" / "managed_state.json"
    else:
        base = Path(__file__).resolve().parent
        cfg = Settings()
        if not cfg.testnet or not cfg.api_key:
            print("[TU CHOI] chi chay tren DEMO (BINANCE_TESTNET=true + co API key).")
            return 2
        cli = _client(cfg)
        ms_path = Path(getattr(cfg, "managed_state_path", "logs/managed_state.json"))
    try:
        poss = [p for p in cli.fetch_positions() if float(p.get("contracts") or 0) != 0]
    except Exception as e:  # noqa: BLE001
        # (19/11, B-063) request vua cham ban ⇒ GHI moc de lan sau khong goi tiep
        try:
            import exchange as _ex
            _ex.note_error_ban(base, e)
        except Exception:  # noqa: BLE001
            pass
        print("[LOI] fetch_positions:", str(e)[:150])
        return 1
    try:
        orders = cli.fetch_open_orders()
    except Exception as e:  # noqa: BLE001
        orders = []
        print("[WARN] khong doc duoc lenh treo:", str(e)[:120])
    # (19/11, B-065) Binance de lenh DIEU KIEN o Algo Order API ⇒ `fetch_open_orders()`
    # tra 0 du dang co SL/TP ⇒ lan arm sau dat TRUNG (do that 13:02: XRP/SOL bi 2 SL + 2 TP).
    try:
        import sys as _sys
        _tools = str(Path(__file__).resolve().parent / "tools")
        if _tools not in _sys.path:
            _sys.path.insert(0, _tools)
        import orders_audit as _oa
        orders = list(orders or []) + list(_oa.algo_orders(cli) or [])
    except Exception as e:  # noqa: BLE001
        print("[WARN] khong doc duoc lenh dieu kien (algo):", str(e)[:120])
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

    ms = json.load(open(ms_path, encoding="utf-8"))
    trades = ms.get("trades") or {}
    # (19/11, B-065) Tai khoan LIVE dang o HEDGE (`dualSidePosition=True`) ⇒ moi lenh
    # PHAI co `positionSide`, va KHONG duoc gui `reduceOnly` (neu khong: `-4061`).
    # Do that 12:56: 4/4 lenh arm that bai ⇒ 3 vi the LIVE khong co SL/TP.
    try:
        hedge = bool((cli.fapiPrivateGetPositionSideDual() or {}).get("dualSidePosition"))
    except Exception:  # noqa: BLE001
        hedge = False
    print("  che do tai khoan: %s" % ("HEDGE (dung positionSide)" if hedge
                                      else "ONE-WAY (dung reduceOnly)"))
    ok = fail = 0
    for p in poss:
        sym = p.get("symbol")
        qty = abs(float(p["contracts"]))
        d = "LONG" if str(p.get("side")).lower() == "long" else "SHORT"
        close_side = "sell" if d == "LONG" else "buy"
        st = trades.get(sym) or {}
        sl, tp = float(st.get("sl") or 0), float(st.get("tp") or 0)
        if sl <= 0 or tp <= 0:
            # (19/11, B-065) Vi the MO TAY (khong co trong managed_state) van phai duoc
            # bao ve: dung `--default-sl-pct` (% tu entry) neu nguoi van hanh bat.
            _entry = float(p.get("entryPrice") or p.get("entryPrice") or 0)
            if sl <= 0 and args.default_sl_pct and _entry > 0:
                sl = (_entry * (1 - args.default_sl_pct / 100.0) if d == "LONG"
                      else _entry * (1 + args.default_sl_pct / 100.0))
                print(f"  {sym}: khong co SL trong state -> dung mac dinh "
                      f"{args.default_sl_pct:g}% tu entry {_entry:g} => {sl:g}")
            if tp <= 0 and args.default_tp_pct and _entry > 0:
                tp = (_entry * (1 + args.default_tp_pct / 100.0) if d == "LONG"
                      else _entry * (1 - args.default_tp_pct / 100.0))
                print(f"  {sym}: khong co TP trong state -> dung mac dinh "
                      f"{args.default_tp_pct:g}% tu entry {_entry:g} => {tp:g}")
            if sl <= 0 and tp <= 0:
                print(f"  {sym}: khong co sl/tp trong managed_state -> bo qua")
                continue
        for tag, otype, price in (("SL", "STOP_MARKET", sl),
                                  ("TP", "TAKE_PROFIT_MARKET", tp)):
            if price <= 0:
                continue
            params = {"stopPrice": price, "workingType": "CONTRACT_PRICE"}
            if hedge:
                params["positionSide"] = d          # B-065: HEDGE bat buoc
            else:
                params["reduceOnly"] = True
            try:
                o = cli.create_order(sym, otype, close_side, qty, params=params)
                print(f"  {sym} {tag} {price} -> OK id={o.get('id')}")
                ok += 1
            except Exception as e:  # noqa: BLE001
                # (19/11, B-063) dat lenh ma cham ban ⇒ ghi moc, dung ngay (dung goi tiep)
                try:
                    import exchange as _ex
                    if _ex.note_error_ban(base, e):
                        print(f"  {sym} {tag} -> BAN IP: dung dat tiep")
                        return 1
                except Exception:  # noqa: BLE001
                    pass
                print(f"  {sym} {tag} {price} -> LOI: {str(e)[:110]}")
                fail += 1
            time.sleep(1)
    print(f"\n=> dat duoc {ok} lenh, loi {fail}. Kiem tra lai: "
          "python arm_protection.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
