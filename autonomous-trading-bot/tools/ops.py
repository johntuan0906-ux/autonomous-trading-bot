"""Bao cao suc khoe 2 instance (TESTNET + LIVE) — 1 lenh, ~30 dong.

    python tools/ops.py                  # bao cao nguoi doc
    python tools/ops.py --json           # cho may doc (state_sync/agent)
    python tools/ops.py --minutes 15     # cua so dem loi (mac dinh 7 phut)

Vi sao co script nay: truoc day moi lan kiem tra phai mo log bang tay (Get-Content
-Tail) roi dem bang mat; log turbo_err.log co dong dai hang KB (tom tat 458 cap)
nen de lam treo terminal VS Code. Script nay doc TRUC TIEP file, cat gon, in ra
dung nhung gi can quyet dinh: bot con song? vong quet co loi khong? kill-switch?
vi the? supervisor?

Khong import ccxt / pandas -> chay < 1s, an toan goi lien tuc.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
TAIL_BYTES = 300_000          # du cho ~2 vong quet 458 cap
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
COUNT_PATTERNS = ("FETCH_TIMEOUT", "DATA_FAIL", "Connection pool is full",
                  "Too many requests", "-1003", "KILL-SWITCH", "LIVE INTERLOCK",
                  "ORDER_FAILED", "OPENED", "REJECTED",
                  "qua han",        # canh bao fetch qua ROUND_TIMEOUT (tieng Viet)
                  "SKIP_DATA",      # du lieu xau bi bo qua (khong phai loi nang)
                  )
STATUS_RE = re.compile(r"'status': '([A-Z_]+)'")


def _read_tail(path: Path) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-TAIL_BYTES:].decode("utf-8", errors="replace")


def _window_lines(tail: str, minutes: float) -> list:
    """Chi lay cac dong co timestamp trong `minutes` phut gan nhat."""
    now = time.time()
    out = []
    for ln in tail.splitlines():
        m = TS_RE.match(ln)
        if not m:
            continue
        try:
            t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if 0 <= (now - t) <= minutes * 60:
            out.append(ln)
    return out


def _last_round(tail: str) -> tuple:
    """(so vong, round cuoi, Counter status) tu dong 'round N monitor=... -> [...]'."""
    rounds = re.findall(r"round (\d+) monitor=\S* -> (\[.*)$", tail, re.M)
    if not rounds:
        return 0, None, Counter()
    n, last = rounds[-1]
    return len(rounds), n, Counter(STATUS_RE.findall(last))

def _instance(name: str, d: Path, minutes: float) -> dict:
    rep: dict = {"name": name, "dir": str(d)}
    hb_p = d / "logs" / "heartbeat.json"
    try:
        hb = json.loads(hb_p.read_text(encoding="utf-8"))
        age = max(0.0, time.time() - hb_p.stat().st_mtime)
        rep.update({"round": hb.get("round"), "phase": hb.get("phase"),
                    "equity": hb.get("equity"), "pid": hb.get("pid"),
                    "hb_age_s": round(age, 1), "hb_stale": age > 900})
    except Exception as e:  # noqa: BLE001
        rep["hb_err"] = str(e)[:80]
    try:
        rs = json.loads((d / "logs" / "risk_state.json").read_text(encoding="utf-8"))
        rep["kill_tripped"] = bool(rs.get("tripped"))
        rep["kill_reason"] = rs.get("reason") or ""
        rep["start_equity"] = rs.get("start_equity")
        rep["consec_losses"] = rs.get("consec_losses")
    except Exception:  # noqa: BLE001
        rep["kill_tripped"] = False
    try:
        rep["supervisor_pid"] = int((d / "logs" / ".supervisor.lock").read_text().strip())
    except Exception:  # noqa: BLE001
        rep["supervisor_pid"] = 0
    try:
        ms = json.loads((d / "logs" / "managed_state.json").read_text(encoding="utf-8"))
        rep["managed_trades"] = len(ms.get("trades") or {})
    except Exception:  # noqa: BLE001
        rep["managed_trades"] = None
    tail = _read_tail(d / "logs" / "turbo_err.log")
    win = _window_lines(tail, minutes)
    counts = {p: sum(p in ln for ln in win) for p in COUNT_PATTERNS}
    rep["errors_win"] = {k: v for k, v in counts.items() if v}
    rep["log_lines_win"] = len(win)
    n_rounds, last_round, st = _last_round(tail)
    rep["rounds_in_tail"] = n_rounds
    rep["last_round"] = last_round
    rep["last_round_status"] = dict(st.most_common(6))
    last_ts = ""
    for ln in reversed(win):
        m = TS_RE.match(ln)
        if m:
            last_ts = m.group(1)
            break
    rep["last_log_ts"] = last_ts
    return rep


def _print(rep: dict, minutes: float) -> None:
    print("%-8s round=%-4s phase=%-16s equity=%-10s hb=%.0fs%s"
          % (rep["name"], rep.get("round"), rep.get("phase"), rep.get("equity"),
             rep.get("hb_age_s") or 0.0,
             "  [NHIP TIM CU -> supervisor se restart]" if rep.get("hb_stale") else ""))
    print("         supervisor=%s child_pid=%s managed=%s"
          % (rep.get("supervisor_pid") or "-", rep.get("pid") or "-",
             rep.get("managed_trades")))
    if rep.get("kill_tripped"):
        print("         KILL-SWITCH: TRIPPED (%s) -> dung bot, python risk.py --reset, chay lai"
              % rep.get("kill_reason"))
    errs = rep.get("errors_win") or {}
    print("         loi trong %.0f phut: %s"
          % (minutes, errs if errs else "KHONG (sach)"))
    print("         vong trong log: %s | vong cuoi #%s: %s"
          % (rep.get("rounds_in_tail"), rep.get("last_round"),
             rep.get("last_round_status") or "-"))
    print("         log cuoi: %s" % (rep.get("last_log_ts") or "-"))


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bao cao suc khoe 2 instance bot")
    ap.add_argument("--minutes", type=float, default=7.0, help="cua so dem loi (phut)")
    ap.add_argument("--json", action="store_true", help="in JSON")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    reps = [_instance("TESTNET", ROOT, args.minutes),
            _instance("LIVE", LIVE_DIR, args.minutes)]
    if args.json:
        print(json.dumps(reps, ensure_ascii=False, indent=1))
        return 0
    print("=== OPS REPORT %s | cua so %.0f phut ==="
          % (time.strftime("%Y-%m-%d %H:%M:%S"), args.minutes))
    for r in reps:
        _print(r, args.minutes)
    bad = [r["name"] for r in reps
           if r.get("kill_tripped") or r.get("hb_stale") or (r.get("errors_win") or {})]
    print("KET LUAN: %s" % ("OK — khong van de" if not bad
                            else "CAN XEM: " + ", ".join(bad)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
