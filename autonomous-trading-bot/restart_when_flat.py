"""Tự ĐỘNG RESTART bot khi ĐÃ HẾT VỊ THẾ (0 lệnh đang mở).

    python restart_when_flat.py                 # theo doi roi restart khi sach vi the
    python restart_when_flat.py --poll 30       # chu ky kiem tra (giay, mac dinh 30)
    python restart_when_flat.py --max-hours 12  # tu bo cuoc sau N gio (mac dinh 12)
    python restart_when_flat.py --dry-run       # chi bao, KHONG restart
    python restart_when_flat.py --once          # kiem tra 1 lan roi thoat

Vì sao cần: muốn áp code/cấu hình mới (vd throttle log RE-ARM, đổi SYMBOLS) mà **KHÔNG cắt
ngang vị thế đang mở**. Chạy NỀN:  `pythonw restart_when_flat.py`

An toàn:
- Chỉ restart khi sàn **xác nhận 0 vị thế** (không bỏ quên vị thế nào).
- Đọc sàn lỗi (`None`) ⇒ **KHÔNG restart** (fail-safe), thử lại vòng sau.
- Ghi `logs/restart_when_flat.log`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "logs" / "restart_when_flat.log"


def log(msg: str) -> None:
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    try:
        print(line, flush=True)
    except Exception:  # noqa: BLE001
        pass


def open_positions(ex) -> int | None:
    """Số vị thế đang mở trên sàn. `None` = KHÔNG đọc được (fail-safe: không restart)."""
    if ex is None:
        return None
    try:
        rows = ex.fetch_positions() or []
    except Exception as e:  # noqa: BLE001
        log("doc vi the loi: %s" % str(e)[:120])
        return None
    n = 0
    for p in rows:
        try:
            if abs(float(p.get("contracts") or 0)) > 0:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def make_exchange(cfg):
    """Client ccxt (đúng endpoint theo cfg.testnet) — CHỈ ĐỌC."""
    import ccxt
    import state_sync as SS
    key, secret, _src = SS.key_pair(cfg)
    ex = ccxt.binanceusdm({"apiKey": key, "secret": secret, "enableRateLimit": True,
                           "timeout": 15000})
    if getattr(cfg, "testnet", True):
        try:
            ex.enable_demo_trading(True)
        except Exception:  # noqa: BLE001
            try:
                ex.set_sandbox_mode(True)
            except Exception:  # noqa: BLE001
                pass
    return ex


def supervisor_pid(root: Path | None = None) -> int:
    """PID supervisor đang chạy (từ `logs/.supervisor.lock`), 0 nếu không có."""
    p = (root or ROOT) / "logs" / ".supervisor.lock"
    try:
        return int((p.read_text(encoding="utf-8").strip() or 0))
    except Exception:  # noqa: BLE001
        return 0


def pythonw() -> str:
    """`pythonw.exe` cạnh `python.exe` (chạy nền, không cửa sổ console)."""
    cand = Path(sys.executable).with_name("pythonw.exe")
    return str(cand) if cand.exists() else sys.executable


def restart_bot(root: Path | None = None) -> dict:
    """Kill supervisor (cả cây tiến trình) rồi chạy lại `run_forever.py`."""
    root = root or ROOT
    pid = supervisor_pid(root)
    killed = False
    if pid:
        try:
            r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True, text=True, timeout=60)
            killed = r.returncode == 0
        except Exception as e:  # noqa: BLE001
            log("taskkill loi: %s" % str(e)[:120])
    time.sleep(3.0)
    try:
        subprocess.Popen([pythonw(), str(root / "run_forever.py")], cwd=str(root))
        return {"ok": True, "killed_pid": pid, "killed": killed}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:160], "killed_pid": pid}


def wait_flat(ex, *, poll: float = 30.0, max_hours: float = 12.0, dry_run: bool = False,
              now=time.time, sleep=time.sleep, fetch=open_positions,
              do_restart=restart_bot) -> dict:
    """Chờ tới khi hết vị thế rồi restart. Trả `{ok, checks, n_open|err}`."""
    t0 = now()
    checks = 0
    while True:
        n = fetch(ex)
        checks += 1
        if n is None:
            log("chua doc duoc trang thai san -> bo qua vong nay (fail-safe)")
        elif n == 0:
            log("HET VI THE -> %s" % ("(dry-run) se restart" if dry_run else "restart bot"))
            if dry_run:
                return {"ok": True, "checks": checks, "n_open": 0, "dry_run": True}
            res = do_restart()
            log("ket qua restart: %s" % res)
            return {"ok": bool(res.get("ok")), "checks": checks, "n_open": 0,
                    "restart": res}
        else:
            log("%d vi the dang mo -> cho them" % n)
        if (now() - t0) >= float(max_hours) * 3600.0:
            return {"ok": False, "checks": checks,
                    "err": "het thoi gian cho (%sh)" % max_hours}
        sleep(poll)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Restart bot khi het vi the")
    ap.add_argument("--poll", type=float, default=30.0, help="chu ky kiem tra (giay)")
    ap.add_argument("--max-hours", type=float, default=12.0, help="bo cuoc sau N gio")
    ap.add_argument("--dry-run", action="store_true", help="chi bao, khong restart")
    ap.add_argument("--once", action="store_true", help="kiem tra 1 lan roi thoat")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    from config import Settings
    cfg = Settings()
    ex = make_exchange(cfg)
    log("theo doi: poll=%ss max=%sh dry_run=%s testnet=%s"
        % (args.poll, args.max_hours, args.dry_run, getattr(cfg, "testnet", None)))
    if args.once:
        n = open_positions(ex)
        log("vi the dang mo: %s" % n)
        return 0 if n == 0 else 1
    res = wait_flat(ex, poll=args.poll, max_hours=args.max_hours, dry_run=args.dry_run)
    log("ket thuc: %s" % res)
    return 0 if res.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
