"""So thay doi HARNESS (prompt / model / gate / risk / lesson) — co BANG CHUNG va quyet dinh.

    python tools/harness_ledger.py --add --kind prompt \
        --change "hoi dong: them vai phan bien so lieu truoc khi vote" \
        --evidence "B-023 + 157 loi/ngay" --decision adopted --by "nguoi van hanh"
    python tools/harness_ledger.py --list
    python tools/harness_ledger.py --check     # exit 1 neu adopted KHONG co bang chung

Vi sao co (21/10, doc `google-research/harness2`): harness = "prompts, tools, memory,
skills, orchestration" quanh model; **harnessing** = toi uu hoa he do. Hai y tuong dang hoc:

  1. **Propose–Probe–Compose tren CUNG mot bai, KHONG can ground truth** — so "contrast
     hanh vi" giua 2 phien ban. Voi bot nay dac biet hop: khong bao gio biet PnL phan thuc
     cua mot lenh BI VETO, nen khong the cham bang ket qua; chi so sanh **hanh vi**
     (ti le VETO, bat dong, chi phi, do tre) tren cung bo payload lich su.
  2. **Harnessing-level: bai hoc phai co BANG CHUNG va duoc ADOPT** — khong phai ghi y
     dinh vao docs roi de do.

`bug_catalog.py` lo lop LOI; file nay lo lop THAY DOI HE THONG (ai doi gi, vi sao, ket qua).
`--check` bao: adopted/rejected ma thieu bang chung; `proposed` qua 7 ngay chua quyet;
kind la. Khong nem exception (kieu tool van hanh cua du an).
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

PATH = ROOT / "logs" / "harness_ledger.jsonl"
KINDS = ("prompt", "model", "gate", "risk", "lesson", "tool", "other")
DECISIONS = ("proposed", "adopted", "rejected", "rolled-back")
STALE_DAYS = 7.0


def read_all(path=PATH) -> list:
    """Doc jsonl; dong hong -> bo qua (khong lam hong ca so)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def next_id(rows, now) -> str:
    """`H-YYYYMMDD-NNN` — so thu tu trong ngay (doc tu chinh so)."""
    day = time.strftime("%Y%m%d", time.localtime(float(now)))
    prefix = "H-%s-" % day
    n = 0
    for r in rows or []:
        rid = str((r or {}).get("id") or "")
        if rid.startswith(prefix):
            try:
                n = max(n, int(rid[len(prefix):]))
            except ValueError:
                continue
    return "%s%03d" % (prefix, n + 1)


