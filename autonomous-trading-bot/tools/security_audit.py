"""security_audit.py — kiem tra bao cao audit bao mat theo 6 pha cua Cloudflare skill.

Chay:
  python tools\\security_audit.py            # in tong ket
  python tools\\security_audit.py --check    # 1 = co bang chung lech (dung trong chuoi truoc commit)
  python tools\\security_audit.py --json

Vi sao co tool nay (pha 5 "independent record verification" cua Cloudflare skill): bao cao audit viet
bang van xuoi thi 2 tuan sau khong ai biet con dung hay khong. Tool nay KHONG tin van xuoi: moi phat hien
phai kem bang chung MAY KIEM DUOC (`file` + `line` + `pattern`), va no tu doc lai file de xac nhan:
  - `present` : mau phai CON trong file (vd dong code chan loi) -> chong "sua lai roi quen cap nhat bao cao"
  - `absent`  : mau KHONG duoc con (vd dieu kien loi cu) -> chong "lo hong quay lai"
  - `line`+`pattern`: dong bao cao phai dung la dong code that (lech <= 2 dong van tinh, nhung co canh bao)
Kiem soat (`controls`) gom bang chung "khong co sink" bang AST (khong grep, vi grep se khop ca chu thich).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "security" / "findings.json"
REPORT = ROOT / "SECURITY_AUDIT.md"
SEVERITY = ("critical", "high", "medium", "low", "info")
STATUS = ("fixed", "accepted", "needs_validation")
REQUIRED = ("id", "title", "severity", "status", "boundary", "exploit", "impact",
            "evidence", "guard")
PHASES = ("Reconnaissance", "Coverage-led hunting", "Candidate validation",
          "Structured output", "Independent verification", "Reporting")
SHIFT = 2          # so dong lech duoc phep giua bao cao va code
SINKS = ("eval", "exec", "os.system", "pickle.load", "yaml.load")


def load(path=None) -> dict:
    p = Path(path) if path else FINDINGS
    return json.loads(p.read_text(encoding="utf-8"))


def _lines(p: Path) -> list:
    return p.read_text(encoding="utf-8", errors="replace").splitlines()


def check_evidence(ev: dict, root=ROOT) -> list:
    """Tra danh sach loi cua 1 muc bang chung."""
    f = Path(root) / str(ev.get("file") or "")
    if not f.is_file():
        return ["khong thay file bang chung: %s" % ev.get("file")]
    lines = _lines(f)
    errs = []
    if "absent" in ev:
        for i, ln in enumerate(lines, 1):
            if str(ev["absent"]) in ln:
                errs.append("%s:%d con chua mau PHAI BIEN MAT: %r"
                            % (ev["file"], i, ev["absent"]))
        return errs
    if "present" in ev:
        txt = "\n" + "\n".join(lines) + "\n"
        if str(ev["present"]) not in txt:
            errs.append("%s thieu mau bat buoc: %r" % (ev["file"], ev["present"]))
        return errs
    want = str(ev.get("pattern") or "")
    try:
        ln_no = int(ev.get("line") or 0)
    except (TypeError, ValueError):
        ln_no = 0
    if not want or ln_no <= 0:
        return ["bang chung thieu `line`/`pattern`: %r" % (ev,)]
    lo = max(0, ln_no - 1 - SHIFT)
    window = lines[lo:ln_no + SHIFT]
    if any(want in ln for ln in window):
        return []
    hit = [i for i, ln in enumerate(lines, 1) if want in ln]
    if hit:
        return ["%s: bao cao ghi dong %d, mau %r nam o dong %s"
                % (ev["file"], ln_no, want[:60], hit[:3])]
    return ["%s: KHONG con mau %r (dong %d) — code da doi, cap nhat bao cao"
            % (ev["file"], want[:60], ln_no)]


def check_test(ident: str, root=ROOT) -> list:
    """`module.py::Class::test` phai ton tai trong tests/."""
    parts = [x for x in str(ident).split("::") if x]
    if len(parts) < 2:
        return ["test id khong hop le: %r (can module.py::Class::test)" % ident]
    f = Path(root) / "tests" / parts[0]
    if not f.is_file():
        return ["khong thay file test: tests/%s" % parts[0]]
    src = "\n".join(_lines(f))
    name = parts[-1]
    if ("def %s(" % name) not in src:
        return ["tests/%s khong co `def %s`" % (parts[0], name)]
    if len(parts) == 3 and ("class %s(" % parts[1]) not in src:
        return ["tests/%s khong co `class %s`" % (parts[0], parts[1])]
    return []


def _fname(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _fname(node.value)
        return ("%s.%s" % (base, node.attr)) if base else node.attr
    return ""


def ast_hits(root=ROOT, globs=("*.py", "tools/*.py")) -> list:
    """Tim sink thuc thi code trong code san xuat (bo qua loi cu phap)."""
    out = []
    for pat in globs:
        for f in sorted(Path(root).glob(pat)):
            if not f.is_file():
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                name = _fname(n.func)
                if name in SINKS:
                    out.append((str(f.relative_to(Path(root))).replace("\\", "/"),
                                n.lineno, name))
                for kw in n.keywords:
                    if (kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                            and kw.value.value is True):
                        out.append((str(f.relative_to(Path(root))).replace("\\", "/"),
                                    n.lineno, "shell=True"))
    return out


def verify(data: dict = None, root=ROOT) -> dict:
    """Kiem tra toan bo bao cao. Tra {ok, errors, warnings, findings, controls, tests}."""
    data = data if data is not None else load()
    errors: list = []
    warnings: list = []
    seen: set = set()

    finds = list(data.get("findings") or [])
    for it in finds:
        fid = str(it.get("id") or "?")
        if fid in seen:
            errors.append("trung id: %s" % fid)
        seen.add(fid)
        miss = [k for k in REQUIRED if not it.get(k)]
        if miss:
            errors.append("%s thieu truong: %s" % (fid, ", ".join(miss)))
            continue
        if it["severity"] not in SEVERITY:
            errors.append("%s severity la: %s" % (fid, it["severity"]))
        if it["status"] not in STATUS:
            errors.append("%s status la: %s" % (fid, it["status"]))
        if it["status"] == "fixed" and not it.get("tests"):
            errors.append("%s da sua thi PHAI co test chot" % fid)
        if it["status"] == "fixed" and not it.get("bug"):
            warnings.append("%s 'fixed' nhung khong gan ma bug catalog" % fid)
        for ev in it.get("evidence") or []:
            errors += ["%s: %s" % (fid, e) for e in check_evidence(ev, root)]
        for t in it.get("tests") or []:
            errors += ["%s: %s" % (fid, e) for e in check_test(t, root)]

    ctrls = list(data.get("controls") or [])
    for c in ctrls:
        cid = str(c.get("id") or "?")
        scan = c.get("scan") or {}
        if "ast_absent" in scan:
            hits = ast_hits(root, tuple(scan.get("globs") or ("*.py",)))
            for f, line, what in hits:
                errors.append("%s: con sink %s tai %s:%d" % (cid, what, f, line))
        for want in scan.get("present") or []:
            hits = {p: (Path(root) / p) for p in scan.get("globs") or []}
            ok = False
            for p, f in hits.items():
                if f.is_file() and str(want) in "\n" + "\n".join(_lines(f)) + "\n":
                    ok = True
                    break
            if not ok:
                errors.append("%s: khong file nao trong %s chua %r"
                              % (cid, scan.get("globs"), want))

    # Doi chieu voi bao cao van xuoi (chong "bao cao va may lech nhau")
    md = Path(root) / REPORT.name
    if not md.is_file():
        errors.append("khong thay %s" % REPORT.name)
    else:
        txt = "\n".join(_lines(md))
        for ph in PHASES:
            if ph not in txt:
                errors.append("%s: thieu pha %r" % (REPORT.name, ph))
        for it in finds + ctrls:
            iid = str(it.get("id") or "")
            if iid and ("| %s |" % iid) not in txt:
                errors.append("%s: %s khong co trong bang cua bao cao" % (REPORT.name, iid))
        # Chi dem dong cua BANG PHAT HIEN (cot 2 = muc do), khong dem bang khac trong bai
        rows = [ln for ln in txt.splitlines()
                if re.match(r"^\| F-\d+ \| (critical|high|medium|low|info) \|", ln)]
        if len(rows) != len(finds):
            errors.append("%s: bang co %d dong F- nhung JSON co %d phat hien"
                          % (REPORT.name, len(rows), len(finds)))

    n_tests = sum(len(it.get("tests") or []) for it in finds)
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "findings": len(finds), "controls": len(ctrls), "tests": n_tests,
            "by_severity": _by_sev(finds)}


def _by_sev(finds: list) -> dict:
    out: dict = {}
    for it in finds:
        out[it.get("severity", "?")] = out.get(it.get("severity", "?"), 0) + 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kiem tra audit bao mat (6 pha Cloudflare).")
    ap.add_argument("--check", action="store_true", help="loi = ma 1 (chuoi truoc commit)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = verify()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["ok"] else 1
    sev = " · ".join("%s %d" % (k, rep["by_severity"][k])
                     for k in SEVERITY if k in rep["by_severity"])
    print("=== SECURITY AUDIT | %d phat hien | %d kiem soat | %d test chot | %s ==="
          % (rep["findings"], rep["controls"], rep["tests"], sev or "-"))
    for e in rep["errors"]:
        print("  [LECH] %s" % e)
    for w in rep["warnings"]:
        print("  [CANH BAO] %s" % w)
    if rep["ok"]:
        print("  KET LUAN: bang chung khop code + khop SECURITY_AUDIT.md")
    else:
        print("  KET LUAN: %d muc lech — sua bao cao hoac sua code (khong noi nguong)"
              % len(rep["errors"]))
    if args.check:
        return 0 if rep["ok"] else 1
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
