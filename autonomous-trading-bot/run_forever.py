"""Supervisor chay turbo_demo lien tuc, tu restart khi crash.

Chay bang pythonw.exe (khong co cua so console) de song doc lap VS Code:
    pythonw run_forever.py

- Chi 1 instance (khoa theo PID trong logs/.supervisor.lock).
- Ghi marker [supervisor] vao logs/turbo_err.log truoc/sau moi lan restart.
- Tu start lai sau 15s neu turbo_demo thoat (crash/loi mang/...).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
try:                       # doc WATCHDOG_SEC... tu .env (giong config.py)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:  # noqa: BLE001
    pass
ERR = ROOT / "logs" / "turbo_err.log"
OUT = ROOT / "logs" / "turbo_out.log"
SYNC_OUT = ROOT / "logs" / "state_sync.log"
# (08/10) Dong bo bo nho du an + tu dong sang LIVE: supervisor goi state_sync.py
# moi STATE_SYNC_SEC giay (0 = tat). Xem state_sync.py (5 chot an toan truoc khi doi).
STATE_SYNC_SEC = int(os.getenv("STATE_SYNC_SEC", "1800"))
LOCK = ROOT / "logs" / ".supervisor.lock"
HEARTBEAT = ROOT / "logs" / "heartbeat.json"
RESTART_DELAY_SEC = 15
# P0-spin: 2026-09-30 thuc te — kill-switch tripped lam turbo exit sau ~1s, supervisor
# restart moi 20s => 3500+ lan trong 1 dem: log phinh, dong ERROR that bi chon trong
# bien. Bot thoat NHANH lien tuc thi phai backoff (x2, tran 5 phut).
FAST_EXIT_SEC = 30
BACKOFF_MAX_SEC = 300
# Kill-switch dang TRIPPED thi du restart cung KHONG the trade (turbo tu thoat ngay).
# Ban cu: cu restart moi 300s -> 1 dem ~288 lan + 1 dong loi lap lai => nhin nhu
# "kill-switch trip lien tuc" du that ra chi 1 lan trip. Gio: backoff rieng, dai hon
# (600s -> 1200 -> 2400 -> 3600), va ghi ro phai lam gi (risk.py --reset).
KILL_BLOCKED = "KILL-SWITCH dang NGUNG"
KILL_MIN_SEC = 600
KILL_CAP_SEC = int(os.getenv("SUPERVISOR_KILL_CAP_SEC", "3600"))
# P0-watchdog: bot co the TREO (HTTP khong tra ve) trong khi tien trinh VAN SONG ->
# `p.wait()` khong bao gio tra ve nen supervisor cu KHONG bao gio restart. Nhip tim
# (logs/heartbeat.json, turbo_demo.py ghi moi vong) la kenh duy nhat phat hien duoc:
# qua WATCHDOG_SEC khong co nhip moi -> coi nhu treo -> kill ca cay + restart.
WATCHDOG_SEC = int(os.getenv("WATCHDOG_SEC", "180"))
POLL_SEC = 5


def heartbeat_age(path=None, now=None) -> float | None:
    """So giay ke tu nhip tim cuoi. None = chua co file (bot chua ghi lan nao)."""
    p = HEARTBEAT if path is None else path
    try:
        ts = time.time() if now is None else now
        return max(0.0, ts - p.stat().st_mtime)
    except OSError:
        return None


def should_restart(age: float | None, child_alive: bool, limit: float) -> bool:
    """Chi restart khi: tien trinh con SONG ma nhip tim da cu hon `limit`."""
    if not child_alive or age is None:
        return False
    return float(age) > float(limit)


def touch_heartbeat(path=None) -> None:
    """Ghi nhip tim truoc khi spawn — de watchdog khong kill con MOI ngay lap tuc."""
    p = HEARTBEAT if path is None else path
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def rotate_log(path, max_bytes: int = 5 * 1024 * 1024, keep: int = 2) -> bool:
    """Xoay vong log khi qua `max_bytes` (giu `keep` ban .1/.2, bo ban cu nhat).

    Vi sao: turbo_err.log phinh mai (1.9 MB/ngay + moi lan restart ghi tiep) -> doc
    log cham, va dong ERROR that bi chon trong bien. Goi 1 lan luc supervisor start
    (truoc khi mo file handle de append) nen khong tranh chap voi tien trinh con.
    """
    p = Path(path)
    try:
        if not p.exists() or p.stat().st_size <= int(max_bytes):
            return False
        for i in range(int(keep), 1, -1):
            src = p.with_suffix(p.suffix + f".{i - 1}")
            if src.exists():
                src.replace(p.with_suffix(p.suffix + f".{i}"))
        p.replace(p.with_suffix(p.suffix + ".1"))
        return True
    except OSError:
        return False


def next_delay(run_sec: float, prev_delay: float,
               base: int = RESTART_DELAY_SEC, fast_exit: float = FAST_EXIT_SEC,
               cap: int = BACKOFF_MAX_SEC) -> int:
    """Cho bao lau moi restart lai.

    - Bot chay du lau (>= fast_exit) roi moi thoat/crash -> cho `base` (15s).
    - Bot thoat NGAY (< fast_exit): khong the chay vi ly do ben vung (kill-switch
      tripped, loi cau hinh, thieu key...) -> tang dan 15s -> 30 -> 60 ... tran `cap`.
    """
    if float(run_sec) >= float(fast_exit):
        return int(base)
    return int(min(cap, max(base, float(prev_delay) * 2)))


def tail_has(path, marker: str, nbytes: int = 8192) -> bool:
    """Doc DUOI file log, kiem tra co `marker` khong (mac dinh: kill-switch chan).

    Dung sau khi tien trinh con thoat de phan biet "bi kill-switch chan" (cho doi
    dai, khong phai crash) voi crash that (backoff thuong).
    """
    try:
        with open(path, "rb") as f:
            try:
                f.seek(-int(nbytes), os.SEEK_END)
            except OSError:
                f.seek(0)
            data = f.read()
        return marker.encode("utf-8") in data
    except OSError:
        return False


def plan_delay(run_sec: float, prev_delay: float, kill_blocked: bool = False,
               base: int = RESTART_DELAY_SEC, fast_exit: float = FAST_EXIT_SEC,
               cap: int = BACKOFF_MAX_SEC, kill_min: int = KILL_MIN_SEC,
               kill_cap: int = KILL_CAP_SEC) -> int:
    """Delay cho lan restart ke tiep.

    kill_blocked=True (log duoi co 'KILL-SWITCH dang NGUNG') -> cho lau hon han:
    max(kill_min, prev*2) tran kill_cap. Vi sao: chi nguoi van hanh `python
    risk.py --reset` moi go duoc, restart lien tuc chi lam phinh log.
    """
    if kill_blocked:
        return int(min(kill_cap, max(int(kill_min), int(prev_delay) * 2)))
    return next_delay(run_sec, prev_delay, base, fast_exit, cap)


def _kill_tree(pid: int) -> bool:
    """Kill ca cay tien trinh (turbo + moi thread/con) tren Windows."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, text=True, timeout=30)
        return True
    except Exception:  # noqa: BLE001
        return False


