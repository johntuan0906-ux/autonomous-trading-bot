"""Ma LY DO chuan hoa (reason code) — lop tu vung CHUNG cho journal, eval va golden set.

Vi sao (09/11, tai lieu "Decision Log" phan II + khao sat repo):
- Hien tai moi ly do deu la **van ban tu do** (`reasons: ["..."]`, `reason="tran risk..."`,
  `note="SKIP_RISK..."`). Do that tren `logs/journal.jsonl`: 7071 dong, **0** truong
  `reason_code` ⇒ khong the dem "vi sao bi chan", khong the so sanh 2 phien ban, khong the
  phan loai loi (data / reasoning / policy / tool / execution) mot cach may moc duoc.
- Tai lieu de xuat 7 nhom loi; o day gop thanh 6 nhom du lieu/logic + 1 nhom "decision"
  (TAKE) de cung mot tu vung mo ta ca "vi sao VAO" lan "vi sao KHONG VAO".

Nguyen tac: file nay THUAN TUY (khong doc file, khong mang, khong import module khac)
⇒ dung duoc ca o noi GHI (bot) va noi DOC (tools/eval), va test duoc offline.
B-045: truoc day `classify_text()` khong ton tai nen moi thong ke "ly do chan" deu phai
grep chuoi — sai ngay khi doi cau chu.
"""
from __future__ import annotations

#: 6 nhom loi (data -> execution) + nhom "decision" cho quyet dinh VAO lenh.
KINDS = ("data", "context", "reasoning", "policy", "tool", "execution", "decision")

#: code -> (nhom, mo ta ngan). Ten code IN HOA, on dinh (dung lam khoa trong bao cao).
CODES: dict[str, tuple[str, str]] = {
    # --- data: du lieu vao lenh khong dung duoc ------------------------------
    "DATA_STALE": ("data", "nen gia / tin hieu cu hon TTL cho phep"),
    "DATA_MISSING": ("data", "thieu truong bat buoc (score/ATR/feats...)"),
    "DATA_INVALID": ("data", "gia tri vo ly (<=0, NaN, vuot dai hop le)"),
    "DATA_CONFLICT": ("data", "2 nguon mau thuan (vd equity san vs state)"),
    # --- context: ngu canh dua cho LLM --------------------------------------
    "CTX_TRUNCATED": ("context", "ngu canh bi cat (vuot ngan sach token)"),
    "CTX_NO_EVIDENCE": ("context", "khong co bang chung (lessons rong) de dua ra y kien"),
    "CTX_CONTRADICT": ("context", "ngu canh mau thuan (khung thoi gian nguoc nhau)"),
    # --- reasoning: model/agent ---------------------------------------------
    "LEARN_NEG_EDGE": ("reasoning", "learner du doan edge am (ky vong lo)"),
    "MODEL_UNCALIBRATED": ("reasoning", "model chua qua kiem dinh calibration"),
    "AGENT_ABSTAIN": ("reasoning", "agent tu choi bo phieu (khong du tin hieu)"),
    "AGENT_DISAGREE": ("reasoning", "phieu khong dong thuan (VETO vs ALLOW)"),
    # --- policy: luat cua bot ------------------------------------------------
    "STRATEGY_BLOCKED": ("policy", "strategy nam trong blocklist / dang am"),
    "LESSONS_GATE": ("policy", "to hop (strategy/setup/regime) bi lessons chan"),
    "RISK_CAP": ("policy", "tran tong risk danh muc (MAX_TOTAL_RISK_PCT)"),
    "MAX_POSITIONS": ("policy", "da du so vi the (MAX_POSITIONS)"),
    "DUP_SYMBOL": ("policy", "cap da co vi the"),
    "ENTRIES_PAUSED": ("policy", "cong tam dung vao lenh dang bat"),
    "KILL_SWITCH": ("policy", "kill-switch da trip"),
    "SPREAD_WIDE": ("policy", "spread/phi vuot nguong cho phep"),
    "MIN_NOTIONAL": ("policy", "notional < muc toi thieu cua san"),
    # --- tool: san / provider ------------------------------------------------
    "API_BAN": ("tool", "san chan IP/rate-limit (418/-1003)"),
    "QUOTA_EXCEEDED": ("tool", "provider het quota thang"),
    "API_ERROR": ("tool", "loi API khac (timeout, 5xx, -2015...)"),
    "PROVIDER_DOWN": ("tool", "CLI/provider chet hoac bi cau dao tat"),
    # --- execution: lenh that ------------------------------------------------
    "ORDER_REJECT": ("execution", "san tu choi lenh"),
    "PARTIAL_FILL": ("execution", "khop mot phan"),
    "EQUITY_MISMATCH": ("execution", "equity trong state khac equity tren san"),
    "SL_TP_MISSING": ("execution", "lenh bao ve (SL/TP) khong con tren san"),
    # --- decision ------------------------------------------------------------
    "TAKE": ("decision", "vao lenh (mo vi the)"),
}

