"""Artifact cho MOI quyet dinh van hanh: 1 file .md (boi canh -> phieu -> hanh dong -> ket qua).

    python tools/ops_artifact.py --from-queue 1          # sinh tu cau hoi da tra loi (#id)
    python tools/ops_artifact.py --question "..." --answer "..." \
        --action "da chay X" --result "kiem chung Y"
    python tools/ops_artifact.py --list                  # liet ke artifact da co
    python tools/ops_artifact.py --json

Vi sao co (19/10, hoi dong **1-4 VETO** viec lam `council_replay` vi ton credit — chon viec
re hon): repo **MetaGPT** (artifact chuan hoa moi buoc), **Dify** (log/observability) va
**LangGraph** (checkpoint) deu cho thay: quyet dinh chi co gia tri khi **boi canh + bang
chung + ket qua** nam cung mot cho. Truoc day phieu hoi dong nam trong `journal.jsonl`,
cau hoi nam trong `logs/ops_questions.json`, hanh dong nam trong log bot ⇒ muon tra loi
"vi sao ngay 19/10 lai doi tham so TESTNET?" phai ghep 3 file bang tay.

Khong goi mang, khong goi LLM (re, chay duoc moi lan). Tu dong sinh khi
`tools/ops_queue.py answer ...` chay (xem hook o cuoi `answer()`).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART_DIR = "logs/ops"
QUEUE_DONE = "logs/ops_queue.json"

sys.path.insert(0, str(ROOT))
import atomic  # noqa: E402
QUEUE_OPEN = "logs/ops_questions.json"
JOURNAL = "logs/journal.jsonl"


def slugify(text: str, maxlen: int = 48) -> str:
    """Ten file an toan tu cau hoi (bo dau tieng Viet, chi [a-z0-9-]).

    (19/10) `đ/Đ` la CHU CAI rieng (khong phai dau cua `d`) nen `NFKD` khong tach duoc —
    phai thay tay, neu khong ten file se co ky tu la (test `test_bo_dau_tieng_viet` bat duoc).
    """
    s = str(text or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    out, prev_dash = [], False
    for ch in s.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return (slug[:maxlen].strip("-") or "quyet-dinh")


def votes_for_question(journal_path: Path, question: str, limit: int = 40) -> list:
    """Phieu hoi dong trong journal cho DUNG cau hoi nay -> [{model, action, confidence, reason}].

    So khop mem: bo khoang trang dau/cuoi + khong phan biet hoa/thuong + so sanh 60 ky tu
    dau (cau hoi dai bi cat khi ghi journal).
    """
    want = str(question or "").strip().lower()[:60]
    rows: list = []
    try:
        lines = journal_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for ln in lines[-20000:]:
        if "COUNCIL" not in ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(d, dict) or str(d.get("status") or "").upper() != "COUNCIL":
            continue
        q = str(d.get("question") or "").strip().lower()[:60]
        if q != want:
            continue
        why = d.get("reasons") or d.get("reason") or []
        if isinstance(why, str):
            why = [why]
        rows.append({"model": str(d.get("model") or "?"), "action": str(d.get("action") or "?"),
                     "confidence": d.get("confidence"),
                     "reason": "; ".join(str(x) for x in why)[:220]})
        if len(rows) >= limit:
            break
    return rows


def tally(votes) -> dict:
    """Dem phieu -> {allow, veto, abstain, verdict}."""
    n_a = sum(1 for v in (votes or []) if str(v.get("action") or "").upper() == "ALLOW")
    n_v = sum(1 for v in (votes or []) if str(v.get("action") or "").upper() == "VETO")
    verdict = ("ALLOW" if n_a > n_v else "VETO" if n_v > n_a else "NO_OPINION")
    return {"allow": n_a, "veto": n_v,
            "abstain": len(votes or []) - n_a - n_v, "verdict": verdict}


def render(rec: dict) -> str:
    """Markdown artifact (ham THUAN TUY -> test duoc). `rec` thieu truong => bo qua muc do."""
    ts = float(rec.get("ts") or 0)
    when = (_dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts
            else _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    votes = rec.get("votes") or []
    t = tally(votes)
    out = ["# Quyet dinh van hanh: %s" % str(rec.get("question") or "(khong ro)"), ""]
    out.append("- **Thoi diem**: %s" % when)
    if rec.get("id") is not None:
        out.append("- **Cau hoi #**: %s" % rec["id"])
    if rec.get("priority"):
        out.append("- **Muc uu tien**: %s" % rec["priority"])
    out.append("- **Nguoi/Agent quyet**: %s" % (rec.get("by") or "?"))
    out.append("- **Trang thai**: %s" % ("DA TRA LOI" if rec.get("answer") else "CHUA TRA LOI"))
    out.append("")
    out.append("## 1. Boi canh")
    out.append(str(rec.get("why") or "(khong ghi)"))
    opts = rec.get("options") or []
    if opts:
        out.append("")
        out.append("Lua chon da neu:")
        for i, o in enumerate(opts, 1):
            out.append("%d. %s" % (i, o))
    out.append("")
    out.append("## 2. Phieu hoi dong (n=%d, doc tu journal)" % len(votes))
    if votes:
        out.append("| Model | Phieu | Conf | Ly do |")
        out.append("|---|---|---|---|")
        for v in votes:
            c = v.get("confidence")
            out.append("| %s | %s | %s | %s |"
                       % (v.get("model"), v.get("action"),
                          ("%.2f" % c) if isinstance(c, (int, float)) else "-",
                          str(v.get("reason") or "").replace("|", "/")[:200]))
        out.append("")
        out.append("**Ket qua**: %d ALLOW / %d VETO / %d khong y kien -> **%s**"
                   % (t["allow"], t["veto"], t["abstain"], t["verdict"]))
    else:
        out.append("(khong co phieu hoi dong cho cau hoi nay trong journal)")
    out.append("")
    out.append("## 3. Quyet dinh")
    out.append(str(rec.get("answer") or "(chua tra loi)"))
    acts = rec.get("actions") or []
    out.append("")
    out.append("## 4. Hanh dong da thuc thi")
    out.extend("- %s" % a for a in acts) if acts else out.append("- (khong ghi)")
    res = rec.get("results") or []
    out.append("")
    out.append("## 5. Ket qua / kiem chung")
    out.extend("- %s" % r for r in res) if res else out.append("- (khong ghi)")
    out.append("")
    out.append("## 6. Truy vet")
    out.append("- Phieu: `logs/journal.jsonl` (`status=COUNCIL`, `question=...`)")
    out.append("- Cau hoi/hang doi: `logs/ops_questions.json` + `logs/ops_queue.json`")
    if rec.get("id") is not None:
        out.append("- Sinh lai: `python tools/ops_artifact.py --from-queue %s`" % rec["id"])
    out.append("- Cong cu lien quan: `tools/trace_trade.py` (1 lenh), `tools/ops_queue.py`")
    return "\n".join(out) + "\n"


def artifact_path(outdir, ts: float, question: str) -> Path:
    """Duong dan artifact: `<outdir>/<YYYYmmdd-HHMM>-<slug>.md`."""
    stamp = _dt.datetime.fromtimestamp(float(ts or 0)).strftime("%Y%m%d-%H%M")
    return Path(outdir) / ("%s-%s.md" % (stamp, slugify(question)))


def write_artifact(rec: dict, outdir=ART_DIR) -> dict:
    """Ghi artifact -> {ok, path, n_votes}. Loi ghi -> ok=False (khong nem ra ngoai).

    `ts` thieu/0 ⇒ lay GIO HIEN TAI (khong de ten file thanh 1970).
    """
    p = artifact_path(outdir, float(rec.get("ts") or time.time()),
                      str(rec.get("question") or ""))
    try:
        # (21/10) Nguyên tử: artifact là bằng chứng của quyết định; file cắt ngang = mất vết.
        atomic.write_text_atomic(p, render(rec))
        return {"ok": True, "path": str(p), "n_votes": len(rec.get("votes") or [])}
    except OSError as e:
        return {"ok": False, "err": str(e)[:160], "path": str(p),
                "n_votes": len(rec.get("votes") or [])}


def _read_json(path) -> list:
    """Doc file JSON (list). Loi/thieu -> [] (khong chan gi)."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return d if isinstance(d, list) else []


