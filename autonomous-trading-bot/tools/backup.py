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
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
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
    raise SystemExit(main())
