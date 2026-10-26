"""Hang doi CAU HOI cho nguoi van hanh — CO THE RESUME qua phien lam viec.

    python tools/ops_queue.py add "Co nen reset kill-switch TESTNET?" \
        --why "trip 15/10, ket 3.6 ngay" --option "reset" --option "giu" --priority high
    python tools/ops_queue.py list              # cau hoi DANG CHO
    python tools/ops_queue.py answer 3 "reset, da siet tham so" --by "nguoi van hanh"
    python tools/ops_queue.py resume            # tom tat de phien AI MOI tiep tuc dung cho
    python tools/ops_queue.py --json
    python tools/ops_queue.py --check           # exit 1 neu co cau hoi cho qua `--stale-hours`

Vi sao (19/10, REPO_IDEAS §15.3 — blueprint "handoff qua Jira/Confluence roi CHO confirm"):
du an co nhieu diem DUNG cho nguoi van hanh (kill-switch khong tu xoa, cong tam dung, xac nhan
LIVE...). Da gap that: TESTNET ket pause 3.6 ngay, cong pause BTW phai viet watcher rieng —
vi **khong co cho nao ghi lai "dang cho nguoi van hanh tra loi gi"**. Phien AI moi doc file
`logs/ops_questions.json` la biet ngay dang cho gi, cho bao lau, co lua chon nao.

2 file (theo TUNG instance):
  - `logs/ops_questions.json`: cau hoi DANG CHO (nguon su that cho "dang bi chan boi gi");
  - `logs/ops_queue.json`    : lich su da tra loi (giu vet ai tra loi, tra loi gi, luc nao).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import atomic  # noqa: E402

OPEN_PATH = "logs/ops_questions.json"
DONE_PATH = "logs/ops_queue.json"
#: Dau hieu "day la thu muc instance bot" (co `logs/` THOI la chua du: Windows cung co
#: `C:\Windows\System32\logs` nhung khong ghi duoc — xem `_instance_base`).
INSTANCE_MARKERS = ("turbo_demo.py", "config.py", "bot.py")
PRIORITIES = ("low", "normal", "high", "blocker")


def _instance_base(base: Path) -> Path:
    """Thu muc INSTANCE neu `base` that su la 1 instance bot, khong thi tra `ROOT`.

    (26/10) Khong the chi kiem `logs/`: Windows CO SAN `C:\\Windows\\System32\\logs` (task
    Scheduler chay voi cwd = System32 khi task khong dat `<WorkingDirectory>`) nhung thu muc
    do **khong ghi duoc** (do that: `PermissionError`) ⇒ canh bao ghi that bai trong thinh
    lang (24/10: dong `VAN DE naked @ LIVE` co trong log, hang doi TRONG).
    Nen phai kiem them DAU HIEU INSTANCE (file loi cua bot o goc thu muc).
    """
    base = Path(base)
    if (base / "logs").is_dir() and any((base / m).exists() for m in INSTANCE_MARKERS):
        return base
    return ROOT


def _paths(cfg=None, open_path=None, done_path=None) -> tuple:
    """(file cau hoi dang cho, file lich su) — theo instance (mac dinh: cwd).

    Chay trong thu muc instance (vd `atb-live`) ⇒ hang doi cua instance do. Chay o noi khac
    (Task Scheduler: cwd = `C:\\Windows\\System32`) ⇒ dung thu muc repo chua cong cu nay,
    KHONG ghi vao noi khong ghi duoc (loi that 24/10, xem `_instance_base`).
    """
    base = _instance_base(Path.cwd())
    o = Path(str(open_path or getattr(cfg, "ops_questions_path", "") or base / OPEN_PATH))
    d = Path(str(done_path or getattr(cfg, "ops_queue_path", "") or base / DONE_PATH))
    return o, d


def _read_list(p: Path) -> list:
    """Doc file JSON (list). File hong / thieu -> [] (fail-open: khong chan gi)."""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return data if isinstance(data, list) else []


def _write_list(p: Path, items: list) -> bool:
    """Ghi nguyen tu (tmp + fsync + replace) — khong lam hong file khi crash."""
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_json_atomic(p, items, indent=1)
        return True
    except OSError as e:
        # (26/10) Loi ghi KHONG duoc im lang (truoc day `return False` trong thinh lang).
        print("[LOI] khong ghi duoc hang doi %s: %s" % (p, str(e)[:120]),
              file=sys.stderr)
        return False


def add(question: str, *, why: str = "", options=(), priority: str = "normal",
        cfg=None, open_path=None, now=None, by: str = "agent") -> dict:
    """Them 1 cau hoi DANG CHO. Tra ban ghi da them (co `id`)."""
    o, _ = _paths(cfg, open_path, None)
    items = _read_list(o)
    ids = [int(x.get("id") or 0) for x in items if isinstance(x, dict)]
    rec = {"id": (max(ids) + 1) if ids else 1,
           "ts": float(now() if callable(now) else time.time()),
           "question": str(question)[:400], "why": str(why)[:600],
           "options": [str(x)[:120] for x in (options or [])],
           "priority": str(priority if priority in PRIORITIES else "normal"),
           "by": str(by)[:40], "status": "OPEN"}
    items.append(rec)
    ok = _write_list(o, items)
    return {"ok": ok, "path": str(o), **rec}


def open_items(cfg=None, open_path=None) -> list:
    """Cau hoi DANG CHO (sap xep: priority cao truoc, roi cu nhat truoc)."""
    o, _ = _paths(cfg, open_path, None)
    items = [x for x in _read_list(o) if isinstance(x, dict)
             and str(x.get("status") or "OPEN") == "OPEN"]
    rank = {p: i for i, p in enumerate(PRIORITIES)}
    return sorted(items, key=lambda x: (-rank.get(str(x.get("priority")), 1),
                                        float(x.get("ts") or 0)))


def done_items(cfg=None, done_path=None) -> list:
    """Lich su da tra loi (moi nhat truoc)."""
    _, d = _paths(cfg, None, done_path)
    items = [x for x in _read_list(d) if isinstance(x, dict)]
    return sorted(items, key=lambda x: -float(x.get("answered_ts") or 0))


def answer(qid: int, answer_text: str, *, by: str = "nguoi van hanh", cfg=None,
           open_path=None, done_path=None, now=None) -> dict:
    """Tra loi cau hoi `qid` -> chuyen sang lich su (`ops_queue.json`)."""
    o, d = _paths(cfg, open_path, done_path)
    items = _read_list(o)
    found = None
    for x in items:
        if isinstance(x, dict) and int(x.get("id") or 0) == int(qid):
            found = x
            break
    if found is None:
        return {"ok": False, "err": "khong co cau hoi id=%s" % qid, "open": len(items)}
    items.remove(found)
    found = dict(found)
    found.update({"status": "ANSWERED", "answer": str(answer_text)[:600],
                  "answered_ts": float(now() if callable(now) else time.time()),
                  "answered_by": str(by)[:40]})
    hist = _read_list(d)
    hist.append(found)
    ok1 = _write_list(o, items)
    ok2 = _write_list(d, hist)
    # (19/10) Hook: sinh ARTIFACT cho quyet dinh nay (muc 16 — MetaGPT/Dify/LangGraph).
    # Best-effort: loi o day KHONG duoc lam hong ket qua tra loi. Phieu hoi dong duoc lay
    # tu journal theo dung cau hoi (xem `tools/ops_artifact.py`).
    art = {}
    if ok1 and ok2:
        try:
            import ops_artifact as _OA
            art = _OA.from_queue(found["id"], done_path=d, open_path=o)
        except Exception:  # noqa: BLE001
            art = {}
    return {"ok": ok1 and ok2, "id": found["id"], "question": found["question"],
            "answer": found["answer"], "open_left": len(items),
            "artifact": art.get("path") if art.get("ok") else None}


def stale(items: list, *, stale_hours: float = 24.0, now=None) -> list:
    """Cau hoi da cho qua `stale_hours` (mac dinh 24h) — dau hieu 'bi chan boi nguoi'."""
    t = float(now() if callable(now) else time.time())
    lim = float(stale_hours) * 3600.0
    return [x for x in (items or []) if (t - float(x.get("ts") or 0)) >= lim]


def resume_text(items: list, *, stale_hours: float = 24.0, now=None) -> list:
    """Dong tom tat de PHIEN MOI doc lai (khong phai hoi lai nguoi van hanh)."""
    if not items:
        return ["Hang doi cau hoi: TRONG (khong cho nguoi van hanh tra loi gi)."]
    old = {id(x) for x in stale(items, stale_hours=stale_hours, now=now)}
    t = float(now() if callable(now) else time.time())
    out = ["Hang doi cau hoi: %d cau DANG CHO nguoi van hanh:" % len(items)]
    for x in items:
        age_h = (t - float(x.get("ts") or 0)) / 3600.0
        mark = "  <-- QUA %gh (can nhac lai)" % stale_hours if id(x) in old else ""
        out.append("  #%s [%s] %.1fh: %s%s"
                   % (x.get("id"), x.get("priority"), age_h, x.get("question"), mark))
        if x.get("why"):
            out.append("      vi sao: %s" % x["why"])
        if x.get("options"):
            out.append("      lua chon: %s" % " | ".join(x["options"]))
    out.append("  Tra loi: `python tools/ops_queue.py answer <id> \"<y kien>\"`")
    return out



def main(argv: list | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Hang doi cau hoi cho nguoi van hanh (resume duoc)")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="them cau hoi dang cho")
    a.add_argument("question")
    a.add_argument("--why", default="", help="vi sao can hoi (bang chung)")
    a.add_argument("--option", action="append", default=[], help="1 lua chon (lap lai duoc)")
    a.add_argument("--priority", default="normal", choices=list(PRIORITIES))
    b = sub.add_parser("answer", help="tra loi 1 cau hoi")
    b.add_argument("qid", type=int)
    b.add_argument("answer")
    b.add_argument("--by", default="nguoi van hanh")
    sub.add_parser("list", help="cau hoi dang cho")
    sub.add_parser("resume", help="tom tat cho phien moi")
    sub.add_parser("done", help="lich su da tra loi")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stale-hours", type=float, default=24.0,
                    help="coi la 'cho qua lau' sau N gio (mac dinh 24)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 neu co cau hoi cho qua --stale-hours")
    args = ap.parse_args(argv)

    cmd = args.cmd or ("list" if not args.check else "check")

    if args.check:
        items = open_items()
        old = stale(items, stale_hours=args.stale_hours)
        rep = {"open": len(items), "stale": len(old),
               "stale_questions": [x.get("question") for x in old],
               "stale_hours": args.stale_hours}
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("=== HANG DOI CAU HOI | %d dang cho | %d qua %.0fh ==="
                  % (rep["open"], rep["stale"], args.stale_hours))
            for q in rep["stale_questions"]:
                print("  QUA LAU: %s" % q)
            print("  KET LUAN: %s" % ("CO cau hoi bi bo quen" if old else "khong"))
        return 1 if old else 0

    if cmd == "add":
        r = add(args.question, why=args.why, options=args.option, priority=args.priority)
        print(json.dumps(r, ensure_ascii=False) if args.json else
              "da them cau hoi #%s [%s] -> %s" % (r.get("id"), r.get("priority"), r.get("path")))
        return 0 if r.get("ok") else 2
    if cmd == "answer":
        r = answer(args.qid, args.answer, by=args.by)
        print(json.dumps(r, ensure_ascii=False) if args.json else
              ("da tra loi #%s: %s (con %s cau cho)"
               % (r.get("id"), r.get("answer"), r.get("open_left"))
               if r.get("ok") else "LOI: %s" % r.get("err")))
        return 0 if r.get("ok") else 2
    if cmd == "done":
        items = done_items()
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=1))
            return 0
        print("=== DA TRA LOI | %d muc ===" % len(items))
        for x in items:
            print("  #%s %s -> %s" % (x.get("id"), str(x.get("question"))[:60],
                                      str(x.get("answer"))[:60]))
        return 0

    items = open_items()
    if cmd == "resume":
        lines = resume_text(items, stale_hours=args.stale_hours)
        print(json.dumps({"open": items, "text": lines}, ensure_ascii=False, indent=1)
              if args.json else "\n".join(lines))
        return 0
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    print("=== CAU HOI DANG CHO | %d ===" % len(items))
    for x in items:
        age_h = (time.time() - float(x.get("ts") or 0)) / 3600.0
        print("  #%s [%s] %.1fh: %s" % (x.get("id"), x.get("priority"), age_h,
                                        str(x.get("question"))[:90]))
    if not items:
        print("  (trong — khong cho nguoi van hanh tra loi gi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

