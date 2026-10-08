"""Cổng "HOÀN THÀNH TESTNET" trước khi sang LIVE — chặt hơn `live_guard.py`.

Vì sao cần: `live_guard.py` chỉ xét **toàn bộ** journal (n>=50, PF>=1.2). Thực tế
08/10: PF toàn bộ = 1.214 (đạt) nhưng cửa sổ **14 ngày = 1.171 (không đạt)** ⇒ nếu
chỉ nhìn 1 con số tổng thì rất dễ sang tiền thật khi edge chưa ổn định. Module này
biến "hoàn thành" thành các cổng đo được, chạy lại được mỗi ngày.

Tất định 100%: chỉ ĐỌC journal + .env + risk_state.json. Không gọi LLM, không gọi
sàn, không sửa state.

    python live_ready.py                    # bảng + verdict (exit 0 = đạt, 2 = chưa)
    python live_ready.py --windows 7,14,30  # mặc định
    python live_ready.py --json logs/live_ready.json

Cổng (tất cả phải đạt):
  1. PF(R) >= 1.2 ở MỌI cửa sổ (7/14/30 ngày)
  2. PF($) >= 1.1 ở mọi cửa sổ  (tính cả phí ⇒ sát LIVE hơn PF(R))
  3. n(lệnh đóng, toàn bộ) >= 300
  4. Kill-switch sạch
  5. MAX_TOTAL_RISK_PCT <= 2.0; LEVERAGE <= 8 khi PF < 1.5
  6. Chiến lược nào có n >= STRAT_MIN_N và avgR <= -STRAT_AVG_R phải nằm trong
     STRATEGY_BLOCK (nếu không ⇒ còn đang trade bằng chiến lược âm)
  7. Cả 2 hướng LONG/SHORT đều >= 5 lệnh
"""
from __future__ import annotations

import argparse
import json
import os

try:  # đọc cùng .env với runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from live_guard import (  # noqa: E402
    MAX_LEVERAGE_UNTESTED, MAX_RISK_PCT_LIVE, PF_FOR_FULL_LEVERAGE, _kill_tripped,
)
from monitor_report import (  # noqa: E402
    DIRECTIONS_REQUIRED, MIN_DIRECTION_TRADES, MIN_PF, load_journal, match_pairs,
    stats,
)

MIN_PF_PNL = 1.1          # PF($) — tính cả phí, sát với tiền thật hơn PF(R)
MIN_TRADES_ALL = int(float(os.getenv("LIVE_MIN_TRADES", "300")) or 300)
WINDOWS_DEFAULT = (7, 14, 30)


def _env_strat() -> tuple:
    """(min_n, avg_r, block_tuple, gate_bat) — đọc lúc gọi để test đổi env được."""
    try:
        min_n = int(float(os.getenv("STRAT_MIN_N", "10")) or 10)
    except Exception:  # noqa: BLE001
        min_n = 10
    try:
        avg_r = float(os.getenv("STRAT_AVG_R", "0.10") or 0.10)
    except Exception:  # noqa: BLE001
        avg_r = 0.10
    block = tuple(s.strip() for s in os.getenv("STRATEGY_BLOCK", "").split(",") if s.strip())
    gate = os.getenv("STRATEGY_GATE", "true").strip().lower() in ("1", "true", "yes", "y", "on")
    return min_n, avg_r, block, gate


def window_pairs(pairs: list, days: float, now: float) -> list:
    """Các cặp (OPEN, CLOSE) có CLOSE trong `days` ngày gần nhất (0/âm = tất cả)."""
    if not days or days <= 0:
        return list(pairs)
    cut = now - float(days) * 86400.0
    out = []
    for o, c in pairs:
        try:
            ts = float((c or {}).get("ts") or 0.0)
        except Exception:  # noqa: BLE001
            ts = 0.0
        if ts and ts >= cut:
            out.append((o, c))
    return out