def from_queue(qid, done_path=QUEUE_DONE, open_path=QUEUE_OPEN, journal=JOURNAL,
               actions=(), results=(), outdir=ART_DIR, council_question: str = "") -> dict:
    """Sinh artifact cho cau hoi `#qid` trong hang doi (da tra loi hoac dang cho).

    Phieu hoi dong duoc TU DONG lay tu journal theo dung cau hoi -> khong phai chep tay.
    `council_question`: khi cau hoi DUA RA HOI DONG khac chu voi cau hoi trong hang doi
    (thuc te 19/10: hang doi ghi ngan, cau hoi hoi dong ghi dai) — neu khong truyen thi
    lay theo cau hoi trong hang doi (va artifact ghi ro "khong co phieu" neu khong khop).
    """
    for rec in _read_json(done_path) + _read_json(open_path):
        if str(rec.get("id")) != str(qid):
            continue
        item = dict(rec)
        item["votes"] = votes_for_question(
            Path(journal), council_question or item.get("question") or "")
        item["actions"] = list(actions or [])
        item["results"] = list(results or [])
        item["ts"] = item.get("answered_ts") or item.get("ts") or time.time()
        return write_artifact(item, outdir=outdir)
    return {"ok": False, "err": "khong thay cau hoi #%s trong hang doi" % qid,
            "n_votes": 0}


