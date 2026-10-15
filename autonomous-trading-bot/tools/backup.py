"""Sao luu co KIEM CHUNG cho 2 instance (offline, chay tay hoac qua Task Scheduler).

    python tools/backup.py                      # ca 2 instance -> backups/
    python tools/backup.py --target live --keep 7
    python tools/backup.py --dry-run --json

Vi sao (14/10): `.env` chua **khoa API LIVE** va `logs/journal.jsonl` la **bang chung**
duy nhat cho moi quyet dinh (lessons, eval model, authority). Ca hai dang nam tren 1 o
dia, khong co ban sao nao. Cong cu nay:

  1. nen `.env` + journal + cac file trang thai nho + tai lieu van hanh vao 1 zip;
  2. **doc lai zip de kiem chung** (so entry + co journal trong do) — backup khong
     kiem chung duoc thi khong phai backup;
  3. giu `--keep` ban moi nhat, xoa dan ban cu (khong de day dia);
  4. KHONG bao gio ghi de len ban cu (ten co timestamp), chay lai an toan.

Y tuong tu `awesome-selfhosted` nhom Backup (Restic/Borg) — xem REPO_IDEAS.md §12.2.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# File nho, quan trong (journal co the lon nhung zip giam manh).
WANTED = ("journal.jsonl", "lessons.json", "strategy_stats.json", "learner.json",
          "risk_state.json", "agent_state.json", "orders_snapshot.json")
WANTED_ROOT = (".env", "LESSONS.md", "STATE.md")


def targets(which: str) -> list:
    """[(ten, thu_muc_goc)] theo `--target`."""
    out = []
    if which in ("both", "testnet"):
        out.append(("testnet", ROOT))
    if which in ("both", "live"):
        out.append(("live", ROOT.parent / "atb-live"))
    return out


def collect(base: Path) -> list:
    """Danh sach file se nen (chi file ton tai, bo qua rong)."""
    files = []
    for name in WANTED:
        p = base / "logs" / name
        if p.is_file() and p.stat().st_size > 0:
            files.append(p)
    for name in WANTED_ROOT:
        p = base / name
        if p.is_file() and p.stat().st_size > 0:
            files.append(p)
    return files


def verify_zip(path: Path) -> dict:
    """Doc lai zip: so entry, co journal hay khong, tong byte goc."""
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            bad = z.testzip()
            total = sum(i.file_size for i in z.infolist())
        return {"ok": bad is None and bool(names), "entries": len(names),
                "has_journal": any(n.endswith("journal.jsonl") for n in names),
                "bytes": total, "bad_member": bad}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "entries": 0, "has_journal": False, "bytes": 0,
                "error": str(e)[:120]}


def prune(outdir: Path, name: str, keep: int) -> list:
    """Xoa ban cu, chi giu `keep` ban moi nhat cua cung instance."""
    olds = sorted(outdir.glob("atb-%s-*.zip" % name), key=lambda p: p.stat().st_mtime)
    removed = []
    for p in olds[:-max(1, int(keep))]:
        try:
            p.unlink()
            removed.append(p.name)
        except OSError:
            pass
    return removed


TASK_NAME = "ATB-Backup"


def hidden_python(exe=None) -> str:
    """Duong dan python KHONG bat cua so console: `pythonw.exe` (cung thu muc).

    (15/10) Loi that nguoi van hanh bao: cu 15 phut lai hien 1 cua so cmd den
    `...\\Python312\\python.exe` — do la Task Scheduler chay `ATB-Deadman`/`ATB-Backup`
    bang `python.exe` (chuong trinh console). `pythonw.exe` khong tao console, va
    `print()` trong pythonw la no-op nen cac tool nay van ghi file binh thuong.
    """
    p = Path(exe or sys.executable)
    if p.name.lower() == "python.exe":
        w = p.with_name("pythonw.exe")
        if w.exists():
            return str(w)
    return str(p)


def task_command(python_exe=None, script=None, target: str = "both", keep: int = 14) -> str:
    """Lenh Task Scheduler se chay (duong dan TUYET DOI + nhay kep — task chay khac cwd)."""
    py = python_exe or hidden_python()
    sc = script or (ROOT / "tools" / "backup.py")
    return '"%s" "%s" --target %s --keep %d' % (py, sc, target, int(keep))


def schtasks_argv(action: str, name: str = TASK_NAME, *, time_str: str = "03:30",
                  command: str = "", sched: str = "DAILY", mod=None) -> list:
    """argv cho `schtasks` (ham THUAN TUY -> test duoc, khong chay gi).

    `sched="DAILY"` -> chay luc `time_str`; `sched="MINUTE"` -> moi `mod` phut.
    """
    if action == "install":
        a = ["schtasks", "/Create", "/TN", name, "/SC", sched]
        if str(sched).upper() == "MINUTE":
            a += ["/MO", str(int(mod or 15))]
        else:
            a += ["/ST", time_str]
        return a + ["/TR", command, "/F"]
    if action == "uninstall":
        return ["schtasks", "/Delete", "/TN", name, "/F"]
    return ["schtasks", "/Query", "/TN", name]


def run_schtasks(argv: list, *, run=None, timeout: float = 60.0) -> dict:
    """Chay schtasks. `run` tiem duoc (test khong dung den may that)."""
    import subprocess
    r = subprocess.run if run is None else run
    try:
        p = r(argv, capture_output=True, text=True, timeout=timeout)
        return {"ok": int(getattr(p, "returncode", 1)) == 0,
                "code": int(getattr(p, "returncode", 1)),
                "out": ((getattr(p, "stdout", "") or "") + (getattr(p, "stderr", "") or "")).strip()[:400]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "code": -1, "out": str(e)[:200]}


def make_backup(name: str, base: Path, outdir: Path, *, keep: int = 14,
                dry_run: bool = False) -> dict:
    """Tao 1 ban sao luu cho 1 instance. Tra dict bao cao (test duoc, khong goi mang)."""
    files = collect(base)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = outdir / ("atb-%s-%s.zip" % (name, stamp))
    rep = {"target": name, "dir": str(base), "files": len(files),
           "path": str(dest), "dry_run": bool(dry_run),
           "sources": [f.name for f in files]}
    if dry_run:
        return rep
    if not files:
        rep.update({"ok": False, "error": "khong co file nao de sao luu"})
        return rep
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                arc = ("logs/" + f.name) if f.parent.name == "logs" else f.name
                z.write(f, arcname=arc)
    except OSError as e:
        rep.update({"ok": False, "error": str(e)[:120]})
        return rep
    rep["size"] = dest.stat().st_size
    rep["verify"] = verify_zip(dest)
    rep["ok"] = bool(rep["verify"].get("ok"))
    rep["pruned"] = prune(outdir, name, keep)
    return rep


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Sao luu co kiem chung (env + journal + state)")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--out", default="", help="thu muc dich (mac dinh <repo>/backups)")
    ap.add_argument("--keep", type=int, default=14, help="so ban moi nhat giu lai / instance")
    ap.add_argument("--dry-run", action="store_true", help="chi liet ke file se nen")
    ap.add_argument("--install-task", action="store_true",
                    help="dang ky Task Scheduler chay hang ngay (go bang --uninstall-task)")
    ap.add_argument("--uninstall-task", action="store_true", help="go Task Scheduler")
    ap.add_argument("--task-status", action="store_true", help="xem task da dang ky chua")
    ap.add_argument("--task-time", default="03:30", help="gio chay (HH:MM, mac dinh 03:30)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.install_task or args.uninstall_task or args.task_status:
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = task_command(target=args.target, keep=args.keep)
        res = run_schtasks(schtasks_argv(action, time_str=args.task_time, command=cmd))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME, "OK" if res["ok"] else "LOI (%s)" % res["code"]))
            print("  lenh: %s" % cmd)
            if res.get("out"):
                print("  %s" % res["out"].replace("\n", "\n  ")[:300])
        return 0 if res["ok"] else 1

    outdir = Path(args.out) if args.out else (ROOT / "backups")
    reps = [make_backup(n, b, outdir, keep=args.keep, dry_run=args.dry_run)
            for n, b in targets(args.target)]
    if args.json:
        print(json.dumps(reps, ensure_ascii=False, indent=1))
    else:
        for r in reps:
            if r.get("dry_run"):
                print("%-8s se nen %d file: %s" % (r["target"], r["files"],
                                                   ", ".join(r["sources"])))
            elif r.get("ok"):
                v = r["verify"]
                print("%-8s OK  %s | %d file | %.0f KB | kiem chung: %d entry, journal=%s%s"
                      % (r["target"], Path(r["path"]).name, r["files"],
                         (r.get("size") or 0) / 1024, v["entries"], v["has_journal"],
                         (" | xoa cu: " + ",".join(r["pruned"])) if r.get("pruned") else ""))
            else:
                print("%-8s LOI %s" % (r["target"], r.get("error") or r.get("verify")))
    return 0 if all(r.get("ok") or r.get("dry_run") for r in reps) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:      # pythonw: khong co console -> loi phai vao file, khong duoc im
        import traceback
        try:
            with open(ROOT / "logs" / "backup_task.log", "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
        except OSError:
            pass
        raise SystemExit(1)