#: Dau hieu van ban -> code. So khop case-insensitive, thu tu TU TREN XUONG
#: (cang cu the cang dat truoc: "tran risk" truoc "risk").
_TEXT_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("tran risk", "max_total_risk", "risk cap"), "RISK_CAP"),
    (("single-best-setup", "max positions"), "MAX_POSITIONS"),
    (("duplicate blocked", "already open"), "DUP_SYMBOL"),
    (("strategy_block", "trong blocklist", "dang am (n="), "STRATEGY_BLOCKED"),
    (("lessons", "to hop"), "LESSONS_GATE"),
    (("blocked_learn", "edge am", "ky vong lo"), "LEARN_NEG_EDGE"),
    (("teapot", "-1003", "banned", "way too many"), "API_BAN"),
    (("quota", "exceeded your monthly"), "QUOTA_EXCEEDED"),
    (("kill-switch", "kill switch", "kill_switch"), "KILL_SWITCH"),
    (("tam dung", "entries_pause", "paused"), "ENTRIES_PAUSED"),
    (("spread",), "SPREAD_WIDE"),
    (("notional", "min_notional", "-4164"), "MIN_NOTIONAL"),
    (("equity",), "EQUITY_MISMATCH"),
    (("stale", "cu hon"), "DATA_STALE"),
    (("thieu du lieu", "insufficient", "missing"), "DATA_MISSING"),
    (("parse_error", "invalid"), "DATA_INVALID"),
    (("reject", "-2010", "-2019"), "ORDER_REJECT"),
    (("timeout", "-2015", "http 5"), "API_ERROR"),
    (("abstain", "khong bo phieu"), "AGENT_ABSTAIN"),
)


def known(code: str) -> bool:
    """`code` co trong tu vung chuan khong (dung de validate truoc khi ghi)."""
    return str(code or "") in CODES


def kind_of(code: str) -> str:
    """Nhom loi cua `code`; code la -> 'unknown' (khong nem loi: log khong duoc lam chet bot)."""
    row = CODES.get(str(code or ""))
    return row[0] if row else "unknown"


def codes_of_kind(kind: str) -> list:
    """Danh sach code thuoc 1 nhom (sap theo ten) — dung trong bao cao/eval."""
    return sorted(c for c, (k, _d) in CODES.items() if k == str(kind or ""))


def classify_text(text: str) -> str:
    """Doan code tu van ban tu do (ly do cu trong journal). Khong khop -> ''.

    Chi la cau noi TAM THOI de doc lich su; quyet dinh MOI phai ghi code truc tiep.
    """
    t = str(text or "").lower()
    if not t.strip():
        return ""
    for needles, code in _TEXT_HINTS:
        for nd in needles:
            if nd in t:
                return code
    return ""


def normalize(code: str, text: str = "") -> str:
    """Tra code hop le: uu tien `code` da dung, sau do doan tu `text`, cuoi cung ''."""
    c = str(code or "").strip().upper()
    if known(c):
        return c
    return classify_text(text)
