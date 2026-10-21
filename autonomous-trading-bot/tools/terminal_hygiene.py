"""Don terminal RAC cua VS Code (shell "mo coi" khong con chay gi) — giai phong RAM.

    python tools/terminal_hygiene.py --dry-run      # chi liet ke, khong xoa
    python tools/terminal_hygiene.py                # don 1 lan
    python tools/terminal_hygiene.py --watch --interval 120   # theo doi lien tuc (nen)
    python tools/terminal_hygiene.py --json

Vi sao co (19/10): extension **Cline** (`saoudrizwan.claude-dev`) tao **1 terminal moi cho
moi lan chay lenh** va **khong tu dong**; Cline/Roo **khong co setting** terminal nao (da
kiem `package.json`) va VS Code cung **khong co setting** tu dong dong tab khi tien trinh
ket thuc ⇒ do that 19/10: **112 shell PowerShell con song = 1138 MB RAM** (nguyen nhan lag
VS Code, khong phai repo). Tool nay don tu ben ngoai.

An toan (3 lop, khong bao gio cat ngang viec dang chay):
  1. Chi xoa shell co **parent la `Code.exe`** (terminal cua VS Code) — shell khac bo qua;
  2. Chi xoa shell **KHONG co tien trinh con** (dang ranh). Bot/watcher (`run_forever.py`,
     `restart_when_flat.py`, `turbo_demo.py`) la CON cua shell nen shell do bi loai;
  3. Bo qua **cay tien trinh dang goi tool** (`os.getpid()` + to tien) — `--protect-pid`
     de bao ve them pid khac.

Kiem tra nhanh trong VS Code: `Ctrl+Shift+P → Terminal: Kill All Terminals` (xoa ca TAB).
Tool nay xoa TIEN TRINH shell (giai phong RAM ngay); danh sach tab se sach sau khi
`Developer: Reload Window` (da dat `terminal.integrated.enablePersistentSessions=false`).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

SHELL_NAMES = ("powershell.exe", "pwsh.exe", "cmd.exe")
CODE_NAME = "Code.exe"
PS_LIST = ("Get-CimInstance Win32_Process | "
           "Select-Object Name,ProcessId,ParentProcessId,WorkingSetSize | "
           "ConvertTo-Json -Compress")


def parse_rows(text: str) -> list:
    """Doc JSON cua `Get-CimInstance` -> list[dict]. Chiu duoc: 1 object, list, rac.

    (PowerShell tra 1 OBJECT khi chi co 1 dong => phai boc thanh list.)
    """
    out: list = []
    for chunk in str(text or "").splitlines():
        chunk = chunk.strip()
        if not chunk.startswith(("{", "[")):
            continue
        try:
            d = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
        elif isinstance(d, list):
            out.extend(x for x in d if isinstance(x, dict))
    return out


def ancestors_of(pid, rows) -> set:
    """Tap pid cua `pid` + MOI to tien (de khong bao gio xoa shell dang chay tool)."""
    by_id = {}
    for r in rows or []:
        try:
            by_id[int(r.get("ProcessId"))] = int(r.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            continue
    chain: set = set()
    cur = int(pid or 0)
    while cur and cur not in chain:
        chain.add(cur)
        cur = by_id.get(cur, 0)
    return chain



def pick_idle_shells(rows, code_pids=None, protect=None) -> list:
    """Danh sach shell RAC nen xoa: `[{pid, name, mb}]` (ham THUAN TUY -> test duoc).

    `code_pids` = None ⇒ tu tim tu `rows` (Name == Code.exe).
    """
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if code_pids is None:
        code_pids = {int(r.get("ProcessId") or 0) for r in rows
                     if str(r.get("Name") or "") == CODE_NAME}
    code_pids = {int(x) for x in code_pids}
    protect = {int(x) for x in (protect or [])}
    parents = {int(r.get("ParentProcessId") or 0) for r in rows}
    out = []
    for r in rows:
        try:
            pid = int(r.get("ProcessId") or 0)
            ppid = int(r.get("ParentProcessId") or 0)
        except (TypeError, ValueError):
            continue
        if str(r.get("Name") or "") not in SHELL_NAMES:
            continue
        if ppid not in code_pids:          # lop 1: chi terminal cua VS Code
            continue
        if pid in parents:                 # lop 2: co tien trinh con => dang ban
            continue
        if pid in protect:                 # lop 3: cay tien trinh dang goi tool
            continue
        try:
            mb = round(float(r.get("WorkingSetSize") or 0) / (1024 * 1024), 1)
        except (TypeError, ValueError):
            mb = 0.0
        out.append({"pid": pid, "name": str(r.get("Name")), "mb": mb})
    return out


def list_processes(timeout: float = 25.0) -> list:
    """Goi PowerShell liet ke tien trinh. Loi/khong co PowerShell -> [] (khong nem ra ngoai).

    (21/10) `**winproc.hide_kwargs()`: tool nay chay NEN (task "Cline: theo doi don
    terminal") duoi `pythonw` ⇒ thieu co nay thi **moi 2 phut mot cua so powershell den
    nhay len** (dung lop loi pop-up console).
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import winproc
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", PS_LIST],
                             capture_output=True, text=True, timeout=timeout,
                             encoding="utf-8", errors="replace", **winproc.hide_kwargs())
    except Exception:  # noqa: BLE001
        return []
    return parse_rows(res.stdout)