def check(cfg, journal_path: str = "logs/journal.jsonl",
          windows=WINDOWS_DEFAULT, now: float | None = None) -> dict:
    """Kiểm tra cổng HOÀN THÀNH. Trả dict(ok, verdict, blockers, warnings, windows, facts)."""
    import time as _time
    now = float(now if now is not None else _time.time())
    opens, closes = load_journal(journal_path)
    pairs, still = match_pairs(opens, closes)
    st_all = stats(pairs)

    wins_stats: dict = {}
    for d in windows:
        wins_stats[int(d)] = stats(window_pairs(pairs, d, now))

    blockers: list = []
    warnings: list = []

    if not st_all["n"]:
        blockers.append("journal chua co lenh dong nao (n=0) — chua the danh gia")
    for d in sorted(wins_stats):
        s = wins_stats[d]
        if not s["n"]:
            blockers.append(f"cua so {d} ngay: khong co lenh dong nao")
            continue
        if float(s["pf_r"]) < MIN_PF:
            blockers.append(f"PF(R) cua so {d} ngay = {s['pf_r']:.3f} < {MIN_PF}")
        if float(s["pf_pnl"]) < MIN_PF_PNL:
            blockers.append(f"PF($) cua so {d} ngay = {s['pf_pnl']:.3f} < {MIN_PF_PNL}")
    if int(st_all["n"]) < MIN_TRADES_ALL:
        blockers.append(f"n lenh dong toan bo = {st_all['n']} < {MIN_TRADES_ALL}")

    risk_pct = float(getattr(cfg, "max_total_risk_pct", 0.0) or 0.0)
    lev = int(getattr(cfg, "leverage", 0) or 0)
    if risk_pct > MAX_RISK_PCT_LIVE:
        blockers.append(f"MAX_TOTAL_RISK_PCT = {risk_pct:.2f}% > {MAX_RISK_PCT_LIVE:.1f}%")
    if float(st_all["pf_r"]) < PF_FOR_FULL_LEVERAGE and lev > MAX_LEVERAGE_UNTESTED:
        blockers.append(f"LEVERAGE = {lev} > {MAX_LEVERAGE_UNTESTED} khi PF < "
                        f"{PF_FOR_FULL_LEVERAGE}")

    ks_path = str(getattr(cfg, "risk_state_path", "logs/risk_state.json") or "")
    tripped, ks_reason = _kill_tripped(ks_path) if ks_path else (False, "")
    if tripped:
        blockers.append(f"kill-switch dang TRIPPED ({ks_reason}) — chay `python risk.py --reset`")

    min_n, avg_r_thr, block, gate = _env_strat()
    weak = {}
    for code, g in (st_all.get("by_strategy") or {}).items():
        if code in ("?", "NONE"):
            continue
        if int(g.get("n", 0)) >= min_n and float(g.get("avg_r", 0.0)) <= -avg_r_thr:
            weak[code] = g
    if gate:
        for code, g in weak.items():
            if code not in block:
                blockers.append(
                    f"chien luoc {code} (n={g['n']} avgR={g['avg_r']:+.2f}) dang am nhung "
                    f"CHUA nam trong STRATEGY_BLOCK")
            else:
                warnings.append(f"chien luoc {code} am (n={g['n']}) — da bi STRATEGY_BLOCK chan")
    for d in DIRECTIONS_REQUIRED:
        g = (st_all.get("by_direction") or {}).get(d) or {}
        if int(g.get("n", 0)) < MIN_DIRECTION_TRADES:
            blockers.append(f"huong {d} chi co {int(g.get('n', 0))} lenh "
                            f"< {MIN_DIRECTION_TRADES} (mau chua can doi)")

    if bool(getattr(cfg, "testnet", True)):
        warnings.append("dang TESTNET (BINANCE_TESTNET=true) — sang LIVE phai doi "
                        "BINANCE_TESTNET=false")
    if not bool(getattr(cfg, "live_confirm", False)):
        warnings.append("LIVE_CONFIRM=false — live_guard.py se chan khi doi sang LIVE")
    if still:
        warnings.append(f"{len(still)} OPEN chua co CLOSE trong journal (lich su ghi chep)")

    facts = {"n_all": int(st_all["n"]), "pf_r_all": float(st_all["pf_r"]),
             "pf_pnl_all": float(st_all["pf_pnl"]), "risk_pct": risk_pct, "leverage": lev,
             "kill_tripped": tripped,
             "weak_unblocked": sorted(c for c in weak if c not in block) if gate else [],
             "min_trades": MIN_TRADES_ALL, "min_pf": MIN_PF, "min_pf_pnl": MIN_PF_PNL}
    return {"ok": not blockers,
            "verdict": "HOAN THANH" if not blockers else "CHUA HOAN THANH",
            "blockers": blockers, "warnings": warnings,
            "windows": wins_stats, "all": st_all, "facts": facts}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cong HOAN THANH TESTNET truoc khi LIVE")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    ap.add_argument("--windows", default=",".join(str(w) for w in WINDOWS_DEFAULT))
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)
    try:
        windows = tuple(int(x) for x in str(args.windows).split(",") if x.strip())
    except Exception:  # noqa: BLE001
        windows = WINDOWS_DEFAULT
    from config import Settings  # import muon -> CLI nhe, test khong can env
    rep = check(Settings(), journal_path=args.journal, windows=windows)
    f = rep["facts"]
    print("=" * 92)
    print("CONG HOAN THANH TESTNET -> LIVE | n_toan_bo=%d/%d | PF(R)=%.3f | PF($)=%.3f"
          % (f["n_all"], f["min_trades"], f["pf_r_all"], f["pf_pnl_all"]))
    print("=" * 92)
    print("  %-10s %5s %7s %8s %8s %9s %10s"
          % ("CUA SO", "n", "WR%", "PF(R)", "PF($)", "E(R)", "PnL$"))
    for d in sorted(rep["windows"]):
        s = rep["windows"][d]
        print("  %-10s %5d %7.1f %8.3f %8.3f %+9.4f %+10.2f"
              % ("%d ngay" % d, s["n"], s["wr"], s["pf_r"], s["pf_pnl"], s["e_r"], s["pnl"]))
    s = rep["all"]
    print("  %-10s %5d %7.1f %8.3f %8.3f %+9.4f %+10.2f"
          % ("toan bo", s["n"], s["wr"], s["pf_r"], s["pf_pnl"], s["e_r"], s["pnl"]))
    print("  nguong    : PF(R)>=%s  PF($)>=%s  n>=%d  risk<=%.1f%%  lev<=%d khi PF<%.1f"
          % (f["min_pf"], f["min_pf_pnl"], f["min_trades"], MAX_RISK_PCT_LIVE,
             MAX_LEVERAGE_UNTESTED, PF_FOR_FULL_LEVERAGE))
    print("  kill-switch: %s" % ("TRIPPED" if f["kill_tripped"] else "binh thuong"))
    print("-" * 92)
    print("VERDICT: %s" % rep["verdict"])
    for b in rep["blockers"]:
        print("   [CHAN] %s" % b)
    for w in rep["warnings"]:
        print("   [WARN] %s" % w)
    if args.json:
        try:
            os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, ensure_ascii=False, indent=1)
            print("[OK] da luu %s" % args.json)
        except Exception as exc:  # noqa: BLE001
            print("[WARN] khong luu duoc json: %s" % exc)
    return 0 if rep["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


