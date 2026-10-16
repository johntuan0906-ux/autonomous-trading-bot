"""Kiem ke MARGIN (chi doc) — de biet vi the nao dang Cross/Isolated + margin con lai.

    python tools/margin_audit.py --target live
    python tools/margin_audit.py --target testnet

Vi sao (16/10): hoi dong (phieu VETO cua `qwen3.7-plus`) canh bao tai khoan LIVE chi ~41
USDT ma co 1 vi the `BTW` do NGUOI DUNG mo o che do Cross => vi the do **chieu margin**
chung voi vi the cua bot, trong khi phep tinh rui ro cua bot khong biet no ton tai. Cong
cu nay tra loi dung cau hoi "BTW dang Cross hay Isolated?" va "con bao nhieu margin du?"
bang API that (khong suy dien).

LUU Y: Binance CHI cho doi margin type khi cap do KHONG con vi the va KHONG con lenh cho
=> neu BTW dang Cross thi phai dong vi the truoc (kem phi/truot gia). Cong cu nay CHI DOC.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def _num(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def audit(ex, symbol_filter=None) -> dict:
    """Doc vi the + vi + cau hinh margin. Tra dict (ham THUAN TUY ve mat mang doc)."""
    rows = []
    try:
        # `fetch_positions` da kiem chung chay duoc voi tai khoan nay (con
        # `fapiPrivateGetPositionRisk` tra 404 -> co the do endpoint v3/WAF).
        poss = ex.fetch_positions() or []
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:200]}
    for p in poss:
        if abs(_num(p.get("contracts"))) <= 0:
            continue
        sym = str(p.get("symbol") or "")
        if symbol_filter and sym.upper() not in {s.upper() for s in symbol_filter}:
            continue
        info = p.get("info") or {}
        iso = info.get("isolated")
        mode = str(p.get("marginMode") or "").lower()
        if mode in ("isolated", "cross"):
            mt = mode.upper()
        elif iso is not None:
            mt = "ISOLATED" if bool(iso) else "CROSS"
        else:
            mt = str(info.get("marginType") or "?")
        rows.append({
            "symbol": sym,
            "side": str(p.get("side") or info.get("positionSide") or "?").upper(),
            "contracts": abs(_num(p.get("contracts"))),
            "notional": abs(_num(p.get("notional"))),
            "margin": _num(info.get("isolatedWallet") or p.get("initialMargin")),
            "lev": _num(p.get("leverage") or info.get("leverage")),
            "isolated": (mt == "ISOLATED"),
            "uPnl": _num(p.get("unrealizedPnl")),
            "liquidation": _num(p.get("liquidationPrice")),
            "margin_type": mt,
        })
    out = {"ok": True, "positions": rows}
    try:
        bal = ex.fetch_balance() or {}
        usdt = (bal.get("USDT") or {})
        out["wallet"] = {
            "total": _num(usdt.get("total")), "free": _num(usdt.get("free")),
            "used": _num(usdt.get("used")),
        }
    except Exception as e:  # noqa: BLE001
        out["wallet"] = {"err": str(e)[:120]}
    try:                      # multi-asset margin (che do dung nhieu tai san lam margin)
        raw = ex.fapiPrivateGetMultiAssetsMargin()
        out["multi_assets_margin"] = bool(raw.get("multiAssetsMargin"))
    except Exception as e:  # noqa: BLE001
        out["multi_assets_margin"] = "khong doc duoc: %s" % str(e)[:60]
    return out


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Kiem ke margin (chi doc)")
    ap.add_argument("--target", default="testnet", choices=("testnet", "live"))
    ap.add_argument("--symbol", default="", help="chi xem 1 cap (vd BTW/USDT:USDT)")
    args = ap.parse_args(argv)

    import restart_bot as RB
    d = RB.instance_dir(args.target)
    ex = RB.exchange_client(d)
    if ex is None:
        print("[LOI] khong tao duoc client cho %s (thieu key trong .env?)" % d)
        return 2
    want = [x.strip() for x in args.symbol.split(",") if x.strip()]
    rep = audit(ex, want or None)
    print("=== KIEM KE MARGIN: %s (%s) ==="
          % (args.target.upper(), "LIVE THAT" if args.target == "live" else "DEMO"))
    if not rep.get("ok"):
        print("  [LOI] khong doc duoc vi the: %s" % rep.get("err"))
        return 1
    w = rep.get("wallet") or {}
    print("  vi USDT: tong=%.2f dung=%.2f con=%.2f | multi-asset-margin=%s"
          % (_num(w.get("total")), _num(w.get("used")), _num(w.get("free")),
             rep.get("multi_assets_margin")))
    if not rep["positions"]:
        print("  (khong co vi the nao dang mo)")
        return 0
    print("  %-22s %-6s %10s %10s %9s %8s %s"
          % ("CAP", "HUONG", "NOTIONAL", "MARGIN", "LEV", "UPNL", "MARGIN TYPE"))
    for r in rep["positions"]:
        mt = "ISOLATED" if r["isolated"] else ("CROSS" if r["isolated"] is False else "?")
        print("  %-22s %-6s %10.2f %10.2f %9.0f %8.2f %s"
              % (r["symbol"][:22], r["side"], r["notional"], r["margin"], r["lev"],
                 r["uPnl"], mt))
    n_cross = sum(1 for r in rep["positions"] if r["isolated"] is False)
    print("  KET LUAN: %d vi the | %d dang CROSS" % (len(rep["positions"]), n_cross))
    if n_cross:
        print("  -> Muon chuyen sang ISOLATED: phai HUY lenh cho + DONG vi the truoc "
              "(Binance khong cho doi margin type khi con vi the/lenh cho).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
