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
                  # (20/10) `-2022 ReduceOnly Order is rejected`: san TU CHOI `reduceOnly`
                  # cho lenh MARKET (do that: qty=1 tren vi the 31 hop dong van bi tu choi).
                  # Da xu ly tuong minh trong `exchange.close_position` (doc lai vi the ⇒
                  # `already_closed`, hoac dong lai bang qty THAT khong reduceOnly) nen no
                  # KHONG con duoc ghi ra log loi. Neu con xuat hien ⇒ **ca duong du phong
                  # cung that bai** (vi the co the dang MO COI) ⇒ phai nguoi xem.
                  "-2022",
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
    # (13/10) So vi the THAT + so lenh cho: doc tu snapshot do `orders_audit --json` ghi
    # (khong goi san o day de ops.py van chay < 1s).
    try:
        snap = json.loads((d / "logs" / "orders_snapshot.json").read_text(encoding="utf-8"))
        rep["positions"] = int(snap.get("positions") or 0)
        rep["orders"] = int(snap.get("orders") or 0)
        rep["orphans"] = int(snap.get("orphans") or 0)
    except Exception:  # noqa: BLE001
        rep["positions"] = rep.get("managed_trades")
        rep["orders"] = None
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
    if rep.get("orders") is not None or rep.get("positions") is not None:
        print("         san: %s vi the / %s lenh cho / %s mo coi (snapshot orders_audit)"
              % (rep.get("positions"), rep.get("orders"), rep.get("orphans", 0)))
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


def prom_lines(reps: list) -> list:
    """Sinh `logs/metrics.prom` (Prometheus textfile) tu bao cao ops.

    Ham thuan -> test duoc. Vi sao: (y tuong tu vxcontrol/pentagi) co stack quan sat
    thi moi thay xu huong (equity, so vi the, lenh cho, kill-switch, loi theo loai)
    thay vi doc log bang mat.
    """
    out = ["# HELP bot_equity USDT equity (demo hoac that)",
           "# TYPE bot_equity gauge",
           "# HELP bot_positions So vi the dang mo",
           "# TYPE bot_positions gauge",
           "# HELP bot_pending_orders So lenh cho (thuong + algo)",
           "# TYPE bot_pending_orders gauge",
           "# HELP bot_kill_switch 1 = kill-switch dang ngung",
           "# TYPE bot_kill_switch gauge",
           "# HELP bot_round Vong quet hien tai",
           "# TYPE bot_round gauge",
           "# HELP bot_heartbeat_age_seconds Tuoi nhip tim",
           "# TYPE bot_heartbeat_age_seconds gauge",
           "# HELP bot_errors_15m So lan xuat hien tung loai trong cua so",
           "# TYPE bot_errors_15m gauge"]
    for r in reps or []:
        lbl = 'instance="%s"' % str(r.get("name", "?")).lower()
        eq = r.get("equity")
        try:
            eqv = float(eq)
        except (TypeError, ValueError):
            eqv = 0.0
        out.append("bot_equity{%s} %s" % (lbl, eqv))
        out.append("bot_positions{%s} %d" % (lbl, int(r.get("positions") or 0)))
        out.append("bot_pending_orders{%s} %d" % (lbl, int(r.get("orders") or 0)))
        out.append("bot_kill_switch{%s} %d" % (lbl, 1 if r.get("kill_tripped") else 0))
        out.append("bot_round{%s} %s" % (lbl, r.get("round") or 0))
        out.append("bot_heartbeat_age_seconds{%s} %.1f"
                   % (lbl, float(r.get("hb_age_s") or 0.0)))
        for k, v in (r.get("errors_win") or {}).items():
            out.append('bot_errors_15m{%s,kind="%s"} %d' % (lbl, k, int(v)))
    return out


def write_prom(reps: list, path=None) -> str:
    """Ghi file metrics.prom (mac dinh logs/metrics.prom). Tra duong dan."""
    p = Path(path) if path else (ROOT / "logs" / "metrics.prom")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(prom_lines(reps)) + "\n", encoding="utf-8")
    except OSError:
        return ""
    return str(p)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bao cao suc khoe 2 instance bot")
    ap.add_argument("--minutes", type=float, default=7.0, help="cua so dem loi (phut)")
    ap.add_argument("--json", action="store_true", help="in JSON")
    ap.add_argument("--prom", action="store_true",
                    help="ghi logs/metrics.prom (Prometheus textfile)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    reps = [_instance("TESTNET", ROOT, args.minutes),
            _instance("LIVE", LIVE_DIR, args.minutes)]
    if args.prom:
        p = write_prom(reps)
        print("da ghi %s" % (p or "LOI"))
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
