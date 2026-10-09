"""Ngưỡng rủi ro theo số dư THẬT — 3 mức (dải), quyết định risk% / MAX_POSITIONS / cặp.

Bảng (theo **equity thật**, USDT) — đúng yêu cầu "ngưỡng theo khoảng":

| Equity thật | Mức | risk/lệnh | MAX_POSITIONS | Cặp | Vì sao |
|---|---|---|---|---|---|
| `< 20` | **giảm lệnh** | 1.0% | **1** | SOL/XRP/ADA/DOGE/AVAX | notional ~16$ > min 5$; BTC(50$)/LINK(20$) bị sàn từ chối; 1 vị thế để margin ~10-18% |
| `20 .. < 100` | **cân bằng** | 0.5% | **2** | + LINK | notional 8-40$; BTC vẫn thiếu (cần ≥50$) |
| `>= 100` | **an toàn** | 1.0% | **4** | đủ (kể cả BTC) | notional ≥80$ ⇒ BTC đủ min 50$; margin 4 vị thế ~40% |

Số liệu gốc (đo thật, xem `logs/money_probe.py`):
- Min notional USDT-M (ccxt): BTC **50$**, LINK **20$**, SOL/XRP/DOGE/ADA/AVAX **5$**.
- SL trung vị **1.24%** ⇒ `notional = risk / SL%`; với equity 20$ & risk 1% ⇒ notional ~16$.
- Margin 8x: 4 vị thế ≈ 40–71% equity ⇒ dưới 20$ chỉ nên 1–2 vị thế.

Chạy: `python risk_tier.py 20`  (xem mức + cấu hình sẽ áp dụng)
"""
from __future__ import annotations

import argparse
import sys

TIERS: tuple = (
    {"name": "reduced", "label": "giảm lệnh", "lo": 0.0, "hi": 20.0,
     "risk_pct": 1.0, "max_positions": 1,
     "symbols": "SOL/USDT:USDT,XRP/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT",
     "note": "1 vi the; bo BTC (50$) va LINK (20$) — chua du notional"},
    {"name": "balanced", "label": "cân bằng", "lo": 20.0, "hi": 62.0,
     "risk_pct": 0.5, "max_positions": 2,
     "symbols": "SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT",
     "note": "2 vi the; risk 0.5% -> notional 8-25$ (LINK tu ~50$, BTC tu 124$)"},
    {"name": "balanced_btc", "label": "cân bằng + BTC", "lo": 62.0, "hi": 100.0,
     "risk_pct": 1.0, "max_positions": 2,
     "symbols": "BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT",
     "note": "2 vi the; BTC da du notional (>=50$) o risk 1%"},
    {"name": "safe", "label": "an toàn", "lo": 100.0, "hi": None,
     "risk_pct": 1.0, "max_positions": 4,
     "symbols": "BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT",
     "note": "4 vi the; du cap (BTC + LINK)"},
)

# Min notional THAT cua san (ccxt, USDT-M) — do 09/10: BTC 50$, LINK 20$, alt 5$.
MIN_NOTIONAL = {"BTC/USDT:USDT": 50.0, "LINK/USDT:USDT": 20.0}
DEFAULT_MIN_NOTIONAL = 5.0
# SL tham chieu = trung vi do tu journal (logs/money_probe.py). Dung de uoc notional.
SL_REF_PCT = 1.24


def min_notional(sym: str) -> float:
    return float(MIN_NOTIONAL.get(str(sym), DEFAULT_MIN_NOTIONAL))


def notional_for(equity, risk_pct, sl_ref_pct: float = SL_REF_PCT) -> float:
    """Notional uoc tinh cho 1 lenh: risk_usd / SL% (risk_usd = equity x risk_pct%)."""
    try:
        eq = float(equity)
    except (TypeError, ValueError):
        eq = 0.0
    try:
        rp = float(risk_pct)
        sl = float(sl_ref_pct)
    except (TypeError, ValueError):
        return 0.0
    if sl <= 0:
        return 0.0
    return (eq * rp / 100.0) / (sl / 100.0)


def feasible(sym: str, equity, risk_pct, sl_ref_pct: float = SL_REF_PCT) -> bool:
    """Cap nay co du notional toi thieu cua san khong (uoc theo SL tham chieu)?"""
    return notional_for(equity, risk_pct, sl_ref_pct) >= min_notional(sym)


def btc_min_equity(risk_pct: float, sl_ref_pct: float = SL_REF_PCT) -> float:
    """Equity toi thieu de BTC du notional 50$ o risk_pct cho truoc."""
    try:
        rp = float(risk_pct)
    except (TypeError, ValueError):
        return 0.0
    if rp <= 0:
        return 0.0
    return min_notional("BTC/USDT:USDT") * (float(sl_ref_pct) / 100.0) / (rp / 100.0)


