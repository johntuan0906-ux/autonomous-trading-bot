"""Dead-man switch: neu bot NGUNG thi phai CO NGUOI BIET.

    python tools/deadman.py                 # kiem tra + bao (Healthchecks neu co URL)
    python tools/deadman.py --dry-run       # chi kiem tra, khong gui
    python tools/deadman.py --json

Vi sao (15/10): ca 2 instance chay nen, khong ai ngoi canh. Lop loi da gap that:
hoi dong CAM 48h, supervisor treo, kill-switch trip — **khong co gi bao** ngoai viec
nguoi van hanh tu mo log ra xem. Dead-man switch dao nguoc: bot phai dinh ky "toi con
song"; im lang = bao dong.

Hai che do (tu dong chon):
  1. co `HEALTHCHECKS_URL` (hoac `..._TESTNET` / `..._LIVE`) trong `.env` -> GET len
     dich vu ngoai (healthchecks.io: `<url>` = OK, `<url>/fail` = loi). Mien phi, khong
     can mo port.
  2. khong co URL -> ghi trang thai cuc bo `logs/deadman.json` + `logs/deadman.log`
     (van huu ich: `tools/ops.py` va con nguoi doc duoc; va san sang khi ban dien URL).

`--mute` (hoac tao file `logs/deadman_mute`) = bao tri co chu dinh -> khong bao loi.

Phan quyet dinh la ham THUAN TUY -> test duoc, khong goi mang.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import ops as OPS          # noqa: E402
import harness_audit as HA  # noqa: E402

MUTE_FILE = ROOT / "logs" / "deadman_mute"
TASK_NAME = "ATB-Deadman"
STATE = ROOT / "logs" / "deadman.json"
LOG = ROOT / "logs" / "deadman.log"
# Loi KHONG tinh la "chet" (du lieu xau bi bo qua la hanh vi dung, khong phai su co).
BENIGN = ("SKIP_DATA",)


def ping_url(base: str, ok: bool) -> str:
    """URL can goi: `<base>` khi OK, `<base>/fail` khi loi (chuan healthchecks.io)."""
    b = str(base or "").strip().rstrip("/")
    if not b:
        return ""
    return b if ok else (b + "/fail")


def decide(reps: list, *, max_hb_sec: float = 900.0, max_errors: int = 0) -> dict:
    """Tu bao cao ops -> {ok, problems, reason}. THUAN TUY (test duoc).

    Coi la CHET khi: khong doc duoc nhip tim, nhip tim qua cu, khong co supervisor,
    kill-switch dang ngung, hoac co loi trong cua so. `max_errors` de nguong nhay.
    """
    bad = []
    for r in reps or []:
        name = str((r or {}).get("name") or "?")
        if (r or {}).get("hb_err") and (r or {}).get("hb_age_s") is None:
            bad.append("%s: khong doc duoc nhip tim (%s)" % (name, r.get("hb_err")))
            continue
        age = float((r or {}).get("hb_age_s") or 0.0)
        if age > float(max_hb_sec):
            bad.append("%s: nhip tim cu %.0fs > %.0fs" % (name, age, max_hb_sec))
        if not int((r or {}).get("supervisor_pid") or 0):
            bad.append("%s: khong co supervisor (lock trong = bot da dung?)" % name)
        if (r or {}).get("kill_tripped"):
            bad.append("%s: KILL-SWITCH dang ngung (%s)"
                       % (name, (r or {}).get("kill_reason") or "?"))
        errs = (r or {}).get("errors_win") or {}
        n_err = sum(int(v) for k, v in errs.items() if k not in BENIGN)
        if n_err > int(max_errors):
            bad.append("%s: %d loi trong cua so %s" % (name, n_err, sorted(errs)))
    return {"ok": not bad, "problems": bad, "reason": "; ".join(bad) if bad else "OK"}


def _default_get(url: str, timeout: float) -> int:
    """GET that (tach ra de test tiem ham gia, khong goi mang trong test)."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=float(timeout)) as r:
        return int(getattr(r, "status", 200))


def send_ping(url: str, *, get=None, timeout: float = 10.0) -> dict:
    """Gui 1 ping. Khong bao gio nem loi (dead-man switch khong duoc lam chet bot)."""
    if not str(url or "").strip():
        return {"ok": False, "error": "chua cau hinh URL (HEALTHCHECKS_URL)"}
    g = _default_get if get is None else get
    try:
        code = int(g(url, timeout))
        return {"ok": 200 <= code < 300, "status": code, "url": url}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:120], "url": url}


def urls_for(env: dict, target: str) -> list:
    """[(ten, url)] can ping cho `target`. Uu tien URL rieng tung instance."""
    common = str(env.get("HEALTHCHECKS_URL") or os.getenv("HEALTHCHECKS_URL") or "").strip()
    names = ["testnet", "live"] if target == "both" else [target]
    out = []
    for n in names:
        u = str(env.get("HEALTHCHECKS_URL_%s" % n.upper()) or "").strip() or common
        out.append((n, u))
    return out


