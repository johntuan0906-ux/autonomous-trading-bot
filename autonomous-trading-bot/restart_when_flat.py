"""Tự ĐỘNG RESTART bot khi ĐÃ HẾT VỊ THẾ (0 lệnh đang mở).

    python restart_when_flat.py                 # theo doi roi restart khi sach vi the
    python restart_when_flat.py --poll 30       # chu ky kiem tra (giay, mac dinh 30)
    python restart_when_flat.py --max-hours 12  # tu bo cuoc sau N gio (mac dinh 12)
    python restart_when_flat.py --dry-run       # chi bao, KHONG restart
    python restart_when_flat.py --once          # kiem tra 1 lan roi thoat
    python restart_when_flat.py --pause-entries-hours 24   # het vi the => TAM DUNG vao lenh 24h

Vì sao cần: muốn áp code/cấu hình mới (vd throttle log RE-ARM, đổi SYMBOLS) mà **KHÔNG cắt
ngang vị thế đang mở**. Chạy NỀN:  `pythonw restart_when_flat.py`

(19/10) `--pause-entries-hours N`: phiếu hội đồng LIVE **4-0 VETO** việc resume ngay sau khi
hết vị thế (kill-switch vừa trip 2 lần, 6/7 lệnh lỗ, chưa qua 24h nguội). Cờ này ghi
`logs/entries_pause.json` (CÓ HẠN — hết hạn tự mở lại, xem `entries_gate`) TRƯỚC khi restart:
bot vẫn quản lý vị thế/SL/TP + học bài, chỉ KHÔNG mở lệnh mới cho tới khi hết hạn.

An toàn:
- Chỉ restart khi sàn **xác nhận 0 vị thế** (không bỏ quên vị thế nào).
- Đọc sàn lỗi (`None`) ⇒ **KHÔNG restart** (fail-safe), thử lại vòng sau.
- Ghi `logs/restart_when_flat.log`.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIVE_DIR = ROOT.parent / "atb-live"
TARGETS = {"testnet": ROOT, "live": LIVE_DIR}
LOG = ROOT / "logs" / "restart_when_flat.log"
# (15/10) Thu muc instance dang lam viec — `make_exchange()` can biet doc key cua instance
# nao (mac dinh: repo chinh). `main()` dat lai theo `--target`.
_ROOT_OVERRIDE: Path | None = None


def target_dir(target: str) -> Path:
    """Thư mục instance ('testnet' -> repo chính, 'live' -> ../atb-live).

    (15/10) LỖI ĐÃ SỬA: trước đây `ROOT = Path(__file__).parent` **cố định** ⇒ chạy
    `python ..\\autonomous-trading-bot\\restart_when_flat.py` từ `atb-live` vẫn đọc `.env`
    và kill supervisor của **TESTNET** ⇒ (a) LIVE không bao giờ được áp cấu hình mới,
    (b) nguy hiểm hơn: kill NHẦM instance khi instance kia đang có vị thế mở.
    """
    key = str(target or "testnet").strip().lower()
    if key not in TARGETS:
        raise SystemExit("--target chỉ nhận: %s" % ", ".join(sorted(TARGETS)))
    return TARGETS[key]


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


def open_positions(ex, symbols=None) -> int | None:
    """Số vị thế đang mở trên sàn. `None` = KHÔNG đọc được (fail-safe: không restart).

    `symbols` (nếu có) = chỉ đếm vị thế thuộc **cặp của bot** — vị thế do người dùng mở TAY
    (vd `1000RATS`) không được tính, nếu không watcher sẽ chờ mãi một lệnh nó không quản.
    """
    if ex is None:
        return None
    try:
        rows = ex.fetch_positions() or []
    except Exception as e:  # noqa: BLE001
        log("doc vi the loi: %s" % str(e)[:120])
        return None
    want = set(symbols) if symbols else None
    n = 0
    for p in rows:
        try:
            if abs(float(p.get("contracts") or 0)) <= 0:
                continue
        except (TypeError, ValueError):
            continue
        if want is not None and p.get("symbol") not in want:
            continue
        n += 1
    return n


def env_symbols(root: Path | None = None) -> list:
    """Danh sách cặp của bot trong `.env` của instance (SYMBOLS + EXTRA_SYMBOLS)."""
    import re
    txt = ""
    try:
        txt = ((root or ROOT) / ".env").read_text(encoding="utf-8")
    except OSError:
        return []
    out: list = []
    for key in ("SYMBOLS", "EXTRA_SYMBOLS"):
        m = re.search(r"^%s=(.*)$" % key, txt, re.M)
        if m:
            out += [s.strip() for s in m.group(1).split(",") if s.strip()]
    return list(dict.fromkeys(out))


def make_exchange(cfg):
    """Client ccxt (đúng endpoint theo cfg.testnet) — CHỈ ĐỌC.

    (15/10) LỖI ĐÃ SỬA: trước đây dùng `state_sync.key_pair(cfg)`, mà hàm đó **ưu tiên
    cặp `BINANCE_LIVE_API_KEY`/`_SECRET`** nếu đã điền. Đo thật ở LIVE: cặp đó trả
    `-2015 Invalid API-key, IP, or permissions` ⇒ watcher **không bao giờ** đọc được vị
    thế ⇒ không bao giờ restart (an toàn nhưng vô dụng: cấu hình mới không được áp).
    Bot thật giao dịch bằng `BINANCE_API_KEY` — dùng ĐÚNG nguồn đó (`tools/restart_bot.py`
    đã kiểm chứng đọc được vị thế LIVE).
    """
    try:
        # `restart_bot.py` nam trong `tools/` — va no doc `.env` cua INSTANCE theo duong
        # dan (khong phu thuoc `Settings()`, xem ghi chu o tren).
        sys.path.insert(0, str(ROOT / "tools"))
        import restart_bot as RB
        ex = RB.exchange_client(ROOT if _ROOT_OVERRIDE is None else _ROOT_OVERRIDE)
        if ex is not None:
            return ex
    except Exception as e:  # noqa: BLE001
        log("khong dung duoc restart_bot.exchange_client (%s) -> thu key_pair" % str(e)[:80])
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


def _instance_testnet(root: Path, cfg=None):
    """`BINANCE_TESTNET` theo `.env` CUA INSTANCE (khong dung `Settings()`).

    (15/10) `Settings()` doc `.env` theo thu muc cua `config.py` => tool chay tu repo chinh
    ma nham LIVE van bao `testnet=True` trong log (gay hieu nham nghiem trong: tuong dang
    o demo). Doc thang file `.env` cua instance nhu `tools/restart_bot.py` dang lam.
    """
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import restart_bot as RB
        return RB.env_kv(root).get("BINANCE_TESTNET", "?")
    except Exception:  # noqa: BLE001
        return getattr(cfg, "testnet", None)


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
            try:
                import winproc
                _kw = winproc.hide_kwargs()
            except Exception:  # noqa: BLE001
                _kw = {}
            r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True, text=True, timeout=60, **_kw)
            killed = r.returncode == 0
        except Exception as e:  # noqa: BLE001
            log("taskkill loi: %s" % str(e)[:120])
    time.sleep(3.0)
    try:
        subprocess.Popen([pythonw(), str(root / "run_forever.py")], cwd=str(root))
        return {"ok": True, "killed_pid": pid, "killed": killed}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:160], "killed_pid": pid}


def pause_entries(root: Path, hours: float, reason: str, now=None) -> dict:
    """Bật CỔNG TẠM DỪNG vào lệnh (CÓ HẠN) cho instance `root` — dùng `entries_gate`.

    (19/10) Vì sao: phiếu hội đồng LIVE 4-0 VETO việc resume ngay khi hết vị thế ⇒ hết vị
    thế thì phải PAUSE (chờ 24h nguội), KHÔNG được tự mở lệnh mới. Ghi trực tiếp file của
    instance (`root/logs/entries_pause.json`) để không phụ thuộc cwd; hết hạn tự mở lại.
    """
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        import entries_gate as EG
        return EG.pause(str(reason), path=root / "logs" / "entries_pause.json",
                        hours=hours, now=now, by="restart_when_flat")
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:160]}


def wait_flat(ex, *, poll: float = 30.0, max_hours: float = 12.0, dry_run: bool = False,
              now=time.time, sleep=time.sleep, fetch=open_positions,
              do_restart=restart_bot, pause_entries_fn=None, pause_hours: float = 0.0) -> dict:
    """Chờ tới khi hết vị thế rồi (tuỳ chọn) TẠM DỪNG vào lệnh rồi restart.

    Trả `{ok, checks, n_open|err}`; thêm `pause` nếu có tạm dừng.
    """
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
            out = {"ok": True, "checks": checks, "n_open": 0}
            # (19/10) Phieu hoi dong: het vi the thi TAM DUNG vao lenh (co han) TRUOC khi
            # restart — neu ghi that bai thi VAN restart (bot chay tiep la mac dinh cu).
            if pause_hours and pause_entries_fn is not None:
                pr = pause_entries_fn()
                out["pause"] = pr
                log("TAM DUNG vao lenh moi %.1fh: %s" % (pause_hours, pr))
            res = do_restart()
            log("ket qua restart: %s" % res)
            out["restart"] = res
            out["ok"] = bool(res.get("ok"))
            return out
        else:
            log("%d vi the dang mo -> cho them" % n)
        if (now() - t0) >= float(max_hours) * 3600.0:
            return {"ok": False, "checks": checks,
                    "err": "het thoi gian cho (%sh)" % max_hours}
        sleep(poll)


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Restart bot khi het vi the")
    ap.add_argument("--target", default="testnet", choices=sorted(TARGETS),
                    help="instance can restart (mac dinh testnet)")
    ap.add_argument("--poll", type=float, default=30.0, help="chu ky kiem tra (giay)")
    ap.add_argument("--max-hours", type=float, default=12.0, help="bo cuoc sau N gio")
    ap.add_argument("--dry-run", action="store_true", help="chi bao, khong restart")
    ap.add_argument("--once", action="store_true", help="kiem tra 1 lan roi thoat")
    ap.add_argument("--pause-entries-hours", type=float, default=0.0,
                    help="sau khi het vi the: TAM DUNG vao lenh moi trong N gio (0 = khong)")
    ap.add_argument("--pause-entries-reason", default="",
                    help="ly do tam dung (ghi vao logs/entries_pause.json)")
    args = ap.parse_args(argv)
    global LOG, _ROOT_OVERRIDE
    root = target_dir(args.target)
    LOG = root / "logs" / "restart_when_flat.log"
    _ROOT_OVERRIDE = root
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    # Phai chdir vao instance TRUOC khi doc `Settings()`: `.env` duoc nap theo thu muc
    # lam viec -> khong chdir thi `testnet`/key cua instance kia bi dung sai.
    try:
        os.chdir(root)
    except OSError as e:
        log("khong chdir duoc vao %s: %s" % (root, str(e)[:120]))
        return 2
    from config import Settings
    cfg = Settings()
    ex = make_exchange(cfg)
    syms = env_symbols(root)
    log("theo doi: target=%s dir=%s poll=%ss max=%sh dry_run=%s testnet=%s | cap cua bot=%d"
        % (args.target, root, args.poll, args.max_hours, args.dry_run,
           _instance_testnet(root, cfg), len(syms)))
    if args.pause_entries_hours:
        log("se TAM DUNG vao lenh moi %.1fh khi het vi the (ly do: %s)"
            % (args.pause_entries_hours, args.pause_entries_reason or "restart_when_flat"))
    if args.once:
        n = open_positions(ex, syms)
        log("vi the cua BOT dang mo: %s (bo qua lenh mo tay)" % n)
        return 0 if n == 0 else 1
    res = wait_flat(ex, poll=args.poll, max_hours=args.max_hours, dry_run=args.dry_run,
                    fetch=lambda e: open_positions(e, syms),
                    do_restart=lambda: restart_bot(root),
                    pause_hours=args.pause_entries_hours,
                    pause_entries_fn=(lambda: pause_entries(
                        root, args.pause_entries_hours,
                        args.pause_entries_reason or
                        "restart_when_flat: het vi the, tam dung vao lenh moi (co han)")))
    log("ket thuc: %s" % res)
    return 0 if res.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
