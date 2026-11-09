"""So khop TAI LIEU <-> CODE (drift report) — chong tai lieu noi dieu code khong lam.

    python tools\\drift_docs.py            # in bang doi chieu
    python tools\\drift_docs.py --check    # exit 1 neu co muc LECH (dung trong chuoi kiem tra)
    python tools\\drift_docs.py --json

Vi sao co (09/11, muc #7 cua REPO_IDEAS §29.3):
- Trong dung 1 ngay lam viec, so lieu trong tai lieu da lech code 3 lan (31 -> 40 ma ly do,
  26 -> 40 ca golden, 43 -> 45 lop bug catalog). Moi lan deu do NGUOI doc phat hien tinh co —
  khong co co che nao bao. Tai lieu sai khong lam bot dung, nhung lam nguoi van hanh va agent
  RA QUYET DINH tren so lieu cu ⇒ nguy hiem hon loi code.
- Cach lam: moi "loi khai" (claim) = 1 regex tren 1 file tai lieu + 1 ham tinh gia tri THAT tu
  code. Khong co tri tue gi o day — chi la phep so sanh, nen khong the "tu lua minh".

Them 1 loi khai = them 1 dong trong `CLAIMS`. Neu tai lieu doi cau chu lam regex khong khop,
bao cao ghi "KHONG TIM THAY" (do cung la drift: mat dau vet so lieu).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))


def _n_reason_codes() -> list:
    import reason_codes as RC
    return [str(len(RC.CODES)), str(len(RC.KINDS))]


def _n_golden() -> list:
    """(so ca, so cong) — doc THANG file ca + danh sach cong trong runner."""
    import golden_set as GS
    p = Path(ROOT / "golden" / "cases.jsonl")
    n = 0
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            n += 1
    return [str(n), str(len(GS.COMPONENTS))]


def _n_catalog() -> list:
    import bug_catalog as BC
    rep = BC.check()
    return [str(rep["n"]), str(rep["pinned"])]


#: Moi loi khai: `file` (tuong doi voi ROOT), `pattern` co nhom bat, `values` -> danh sach
#: gia tri THAT (cung thu tu nhom), `what` de in bao cao.
CLAIMS = (
    {"file": "OPERATIONS.md", "pattern": r"(\d+) m\u00e3 / (\d+) nh\u00f3m",
     "values": _n_reason_codes, "what": "so ma ly do / so nhom"},
    {"file": "OPERATIONS.md", "pattern": r"(\d+) ca / (\d+) c\u1ed5ng",
     "values": _n_golden, "what": "so ca golden / so cong"},
    {"file": "OPERATIONS.md", "pattern": r"(\d+) l\u1edbp / (\d+) test ch\u1ed1t",
     "values": _n_catalog, "what": "so lop bug catalog / so test chot"},
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_claims(claims=CLAIMS, root: Path | None = None) -> list:
    """So khop tung loi khai -> list {file, what, doc, code, ok, note} (ham THUAN TUY)."""
    base = Path(root or ROOT)
    rows: list = []
    for c in claims:
        text = _read(base / str(c["file"]))
        want = [str(x) for x in (c["values"]() or [])]
        m = re.search(str(c["pattern"]), text or "")
        if not m:
            rows.append({"file": c["file"], "what": c["what"], "doc": None,
                         "code": want, "ok": False,
                         "note": "KHONG TIM THAY loi khai trong tai lieu (mat dau vet)"})
            continue
        got = list(m.groups())
        ok = got == want
        rows.append({"file": c["file"], "what": c["what"], "doc": got, "code": want,
                     "ok": ok, "note": "" if ok else "tai lieu ghi %s, code la %s"
                     % ("/".join(got), "/".join(want))})
    return rows


def check_tools_documented(root: Path | None = None, docs=("OPERATIONS.md", "README.md",
                                                           "AGENTS.md")) -> list:
    """Moi tool trong `tools/*.py` phai duoc NHAC TEN o it nhat 1 tai lieu van hanh."""
    base = Path(root or ROOT)
    text = "\n".join(_read(base / d) for d in docs)
    rows: list = []
    for p in sorted((base / "tools").glob("*.py")):
        name = p.stem
        if name.startswith("_"):
            continue
        ok = name in text
        rows.append({"file": "tools/%s.py" % name, "what": "tool duoc tai lieu hoa",
                     "doc": None, "code": None, "ok": ok,
                     "note": "" if ok else "khong tai lieu nao trong %s nhac ten" % "/".join(docs)})
    return rows


def _edit_distance(a: str, b: str) -> int:
    """Khoang cach sua (Levenshtein) — du de bat LENH GO SAI ma (`DATA_STALED`)."""
    a, b = str(a), str(b)
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _env_names(root: Path) -> set:
    """Ten bien moi truong THAT (doc tu `config.py`) — de khong bao nham `DATA_TTL_SEC`."""
    text = _read(Path(root) / "config.py")
    return set(re.findall(r'_get\w*\("([A-Z][A-Z0-9_]+)"', text))


def check_codes_documented(root: Path | None = None,
                           docs=("OPERATIONS.md", "REPO_IDEAS.md", "CONTEXT.md",
                                 "README.md", "AGENTS.md", "OPERATIONS.md")) -> list:
    """Ma ly do / ma lop loi duoc NHAC trong tai lieu thi phai TON TAI trong code.

    Muc do:
      * ma LY DO GO SAI (cach 1 ma that <= 2 ky tu) -> `drift`: bao cao theo ma sai thi
        khong bao gio dem duoc, va khong ai biet vi sao;
      * ma LOP LOI cu (vd B-034 co truoc khi lap danh muc) -> `warn` (lich su, khong chan).

    Khong bao nham bien moi truong: ten trong `config.py` (`DATA_TTL_SEC`...) bi loai.
    """
    import bug_catalog as BC
    import reason_codes as RC
    base = Path(root or ROOT)
    text = "\n".join(_read(base / d) for d in docs)
    rows: list = []
    prefixes = {k.upper() for k in RC.KINDS}
    skip = _env_names(base) | set(RC.STATUS_CODES) | {str(s).upper() for s in RC.STATUS_CODES}
    for code in sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", text))):
        if code in RC.CODES or code in skip:
            continue
        if "_" not in code or code.split("_")[0] not in prefixes:
            continue                      # khong phai khuon ma ly do
        near = [c for c in RC.CODES if _edit_distance(c, code) <= 2]
        if near:
            rows.append({"file": "docs", "what": "ma ly do go sai", "level": "drift",
                         "doc": [code], "code": sorted(near), "ok": False,
                         "note": "ma %s khong co; gan nhat la %s"
                                 % (code, ", ".join(sorted(near)))})
    known = {c.get("code") for c in BC.CLASSES}
    for bc in sorted(set(re.findall(r"\bB-\d{3}\b", text))):
        if bc not in known:
            rows.append({"file": "docs", "what": "ma lop loi trong tai lieu", "level": "warn",
                         "doc": [bc], "code": None, "ok": False,
                         "note": "ma %s khong co trong bug_catalog.CLASSES (co the la lich su)"
                                 % bc})
    return rows


def report(root: Path | None = None, claims=CLAIMS) -> dict:
    """Toan bo bao cao drift -> {rows, drift, warn, n, ok}.

    `ok` chi False khi co muc `level='drift'` — canh bao (`warn`) khong chan commit, nhung
    van hien ra de nguoi doc biet.
    """
    rows = (check_claims(claims, root) + check_tools_documented(root)
            + check_codes_documented(root))
    for r in rows:
        r.setdefault("level", "drift")
    drift = [r for r in rows if not r["ok"] and r.get("level") == "drift"]
    warn = [r for r in rows if not r["ok"] and r.get("level") != "drift"]
    return {"rows": rows, "drift": drift, "warn": warn, "n": len(rows), "ok": not drift}


def render(rep: dict) -> str:
    out = ["=== DRIFT TAI LIEU <-> CODE | %d muc | LECH %d | CANH BAO %d ==="
           % (rep["n"], len(rep["drift"]), len(rep.get("warn") or []))]
    for r in rep["drift"]:
        out.append("  [LECH] %-28s %-26s %s" % (r["file"], r["what"], r["note"]))
    for r in rep.get("warn") or []:
        out.append("  [WARN] %-28s %-26s %s" % (r["file"], r["what"], r["note"]))
    if not rep["drift"]:
        out.append("  KET LUAN: tai lieu khop code (so lieu + ten tool + ma deu dung)")
    return "\n".join(out)


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="So khop tai lieu <-> code (drift)")
    ap.add_argument("--check", action="store_true", help="exit 1 neu co muc LECH")
    ap.add_argument("--json", action="store_true", help="in JSON")
    args = ap.parse_args(argv)
    rep = report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(render(rep))
    return 0 if (rep["ok"] or not args.check) else 1


if __name__ == "__main__":
    raise SystemExit(main())