def _pid_alive(pid: int) -> bool:
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        return str(pid) in out
    except Exception:  # noqa: BLE001
        return False


def _acquire_lock() -> bool:
    if LOCK.exists():
        try:
            old = int(LOCK.read_text().strip())
        except (OSError, ValueError):
            old = 0
        if old and _pid_alive(old) and old != os.getpid():
            return False
    LOCK.write_text(str(os.getpid()))
    return True


def _mark(msg: str) -> None:
    ERR.parent.mkdir(exist_ok=True)
    with open(ERR, "a", encoding="utf-8") as f:
        f.write(f"[supervisor] {msg} {time.strftime('%Y-%m-%d %H:%M:%S')}\n")


def main() -> int:
    if not _acquire_lock():
        _mark("already running — exit")
        return 0
    # Xoay vong log TRUOC khi mo handle append (1.9 MB/ngay -> doc log cham,
    # dong ERROR that bi chon trong bien).
    for _p in (ERR, OUT):
        if rotate_log(_p):
            _mark(f"rotate log: {_p.name} -> .1")
    _mark(f"=== supervisor start pid={os.getpid()} ===")
    n = 0
    delay = RESTART_DELAY_SEC
    # (08/10) Dong bo STATE.md + auto-live: chay lan dau sau 30s, sau do moi STATE_SYNC_SEC.
    sync_proc = None
    next_sync = time.time() + 30.0 if STATE_SYNC_SEC > 0 else 0.0
    try:
        while True:
            n += 1
            _mark(f"turbo start #{n}")
            t0 = time.time()
            with open(OUT, "a", encoding="utf-8") as out, \
                    open(ERR, "a", encoding="utf-8") as err:
                touch_heartbeat()
                p = subprocess.Popen(
                    [PY, str(ROOT / "turbo_demo.py")],
                    cwd=str(ROOT), stdout=out, stderr=err,
                )
                # Poll thay vi p.wait(): phat hien bot TREO du tien trinh con song
                while True:
                    rc = p.poll()
                    if rc is not None:
                        break
                    age = heartbeat_age()
                    if should_restart(age, True, WATCHDOG_SEC):
                        _mark(f"watchdog: nhip tim cu {age:.0f}s > {WATCHDOG_SEC}s "
                              f"nhung pid={p.pid} van song -> KILL + restart")
                        _kill_tree(p.pid)
                        try:
                            rc = p.wait(timeout=30)
                        except Exception:  # noqa: BLE001
                            rc = -9
                        break
                    # (08/10) Dong bo bo nho du an + auto-live (khong chan vong lap).
                    if next_sync and time.time() >= next_sync and (
                            sync_proc is None or sync_proc.poll() is not None):
                        next_sync = time.time() + STATE_SYNC_SEC
                        try:
                            with open(SYNC_OUT, "a", encoding="utf-8") as so:
                                sync_proc = subprocess.Popen(
                                    [PY, str(ROOT / "state_sync.py"), "--git", "--auto-live"],
                                    cwd=str(ROOT), stdout=so, stderr=so)
                        except Exception as e:  # noqa: BLE001
                            _mark(f"state_sync khong chay duoc: {e}")
                    time.sleep(POLL_SEC)
            run_sec = time.time() - t0
            kill_blocked = tail_has(ERR, KILL_BLOCKED)
            delay = plan_delay(run_sec, delay, kill_blocked)
            if kill_blocked:
                _mark(f"turbo exit rc={rc} sau {run_sec:.0f}s — KILL-SWITCH dang chan: "
                      "bot KHONG the trade cho toi khi co nguoi xu ly "
                      "(`python risk.py --reset`). Restart sau "
                      f"{delay}s ({delay // 60} phut), KHONG phai crash.")
            elif run_sec < FAST_EXIT_SEC:
                # Khong the chay -> KHONG spin 20s/lan (3500 lan/dem nhu ban cu):
                # backoff dan va chi ro dong ERROR ngay tren la nguyen nhan.
                _mark(f"turbo exit rc={rc} sau {run_sec:.0f}s — THOAT NHANH: bot khong "
                      "the chay (loi cau hinh / thieu key / ...). "
                      f"Xem dong ERROR ngay tren {n}; restart sau {delay}s")
            else:
                _mark(f"turbo exit rc={rc} sau {run_sec:.0f}s — restart sau {delay}s")
            time.sleep(delay)
    except KeyboardInterrupt:
        _mark("supervisor stopped by user")
        return 130
    finally:
        try:
            LOCK.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