def kill_pids(pids, timeout: float = 25.0) -> int:
    """Xoa cac pid (`Stop-Process -Force`). Tra so pid da ra lenh xoa."""
    pids = [int(p) for p in (pids or [])]
    if not pids:
        return 0
    cmd = "; ".join("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % p
                    for p in pids)
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    except Exception:  # noqa: BLE001
        return 0
    return len(pids)


def run_once(dry_run: bool = False, protect_extra=(), rows=None, kill=True,
             min_shells: int = 1) -> dict:
    """1 lan don: tra `{found, killed, freed_mb, below_min, shells}`.

    `rows` de test (khong goi PowerShell); `kill=False` de chi do luong.
    `min_shells`: chi DỌN khi co it nhat N shell rac (mac dinh 1). Dat 5 cho che do nen
    de khong xoa lat nhat (moi lan xoa deu sinh 1 thong bao "terminal process terminated"
    cua VS Code — xem `terminal.integrated.showExitAlert`).
    """
    rows = list_processes() if rows is None else rows
    protect = ancestors_of(os.getpid(), rows)
    protect |= {int(x) for x in (protect_extra or [])}
    shells = pick_idle_shells(rows, protect=protect)
    freed = round(sum(float(s.get("mb") or 0) for s in shells), 1)
    below = len(shells) < max(1, int(min_shells or 1))
    killed = 0
    if shells and not dry_run and kill and not below:
        killed = kill_pids([s["pid"] for s in shells])
    return {"found": len(shells), "killed": killed, "freed_mb": freed,
            "below_min": below, "shells": shells}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Don terminal rac cua VS Code")
    ap.add_argument("--dry-run", action="store_true", help="chi liet ke, khong xoa")
    ap.add_argument("--watch", action="store_true", help="chay lien tuc (nen)")
    ap.add_argument("--interval", type=float, default=120.0, help="chu ky khi --watch (giay)")
    ap.add_argument("--protect-pid", action="append", type=int, default=[],
                    help="them pid can bao ve (lap lai duoc)")
    ap.add_argument("--quiet", action="store_true", help="chi in khi co viec lam")
    ap.add_argument("--min-shells", type=int, default=1,
                    help="chi don khi co it nhat N shell rac (dat 5 cho che do nen)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    def _once() -> dict:
        rep = run_once(dry_run=args.dry_run, protect_extra=args.protect_pid,
                       min_shells=args.min_shells)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False))
        elif rep["found"] and not args.quiet:
            print("terminal rac: %d shell (~%.0f MB)%s"
                  % (rep["found"], rep["freed_mb"],
                     " — DRY-RUN (khong xoa)" if args.dry_run else " -> da xoa"))
            for s in rep["shells"][:8]:
                print("   pid %-8d %-16s %.1f MB" % (s["pid"], s["name"], s["mb"]))
        return rep

    if not args.watch:
        _once()
        return 0
    while True:                      # --watch: khong bao gio nem loi ra ngoai
        try:
            _once()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(max(10.0, float(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