def list_artifacts(outdir=ART_DIR) -> list:
    """Danh sach artifact da sinh (moi nhat truoc)."""
    try:
        return sorted((str(p) for p in Path(outdir).glob("*.md")), reverse=True)
    except OSError:
        return []


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Artifact cho quyet dinh van hanh")
    ap.add_argument("--from-queue", type=int, help="id cau hoi trong hang doi")
    ap.add_argument("--question", help="cau hoi (khi khong dung hang doi)")
    ap.add_argument("--answer", default="")
    ap.add_argument("--why", default="", help="boi canh")
    ap.add_argument("--option", action="append", default=[], help="lua chon da neu")
    ap.add_argument("--action", action="append", default=[], help="hanh dong da lam (lap lai)")
    ap.add_argument("--result", action="append", default=[], help="ket qua/kiem chung (lap lai)")
    ap.add_argument("--by", default="nguoi van hanh")
    ap.add_argument("--council-question", default="",
                    help="cau hoi DUNG khi hoi hoi dong (neu khac cau hoi trong hang doi)")
    ap.add_argument("--journal", default=JOURNAL)
    ap.add_argument("--queue", default=QUEUE_DONE)
    ap.add_argument("--open", dest="open_path", default=QUEUE_OPEN)
    ap.add_argument("--dir", default=ART_DIR)
    ap.add_argument("--list", action="store_true", help="liet ke artifact da co")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        items = list_artifacts(args.dir)
        if args.json:
            print(json.dumps({"dir": args.dir, "n": len(items), "files": items},
                             ensure_ascii=False, indent=1))
        else:
            print("=== ARTIFACT | %d file | %s ===" % (len(items), args.dir))
            for p in items:
                print("  " + p)
        return 0
    if args.from_queue is not None:
        rep = from_queue(args.from_queue, args.queue, args.open_path, args.journal,
                         args.action, args.result, args.dir, args.council_question)
    elif args.question:
        rep = write_artifact({"question": args.question, "answer": args.answer,
                              "why": args.why, "options": args.option, "by": args.by,
                              "actions": args.action, "results": args.result,
                              "votes": votes_for_question(Path(args.journal), args.question)},
                             outdir=args.dir)
    else:
        print("LOI: can --from-queue <id> hoac --question \"...\" (hoac --list)")
        return 2
    print(json.dumps(rep, ensure_ascii=False) if args.json else
          ("artifact: %s (%d phieu)" % (rep.get("path"), rep.get("n_votes", 0))
           if rep.get("ok") else "LOI: %s" % rep.get("err")))
    return 0 if rep.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
