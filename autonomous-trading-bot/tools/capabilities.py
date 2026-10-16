"""Manifest NANG LUC cua bot: tool -> muc dich -> vi du -> test lien quan (doc bang MAY).

    python tools/capabilities.py             # bang cho nguoi doc
    python tools/capabilities.py --json      # cho AGENT (hoi dong/LLM) tu kham pha
    python tools/capabilities.py --check     # CI: tool nao thieu docstring / thieu test

Y tuong lay tu HKUDS/CLI-Anything ("Making ALL Software Agent-Native", 53k sao): moi nang
luc duoc dong goi thanh 1 LENH CLI **tu mo ta duoc** + co harness test rieng, de agent tu
kham pha va goi dung cong cu thay vi doan. Do that trong du an nay: hoi dong/agent chi
"co van" (khong tu goi duoc cong cu nao) va nguoi van hanh phai nho ten ~20 tool. Manifest
nay la buoc 1: LAP BANG tu chinh docstring (khong khai bao tay -> khong lech thuc te).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _first_sentence(doc: str) -> str:
    """Dong dau tien co nghia cua docstring (bo khoang trang, gioi han 160 ky tu)."""
    for ln in str(doc or "").splitlines():
        s = ln.strip()
        if s:
            return s[:160]
    return ""


def _example(doc: str) -> str:
    """Dong vi du dau tien dang `python ...` trong docstring (neu co)."""
    for ln in str(doc or "").splitlines():
        s = ln.strip()
        if s.startswith("python ") or s.startswith("pythonw "):
            return s[:160]
    return ""


def _tests_for(name: str, tests_dir: Path) -> int:
    """So lan `name` duoc nhac trong tests/ (uoc luong do phu test)."""
    n = 0
    try:
        for p in Path(tests_dir).glob("test_*.py"):
            txt = p.read_text(encoding="utf-8", errors="replace")
            n += len(re.findall(r"\b%s\b" % re.escape(name), txt))
    except OSError:
        return 0
    return n


def scan(root=None, tests_dir=None) -> list:
    """Quet `tools/*.py` -> [{name, purpose, example, tests, documented}] (ham THUAN TUY)."""
    root = Path(root or ROOT)
    tools = root / "tools"
    tests = Path(tests_dir) if tests_dir else root / "tests"
    out = []
    for p in sorted(tools.glob("*.py")):
        if p.name.startswith("_"):
            continue
        try:
            doc = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # docstring module = chuoi 3 nhay dau tien
        m = re.search(r'^\s*(?:#.*\n)*\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')',
                      doc, re.S | re.M)
        d = (m.group(1) or m.group(2)) if m else ""
        purpose = _first_sentence(d)
        out.append({"name": p.stem, "purpose": purpose, "example": _example(d),
                    "tests": _tests_for(p.stem, tests), "documented": bool(purpose)})
    return out


def check(items: list) -> dict:
    """Kiem tra ky luat toi thieu: moi tool phai co docstring + duoc test nhac toi."""
    missing_doc = [i["name"] for i in items if not i["documented"]]
    no_test = [i["name"] for i in items if not i["tests"]]
    return {"n": len(items), "missing_doc": missing_doc, "no_test": no_test,
            "ok": not missing_doc}


def main(argv: list | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Manifest nang luc (tool) cua bot")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    items = scan()
    if args.json:
        print(json.dumps({"tools": items, **check(items)}, ensure_ascii=False, indent=1))
        return 0
    if args.check:
        rep = check(items)
        print("=== KIEM TRA MANIFEST: %d tool ===" % rep["n"])
        print("  thieu docstring : %s" % (", ".join(rep["missing_doc"]) or "khong co"))
        print("  khong duoc test : %s" % (", ".join(rep["no_test"]) or "khong co"))
        print("  KET LUAN: %s" % ("OK" if rep["ok"] else "THIEU DOCSTRING"))
        return 0 if rep["ok"] else 1
    print("=== NANG LUC CUA BOT (%d tool) ===" % len(items))
    print("  %-22s %-4s %s" % ("TOOL", "TEST", "MUC DICH"))
    for i in items:
        print("  %-22s %-4s %s" % (i["name"][:22], i["tests"] or "-",
                                   i["purpose"][:96] or "(thieu docstring)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