def check(target: str = "both", *, minutes: float = 15.0, max_hb_sec: float = 900.0,
          max_errors: int = 0) -> dict:
    """Doc trang thai that cua cac instance -> bao cao (khong goi mang)."""
    if target == "testnet":
        dirs = [("TESTNET", OPS.ROOT)]
    elif target == "live":
        dirs = [("LIVE", OPS.LIVE_DIR)]
    else:
        dirs = [("TESTNET", OPS.ROOT), ("LIVE", OPS.LIVE_DIR)]
    reps = [OPS._instance(n, d, minutes) for n, d in dirs]
    dec = decide(reps, max_hb_sec=max_hb_sec, max_errors=max_errors)
    dec["instances"] = [{"name": r.get("name"), "round": r.get("round"),
                         "hb_age_s": r.get("hb_age_s"),
                         "supervisor_pid": r.get("supervisor_pid"),
                         "kill_tripped": bool(r.get("kill_tripped")),
                         "errors_win": r.get("errors_win") or {}}
                        for r in reps]
    dec["ts"] = time.time()
    dec["minutes"] = minutes
    return dec


def env_urls(target: str = "both") -> list:
    """Doc `.env` cua tung instance -> URL Healthchecks (neu da dien)."""
    out = []
    for n, base in (("testnet", ROOT), ("live", ROOT.parent / "atb-live")):
        if target != "both" and target != n:
            continue
        try:
            env = HA.read_env(base / ".env")
        except Exception:  # noqa: BLE001
            env = {}
        out += urls_for(env, n)
    return out


def save_state(rec: dict, *, state=STATE, log=LOG) -> dict:
    """Ghi `logs/deadman.json` (may doc) + 1 dong `logs/deadman.log` (nguoi doc)."""
    rep = {"state": "", "log": ""}
    try:
        Path(state).parent.mkdir(parents=True, exist_ok=True)
        Path(state).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        rep["state"] = str(state)
    except OSError as e:
        rep["state_error"] = str(e)[:100]
    try:
        line = "%s %s %s | %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "OK  " if rec.get("ok") else "FAIL",
                                    rec.get("target", "?"), rec.get("reason", ""))
        with open(log, "a", encoding="utf-8") as f:
            f.write(line)
        rep["log"] = str(log)
    except OSError as e:
        rep["log_error"] = str(e)[:100]
    return rep


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Dead-man switch (bao khi bot NGUNG)")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--minutes", type=float, default=15.0, help="cua so dem loi (phut)")
    ap.add_argument("--max-hb-sec", type=float, default=900.0,
                    help="nhip tim cu hon bao nhieu giay thi coi la chet (mac dinh 900)")
    ap.add_argument("--max-errors", type=int, default=0, help="cho phep bao nhieu loi")
    ap.add_argument("--mute", action="store_true", help="bao tri co chu dinh (khong bao)")
    ap.add_argument("--dry-run", action="store_true", help="khong gui ping, khong ghi")
    ap.add_argument("--install-task", action="store_true",
                    help="dang ky Task Scheduler chay moi --task-min phut")
    ap.add_argument("--uninstall-task", action="store_true", help="go Task Scheduler")
    ap.add_argument("--task-status", action="store_true", help="xem task da dang ky chua")
    ap.add_argument("--task-min", type=int, default=15, help="chu ky task (phut, mac dinh 15)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.install_task or args.uninstall_task or args.task_status:
        import backup as BK
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = '"%s" "%s" --target both' % (BK.hidden_python(), Path(__file__).resolve())
        res = BK.run_schtasks(BK.schtasks_argv(action, TASK_NAME, command=cmd,
                                              sched="MINUTE", mod=args.task_min))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME, "OK" if res["ok"] else "LOI (%s)" % res["code"]))
            print("  lenh: %s  (moi %d phut)" % (cmd, args.task_min))
            if res.get("out"):
                print("  %s" % res["out"].replace("\n", "\n  ")[:300])
        return 0 if res["ok"] else 1


    rep = check(args.target, minutes=args.minutes, max_hb_sec=args.max_hb_sec,
                max_errors=args.max_errors)
    rep["target"] = args.target
    muted = bool(args.mute) or MUTE_FILE.exists()
    rep["muted"] = muted
    rep["pings"] = []
    if not args.dry_run:
        for name, base in env_urls(args.target):
            url = ping_url(base, rep["ok"])
            if not url:
                rep["pings"].append({"instance": name, "url": "", "ok": False,
                                     "error": "chua cau hinh (dien HEALTHCHECKS_URL vao .env)"})
                continue
            r = send_ping(url)
            r["instance"] = name
            rep["pings"].append(r)
    rep["saved"] = {} if args.dry_run else save_state(rep)

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print("=== DEAD-MAN SWITCH | %s | %s ==="
              % (args.target.upper(), time.strftime("%Y-%m-%d %H:%M:%S")))
        print("  ket luan : %s%s" % ("OK" if rep["ok"] else "CO VAN DE",
                                     "  (MUTE: bao tri co chu dinh)" if muted else ""))
        for p in rep["problems"]:
            print("    - %s" % p)
        for i in rep["instances"]:
            print("  %-8s round=%-4s hb=%ss supervisor=%s kill=%s loi=%s"
                  % (i["name"], i["round"], i["hb_age_s"], i["supervisor_pid"],
                     i["kill_tripped"], i["errors_win"] or "-"))
        if args.dry_run:
            print("  (dry-run: khong gui ping, khong ghi trang thai)")
        else:
            for p in rep["pings"]:
                print("  ping %-8s -> %-40s %s"
                      % (p.get("instance"), (p.get("url") or "(chua dien)")[:40],
                         "OK" if p.get("ok") else "LOI: %s" % (p.get("error") or p.get("status"))))
            print("  trang thai: %s"
                  % (rep["saved"].get("state") or rep["saved"].get("state_error")))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:      # pythonw: khong co console -> loi phai vao file, khong duoc im
        import traceback
        try:
            with open(ROOT / "logs" / "deadman_task.log", "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc() + "\n")
        except OSError:
            pass
        raise SystemExit(1)
