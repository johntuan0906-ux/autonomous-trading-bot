"""Kiểm kê lệnh CHỜ trên sàn (chỉ ĐỌC) + đề xuất gom lại.

    python tools/orders_audit.py                    # TESTNET (repo chinh)
    python tools/orders_audit.py --target live      # LIVE (../atb-live)
    python tools/orders_audit.py --cancel-orphans   # huy lenh treo KHONG co vi the

Vì sao có công cụ này (12/10): trên Binance, mục **lệnh mở có điều kiện** tích tụ
rất nhiều lệnh chờ (tới hàng trăm). Nguyên nhân không phải bot "mở 200 lệnh vào
lệnh" — bot chỉ vào **MARKET** + 2 lệnh bảo vệ/cặp — mà do:

  1. `_rearm_missing()` retry đặt lại SL/TP mỗi 60s khi sàn trả `-4045`
     (`cancel_first=False`) ⇒ lệnh đặt được nhưng lần đối soát sau KHÔNG thấy
     (API demo đọc chập chờn) ⇒ đặt tiếp ⇒ **trùng lặp tích tụ**.
  2. Lệnh của vị thế ĐÃ ĐÓNG không được huỷ (chỉ huỷ khi arm lại cùng symbol).
  3. Partial/BE/trail gọi `stop_tp_orders` nhiều lần.

Hệ quả: chạm trần stop-order của tài khoản (`-4045`) ⇒ **lệnh bảo vệ mới không
đặt được nữa** (đúng lúc cần nhất) + khó đọc trạng thái thật.

Cách xử lý đúng (theo hướng "ít mà chất"): giữ **đúng 1 SL + 1 TP cho mỗi vị thế
đang mở**, huỷ mọi lệnh treo mồ côi/trùng. Công cụ này đo trước, rồi mới huy.

An toàn: mặc định CHỈ ĐỌC. `--cancel-orphans` chỉ huỷ lệnh của symbol **không có
vị thế** (không bao giờ đụng vào lệnh bảo vệ của vị thế đang mở).
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
PROTECT_TYPES = ("STOP_MARKET", "TAKE_PROFIT_MARKET", "STOP", "TAKE_PROFIT",
                 "TRAILING_STOP_MARKET", "STOP_LOSS", "TAKE_PROFIT_LIMIT")


def read_env(path: Path) -> dict:
    """Doc `.env` thanh dict (khong ghi de os.environ cua instance khac)."""
    out: dict = {}
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def classify(orders: list) -> Counter:
    """Dem lenh cho theo type (STOP_MARKET / TAKE_PROFIT_MARKET / LIMIT / ...)."""
    c: Counter = Counter()
    for o in orders or []:
        c[str((o or {}).get("type") or "?")] += 1
    return c


def to_ccxt_symbol(raw: str) -> str:
    """`AEROUSDT` -> `AERO/USDT:USDT` (giu nguyen neu da dung dang ccxt)."""
    s = str(raw or "")
    if "/" in s:
        return s
    if s.endswith("USDT") and len(s) > 4:
        return "%s/USDT:USDT" % s[:-4]
    return s


def to_raw_symbol(sym: str) -> str:
    """`AERO/USDT:USDT` -> `AEROUSDT`."""
    return str(sym or "").replace("/", "").split(":")[0]


def algo_orders(cli, symbol: str | None = None) -> list:
    """Lenh cho DIEU KIEN tu Algo Order API (ccxt `fetch_open_orders` KHONG thay).

    Do that 12/10: LIVE co 200 lenh o day trong khi `fetch_open_orders` bao 0.
    """
    fn = getattr(cli, "fapiPrivateGetOpenAlgoOrders", None)
    if fn is None:
        return []
    out: list = []
    try:
        params = {"symbol": to_raw_symbol(symbol)} if symbol else {}
        for o in (fn(params) or []):
            st = str((o or {}).get("algoStatus") or "NEW").upper()
            if st not in ("NEW", "WORKING", "PENDING", ""):
                continue
            out.append({"id": o.get("algoId"),
                        "symbol": to_ccxt_symbol(o.get("symbol")),
                        "type": o.get("orderType") or o.get("algoType") or "",
                        "stopPrice": o.get("triggerPrice"),
                        "clientOrderId": o.get("clientAlgoId"),
                        "algo": True,
                        "ts": float(o.get("bookTime") or o.get("time") or 0)})
    except Exception:  # noqa: BLE001
        return out
    return out


def plan_cleanup(orders: list, positions: list) -> dict:
    """Chia lenh cho thanh KEEP / CANCEL (ham thuan, test duoc).

    Quy tac (theo huong "it ma chat"):
      1. Lenh cua symbol KHONG con vi the  -> HUY (mo coi, co the kich hoat nham).
      2. Moi cap (symbol, type) cua vi the dang mo chi giu **1 lenh MOI NHAT**
         -> cac ban sao cu HUY.
    """
    live = open_symbols(positions)
    keep: list = []
    cancel: list = []
    newest: dict = {}
    for o in orders or []:
        sym = str((o or {}).get("symbol"))
        if sym not in live:
            cancel.append(o)
            continue
        key = (sym, str((o or {}).get("type") or ""))
        cur = newest.get(key)
        if cur is None or float((o or {}).get("ts") or 0) >= float(cur.get("ts") or 0):
            if cur is not None:
                cancel.append(cur)
            newest[key] = o
        else:
            cancel.append(o)
    keep.extend(newest.values())
    return {"keep": keep, "cancel": cancel}


def open_symbols(positions: list) -> set:
    """Symbol dang co vi the THAT (contracts != 0)."""
    out = set()
    for p in positions or []:
        try:
            if float((p or {}).get("contracts") or 0) != 0:
                out.add(str(p.get("symbol")))
        except (TypeError, ValueError):
            continue
    return out


def orphans(orders: list, positions: list) -> list:
    """Lenh treo thuoc symbol KHONG con vi the -> rac, nen huy."""
    live = open_symbols(positions)
    return [o for o in (orders or []) if str((o or {}).get("symbol")) not in live]


def protect_count(orders: list, symbol: str) -> int:
    """So lenh BAO VE (stop/tp) dang treo cho 1 symbol."""
    n = 0
    for o in orders or []:
        if str((o or {}).get("symbol")) != symbol:
            continue
        if str((o or {}).get("type") or "").upper() in PROTECT_TYPES:
            n += 1
    return n


def dupes(orders: list, positions: list) -> dict:
    """symbol -> so lenh bao ve khi nhieu hon 2 (dung ra chi can 1 SL + 1 TP)."""
    out: dict = {}
    for s in sorted(open_symbols(positions)):
        n = protect_count(orders, s)
        if n > 2:
            out[s] = n
    return out


def load_dust(base: Path) -> set:
    """Symbol trong `logs/dust_skip.json` (B-024) — vi the BUI da biet, KHONG the
    dong/bao ve duoc (qty < minNotional) nen thieu SL/TP la *dung nhu thiet ke*.

    Khong doc file nay thi cong cu bao "KHONG co SL/TP" cho ca bui => bao dong gia
    va lam mat tin hieu cho vi the TRAN that (do that 22/10: 2/6 vi the TESTNET
    la bui, 0 vi the tran).
    """
    try:
        import json
        data = json.loads((Path(base) / "logs" / "dust_skip.json")
                          .read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return set()
    syms = data.get("symbols") if isinstance(data, dict) else data
    return {str(s) for s in (syms or [])}


def summarize(orders: list, positions: list, dust=None) -> dict:
    """Tong hop 1 lan cho ca bao cao + quyet dinh."""
    by_type = classify(orders)
    live = open_symbols(positions)
    orph = orphans(orders, positions)
    plan = plan_cleanup(orders, positions)
    dust_live = sorted({str(s) for s in (dust or ())} & live)
    per_symbol = {s: protect_count(orders, s) for s in sorted(live)}
    naked = sorted(s for s, n in per_symbol.items()
                   if int(n) == 0 and s not in set(dust_live))
    return {
        "orders": len(orders or []),
        "positions": len(live),
        "by_type": dict(by_type),
        "protect_orders": sum(v for k, v in by_type.items()
                              if k.upper() in PROTECT_TYPES),
        "orphans": len(orph),
        "orphan_symbols": sorted({str((o or {}).get("symbol")) for o in orph}),
        "dupes": dupes(orders, positions),
        "per_symbol": per_symbol,
        "dust": dust_live,
        "naked": naked,
        "keep": len(plan["keep"]),
        "to_cancel": len(plan["cancel"]),
    }


def verdict(s: dict) -> str:
    """Ket luan 1 dong tu ket qua `summarize` (tach rieng de test duoc)."""
    if not s["orders"]:
        return "sach (khong co lenh cho)"
    if s["orphans"]:
        return ("%d lenh MO COI -> nen huy (python tools/orders_audit.py "
                "--cancel-orphans)" % s["orphans"])
    if s["dupes"]:
        return ("%d cap co lenh bao ve TRUNG -> nen gom lai con 1 SL + 1 TP "
                "(python tools/orders_audit.py --dedupe)" % len(s["dupes"]))
    if int(s.get("to_cancel") or 0) > 0:
        return ("con %d lenh thua -> gom lai (python tools/orders_audit.py "
                "--dedupe)" % s["to_cancel"])
    # (22/10) Vi the TRAN (khong SL/TP, khong phai bui) phai la KET LUAN rieng —
    # truoc day bi lan vao dong "gon" nen khong ai thay.
    naked = [str(x) for x in (s.get("naked") or ())]
    if naked:
        return ("%d vi the TRAN (khong SL/TP) -> dat bao ve ngay: %s"
                % (len(naked), ", ".join(sorted(naked)[:3])))
    dust = {str(x) for x in (s.get("dust") or ())}
    if dust:
        return ("gon (ngoai %d vi the BUI da ghi dust_skip — khong the dat SL/TP)"
                % len(dust))
    return "gon (moi vi the dung 2 lenh bao ve)"


def build_client(env: dict, live: bool):
    """ccxt client theo `.env` cua instance (demo hay LIVE that)."""
    import ccxt  # type: ignore
    key = env.get("BINANCE_API_KEY") or ""
    sec = env.get("BINANCE_API_SECRET") or ""
    cli = ccxt.binance({"apiKey": key, "secret": sec,
                        "options": {"defaultType": "future"},
                        "enableRateLimit": True})
    if not live:
        cli.enable_demo_trading(True)
    cli.options["fetchOpenOrders"] = {"warnWithoutSymbol": False}
    return cli


def _all_orders(cli, symbols) -> tuple:
    """(orders, loi) — lenh THUONG + lenh DIEU KIEN (algo).

    Phai gop ca 2 nguon: Binance de lenh dieu kien o Algo Order API nen chi doc
    `fetch_open_orders` se thay 0 lenh du tai khoan dang co hang tram lenh SL/TP.
    """
    out: list = []
    err = None
    try:
        out.extend(cli.fetch_open_orders() or [])
    except Exception as e:  # noqa: BLE001
        err = str(e)[:150]
        for s in symbols:
            try:
                out.extend(cli.fetch_open_orders(s) or [])
            except Exception:  # noqa: BLE001
                continue
    out.extend(algo_orders(cli))
    return out, err


def all_orders(cli, symbols=None) -> tuple:
    """Alias cong khai cua `_all_orders` (cho `watch_regress`/`harness_audit` dung).

    Tra (orders, err): gop lenh THUONG + lenh DIEU KIEN (Algo Order API).
    """
    return _all_orders(cli, symbols or [])


def cancel_orders(cli, orders: list) -> tuple:
    """Huy tung lenh (algo -> endpoint algo, thuong -> cancel_order). Tra (ok, loi)."""
    ok = bad = 0
    for o in orders or []:
        try:
            if (o or {}).get("algo"):
                fn = getattr(cli, "fapiPrivateDeleteAlgoOrder", None)
                if fn is None:
                    bad += 1
                    continue
                fn({"algoId": o.get("id")})
            else:
                cli.cancel_order(str(o.get("id")), str(o.get("symbol")))
            ok += 1
        except Exception as e:  # noqa: BLE001
            bad += 1
            print("    loi huy %s %s: %s"
                  % (o.get("symbol"), o.get("type"), str(e)[:90]))
    return ok, bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiem ke lenh cho tren san (chi doc)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--cancel-orphans", action="store_true",
                    help="HUY lenh treo cua symbol KHONG co vi the (rac)")
    ap.add_argument("--dedupe", action="store_true",
                    help="GOM LAI: moi vi the giu dung 1 SL + 1 TP moi nhat, huy phan con lai")
    ap.add_argument("--json", action="store_true", help="in JSON cho may doc")
    args = ap.parse_args(argv)

    base = ROOT if args.target == "testnet" else LIVE_DIR
    envp = base / ".env"
    env = read_env(envp)
    if not env:
        print("[LOI] khong doc duoc %s" % envp)
        return 2
    live = str(env.get("BINANCE_TESTNET", "true")).lower() in ("false", "0", "no")
    if (args.target == "live") != live:
        print("[CANH BAO] --target %s nhung .env ghi BINANCE_TESTNET=%s"
              % (args.target, env.get("BINANCE_TESTNET")))
    if not (env.get("BINANCE_API_KEY") and env.get("BINANCE_API_SECRET")):
        print("[LOI] thieu API key trong %s" % envp)
        return 2

    cli = build_client(env, live)
    try:
        poss = [p for p in cli.fetch_positions() if float(p.get("contracts") or 0) != 0]
    except Exception as e:  # noqa: BLE001
        print("[LOI] fetch_positions: %s" % str(e)[:150])
        return 1
    syms = [str(p.get("symbol")) for p in poss]
    orders, err = _all_orders(cli, syms)
    s = summarize(orders, poss, dust=load_dust(base))
    s["target"] = args.target
    s["live"] = live

    if args.json:
        import json
        print(json.dumps(s, ensure_ascii=False, indent=2))
        # (13/10) Luu snapshot de `tools/ops.py` + `harness_audit` doc lai (khong goi san).
        try:
            (base / "logs" / "orders_snapshot.json").write_text(
                json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
    else:
        print("=== KIEM KE LENH CHO: %s (%s) ==="
              % (args.target.upper(), "LIVE THAT" if live else "DEMO"))
        print("  vi the dang mo   : %d" % s["positions"])
        print("  lenh cho         : %d  (bao ve: %d)"
              % (s["orders"], s["protect_orders"]))
        if s["by_type"]:
            print("  theo loai        : %s"
                  % ", ".join("%s=%d" % kv for kv in sorted(s["by_type"].items())))
        if err:
            print("  [WARN] fetch toan bo loi: %s" % err)
        dust = {str(x) for x in (s.get("dust") or ())}
        for sym, n in s["per_symbol"].items():
            if sym in dust:
                flag = "   <-- BUI (da ghi dust_skip: khong the dat SL/TP)"
            elif n > 2:
                flag = "   <-- DU/TRUNG (chi can 2)"
            elif n == 0:
                flag = "   <-- TRAN: KHONG co SL/TP"
            else:
                flag = ""
            print("    %-20s bao ve=%d%s" % (sym, n, flag))
        if s["orphans"]:
            print("  MO COI (khong co vi the): %d lenh / %d symbol"
                  % (s["orphans"], len(s["orphan_symbols"])))
            print("    %s" % ", ".join(s["orphan_symbols"][:25]))
        print("  GIU / HUY (gom lai): giu %d, huy %d" % (s["keep"], s["to_cancel"]))
        print("  KET LUAN: %s" % verdict(s))

    plan = plan_cleanup(orders, poss)
    if (args.dedupe or args.cancel_orphans) and plan["cancel"]:
        todo = plan["cancel"]
        if args.cancel_orphans and not args.dedupe:
            todo = [o for o in todo if str(o.get("symbol")) not in open_symbols(poss)]
        print("--- HUY %d LENH (giu %d) ---" % (len(todo), len(plan["keep"])))
        ok, bad = cancel_orders(cli, todo)
        print("  da huy %d, loi %d" % (ok, bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
