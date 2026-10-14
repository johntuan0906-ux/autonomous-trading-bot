"""prompt_guard.py — cong TAT DINH khua du lieu truoc khi vao prompt hoi dong.

    from prompt_guard import sanitize_payload
    clean, findings = sanitize_payload(payload)

Vi sao (14/10): hoi dong LLM la lop **co van**, nhung prompt cua no co the chua du lieu
den tu NGOAI (ten cap, chuoi pattern/regime, ly do dong lenh, sau nay la tieu de tin).
Moi chuoi nhu vay la **du lieu KHONG dang tin**: neu chua chi thi ("bo qua huong dan
tren", "system:", ...) thi model co the nghe theo chu khong phan tich so lieu.

Cach lam (tat dinh, khong LLM — lay y tuong tu phase I cua
`rohitg00/ai-engineering-from-scratch`: prompt-injection detector + constitutional gate):
  * so/bool/None giu nguyen;
  * chuoi: bo ky tu dieu khien, gop khoang trang, **bo mau chi thi** (ignore previous,
    system:, assistant:, <|...|>, ``` ...), bo URL, cat do dai;
  * dict/list: de quy;
  * tra ve `(clean, findings)` — findings de ghi log, KHONG im lang.

KHONG import risk/portfolio/bot; thuan tuy -> test duoc, khong goi mang.
"""
from __future__ import annotations

import re

# Do dai toi da cho 1 chuoi du lieu (du cho enum/ly do ngan, khong du cho "bai giang").
MAX_TEXT = 120
MAX_KEY = 40

# Mau CHI THI thuong dung de lai model (khong phan biet hoa/thuong).
INJECTION_PATTERNS = (
    r"ignore\s+(all\s+|any\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
    r"disregard\s+(all\s+|any\s+)?(previous|above|prior)",
    r"forget\s+(everything|all\s+previous)",
    r"bo\s+qua\s+(moi\s+|tat\s+ca\s+)?(huong\s+dan|chi\s+dan|lenh)\s*(tren|truoc)?",
    r"(system|assistant|user|developer)\s*:",
    r"<\|[^|]{0,40}\|>",
    r"\[\s*(system|inst|/inst)\s*\]",
    r"^\s*#{2,}\s*",
    r"you\s+are\s+now\b",
    r"ban\s+la\s+(mot\s+)?(ai|tro\s+ly|assistant)\b",
    r"new\s+(instructions?|rules?|task)\s*:",
    r"override\s+(the\s+)?(rules?|instructions?|safety)",
    r"act\s+as\s+(if\s+)?(you\s+are\s+)?",
)
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
_URL = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WS = re.compile(r"\s+")
_CODE_FENCE = re.compile(r"```+")


def clean_text(value: str, *, max_len: int = MAX_TEXT) -> tuple:
    """Lam sach 1 chuoi du lieu -> (chuoi_sach, ly_do_bo_bot | '')."""
    s = str(value or "")
    reasons = []
    if _CTRL.search(s):
        s = _CTRL.sub(" ", s)
        reasons.append("control-char")
    if _CODE_FENCE.search(s):
        s = _CODE_FENCE.sub(" ", s)
        reasons.append("code-fence")
    if _URL.search(s):
        s = _URL.sub("[link]", s)
        reasons.append("url")
    if _INJ.search(s):
        s = _INJ.sub("[bo chi thi]", s)
        reasons.append("injection-pattern")
    s = _WS.sub(" ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip() + "..."
        reasons.append("qua-dai")
    return s, ",".join(reasons)


def sanitize_payload(payload: dict, *, max_len: int = MAX_TEXT) -> tuple:
    """Lam sach payload truoc khi dua vao prompt.

    Tra `(clean, findings)`: `findings` = [{"field", "reason", "preview"}] de ghi log —
    nguoi van hanh phai BIET la du lieu ngoai lai da bi cat (khong im lang).
    """
    clean: dict = {}
    findings: list = []
    for k, v in (payload or {}).items():
        key = str(k)[:MAX_KEY]
        if isinstance(v, bool) or v is None or isinstance(v, (int, float)):
            clean[key] = v
            continue
        if isinstance(v, dict):
            sub, sub_f = sanitize_payload(v, max_len=max_len)
            clean[key] = sub
            findings.extend([{**f, "field": "%s.%s" % (key, f["field"])} for f in sub_f])
            continue
        if isinstance(v, (list, tuple)):
            items, sub_f = [], []
            for it in v:
                if isinstance(it, (dict, list, tuple)):
                    sub2, f2 = sanitize_payload({"x": it}, max_len=max_len)
                    items.append(sub2.get("x"))
                    sub_f.extend(f2)
                elif isinstance(it, bool) or it is None or isinstance(it, (int, float)):
                    items.append(it)
                else:
                    txt, why = clean_text(str(it), max_len=max_len)
                    items.append(txt)
                    if why:
                        sub_f.append({"field": key, "reason": why,
                                      "preview": txt[:60]})
            clean[key] = items
            findings.extend(sub_f)
            continue
        txt, why = clean_text(str(v), max_len=max_len)
        clean[key] = txt
        if why:
            findings.append({"field": key, "reason": why, "preview": txt[:60]})
    return clean, findings


def describe(findings: list) -> str:
    """1 dong de ghi log (rong neu khong co gi bi loc)."""
    if not findings:
        return ""
    return "prompt_guard: loc %d truong du lieu ngoai lai (%s)" % (
        len(findings), "; ".join("%s:%s" % (f["field"], f["reason"]) for f in findings[:5]))