def _filter(csv_text, equity, risk_pct, sl_ref_pct: float = SL_REF_PCT) -> tuple:
    """(csv giu lai, danh sach bi loai) theo kha thi notional."""
    keep, drop = [], []
    for s in [x.strip() for x in str(csv_text or "").split(",") if x.strip()]:
        (keep if feasible(s, equity, risk_pct, sl_ref_pct) else drop).append(s)
    return ",".join(keep), drop


def tier_for(equity, sl_ref_pct: float = SL_REF_PCT) -> dict:
    """Mức rủi ro cho số dư `equity` (USDT) — đã LỌC cặp theo min notional thật.

    Equity None/<=0 -> mức thấp nhất. Trả kèm:
      `dropped` (cặp bị loại vì thiếu notional), `notional`/`risk_usd` (ước tính/lệnh),
      `equity` (số dư đã dùng), `feasible_any` (còn cặp nào vào được không).
    """
    try:
        eq = float(equity)
    except (TypeError, ValueError):
        eq = 0.0
    if eq <= 0:
        base = dict(TIERS[0])
    else:
        base = dict(TIERS[-1])
        for t in TIERS:
            hi = t["hi"]
            if hi is None or eq < float(hi):
                base = dict(t)
                break
    risk_pct = float(base["risk_pct"])
    syms, drop1 = _filter(base["symbols"], eq, risk_pct, sl_ref_pct)
    extra, drop2 = _filter(base["extra_symbols"], eq, risk_pct, sl_ref_pct)
    base["symbols"] = syms
    base["extra_symbols"] = extra
    base["dropped"] = drop1 + drop2
    base["notional"] = round(notional_for(eq, risk_pct, sl_ref_pct), 2)
    base["risk_usd"] = round(eq * risk_pct / 100.0, 4)
    base["equity"] = eq
    base["feasible_any"] = bool(syms or extra)
    return base


def env_updates(tier: dict) -> dict:
    """Các dòng `.env` cần đổi để áp mức này."""
    return {"RISK_PER_TRADE_PCT": str(tier["risk_pct"]),
            "MAX_POSITIONS": str(tier["max_positions"]),
            "SYMBOLS": str(tier["symbols"]),
            "EXTRA_SYMBOLS": str(tier["extra_symbols"])}


def table_md(equity=None) -> str:
    """Bảng 3 mức (markdown) — dùng cho STATE.md; đánh dấu mức hiện tại nếu có equity."""
    cur = tier_for(equity)["name"] if equity is not None else None
    lines = ["| Equity thật (USDT) | Mức | risk/lệnh | MAX_POS | Cặp |", "|---|---|---|---|---|"]
    for t in TIERS:
        hi = "trở lên" if t["hi"] is None else ("– < %g" % t["hi"])
        mark = " ⬅ **hiện tại**" if cur == t["name"] else ""
        rng = ("< %g" % t["hi"]) if t["lo"] == 0 else ("%g %s" % (t["lo"], hi))
        lines.append("| %s | **%s**%s | %s%% | %s | %s |"
                     % (rng, t["label"], mark, t["risk_pct"], t["max_positions"],
                        t["symbols"] + (" + " + t["extra_symbols"] if t["extra_symbols"] else "")))
    return "\n".join(lines)


def preview(equity) -> str:
    """Text cho CLI: mức + cấu hình sẽ ghi vào .env + lý do lọc cặp."""
    t = tier_for(equity)
    out = ["Equity = %s USDT -> muc **%s** (%s)" % (t.get("equity"), t["name"], t["label"]),
           "  %s" % t["note"],
           "  notional uoc tinh/lenh = %.2f$ · risk/lệnh = %.4f$" % (t["notional"], t["risk_usd"])]
    if t["dropped"]:
        out.append("  LOAI %s (thieu notional toi thieu cua san)" % ", ".join(t["dropped"]))
    if not t["feasible_any"]:
        out.append("  ! KHONG cap nao du notional -> chua the vao lenh (can nap them)")
    out.append("")
    for k, v in env_updates(t).items():
        out.append("  %-20s = %s" % (k, v))
    out += ["",
            "Nguong BTC (min notional 50$): can equity >= %.0f$ o risk 1%%, >= %.0f$ o risk 0.5%%"
            % (btc_min_equity(1.0), btc_min_equity(0.5)),
            "",
            table_md(equity)]
    return "\n".join(out)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Nguong rui ro theo so du that (3 muc)")
    ap.add_argument("equity", nargs="?", type=float, default=0.0,
                    help="so du THAT (USDT); bo trong = 0")
    args = ap.parse_args(argv)
    try:  # console Windows (cp1252) khong in duoc tieng Viet -> ep UTF-8
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print(preview(args.equity))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
