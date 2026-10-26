"""Cau noi Telegram 2 CHIEU cho van hanh (26/10).

Vi sao co file nay (tra loi cau hoi cua nguoi van hanh):
  * Bot DA co Telegram **1 chieu**: `notify.send()` cho OPEN/CLOSE/KILL (turbo_demo),
    `telegram_report.py` (bao cao trang thai), tom tat phien hoi dong (state_sync).
  * NHUNG (a) canh bao cua `watch_regress`/`ops_queue` (B-028/B-029) **khong** ra Telegram;
    (b) **khong co duong VAO** ⇒ doc canh bao tren dien thoai xong khong the tra loi/ra lenh.

Cach lam: 1 task Scheduler moi 1 phut chay `--poll --push`:
  * `--push`: gui cau hoi DANG CHO + van de (chong spam bang state `logs/telegram_bridge.json`);
  * `--poll`: doc `getUpdates` -> xu ly lenh -> tra loi lai qua Telegram.

LENH (mac dinh CHI DOC — an toan):
  `/help`  `/status`  `/list`  `/health`  `/ask <cau hoi>`  `/answer <id> <tra loi>`
LENH GHI (chi khi `.env` co `TELEGRAM_ALLOW_WRITE=true`):
  `/dedupe <testnet|live>` · `/reset <testnet|live> confirm` · `/restart <testnet|live>`

An toan:
  - chi nghe tu chat_id trong `.env` (`TELEGRAM_CHAT_ID` + `TELEGRAM_ALLOW_CHAT_IDS`);
  - moi lenh ghi vet vao `logs/telegram_bridge.log` (co nguon + ket qua);
  - goi tool khac bang argv CO DINH, khong `shell=True` (khong the tiem lenh);
  - khong co token/chat ⇒ che do DRY: ghi vao log, khong goi mang.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atomic          # noqa: E402
import ops_queue as OQ  # noqa: E402

STATE_NAME = "logs/telegram_bridge.json"
LOG_NAME = "logs/telegram_bridge.log"
TASK_NAME = "ATB-Telegram"
API = "https://api.telegram.org/bot{token}/{method}"
MAX_LEN = 3800
REPEAT_H = 6.0          # gui lai cau hoi con treo sau N gio (khong spam moi phut)

HELP = (
    "LENH (chi doc):\n"
    "/status - tinh trang 2 instance (ops.py)\n"
    "/health - kiem tra tai phat + pho bao ve (watch_regress --check --orders)\n"
    "/list   - cau hoi dang cho (kem /answer)\n"
    "/ask <cau hoi> - gui cau hoi moi cho phien lam viec sau\n"
    "/answer <id> <tra loi> - tra loi cau hoi trong hang doi\n"
    "LENH GHI (can TELEGRAM_ALLOW_WRITE=true):\n"
    "/dedupe <testnet|live> - gom cap lenh bao ve TRUNG\n"
    "/reset <testnet|live> confirm - go kill-switch (can chu 'confirm')\n"
    "/restart <testnet|live> - restart bot an toan\n"
    "/help"
)


def read_env(path: Path) -> dict:
    """Doc `.env` thanh dict (khong ghi de os.environ)."""
    out: dict = {}
    try:
        txt = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def cfg_for(base: Path) -> dict:
    """Cau hinh Telegram cua 1 instance (token/chat + co cho phep GHI + danh sach cho phep)."""
    env = read_env(Path(base) / ".env")
    allow = [x.strip() for x in str(env.get("TELEGRAM_ALLOW_CHAT_IDS") or "").split(",")
             if x.strip()]
    chat = str(env.get("TELEGRAM_CHAT_ID") or "").strip()
    if chat and chat not in allow:
        allow.append(chat)
    return {"token": str(env.get("TELEGRAM_BOT_TOKEN") or "").strip(),
            "chat": chat, "allow_ids": allow,
            "allow_write": str(env.get("TELEGRAM_ALLOW_WRITE", "false")).lower()
            in ("true", "1", "yes")}


def state_path(base: Path = ROOT) -> Path:
    return Path(base) / STATE_NAME


def load_state(path=None) -> dict:
    """Doc state (offset + da gui gi). Hong/thieu -> {} (khong chan gi)."""
    p = Path(path) if path else state_path()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return d if isinstance(d, dict) else {}


def save_state(state: dict, path=None) -> str:
    p = Path(path) if path else state_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_json_atomic(p, state, indent=1)
        return str(p)
    except OSError:
        return ""


def append_log(text: str, path=None) -> str:
    """Ghi 1 dong vet (khong nem loi)."""
    p = Path(path) if path else (ROOT / LOG_NAME)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(str(text).rstrip() + "\n")
        return str(p)
    except OSError:
        return ""


def api_call(token: str, method: str, payload: dict, *, post=None, timeout: float = 15.0):
    """Goi Bot API. `post` tiem duoc (test khong dung mang). Tra dict (rong = loi)."""
    if post is not None:
        return post(token, method, payload)
    try:
        import requests
        r = requests.post(API.format(token=token, method=method), json=payload,
                          timeout=timeout)
        return r.json() if r.ok else {"ok": False, "error": r.text[:200]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200]}


def send(text: str, *, token: str, chat: str, post=None, dry: bool = False,
         log_path=None) -> dict:
    """Gui 1 tin nhan. Khong token/chat hoac `dry` ⇒ chi ghi log (khong im lang)."""
    body = str(text or "")[:MAX_LEN]
    if dry or not token or not chat:
        append_log("%s [DRY] -> %s: %s"
                   % (time.strftime("%Y-%m-%d %H:%M:%S"), chat or "?",
                      body.replace("\n", " | ")), path=log_path)
        return {"ok": True, "dry": True, "chars": len(body)}
    res = api_call(token, "sendMessage", {"chat_id": chat, "text": body}, post=post)
    ok = bool((res or {}).get("ok"))
    append_log("%s GUI %s: %s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                  "OK" if ok else "LOI (%s)" % str(res.get("error"))[:80],
                                  body.replace("\n", " | ")[:200]), path=log_path)
    return {"ok": ok, "dry": False, "chars": len(body), "error": (res or {}).get("error")}


def open_questions(base: Path) -> list:
    """Cau hoi DANG CHO cua 1 instance (doc truc tiep file cua instance do)."""
    p = Path(base) / "logs" / "ops_questions.json"
    return OQ.open_items(open_path=p)


def targets() -> dict:
    """Thu muc 2 instance (nhu cac tool khac trong repo)."""
    return {"testnet": ROOT, "live": LIVE_DIR}


def push(dirs=None, *, token="", chat="", state=None, now=None, post=None, dry=False,
         log_path=None, repeat_h: float = REPEAT_H) -> dict:
    """Gui cau hoi DANG CHO cua ca 2 instance ra Telegram.

    Chong SPAM nhung KHONG im lang: moi cau hoi gui 1 lan, va gui lai sau `repeat_h` gio
    neu van con treo (nguoi van hanh nghi ngo "co the bi chan" — dung lop loi B-003).
    """
    dirs = dirs or {"TESTNET": ROOT, "LIVE": LIVE_DIR}
    st = dict(state if state is not None else load_state())
    sent_map = dict(st.get("sent") or {})
    t = float(now() if callable(now) else (now or time.time()))
    out: list = []
    for name, base in dirs.items():
        for q in open_questions(base):
            key = "%s/%s" % (name, q.get("id"))
            prev = float(sent_map.get(key) or 0.0)
            if prev and (t - prev) < float(repeat_h) * 3600.0:
                continue
            txt = ("[%s] #%s (%s) %s\nTra loi: /answer %s %s <noi dung>"
                   % (name, q.get("id"), q.get("priority"), q.get("question"),
                      name, q.get("id")))
            if q.get("why"):
                txt += "\n" + str(q["why"])[:600]
            if q.get("options"):
                txt += "\nLua chon: " + " | ".join(str(x) for x in q["options"])
            res = send(txt, token=token, chat=chat, post=post, dry=dry, log_path=log_path)
            sent_map[key] = t
            out.append({"key": key, "ok": res.get("ok"), "dry": res.get("dry")})
    st["sent"] = sent_map
    st["last_push"] = t
    st["saved"] = save_state(st)
    return {"pushed": out, "state": st}


def parse_command(text: str) -> tuple:
    """`'/answer@MyBot 3 ok'` -> `('answer', ['3', 'ok'])` (bo `/` + @ten bot)."""
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return "", []
    head, _, rest = raw.partition(" ")
    cmd = head[1:].split("@", 1)[0].strip().lower()
    return cmd, [x for x in rest.split() if x]


def run_tool(argv: list, *, cwd: Path, timeout: float = 180.0) -> dict:
    """Chay tool khac bang argv CO DINH (khong shell=True ⇒ khong tiem duoc lenh).

    An cua so console (`winproc.hide_kwargs`) — task chay bang pythonw nen thieu co se
    nhay cua so den moi phut (loi nguoi van hanh da bao 15/10).
    """
    import subprocess
    try:
        import winproc
        kw = winproc.hide_kwargs()
    except Exception:  # noqa: BLE001
        kw = {}
    try:
        r = subprocess.run([str(x) for x in argv], cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, **kw)
        out = (r.stdout or "") + (r.stderr or "")
        return {"ok": r.returncode == 0, "code": r.returncode, "out": out[-2500:]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "code": -1, "out": str(e)[:200]}


def _fmt_questions(dirs=None) -> str:
    dirs = dirs or {"TESTNET": ROOT, "LIVE": LIVE_DIR}
    lines = []
    for name, base in dirs.items():
        for q in open_questions(base):
            lines.append("[%s] #%s (%s) %s" % (name, q.get("id"), q.get("priority"),
                                               str(q.get("question"))[:300]))
    return "\n".join(lines) if lines else "(khong co cau hoi nao dang cho)"


def _lookup(dirs) -> dict:
    """{'live': ('LIVE', Path)} — chap nhan ca chu HOA/thuong khi go lenh."""
    return {str(k).lower(): (k, v) for k, v in (dirs or {}).items()}


def _answer(args, *, dirs, queue) -> dict:
    """`/answer <id> <text>` hoac `/answer <target> <id> <text>` (id co the TRUNG giua 2 instance)."""
    if len(args) < 2:
        return {"reply": "Dung: /answer <TESTNET|LIVE> <id> <noi dung>",
                "cmd": "answer", "write": False}
    low = _lookup(dirs)
    target = ""
    if len(args) >= 3 and args[0].lower() in low:
        target, args = args[0].lower(), args[1:]
    try:
        qid = int(args[0])
    except (TypeError, ValueError):
        return {"reply": "id phai la so: %s" % args[0], "cmd": "answer", "write": False}
    body = " ".join(args[1:]).strip()
    if not body:
        return {"reply": "Thieu noi dung tra loi", "cmd": "answer", "write": False}
    if target:
        cands = {low[target][0]: low[target][1]}
    else:
        cands = {n: b for n, b in dirs.items()
                 if any(int(q.get("id") or 0) == qid for q in open_questions(b))}
    if not cands:
        return {"reply": "Khong thay cau hoi #%d dang cho" % qid,
                "cmd": "answer", "write": False}
    if len(cands) > 1:
        return {"reply": ("Cau hoi #%d co o CA 2 instance -> ghi ro: "
                          "/answer <TESTNET|LIVE> %d <noi dung>" % (qid, qid)),
                "cmd": "answer", "write": False}
    name, base = next(iter(cands.items()))
    r = queue.answer(qid, body, by="nguoi van hanh (Telegram)",
                     open_path=base / "logs" / "ops_questions.json",
                     done_path=base / "logs" / "ops_queue.json")
    return {"reply": "Da tra loi #%s (%s): %s" % (qid, name.upper(),
                                                  "OK" if r.get("ok") else "GHI LOI"),
            "cmd": "answer", "write": True}


def _write_cmd(cmd, args, *, cfg, dirs, py, runner) -> dict:
    """Lenh cham vao he thong — CHI chay khi `.env` cho phep (`TELEGRAM_ALLOW_WRITE=true`)."""
    if not cfg.get("allow_write"):
        return {"reply": ("Lenh GHI dang TAT (mac dinh an toan). Bat bang "
                          "`TELEGRAM_ALLOW_WRITE=true` trong .env roi chay lai task."),
                "cmd": cmd, "write": True, "blocked": True}
    target = (args[0].lower() if args else "")
    low = _lookup(dirs)
    if target not in low:
        return {"reply": "Dung: /%s <testnet|live>" % cmd, "cmd": cmd, "write": True,
                "blocked": True}
    base = low[target][1]
    if cmd == "dedupe":
        r = runner([py, str(ROOT / "tools" / "orders_audit.py"), "--target", target,
                    "--dedupe"], cwd=base)
    elif cmd == "restart":
        r = runner([py, str(ROOT / "tools" / "restart_bot.py"), "--target", target],
                   cwd=ROOT)
    else:  # reset kill-switch
        if "confirm" not in [a.lower() for a in args[1:]]:
            return {"reply": ("Go kill-switch %s: phai them chu 'confirm' "
                              "(vd `/reset %s confirm`) — day la diem chan an toan."
                              % (target, target)),
                    "cmd": cmd, "write": True, "blocked": True}
        r = runner([py, str(base / "risk.py"), "--reset"], cwd=base)
    return {"reply": (r.get("out") or "(khong co ket qua)")[-2500:], "cmd": cmd,
            "write": True, "ran": r.get("ok")}


def handle(text: str, *, cfg: dict, py=None, runner=run_tool, queue=OQ, dirs=None,
           dry=False, post=None, log_path=None) -> dict:
    """Xu ly 1 lenh Telegram. Tra {reply, cmd, write}. Khong bao gio nem loi ra ngoai."""
    dirs = dirs or targets()
    py = py or sys.executable
    cmd, args = parse_command(text)
    if cmd in ("", "help", "start"):
        return {"reply": HELP, "cmd": cmd or "help", "write": False}
    if cmd in ("status", "health"):
        argv = ([py, str(ROOT / "tools" / "ops.py")] if cmd == "status" else
                [py, str(ROOT / "tools" / "watch_regress.py"), "--check", "--orders",
                 "--no-notify"])
        r = runner(argv, cwd=ROOT)
        return {"reply": (r.get("out") or "(khong co ket qua)")[-3000:], "cmd": cmd,
                "write": False, "ran": r.get("ok")}
    if cmd == "list":
        return {"reply": _fmt_questions(dirs), "cmd": cmd, "write": False}
    if cmd == "ask":
        q = " ".join(args).strip()
        if not q:
            return {"reply": "Dung: /ask <cau hoi>", "cmd": cmd, "write": False}
        rec = queue.add(q, why="nguoi van hanh gui tu Telegram", by="telegram")
        return {"reply": "Da ghi cau hoi #%s vao hang doi: %s"
                         % (rec.get("id"), "OK" if rec.get("ok") else "GHI LOI"),
                "cmd": cmd, "write": True}
    if cmd == "answer":
        return _answer(args, dirs=dirs, queue=queue)
    if cmd in ("dedupe", "reset", "restart"):
        return _write_cmd(cmd, args, cfg=cfg, dirs=dirs, py=py, runner=runner)
    return {"reply": "Lenh khong ro: %s\n\n%s" % (cmd, HELP), "cmd": cmd, "write": False}


def poll(*, token: str, chat: str = "", cfg: dict | None = None, state=None, now=None,
         post=None, get=None, dry: bool = False, log_path=None, runner=run_tool,
         queue=OQ, dirs=None) -> dict:
    """Doc `getUpdates` 1 lan -> xu ly lenh tu chat_id DUOC PHEP -> tra loi lai.

    An toan: chat_id la (khong nam trong `TELEGRAM_CHAT_ID`/`TELEGRAM_ALLOW_CHAT_IDS`) bi
    BO QUA va ghi vet (khong tra loi ⇒ khong lo thong tin trang thai bot cho nguoi la).
    """
    cfg = cfg or {"token": token, "chat": chat, "allow_ids": [chat] if chat else [],
                  "allow_write": False}
    st = dict(state if state is not None else load_state())
    offset = int(st.get("offset") or 0)
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    if get is None:
        def get(tok, off):  # noqa: E306  (mac dinh: goi Bot API)
            return api_call(tok, "getUpdates", {"offset": off + 1, "timeout": 0},
                            post=post)
    upd = get(token, offset)
    if not isinstance(upd, dict) or not upd.get("ok"):
        err = str((upd or {}).get("error") or "getUpdates loi")[:150]
        append_log("%s POLL loi: %s" % (t, err), path=log_path)
        return {"handled": [], "state": st, "error": err}
    handled: list = []
    for u in upd.get("result") or []:
        try:
            uid = int(u.get("update_id") or 0)
        except (TypeError, ValueError):
            uid = 0
        if uid > offset:
            offset = uid
        msg = u.get("message") or u.get("edited_message") or {}
        cid = str((msg.get("chat") or {}).get("id") or "")
        text = str(msg.get("text") or "")
        if not cid or not text.startswith("/"):
            continue
        allow = [str(x) for x in (cfg.get("allow_ids") or [])]
        if allow and cid not in allow:
            append_log("%s BO QUA lenh tu chat_id la %s: %s" % (t, cid, text[:80]),
                       path=log_path)
            handled.append({"cmd": "blocked", "from": cid})
            continue
        res = handle(text, cfg=cfg, runner=runner, queue=queue, dirs=dirs, dry=dry,
                     post=post, log_path=log_path)
        append_log("%s LENH %s -> %s (write=%s)" % (t, text[:120], res.get("cmd"),
                                                    res.get("write")), path=log_path)
        send(res.get("reply") or "(khong co noi dung)", token=token, chat=cid,
             post=post, dry=dry, log_path=log_path)
        handled.append({"cmd": res.get("cmd"), "from": cid, "ran": res.get("ran")})
    st["offset"] = offset
    st["last_poll"] = time.time()
    st["saved"] = save_state(st)
    return {"handled": handled, "state": st}


def task_command(python_exe=None, script=None) -> str:
    """Lenh Task Scheduler se chay (duong dan TUYET DOI; cwd khong quan trong)."""
    py = python_exe or sys.executable
    try:
        import backup as BK
        py = BK.hidden_python(py)      # pythonw: khong hien cua so moi phut
    except Exception:  # noqa: BLE001
        pass
    return '"%s" "%s" --once' % (py, str(script or Path(__file__).resolve()))


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(
        description="Cau noi Telegram 2 chieu: push canh bao + nhan lenh tu dien thoai")
    ap.add_argument("--push", action="store_true", help="gui cau hoi DANG CHO ra Telegram")
    ap.add_argument("--poll", action="store_true", help="doc lenh tu Telegram va tra loi")
    ap.add_argument("--once", action="store_true", help="push + poll (dung cho task 1 phut)")
    ap.add_argument("--test", metavar="TEXT", help="gui 1 tin nhan kiem tra")
    ap.add_argument("--dry", action="store_true",
                    help="khong goi mang (ghi vao logs/telegram_bridge.log)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--uninstall-task", action="store_true")
    ap.add_argument("--task-status", action="store_true")
    ap.add_argument("--task-min", type=int, default=1, help="chu ky task (phut, mac dinh 1)")
    args = ap.parse_args(argv)

    cfg = cfg_for(ROOT)
    if not cfg["token"]:                      # instance LIVE co the dung token khac
        cfg = cfg_for(LIVE_DIR) or cfg

    if args.install_task or args.uninstall_task or args.task_status:
        import backup as BK
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = task_command()
        res = BK.run_schtasks(BK.schtasks_argv(action, TASK_NAME, command=cmd,
                                              sched="MINUTE", mod=args.task_min))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME, "OK" if res["ok"] else "LOI (%s)" % res["code"]))
            print("  lenh: %s  (moi %d phut)" % (cmd, args.task_min))
        return 0 if res["ok"] else 1

    out: dict = {}
    if args.test:
        out["test"] = send(args.test, token=cfg["token"], chat=cfg["chat"], dry=args.dry)
    if args.push or args.once:
        out["push"] = push(token=cfg["token"], chat=cfg["chat"], dry=args.dry)
    if args.poll or args.once:
        out["poll"] = poll(token=cfg["token"], chat=cfg["chat"], cfg=cfg, dry=args.dry)
    if not out:
        out["help"] = ("dung --push / --poll / --once / --test <text> / --install-task "
                       "(--dry de thu khong goi mang)")
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        if "push" in out:
            print("push: %d cau hoi%s" % (len(out["push"]["pushed"]),
                                          " (DRY)" if args.dry else ""))
        if "poll" in out:
            print("poll: xu ly %d lenh%s"
                  % (len(out["poll"]["handled"]),
                     (" | LOI: " + out["poll"]["error"]) if out["poll"].get("error") else ""))
        if "test" in out:
            print("test:", "DA GUI" if out["test"].get("ok") else "LOI")
        if "help" in out:
            print(out["help"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
