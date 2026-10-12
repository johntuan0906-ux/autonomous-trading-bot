"""Dung -> (tuy chon) cho HET vi the -> reset kill-switch -> chay lai — 1 lenh.

    python tools/restart_bot.py --target live --reset --wait-flat
    python tools/restart_bot.py --target both --reset
    python tools/restart_bot.py --target testnet --dry-run

Vi sao co script nay: quy trinh thu cong truoc day 5-6 buoc (tim PID supervisor,
tim PID con, taskkill, doi, `python risk.py --reset`, chay lai `pythonw
run_forever.py`, roi lai phai kiem tra) — moi buoc la mot lenh trong terminal VS
Code dang chap chon, va rat de quen buoc reset (bot boot lai van bi kill-switch).

Thu tu AN TOAN (dung nhu CONTEXT §6):
 1. (--wait-flat) cho den khi khong con vi the mo -> khong bo roi vi the khi tat.
 2. taskkill /F /T cay supervisor (kill ca con + thread).
 3. xoa logs/risk_state.json ( = `python risk.py --reset`) — CHI khi bot da dung.
 4. chay lai `pythonw run_forever.py` (an cua so).
 5. (--stagger) cho N giay giua 2 instance de khong chong vong quet dau.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
TARGETS = {"testnet": ROOT, "live": LIVE_DIR}


def instance_dir(target: str) -> Path:
    """Thu muc cua instance ('testnet' -> repo chinh, 'live' -> ../atb-live)."""
    return TARGETS[str(target).lower()]


def read_supervisor_pid(d: Path) -> int:
    try:
        return int((d / "logs" / ".supervisor.lock").read_text(encoding="utf-8").strip())
    except Exception:  # noqa: BLE001
        return 0


def _hide() -> dict:
    try:
        import winproc
        return winproc.hide_kwargs()
    except Exception:  # noqa: BLE001
        return {}


def pid_alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                             capture_output=True, text=True, timeout=15, **_hide()).stdout
        return str(pid) in (out or "")
    except Exception:  # noqa: BLE001
        return False


def kill_tree(pid: int) -> bool:
    """Kill ca cay tien trinh (supervisor + turbo + thread)."""
    if not pid:
        return False
    try:
        r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, text=True, timeout=60, **_hide())
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def env_kv(d: Path) -> dict:
    """Doc `.env` cua instance -> dict (bo comment, cat khoang trang)."""
    out: dict = {}
    try:
        txt = (d / ".env").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, _, v = ln.partition("=")
        out[k.strip()] = v.strip()
    return out


def exchange_client(d: Path):
    """Client ccxt theo `.env` cua instance (None neu thieu key/ccxt).

    Dung de doc VI THE THAT tren san — nguon su that duy nhat (journal chi la
    lich su ghi chep, da nhieu lan co dong OPEN mo coi lam tuong con vi the).
    """
    kv = env_kv(d)
    key, sec = kv.get("BINANCE_API_KEY", ""), kv.get("BINANCE_API_SECRET", "")
    if not key or not sec:
        return None
    try:
        import ccxt
    except Exception:  # noqa: BLE001
        return None
    try:
        ex = ccxt.binanceusdm({"apiKey": key, "secret": sec,
                               "enableRateLimit": True, "timeout": 20000})
        if str(kv.get("BINANCE_TESTNET", "true")).lower() in ("1", "true", "yes"):
            try:
                ex.enable_demo_trading(True)
            except Exception:  # noqa: BLE001
                pass
        return ex
    except Exception:  # noqa: BLE001
        return None


def live_open_positions(d: Path, client=None) -> int | None:
    """So vi the DANG MO tren san. None = khong doc duoc (fail-safe)."""
    ex = client if client is not None else exchange_client(d)
    if ex is None:
        return None
    try:
        rows = ex.fetch_positions() or []
    except Exception:  # noqa: BLE001
        return None
    n = 0
    for p in rows:
        try:
            if abs(float(p.get("contracts") or 0)) > 0:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def open_positions(d: Path) -> int:
    """So vi the dang mo theo JOURNAL (OPEN chua co CLOSE cung cap).

    Chi la kiem tra MEM — journal co the con dong OPEN mo coi (lenh da dong
    nhung thieu ban ghi CLOSE). Uu tien `live_open_positions()` khi co mang.
    """
    opened: dict = {}
    j = d / "logs" / "journal.jsonl"
    try:
        lines = j.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0
    for ln in lines[-20000:]:
        try:
            rec = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        sym = rec.get("pair")
        if not sym:
            continue
        ev = rec.get("event")
        if ev == "OPEN":
            opened[sym] = opened.get(sym, 0) + 1
        elif ev == "CLOSE":
            opened[sym] = opened.get(sym, 0) - 1
    return sum(1 for v in opened.values() if v > 0)


def wait_flat(d: Path, timeout: float = 900.0, poll: float = 30.0) -> tuple:
    """Cho den khi HET vi the mo (uu tien doc san; khong doc duoc thi dung journal)."""
    t0 = time.time()
    while True:
        n = live_open_positions(d)
        src = "san"
        if n is None:
            n, src = open_positions(d), "journal"
        if n <= 0:
            return True, "da phang (%s)" % src
        if time.time() - t0 > timeout:
            return False, "con %d vi the (%s) sau %ds" % (n, src, int(timeout))
        time.sleep(poll)


def reset_killswitch(d: Path) -> bool:
    """Xoa logs/risk_state.json (= `python risk.py --reset`). Chi khi bot DA DUNG."""
    p = d / "logs" / "risk_state.json"
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False


def start(d: Path) -> int:
    """Chay lai supervisor (an cua so) — tra PID."""
    py = Path(sys.executable)
    pythonw = py.with_name("pythonw.exe")
    exe = str(pythonw if pythonw.exists() else py)
    p = subprocess.Popen([exe, "run_forever.py"], cwd=str(d), **_hide())
    return int(p.pid)

def restart_one(target: str, reset: bool, wait: bool, dry: bool,
                timeout: float = 900.0) -> dict:
    """Chay tron quy trinh an toan cho 1 instance. Tra bao cao dict."""
    d = instance_dir(target)
    rep: dict = {"target": target, "dir": str(d)}
    if not d.exists():
        rep["err"] = "khong co thu muc instance"
        return rep
    rep["positions_before"] = open_positions(d)
    n_ex = live_open_positions(d)
    rep["positions_on_exchange"] = n_ex
    if n_ex is not None:
        rep["positions_before"] = n_ex
    if wait and rep["positions_before"]:
        if dry:
            rep["wait_flat"] = "dry-run: se cho het vi the"
        else:
            ok, why = wait_flat(d, timeout=timeout)
            rep["wait_flat"] = why
            if not ok:
                rep["err"] = "chua phang — KHONG dung bot (tranh bo roi vi the)"
                return rep
    pid = read_supervisor_pid(d)
    rep["supervisor_pid"] = pid
    if dry:
        rep["dry_run"] = True
        return rep
    if pid_alive(pid):
        rep["killed"] = kill_tree(pid)
        time.sleep(3.0)
    else:
        rep["killed"] = False
        rep["note"] = "supervisor khong song (khong can kill)"
    if reset:
        rep["reset"] = reset_killswitch(d)
    rep["started_pid"] = start(d)
    return rep


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Restart bot an toan (dung -> reset -> chay)")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--reset", action="store_true", help="xoa risk_state (go kill-switch)")
    ap.add_argument("--wait-flat", action="store_true",
                    help="cho het vi the mo truoc khi dung (an toan cho LIVE)")
    ap.add_argument("--timeout", type=float, default=900.0,
                    help="giay cho toi da khi --wait-flat")
    ap.add_argument("--stagger", type=float, default=90.0,
                    help="giay cho giua 2 instance (mac dinh 90 — tranh chong vong quet dau)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    targets = ["live", "testnet"] if args.target == "both" else [args.target]
    for i, t in enumerate(targets):
        if i and not args.dry_run:
            print("... cho %.0fs de lech pha vong quet" % args.stagger)
            time.sleep(max(0.0, args.stagger))
        rep = restart_one(t, args.reset, args.wait_flat, args.dry_run, args.timeout)
        print("%-8s %s" % (t.upper(), json.dumps(rep, ensure_ascii=False)))
        if rep.get("err"):
            print("         LOI: %s" % rep["err"])
    print("XONG. Kiem tra lai: python tools/ops.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
