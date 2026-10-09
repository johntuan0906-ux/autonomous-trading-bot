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
     "note": "1 vi the; bo BTC (min notional 50$) va LINK (20$)"},
    {"name": "balanced", "label": "cân bằng", "lo": 20.0, "hi": 100.0,
     "risk_pct": 0.5, "max_positions": 2,
     "symbols": "SOL/USDT:USDT,XRP/USDT:USDT,LINK/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,AVAX/USDT:USDT",
     "note": "2 vi the; bo BTC (can notional >= 50$)"},
    {"name": "safe", "label": "an toàn", "lo": 100.0, "hi": None,
     "risk_pct": 1.0, "max_positions": 4,
     "symbols": "BTC/USDT:USDT,SOL/USDT:USDT,XRP/USDT:USDT",
     "extra_symbols": "ADA/USDT:USDT,DOGE/USDT:USDT,LINK/USDT:USDT,AVAX/USDT:USDT",
     "note": "4 vi the; du cap (BTC du min notional)"},
)


def tier_for(equity) -> dict:
    """Mức rủi ro cho số dư `equity` (USDT). Equity None/<=0 -> mức thấp nhất."""
    try:
        eq = float(equity)
    except (TypeError, ValueError):
        eq = 0.0
    if eq <= 0:
        return dict(TIERS[0])
    for t in TIERS:
        hi = t["hi"]
        if hi is None or eq < float(hi):
            return dict(t)
    return dict(TIERS[-1])


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
    """Text cho CLI: mức + cấu hình sẽ ghi vào .env."""
    t = tier_for(equity)
    out = ["Equity = %s USDT -> muc **%s** (%s)" % (equity, t["name"], t["label"]),
           "  %s" % t["note"], ""]
    for k, v in env_updates(t).items():
        out.append("  %-20s = %s" % (k, v))
    out += ["", table_md(equity)]
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
