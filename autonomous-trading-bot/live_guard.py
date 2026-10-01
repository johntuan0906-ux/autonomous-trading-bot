"""Phase 5 - INTERLOCK LIVE: chan cung truoc khi chay tien that.

Vi sao: doi `BINANCE_TESTNET=false` la thay doi RUI RO LON NHAT cua ca du an,
truoc day chi can 1 dong .env -> mot lan doi nham se bo qua toan bo thoi gian
thu nghiem (va co the mat tien that). Module nay bien cac "dieu kien san sang"
trong README thanh CODE CHAY THAT, duoc goi tu `turbo_demo.main()` truoc vong
lap trade, va co the kiem tra tay bat cu luc nao:

    python live_guard.py

Blocker (KHONG cho chay LIVE):
  1. LIVE_CONFIRM != true                                (phai xac nhan tay)
  2. Journal: n(lenh dong) < MIN_TRADES(50) hoac PF(R) < MIN_PF(1.2)
  3. MAX_TOTAL_RISK_PCT > 2.0                            (moi len live <= 2%)
  4. LEVERAGE > 10
  5. LEVERAGE > 8 khi PF < 1.5                           (chua co edge thi khong tang don)
  6. Kill-switch dang tripped                            (phai --reset truoc)

Warn (KHONG chan): DRY_RUN=true, OPEN chua ghep trong journal.
Tat dinh 100%: khong goi LLM, khong goi san, khong sua state — chi DOC va KET LUAN.
"""
from __future__ import annotations

import argparse
import json

try:  # doc cung .env voi runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

from monitor_report import MIN_PF, MIN_TRADES, load_journal, match_pairs, stats  # noqa: E402

MAX_RISK_PCT_LIVE = 2.0      # tran tong risk khi vao tien that
MAX_LEVERAGE_LIVE = 10
MAX_LEVERAGE_UNTESTED = 8    # chua chung minh edge (PF<1.5) -> khong vuot
PF_FOR_FULL_LEVERAGE = 1.5


def _get(cfg, name, default):
    """Doc thuoc tinh config an toan (ho tro ca SimpleNamespace trong test)."""
    try:
        v = getattr(cfg, name, default)
    except Exception:  # noqa: BLE001
        return default
    return default if v is None else v