def add(kind: str, change: str, evidence: str = "", *, decision: str = "proposed",
        probe: str = "", by: str = "agent", note: str = "", path=PATH, now=None) -> dict:
    """Them 1 dong. Tra {ok, record} hoac {ok: False, err} (khong nem ra ngoai)."""
    k = str(kind or "").strip().lower()
    d = str(decision or "").strip().lower()
    if k not in KINDS:
        return {"ok": False, "err": "kind khong hop le: %r (dung: %s)"
                                    % (kind, ", ".join(KINDS))}
    if d not in DECISIONS:
        return {"ok": False, "err": "decision khong hop le: %r" % decision}
    txt = str(change or "").strip()
    if not txt:
        return {"ok": False, "err": "thieu --change"}
    now_t = float(now if now is not None else time.time())
    rows = read_all(path)
    rec = {"id": next_id(rows, now_t), "ts": now_t, "kind": k, "change": txt[:600],
           "evidence": str(evidence or "")[:600], "probe": str(probe or "")[:400],
           "decision": d, "by": str(by or "agent")[:60], "note": str(note or "")[:400]}
    rows.append(rec)
    try:
        atomic.write_text_atomic(
            path, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    except OSError as e:
        return {"ok": False, "err": "khong ghi duoc: %s" % str(e)[:160]}
    return {"ok": True, "record": rec}


def decide(rid: str, decision: str, *, evidence: str = "", note: str = "", by: str = "agent",
           path=PATH, now=None) -> dict:
    """Chot quyet dinh cho 1 muc da ghi (theo `id`): giu `history` de khong mat vet cu.

    Vi sao co: mot de xuat co the duoc DO roi moi chot (vd `proposed` -> `rejected` sau khi
    do bang `council_probe`). Neu chi them dong moi thi muc cu van nam `proposed` va
    `--check` bao "treo qua 7 ngay" mai — bao dong gia.
    """
    d = str(decision or "").strip().lower()
    if d not in DECISIONS:
        return {"ok": False, "err": "decision khong hop le: %r" % decision}
    rows = read_all(path)
    hit = None
    for r in rows:
        if str(r.get("id")) == str(rid):
            hit = r
            break
    if hit is None:
        return {"ok": False, "err": "khong tim thay id %r" % rid}
    now_t = float(now if now is not None else time.time())
    hist = list(hit.get("history") or [])
    hist.append({"ts": now_t, "decision": hit.get("decision"), "by": hit.get("by"),
                 "evidence": hit.get("evidence")})
    hit["history"] = hist
    hit["decision"] = d
    if evidence:
        hit["evidence"] = str(evidence)[:600]
    if note:
        hit["note"] = str(note)[:400]
    hit["by"] = str(by or "agent")[:60]
    hit["decided_at"] = now_t
    try:
        atomic.write_text_atomic(
            path, "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    except OSError as e:
        return {"ok": False, "err": "khong ghi duoc: %s" % str(e)[:160]}
    return {"ok": True, "record": hit}


def check(rows=None, *, now=None, stale_days: float = STALE_DAYS) -> dict:
    """Tim thay doi THIEU bang chung hoac treo qua lau. Tra {ok, problems, n}."""
    rows = read_all() if rows is None else list(rows)
    now_t = float(now if now is not None else time.time())
    probs = []
    for r in rows:
        rid = str(r.get("id") or "?")
        ev = str(r.get("evidence") or "").strip()
        dec = str(r.get("decision") or "")
        if dec in ("adopted", "rejected", "rolled-back") and not ev:
            probs.append("%s: %s nhung KHONG co bang chung (--evidence)" % (rid, dec))
        if dec == "proposed":
            try:
                age_d = (now_t - float(r.get("ts") or 0.0)) / 86400.0
            except (TypeError, ValueError):
                age_d = 0.0
            if age_d > float(stale_days):
                probs.append("%s: de xuat qua %.0f ngay chua quyet" % (rid, age_d))
        if str(r.get("kind") or "") not in KINDS:
            probs.append("%s: kind la %r" % (rid, r.get("kind")))
    return {"ok": not probs, "n": len(rows), "problems": probs}



def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="So thay doi harness (co bang chung)")
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--kind", choices=KINDS)
    ap.add_argument("--change", default="")
    ap.add_argument("--evidence", default="")
    ap.add_argument("--probe", default="", help="ket qua do hanh vi (contrast) neu co")
    ap.add_argument("--decision", choices=DECISIONS, default="proposed")
    ap.add_argument("--by", default="agent")
    ap.add_argument("--note", default="")
    ap.add_argument("--decide", metavar="ID", help="chot quyet dinh cho muc da ghi")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.decide:
        r = decide(args.decide, args.decision, evidence=args.evidence, note=args.note,
                   by=args.by)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        elif r["ok"]:
            rec = r["record"]
            print("%s -> %s (giu %d muc lich su)"
                  % (rec["id"], rec["decision"], len(rec.get("history") or [])))
        else:
            print("LOI: %s" % r["err"])
        return 0 if r["ok"] else 1

    if args.add:
        r = add(args.kind or "", args.change, args.evidence, decision=args.decision,
                probe=args.probe, by=args.by, note=args.note)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        elif r["ok"]:
            rec = r["record"]
            print("%s [%s/%s] %s" % (rec["id"], rec["kind"], rec["decision"],
                                     rec["change"][:100]))
        else:
            print("LOI: %s" % r["err"])
        return 0 if r["ok"] else 1

    rows = read_all()
    if args.check:
        rep = check(rows)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("=== HARNESS LEDGER | %d thay doi ===" % rep["n"])
            for p in rep["problems"]:
                print("  - %s" % p)
            print("  KET LUAN: %s" % ("OK" if rep["ok"] else "CAN XEM"))
        return 0 if rep["ok"] else 1

    tail = rows[-max(1, int(args.limit)):]
    if args.json:
        print(json.dumps(tail, ensure_ascii=False, indent=1))
    else:
        print("=== HARNESS LEDGER | %d dong (hien %d) ===" % (len(rows), len(tail)))
        for r in tail:
            print("  %-14s %-7s %-10s %s"
                  % (r.get("id"), r.get("kind"), r.get("decision"),
                     str(r.get("change") or "")[:90]))
            if r.get("evidence"):
                print("                 bang chung: %s" % str(r["evidence"])[:100])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

