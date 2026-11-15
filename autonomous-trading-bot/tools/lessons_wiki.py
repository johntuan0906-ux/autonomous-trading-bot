"""lessons_wiki.py — sinh `LESSONS.md` TU JOURNAL, co TRICH DAN nguon + may kiem lai duoc.

Chay:
  python tools\\lessons_wiki.py                  # xem truoc (khong ghi)
  python tools\\lessons_wiki.py --write          # ghi phan AUTO (giu nguyen khoi <!-- HUMAN -->)
  python tools\\lessons_wiki.py --check          # so so lieu trong LESSONS.md voi journal THAT

Vi sao (RESEARCH_1211 §1 muc 6 — karpathy/llm-wiki + ai-memory): `LESSONS.md` viet tay thi khong ai
biet so co dung khong; nam sau doc lai tuong la so lieu. Tool nay:
  1) tinh lai TU JOURNAL (nguon duy nhat) theo dung khoa cua `lessons.KEYS_DEFAULT`;
  2) moi dong co TRICH DAN (`decision_id` hoac moc thoi gian cua lenh da dung);
  3) nhung mot khoi JSON de `--check` so lai: so trong tai lieu KHONG khop nguon ⇒ bao loi.
Khoi `<!-- HUMAN -->...<!-- /HUMAN -->` (neu co) duoc giu NGUYEN khi `--write`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import lessons as LS            # noqa: E402  (KEYS_DEFAULT / key_of / HUMAN_*)
import perf_report as PR        # noqa: E402  (rows / closes)

DEFAULT_MD = ROOT / "LESSONS.md"
AUTO_BEGIN = "<!-- AUTO:LESSONS -->"
AUTO_END = "<!-- /AUTO:LESSONS -->"
MIN_N = 8                       # so lenh toi thieu de mot to hop duoc coi la "bai hoc"


def _ref(rec: dict) -> str:
    """Trich dan ngan: uu tien `decision_id`, khong co thi dung moc thoi gian."""
    did = str(rec.get("decision_id") or "").strip()
    if did:
        return did
    try:
        return "ts=%d" % int(float(rec.get("ts") or 0))
    except (TypeError, ValueError):
        return "ts=?"


def collect(rows, min_n: int = MIN_N) -> dict:
    """Tu ban ghi journal -> {khoa: {n, winrate, avg_r, pnl, refs}} (chi khoa du mau)."""
    opens: dict = {}
    for r in rows:
        if "entry" in r and str(r.get("event") or "") == "OPEN":
            key = str(r.get("pair") or r.get("symbol") or "")
            opens.setdefault(key, []).append(r)
    out: dict = {}
    for c in PR.closes(rows):
        rec = dict(c)
        pair = str(rec.get("pair") or rec.get("symbol") or "")
        queue = opens.get(pair) or []
        o = queue.pop(0) if queue else {}
        for k in LS.KEYS_DEFAULT:
            if rec.get(k) in (None, "") and o.get(k) not in (None, ""):
                rec[k] = o.get(k)
        key = LS.key_of(rec)
        row = out.setdefault(key, {"n": 0, "wins": 0, "sum_r": 0.0, "pnl": 0.0, "refs": []})
        row["n"] += 1
        try:
            r = float(rec.get("r") or 0.0)
        except (TypeError, ValueError):
            r = 0.0
        row["sum_r"] += r
        row["wins"] += 1 if r > 0 else 0
        try:
            row["pnl"] += float(rec.get("pnl") or 0.0)
        except (TypeError, ValueError):
            pass
        if len(row["refs"]) < 3:
            row["refs"].append(_ref(rec))
    keep = {}
    for key, row in out.items():
        if row["n"] < int(min_n):
            continue
        keep[key] = {"n": row["n"], "wins": row["wins"],
                     "winrate": round(100.0 * row["wins"] / row["n"], 1),
                     "avg_r": round(row["sum_r"] / row["n"], 3),
                     "pnl": round(row["pnl"], 2), "refs": row["refs"]}
    return keep


def render(data: dict, min_n: int = MIN_N, journal: str = "") -> str:
    """Khoi AUTO: bang bai hoc (xau truoc) + JSON de may kiem."""
    lines = [AUTO_BEGIN, "",
             "## Bài học tự sinh (đừng sửa tay — chạy `python tools\\lessons_wiki.py --write`)",
             "",
             "Nguồn: `%s` · khóa = `%s` · ngưỡng mẫu n ≥ %d · sắp theo `avg_r` tăng dần."
             % (journal or "logs/journal.jsonl", " + ".join(LS.KEYS_DEFAULT), int(min_n)),
             "",
             "| Khóa (strategy · setup · regime · hướng) | n | thắng | avg R | PnL | trích dẫn |",
             "|---|---|---|---|---|---|"]
    for key, s in sorted(data.items(), key=lambda kv: (kv[1]["avg_r"], -kv[1]["n"])):
        flag = " (!)" if s["avg_r"] < 0 else ""
        lines.append("| %s%s | %d | %.1f%% | %+.3f | %+.2f | %s |"
                     % (key, flag, s["n"], s["winrate"], s["avg_r"], s["pnl"],
                        ", ".join(s["refs"])))
    lines += ["", "```json", json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1),
              "```", AUTO_END]
    return "\n".join(lines)


def human_block(text: str) -> str:
    """Khoi `<!-- HUMAN -->...<!-- /HUMAN -->` (giu nguyen khi ghi)."""
    i = text.find(LS.HUMAN_BEGIN)
    j = text.find(LS.HUMAN_END)
    if i < 0 or j < 0:
        return ""
    return text[i:j + len(LS.HUMAN_END)]


def parse_auto(text: str):
    """Doc khoi JSON trong LESSONS.md (None neu khong co / hong)."""
    i = text.find(AUTO_BEGIN)
    j = text.find(AUTO_END)
    if i < 0 or j < 0:
        return None
    body = text[i:j]
    k = body.find("```json")
    if k < 0:
        return None
    k2 = body.find("```", k + 7)
    try:
        return json.loads(body[k + 7:k2])
    except ValueError:
        return None


def journal_path(instance: str = "testnet") -> Path:
    """Journal cua instance (dung lai logic cua `perf_report`)."""
    return PR.journal_for(instance)


def check(md_path=None, rows=None, min_n: int = MIN_N, instance: str = "testnet") -> dict:
    """So so lieu trong LESSONS.md voi journal. Tra {ok, reason, diff}."""
    p = Path(md_path) if md_path else DEFAULT_MD
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"ok": False, "reason": "khong thay %s" % p, "diff": []}
    was = parse_auto(text)
    if was is None:
        return {"ok": False, "reason": "LESSONS.md thieu khoi AUTO (chay --write)", "diff": []}
    now = collect(rows if rows is not None else PR.rows(journal_path(instance)), min_n)
    diff = []
    for key in sorted(set(was) | set(now)):
        a, b = was.get(key), now.get(key)
        if a != b:
            diff.append({"key": key, "in_doc": a, "in_journal": b})
    return {"ok": not diff,
            "reason": ("" if not diff else
                       "%d khoa KHONG khop nguon (so trong tai lieu ≠ journal)" % len(diff)),
            "diff": diff}


def write(md_path=None, rows=None, min_n: int = MIN_N, instance: str = "testnet") -> dict:
    """Ghi phan AUTO vao LESSONS.md, giu khoi HUMAN + phan dau tai lieu."""
    p = Path(md_path) if md_path else DEFAULT_MD
    try:
        old = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        old = "# LESSONS\n"
    data = collect(rows if rows is not None else PR.rows(journal_path(instance)), min_n)
    block = render(data, min_n, str(journal_path(instance)))
    i, j = old.find(AUTO_BEGIN), old.find(AUTO_END)
    if i >= 0 and j >= 0:
        new = old[:i] + block + old[j + len(AUTO_END):]
    else:
        human = human_block(old)
        head = old.split(LS.HUMAN_BEGIN)[0].rstrip()
        new = (head + "\n\n" + block + "\n" + (("\n" + human + "\n") if human else ""))
    try:
        p.write_text(new, encoding="utf-8")
    except OSError as e:
        return {"ok": False, "err": str(e)[:160], "n_keys": len(data)}
    return {"ok": True, "path": str(p), "n_keys": len(data)}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Sinh LESSONS.md tu journal (co trich dan).")
    ap.add_argument("--write", action="store_true", help="ghi vao LESSONS.md")
    ap.add_argument("--check", action="store_true", help="so tai lieu voi journal (exit 1 neu lech)")
    ap.add_argument("--min-n", type=int, default=MIN_N)
    ap.add_argument("--instance", default="testnet", choices=("testnet", "live"))
    ap.add_argument("--md", default="", help="duong dan LESSONS.md (mac dinh: repo)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    md = Path(args.md) if args.md else None
    if args.check:
        rep = check(md, min_n=args.min_n, instance=args.instance)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print("=== LESSONS | check | %s ===" % ("KHOP" if rep["ok"] else "LECH"))
            for d in rep["diff"][:10]:
                print("  - %s\n      trong tai lieu: %s\n      trong journal : %s"
                      % (d["key"], d["in_doc"], d["in_journal"]))
            if not rep["ok"]:
                print("  KET LUAN: %s" % rep["reason"])
        return 0 if rep["ok"] else 1
    if args.write:
        r = write(md, min_n=args.min_n, instance=args.instance)
        print(("da ghi %s (%d khoa)" % (r["path"], r["n_keys"])) if r["ok"]
              else ("LOI ghi: %s" % r.get("err")))
        return 0 if r["ok"] else 1
    data = collect(PR.rows(journal_path(args.instance)), args.min_n)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=1))
        return 0
    print(render(data, args.min_n, str(journal_path(args.instance))))
    print("\n(khoa=%d; chay --write de ghi vao LESSONS.md, --check de kiem lai)"
          % len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