def _kill_tripped(path: str) -> tuple:
    """Tra (tripped, reason) tu risk_state.json — thieu file/loi -> (False, '')."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            rs = json.load(f)
        return bool(rs.get("tripped")), str(rs.get("reason") or "")
    except Exception:  # noqa: BLE001
        return False, ""


def _gather(cfg, journal_path: str) -> tuple:
    """Doc journal + risk_state -> (facts, blockers, warns, targets)."""
    testnet = bool(_get(cfg, "testnet", True))
    dry_run = bool(_get(cfg, "dry_run", True))
    confirm = bool(_get(cfg, "live_confirm", False))
    lev = int(_get(cfg, "leverage", 0) or 0)
    risk_pct = float(_get(cfg, "max_total_risk_pct", 0.0) or 0.0)
    ks_path = str(_get(cfg, "risk_state_path", "logs/risk_state.json"))
    tripped, ks_reason = _kill_tripped(ks_path)

    opens, closes = load_journal(journal_path)
    pairs, still = match_pairs(opens, closes)
    st = stats(pairs)
    n, pf = int(st.get("n", 0) or 0), float(st.get("pf_r", 0.0) or 0.0)

    facts = {"testnet": testnet, "dry_run": dry_run, "live_confirm": confirm,
             "n_closed": n, "pf_r": round(pf, 3), "max_total_risk_pct": risk_pct,
             "leverage": lev, "kill_tripped": tripped, "kill_reason": ks_reason,
             "journal_open_orphans": len(still)}
    targets = {"min_trades": MIN_TRADES, "min_pf": MIN_PF,
               "max_total_risk_pct": MAX_RISK_PCT_LIVE,
               "max_leverage": MAX_LEVERAGE_LIVE,
               "pf_de_tang_don": PF_FOR_FULL_LEVERAGE}
    blockers: list = []
    warns: list = []

    if not testnet:
        if not confirm:
            blockers.append("LIVE_CONFIRM != true — phai bat tay trong .env "
                            "(LIVE_CONFIRM=true) de xac nhan doi tien that")
        if n < MIN_TRADES:
            blockers.append(f"journal moi co {n} lenh dong < {MIN_TRADES} — "
                            "chua du bang chung")
        if pf < MIN_PF:
            blockers.append(f"PF(R)={pf:.3f} < {MIN_PF} — heuristic chua co edge")
        if risk_pct > MAX_RISK_PCT_LIVE + 1e-9:
            blockers.append(f"MAX_TOTAL_RISK_PCT={risk_pct:g} > {MAX_RISK_PCT_LIVE:g} — "
                            "ha xuong <= 2% truoc khi vao tien that")
        if lev > MAX_LEVERAGE_LIVE:
            blockers.append(f"LEVERAGE={lev} > {MAX_LEVERAGE_LIVE}")
        elif lev > MAX_LEVERAGE_UNTESTED and pf < PF_FOR_FULL_LEVERAGE:
            blockers.append(f"LEVERAGE={lev} > {MAX_LEVERAGE_UNTESTED} nhung "
                            f"PF(R)={pf:.3f} < {PF_FOR_FULL_LEVERAGE} — "
                            "chua chung minh edge, ha don bay")
        if tripped:
            blockers.append(f"kill-switch dang tripped ({ks_reason}) — xu ly roi "
                            "`python risk.py --reset`")
        if dry_run:
            warns.append("DRY_RUN=true — bot se khong gui lenh that du da qua interlock")
        if still:
            warns.append(f"{len(still)} OPEN chua co CLOSE trong journal (co the la vi the "
                         "mo tay hoac lenh dong bi thieu) — xem `python positions.py`")
    return facts, blockers, warns, targets


def check(cfg, journal_path: str = "logs/journal.jsonl") -> dict:
    """Kiem tra dieu kien LIVE. Tra dict(ok, live, blockers, warnings, facts, targets)."""
    facts, blockers, warns, targets = _gather(cfg, journal_path)
    if facts["testnet"]:
        return {"ok": True, "live": False, "blockers": [],
                "warnings": ["dang TESTNET (BINANCE_TESTNET=true) -> interlock "
                             "khong ap dung"],
                "facts": facts, "targets": targets}
    return {"ok": not blockers, "live": True, "blockers": blockers,
            "warnings": warns, "facts": facts, "targets": targets}


def enforce(cfg, log=None, journal_path: str = "logs/journal.jsonl") -> dict:
    """Goi tu turbo_demo: log ket qua, tra report (caller tu exit neu not ok)."""
    rep = check(cfg, journal_path=journal_path)
    if log is not None:
        f = rep["facts"]
        if rep["live"] and rep["ok"]:
            log.warning("LIVE INTERLOCK OK: du dieu kien sang tien that "
                        "(n=%s PF=%s risk=%s%% lev=%s)", f["n_closed"], f["pf_r"],
                        f["max_total_risk_pct"], f["leverage"])
        elif rep["live"]:
            log.error("LIVE INTERLOCK CHAN: %s", " | ".join(rep["blockers"]))
        else:
            log.info("che do TESTNET — khong ap dung interlock LIVE")
        for w in rep["warnings"]:
            log.warning("live_guard: %s", w)
    return rep


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 5: kiem tra dieu kien chay LIVE")
    ap.add_argument("--journal", default="logs/journal.jsonl")
    args = ap.parse_args(argv)
    from config import Settings  # import muon -> CLI nhe, test khong can env
    rep = check(Settings(), journal_path=args.journal)
    f, t = rep["facts"], rep["targets"]
    print("=" * 88)
    print("LIVE INTERLOCK (Phase 5) | testnet=%s dry_run=%s live_confirm=%s"
          % (f["testnet"], f["dry_run"], f["live_confirm"]))
    print("=" * 88)
    print("  journal     : n_dong=%d/%d   PF(R)=%.3f/%s"
          % (f["n_closed"], t["min_trades"], f["pf_r"], t["min_pf"]))
    print("  risk/account: risk_tong=%.2f%%/%.0f%%  leverage=%d/%d (PF<%.1f -> <=8)"
          % (f["max_total_risk_pct"], t["max_total_risk_pct"], f["leverage"],
             t["max_leverage"], t["pf_de_tang_don"]))
    print("  kill-switch : %s" % ("TRIPPED — " + f["kill_reason"] if f["kill_tripped"]
                                  else "binh thuong"))
    if not rep["live"]:
        print("\n-> Dang TESTNET: khong co gi bi chan. Muon thu LIVE: "
              "dat BINANCE_TESTNET=false (interlock se kiem tra lai).")
        return 0
    print("\n-> %s" % ("DU DIEU KIEN: cho phep chay LIVE."
                       if rep["ok"] else "CHAN: KHONG duoc chay LIVE."))
    for b in rep["blockers"]:
        print("   [BLOCK] %s" % b)
    for w in rep["warnings"]:
        print("   [WARN ] %s" % w)
    return 0 if rep["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
