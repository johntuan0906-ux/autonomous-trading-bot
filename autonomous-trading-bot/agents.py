"""agents.py — tang multi-AI agent (Phase 1: CHI CO VAN, offline-testable).

Vi sao thiet ke nhu vay (doc ky truoc khi mo rong):
- Moi quyet dinh TIEN (qty, SL/TP, veto, kill-switch, tran risk) van do cac ham
  TAT DINH quyet dinh (risk.py / portfolio.py / turbo_demo.py). Agent KHONG duoc
  sua chung, khong duoc mo/dong lenh, khong duoc doi trong so.
- Provider INJECTABLE: StubProvider (offline, tat dinh, khong mang) |
  OpenAIProvider | AnthropicProvider (REST qua `requests` co san; thieu key ->
  tu dong quay ve stub). Nho vay: test suite khong bao gio cham mang, va bot van
  chay y nguyen khi chua co API key (Phase 1).
- Moi cau tra loi phai la JSON dung schema {"action", "confidence", "reasons",
  "risk_flags"}; sai/khong doc duoc -> NO_OPINION (fail-open, khong nem loi).
- Guardrail bat buoc: cache TTL, timeout, tran so cuoc goi/ngay, tran chi phi/ngay,
  circuit breaker khi loi lien tiep. Loi -> NO_OPINION, khong bao gio lam chet
  vong lap trading.
- shadow=True (mac dinh Phase 1): quyet dinh chi duoc GHI NHAN vao journal
  (event=AGENT) de do luong, khong anh huong hanh vi bot.

CLI:
    python agents.py --selftest          # chay stub offline + in quyet dinh
    python agents.py --stats             # trang thai ngan sach/chi phi + dem AGENT
"""
from __future__ import annotations

import argparse
import concurrent.futures as _fut
import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field

# Tu nap .env (giong config.py): neu khong, chay `python agents.py ...` hoac import
# rieng module se KHONG thay COPILOT_GITHUB_TOKEN/OPENAI_API_KEY -> provider that
# bao "No authentication information found" (da gap that 01/10/2026).
_DOTENV_LOADED = False
try:  # pragma: no cover - phu thuoc moi truong
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
    _DOTENV_LOADED = True
except Exception:  # noqa: BLE001
    pass

ACTIONS = ("ALLOW", "VETO", "NO_OPINION")
ROLES = ("macro", "critic", "review", "reflect", "arbiter")
# Hoi dong (council) = 2 vong + chu toa: macro -> critic (da doc y kien macro) -> arbiter.
COUNCIL_ROLES = ("macro", "critic", "arbiter")
# Hoi dong NHIEU MODEL THAT (kiem chung qua Copilot CLI headless, 01/10/2026).
# 5 model con lai trong model picker (gpt-5.3-codex, gpt-5.6-luna, gpt-6-luna,
# grok-4.7, mai-code-1.1-flash) van o trang thai cho cap quyen headless -> treo
# roi tu fail-open ve NO_OPINION; KHONG dua vao danh sach mac dinh nay.
COUNCIL_MULTI_MODELS = ("claude-sonnet-5.5", "claude-sonnet-5", "claude-haiku-4.5",
                       "gemini-3.8-flash", "grok-4.6", "kimi-k3", "gpt-5.6-terra")
STATE_PATH = "logs/agent_state.json"
JOURNAL_PATH = "logs/journal.jsonl"
PROPOSALS_PATH = "logs/agent_proposals.jsonl"
# Phase 3: chi cho phep de xuat trong PHAM VI nay — moi thu khac bi tu choi.
PROPOSAL_TYPES = ("block_strategy", "unblock_strategy", "watch_strategy", "none")
PROPOSAL_TARGETS = ("A_TREND_PULLBACK", "B_BREAKOUT_RETEST", "C_LIQ_SWEEP_RECLAIM",
                    "D_RANGE_REVERSAL")
# Tu khoa cam: de xuat cham vao risk/size/SL/TP/leverage => REJECT ngay.
FORBIDDEN_TERMS = ("risk", "size", "qty", "quantity", "sl_", "tp_", "stoploss",
                   "takeprofit", "leverage", "kill", "max_total", "margin",
                   "balance", "capital")

# USD / 1 trieu token (in, out) — uoc luong de chan chi phi, khong phai hoa don.
PRICES: dict = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "stub-rules": (0.0, 0.0),
}
DEFAULT_PRICE = (1.00, 3.00)   # model la -> tinh gia cao cho an toan


def approx_tokens(text) -> int:
    """Uoc luong token (1 token ~ 4 ky tu) — dung cho tran chi phi."""
    return max(1, len(str(text or "")) // 4)


def price_of(model: str) -> tuple:
    m = str(model or "")
    for k, v in PRICES.items():
        if k in m:
            return v
    return DEFAULT_PRICE


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = price_of(model)
    return round(tokens_in / 1e6 * pin + tokens_out / 1e6 * pout, 8)


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _cache_key(role: str, model: str, payload: dict) -> str:
    raw = json.dumps([role, model, payload], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def parse_decision(text: str, *, role: str = "", agent: str = "") -> dict:
    """Doc JSON agent tra ve -> dict chuan hoa. Sai -> NO_OPINION (fail-open).

    Chap nhan ca truong hop model tra ve van ban co JSON lan trong
    (lay doan {...} dau tien). Khong bao gio nem loi.
    """
    out = {"action": "NO_OPINION", "confidence": 0.0, "reasons": [],
           "risk_flags": [], "parse": "fail"}
    raw = str(text or "").strip()
    if not raw:
        return out
    data = None
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        i, j = raw.find("{"), raw.rfind("}")
        if 0 <= i < j:
            try:
                data = json.loads(raw[i:j + 1])
            except Exception:  # noqa: BLE001
                data = None
    if not isinstance(data, dict):
        return out
    act = str(data.get("action") or data.get("verdict") or "").strip().upper()
    act = act.replace(" ", "_")
    if act not in ACTIONS:
        act = {"BLOCK": "VETO", "BLOCKED": "VETO", "NO": "VETO", "YES": "ALLOW",
               "PASS": "ALLOW", "HOLD": "NO_OPINION", "NONE": "NO_OPINION"}.get(act,
                                                                               "NO_OPINION")
    reasons = data.get("reasons") or data.get("reason") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    flags = data.get("risk_flags") or data.get("flags") or []
    if isinstance(flags, str):
        flags = [flags]
    return {
        "action": act,
        "confidence": max(0.0, min(1.0, _f(data.get("confidence"), 0.0))),
        "reasons": [str(x)[:160] for x in list(reasons)[:5]],
        "risk_flags": [str(x)[:60] for x in list(flags)[:6]],
        "parse": "ok",
        "role": role, "agent": agent,
    }


@dataclass
class Decision:
    """Ket qua 1 lan 'xin y kien' agent (chi de doc/ghi nhan)."""

    role: str
    agent: str
    action: str = "NO_OPINION"
    confidence: float = 0.0
    reasons: list = field(default_factory=list)
    risk_flags: list = field(default_factory=list)
    provider: str = "stub"
    model: str = ""
    shadow: bool = True
    cache_hit: bool = False
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    ts: float = field(default_factory=time.time)
    note: str = ""
    # Van ban goc tu provider (cat bot) — Phase 3 can doc lai JSON de xuat.
    raw_text: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---- Provider (injectable) -----------------------------------------------------

class StubProvider:
    """Provider OFFLINE tat dinh — dung luat don gian, khong goi mang.

    Vai tro: (1) cho test suite chay khong can key/mang; (2) la phuong an du phong
    khi thieu key (Phase 2) => van co y kien 'co ly' thay vi im lang.
    """

    name = "stub"

    def __init__(self, model: str = "stub-rules"):
        self.model = model
        self.calls = 0

    def complete(self, system: str, user: str, *, timeout: float = 5.0) -> dict:
        self.calls += 1
        feats: dict = {}
        i, j = str(user).find("{"), str(user).rfind("}")
        if 0 <= i < j:
            try:
                feats = json.loads(str(user)[i:j + 1]) or {}
            except Exception:  # noqa: BLE001
                feats = {}
        role = str(feats.get("role") or "")
        news = _f(feats.get("news_score"))
        urg = _i(feats.get("urgent_bearish"))
        rsi = _f(feats.get("rsi"), 50.0)
        atr_pct = _f(feats.get("atr_pct"))
        alpha = _f(feats.get("alpha"))
        direction = str(feats.get("direction") or "").upper()
        flags: list = []
        action, conf, why = "NO_OPINION", 0.0, []

        if news <= -0.5:
            action, conf = "VETO", min(0.9, 0.5 + abs(news) / 2)
            why.append(f"news_score {news:+.2f} rat tieu cuc")
            flags.append("macro_negative")
        if role == "macro" and urg >= 20:
            action, conf = "VETO", max(conf, 0.7)
            why.append(f"{urg} tin khan cap vi mo")
            flags.append("urgent_macro")
        if role == "critic":
            if direction == "LONG" and rsi >= 75:
                action, conf = "VETO", max(conf, 0.5)
                why.append(f"LONG nhung RSI {rsi:.0f} qua mua")
                flags.append("overbought")
            if direction == "SHORT" and rsi <= 25:
                action, conf = "VETO", max(conf, 0.5)
                why.append(f"SHORT nhung RSI {rsi:.0f} qua ban")
                flags.append("oversold")
            if atr_pct >= 0.05:
                action, conf = "VETO", max(conf, 0.5)
                why.append(f"ATR {atr_pct:.1%} bien dong qua cao")
                flags.append("high_volatility")
            if abs(alpha) < 0.06:
                why.append(f"alpha {alpha:+.3f} qua mong")
        if role == "review":
            r_mult = _f(feats.get("r_multiple"))
            won = bool(feats.get("won"))
            if won and r_mult >= 0.5:
                action, conf = "ALLOW", 0.6
                why.append(f"thang {r_mult:+.2f}R — setup nay nen uu tien lap lai")
            elif (not won) and r_mult <= -0.9:
                action, conf = "VETO", 0.6
                why.append(f"thua {r_mult:+.2f}R (SL day du) — tranh lap lai setup tuong tu")
            else:
                why.append(f"ket qua {r_mult:+.2f}R — chua du de ket luan")
        if role == "reflect":
            st = feats.get("by_strategy") or {}
            for tgt, sv in st.items():
                n = _i(sv.get("n"))
                avg = _f(sv.get("avg_r"))
                if n >= _i(feats.get("reflect_min_n"), 20) and avg <= -0.05:
                    action, conf = "VETO", 0.6
                    why.append(f"{tgt}: n={n}, avgR={avg:+.3f} -> de xuat block_strategy")
                    flags.append("propose_block:" + str(tgt))
            if action == "NO_OPINION":
                why.append("khong nhom nao du bang chung am de de xuat")
        if action == "NO_OPINION" and news >= 0.2 and abs(alpha) >= 0.1:
            action, conf = "ALLOW", 0.5
            why = [f"news {news:+.2f} ho tro, alpha {alpha:+.3f}"]
        if role == "reflect":
            props = [{"type": "block_strategy", "target": f.split(":", 1)[1],
                      "reason": w, "evidence": {}}
                     for f, w in zip(flags, why)
                     if str(f).startswith("propose_block:")]
            text = json.dumps({"proposals": props, "confidence": round(conf, 2),
                               "reasons": why or ["khong de xuat gi"]},
                              ensure_ascii=False)
        else:
            text = json.dumps({"action": action, "confidence": round(conf, 2),
                               "reasons": why or ["khong du du lieu de ket luan"],
                               "risk_flags": flags}, ensure_ascii=False)
        return {"text": text, "tokens_in": approx_tokens(system + user),
                "tokens_out": approx_tokens(text)}
# ---- Phase 3: de xuat chinh strategy (PHAI qua gate TAT DINH) -----------------

def parse_proposals(text: str, role: str = "reflect") -> dict:
    """Doc JSON de xuat tu agent -> {"proposals": [...], "reasons", "confidence"}.

    Chap nhan JSON lan trong van ban; moi proposal duoc chuan hoa ve
    {"type", "target", "value", "reason", "evidence"}. Khong bao gio nem loi.
    """
    out = {"proposals": [], "reasons": [], "confidence": 0.0, "parse": "fail"}
    raw = str(text or "").strip()
    if not raw:
        return out
    data = None
    try:
        data = json.loads(raw)
    except Exception:  # noqa: BLE001
        i, j = raw.find("{"), raw.rfind("}")
        if 0 <= i < j:
            try:
                data = json.loads(raw[i:j + 1])
            except Exception:  # noqa: BLE001
                data = None
    if not isinstance(data, dict):
        return out
    props = data.get("proposals") or data.get("proposal") or []
    if isinstance(props, dict):
        props = [props]
    norm: list = []
    for p in list(props)[:10]:
        if isinstance(p, str):
            norm.append({"type": p.strip().lower(), "target": "", "value": None,
                         "reason": "", "evidence": {}})
            continue
        if not isinstance(p, dict):
            continue
        norm.append({
            "type": str(p.get("type") or p.get("action") or "").strip().lower(),
            "target": str(p.get("target") or p.get("strategy") or "").strip().upper(),
            "value": p.get("value"),
            "reason": str(p.get("reason") or "")[:200],
            "evidence": p.get("evidence") if isinstance(p.get("evidence"), dict) else {},
        })
    reasons = data.get("reasons") or []
    if isinstance(reasons, str):
        reasons = [reasons]
    return {"proposals": norm,
            "reasons": [str(x)[:200] for x in list(reasons)[:5]],
            "confidence": max(0.0, min(1.0, _f(data.get("confidence"), 0.0))),
            "parse": "ok", "role": role}


def build_digest(journal: str = JOURNAL_PATH, blocked=()) -> dict:
    """Tong hop hieu qua THEO STRATEGY (tat dinh) lam du lieu cho agent phan tich.

    Dung dung cach ghep cap cua monitor_report (OPEN+CLOSE theo FIFO) de so lieu
    khop bao cao; KHONG gui du lieu tai khoan / thong tin nhay cam.
    """
    try:
        from monitor_report import load_journal, match_pairs
        opens, closes = load_journal(journal)
        pairs, still = match_pairs(opens, closes)
    except Exception:  # noqa: BLE001
        return {"n": 0, "by_strategy": {}, "current_block": list(blocked),
                "note": "loi doc journal"}
    agg: dict = {}
    dirs: dict = {}
    for o, c in pairs:
        s = str((o or {}).get("strategy") or "NONE").upper()
        a = agg.setdefault(s, {"n": 0, "wins": 0, "sum_r": 0.0})
        a["n"] += 1
        a["wins"] += 1 if c.get("won") else 0
        a["sum_r"] = round(a["sum_r"] + _f(c.get("r")), 4)
        d = str(c.get("direction") or "?").upper()
        dd = dirs.setdefault(d, {"n": 0, "sum_r": 0.0})
        dd["n"] += 1
        dd["sum_r"] = round(dd["sum_r"] + _f(c.get("r")), 4)
    by_strat = {k: {"n": v["n"], "wr": round(100.0 * v["wins"] / max(v["n"], 1), 1),
                    "avg_r": round(v["sum_r"] / max(v["n"], 1), 3), "sum_r": v["sum_r"]}
                for k, v in agg.items()}
    sums = [v["sum_r"] for v in agg.values()]
    return {"n": sum(v["n"] for v in agg.values()),
            "sum_r": round(sum(sums), 3),
            "by_strategy": by_strat,
            "by_direction": {k: {"n": v["n"], "avg_r": round(v["sum_r"] / max(v["n"], 1), 3)}
                             for k, v in dirs.items()},
            "current_block": [str(x) for x in (blocked or [])],
            "open_positions": len(still)}


def validate_proposals(props: list, digest: dict, *, min_n: int = 20,
                       min_abs_r: float = 0.05, max_accept: int = 2) -> list:
    """GATE TAT DINH cho de xuat (ly do Phase 3 an toan).

    Agent co the noi gi cung duoc, nhung de xuat chi duoc CHAP NHAN khi:
      * type nam trong PROPOSAL_TYPES (khac -> REJECT);
      * khong cham risk/size/SL/TP/leverage (FORBIDDEN_TERMS -> REJECT);
      * target hop le;
      * block:  n >= min_n VA avg_r <= -min_abs_r;
      * unblock: dang bi chan VA (avg_r >= +min_abs_r hoac n < 5);
      * toi da max_accept de xuat duoc chap nhan moi lan.
    """
    out: list = []
    accepted = 0
    stats = (digest or {}).get("by_strategy") or {}
    blocked = [str(x).upper() for x in (digest or {}).get("current_block") or []]
    for p in props or []:
        rec = dict(p)
        typ = str(p.get("type") or "").lower()
        tgt = str(p.get("target") or "").upper()
        blob = json.dumps(p, ensure_ascii=False).lower()
        st = stats.get(tgt) or {}
        n = _i(st.get("n"))
        avg = _f(st.get("avg_r"))
        why = ""
        if typ not in PROPOSAL_TYPES:
            why = f"type '{typ}' khong nam trong allowlist {PROPOSAL_TYPES}"
        elif any(t in blob for t in FORBIDDEN_TERMS):
            why = "de xuat cham vao risk/size/SL/TP/leverage (ngoai pham vi Phase 3)"
        elif typ in ("block_strategy", "unblock_strategy") and tgt not in PROPOSAL_TARGETS:
            why = f"target '{tgt}' khong hop le"
        elif typ == "block_strategy" and n < min_n:
            why = f"chua du mau: n={n} < {min_n}"
        elif typ == "block_strategy" and avg > -min_abs_r:
            why = f"avgR {avg:+.3f} chua du am (can <= -{min_abs_r})"
        elif typ == "block_strategy" and tgt in blocked:
            why = "target dang bi chan san"
        elif typ == "unblock_strategy" and tgt not in blocked:
            why = "target khong bi chan -> khong co gi de mo"
        elif typ == "unblock_strategy" and n >= 5 and avg < min_abs_r:
            why = f"avgR {avg:+.3f} chua du duong (can >= +{min_abs_r})"
        elif typ in ("block_strategy", "unblock_strategy") and accepted >= max_accept:
            why = f"vuot tran {max_accept} de xuat duoc chap nhan moi lan"
        rec["status"] = "REJECTED" if why else "ACCEPTED"
        rec["why"] = why or ("du bang chung, trong pham vi cho phep"
                             if typ != "none" else "khong de xuat gi")
        if not why and typ != "none":
            accepted += 1
        rec["digest_evidence"] = {"n": n, "avg_r": avg}
        out.append(rec)
    return out


class OpenAIProvider:
    """REST /v1/chat/completions — KHONG can SDK `openai` (dung `requests`)."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "",
                 base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", base_url)

    def complete(self, system: str, user: str, *, timeout: float = 6.0) -> dict:
        if not self.api_key:
            raise RuntimeError("thieu OPENAI_API_KEY")
        import requests  # da co trong dependencies
        r = requests.post(
            self.base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + self.api_key,
                     "Content-Type": "application/json"},
            json={"model": self.model, "temperature": 0.0, "max_tokens": 160,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]},
            timeout=timeout)
        r.raise_for_status()
        js = r.json()
        usage = js.get("usage") or {}
        return {"text": str((js.get("choices") or [{}])[0].get("message", {})
                            .get("content") or "").strip(),
                "tokens_in": _i(usage.get("prompt_tokens"), approx_tokens(system + user)),
                "tokens_out": _i(usage.get("completion_tokens"), 60)}


class AnthropicProvider:
    """REST /v1/messages — KHONG can SDK `anthropic` (dung `requests`)."""

    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku", api_key: str = "",
                 base_url: str = "https://api.anthropic.com/v1"):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", base_url)

    def complete(self, system: str, user: str, *, timeout: float = 6.0) -> dict:
        if not self.api_key:
            raise RuntimeError("thieu ANTHROPIC_API_KEY")
        import requests  # da co
        r = requests.post(
            self.base_url.rstrip("/") + "/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json={"model": self.model, "max_tokens": 160, "temperature": 0.0,
                  "system": system, "messages": [{"role": "user", "content": user}]},
            timeout=timeout)
        r.raise_for_status()
        js = r.json()
        usage = js.get("usage") or {}
        parts = js.get("content") or []
        txt = "".join(str(p.get("text") or "") for p in parts if isinstance(p, dict))
        return {"text": txt.strip(),
                "tokens_in": _i(usage.get("input_tokens"), approx_tokens(system + user)),
                "tokens_out": _i(usage.get("output_tokens"), 60)}


# ---- Phase 2 provider: dung subscription Copilot (khong can API key rieng) ----

# Shim do extension Copilot Chat dat vao PATH khi CHUA cai CLI that: no hoi
# "Install GitHub Copilot CLI? (y/N)" -> neu khong phat hien se TREO bot. Chan som.
_SHIM_MARKS = ("Cannot find GitHub Copilot CLI", "Install GitHub Copilot CLI?")
CLI_HINT = ("chay `npm install -g @github/copilot` roi `copilot login` "
            "(hoac dat COPILOT_GITHUB_TOKEN = PAT v2 co quyen 'Copilot Requests')")


def _subprocess_runner(cmd: list, timeout: float, cwd=None, env=None) -> tuple:
    """Chay lenh ngoai (injectable de test khong can subprocess that).

    stdin=DEVNULL -> CLI khong the hoi interactive => khong the treo bot.
    encoding='utf-8' + errors='replace': CLI (Copilot) tra van ban UTF-8 (tieng
    Viet, emoji...); mac dinh cua Windows la cp1252 -> tung gay UnicodeDecodeError
    lam hong ca luot vote (da gap that 01/10/2026).

    (05/10) creationflags=CREATE_NO_WINDOW tren Windows: bot chay duoi pythonw
    (KHONG co console) nen khi spawn con (node/copilot CLI), Windows tu mo 1 cua so
    console cho con -> nguoi dung thay "pop-up node" nhay len roi bien mat moi lan
    co vote. Flag nay cho con chay ngam, khong con cua so nao.
    """
    import subprocess
    import sys
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                       encoding="utf-8", errors="replace", **kwargs)
    return p.returncode, p.stdout or "", p.stderr or ""


def _extract_text(raw) -> str:
    """Lay phan van ban tu output CLI/bridge (JSON, JSONL hoac text thuong).

    Quy uoc:
      * JSON co field van ban ("response"/"text"/...) -> tra field do;
      * JSON la QUYET DINH (co "action"/"verdict") -> tra nguyen chuoi JSON;
      * JSONL (copilot --output-format json: moi dong 1 JSON) -> lay dong CUOI
        co field van ban / quyet dinh;
      * JSON khac (vi du {} rong) -> "" (provider se coi la loi).
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    if "\n" in s:                      # JSONL / log lan van ban: quet dong bat dau bang {
        jsonish = [l.strip() for l in s.splitlines() if l.strip().startswith("{")]
        if jsonish:
            for line in reversed(jsonish):
                t = _extract_text(line)
                if t:
                    return t
            return ""                  # co JSON nhung khong co van ban -> coi nhu rong
        return s                       # van ban nhieu dong thuan -> giu nguyen
    if s.startswith("{"):
        try:
            js = json.loads(s)
        except Exception:  # noqa: BLE001
            return s
        for k in ("response", "text", "content", "message", "output", "result",
                  "data"):
            v = js.get(k) if isinstance(js, dict) else None
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, dict):
                for k2 in ("text", "content"):
                    if isinstance(v.get(k2), str) and v[k2].strip():
                        return v[k2].strip()
        if isinstance(js, dict) and ("action" in js or "verdict" in js
                                     or "proposals" in js or "proposal" in js):
            return s          # JSON quyet dinh HOAC JSON de xuat (Phase 3)
        return ""
    return s


def _resolve_exe(name: str) -> str:
    """Tim duong dan THAT cua executable (vd `node`).

    Vi sao: supervisor spawn turbo bang pythonw -> tien trinh con KHONG co PATH day
    du (khong thay `C:\\Program Files\\nodejs`) => `node` bao WinError 2, agent luon
    NO_OPINION moi vong. Thu tu: duong dan da cho -> PATH -> vi tri chuan Windows.
    """
    p = str(name or "").strip()
    if not p:
        return p
    if os.sep in p or (os.altsep and os.altsep in p):
        return p                                  # da la duong dan (tuong doi/tuyet doi)
    found = shutil.which(p)
    if found:
        return found
    pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
    appdata = os.environ.get("APPDATA") or ""
    for cand in (os.path.join(pf, "nodejs", p + ".exe"),
                 os.path.join(appdata, "npm", p + ".cmd"),
                 os.path.join(appdata, "npm", p)):
        if cand and os.path.exists(cand):
            return cand
    return p


def _split_cmd(s: str) -> list:
    """Tach chuoi lenh thanh argv, TON TRONG nhay kep (duong dan Windows co space).

    Vi sao can: `AGENT_COPILOT_BIN=node C:\\...\\npm-loader.js` chay duoc khi co
    PATH day du, nhung tien trinh pythonw (do supervisor spawn) khong co `node`
    trong PATH -> loi `[WinError 2] The system cannot find the file specified`
    (agent luon NO_OPINION). Dat duong dan TUYET DOI thi lai co khoang trang
    ("C:\\Program Files\\nodejs\\node.exe") -> phai co nhay kep, va str.split()
    se cat sai. Ham nay cat dung ca hai truong hop.
    """
    out: list = []
    cur = ""
    q = False
    for ch in str(s or ""):
        if ch == '"':
            q = not q
            continue
        if ch == " " and not q:
            if cur:
                out.append(cur)
                cur = ""
            continue
        cur += ch
    if cur:
        out.append(cur)
    return out


class CopilotCliProvider:
    """GitHub Copilot CLI (chinh thuc) o che do PROGRAMMATIC: `copilot -p <prompt>`.

    Uu diem: dung subscription Copilot (Pro/Business...) — khong can API key rieng,
    khong can SDK openai/anthropic. Nhuoc diem: ton "AI credits" cua goi, va day la
    CLI agentic nen phai chan tool + timeout chat.

    Bao mat: cwd = thu muc tam (khong quet repo), stdin dong, timeout cung.
    """

    name = "copilot_cli"

    def __init__(self, model: str = "", bin_path: str = "copilot",
                 args: list | None = None, runner=None, cwd: str | None = None,
                 env: dict | None = None):
        self.model = model or ""
        # bin_path co the gom NHIEU token: "node C:\\...\\npm-loader.js" hoac
        # duong dan tuyet doi co khoang trang: "\"C:\\Program Files\\nodejs\\node.exe\" C:\\..".
        # Vi sao can: tren Windows, `copilot.cmd` (wrapper cua npm) chuyen tiep
        # tham so qua cmd.exe -> DAU NGOAC KEP trong prompt JSON bi pha; goi thang
        # `node npm-loader.js` thi argv duoc truyen nguyen ven.
        self._base = _split_cmd(bin_path) or ["copilot"]
        self._base[0] = _resolve_exe(self._base[0])
        self.bin = self._base[0]
        self.args = list(args or ["-p", "{prompt}"])
        self._runner = runner or _subprocess_runner
        self.cwd = cwd
        self.env = env

    def _build_cmd(self, prompt: str) -> list:
        """Thay {prompt}/{model} bang replace (khong dung format -> tranh vo JSON {})."""
        out: list = []
        has_model_flag = False
        for a in self.args:
            a = str(a)
            if "{prompt}" in a:
                out.append(a.replace("{prompt}", prompt))
            elif "{model}" in a:
                out.append(a.replace("{model}", self.model))
                has_model_flag = True
            else:
                if a in ("--model", "-m"):
                    has_model_flag = True
                out.append(a)
        if self.model and not has_model_flag:
            out += ["--model", self.model]
        return list(self._base) + out

    def complete(self, system: str, user: str, *, timeout: float = 20.0) -> dict:
        prompt = f"{system}\n\n{user}"
        cmd = self._build_cmd(prompt)
        rc, out, err = self._runner(cmd, timeout, cwd=self.cwd, env=self.env)
        blob = f"{out}\n{err}"
        if any(m in blob for m in _SHIM_MARKS):
            raise RuntimeError(f"Copilot CLI chua duoc cai that (chi co shim): {CLI_HINT}")
        if rc != 0 and not str(out).strip():
            raise RuntimeError(f"copilot CLI rc={rc}: {str(err).strip()[:200]}")
        text = _extract_text(out)
        if not text:
            raise RuntimeError(f"copilot CLI khong tra van ban (rc={rc}): "
                               f"{str(err).strip()[:160]}")
        return {"text": text, "tokens_in": approx_tokens(prompt),
                "tokens_out": approx_tokens(text)}


class VscodeLmProvider:
    """Cau noi toi VS Code Language Model API (`vscode.lm`) qua bridge localhost.

    Extension `vscode_lm_bridge/` (kem repo) chay trong VS Code va goi
    `vscode.lm.selectChatModels()` -> dung subscription Copilot cua ban. Python chi
    POST JSON toi 127.0.0.1 => khong can SDK, khong can API key.

    Luu y (tai lieu VS Code): API nay co rate-limit, VS Code hien thi ro extension
    nao dung model nao, va khong nen dung cho integration test.
    """

    name = "vscode_lm"

    def __init__(self, url: str = "http://127.0.0.1:8765/complete", token: str = "",
                 model: str = "", http_fn=None):
        self.url = url
        self.token = token
        self.model = model or ""
        self._http = http_fn or self._requests_post

    @staticmethod
    def _requests_post(url: str, payload: dict, headers: dict, timeout: float) -> dict:
        import requests
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def complete(self, system: str, user: str, *, timeout: float = 8.0) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        js = self._http(self.url, {"system": system, "prompt": user,
                                   "model": self.model}, headers, timeout)
        text = _extract_text(json.dumps(js, ensure_ascii=False)
                             if isinstance(js, dict) else str(js))
        if not text:
            raise RuntimeError("bridge vscode_lm tra rong")
        return {"text": text, "tokens_in": approx_tokens(system + user),
                "tokens_out": approx_tokens(text)}


class OpenAICompatProvider:
    """Endpoint 'OpenAI-compatible' bat ky (Azure/OpenRouter/Ollama/vLLM...).

    Dung khi muon BYOK (base_url + key + model tu env). Khong lien quan Copilot.
    """

    name = "openai_compatible"

    def __init__(self, model: str = "", api_key: str = "", base_url: str = ""):
        self.model = model or os.getenv("AGENT_COMPAT_MODEL", "")
        self.api_key = (api_key or os.getenv("AGENT_COMPAT_API_KEY")
                        or os.getenv("OPENAI_API_KEY", ""))
        self.base_url = (base_url or os.getenv("AGENT_COMPAT_BASE_URL")
                         or os.getenv("OPENAI_BASE_URL", ""))

    def complete(self, system: str, user: str, *, timeout: float = 8.0) -> dict:
        if not self.base_url:
            raise RuntimeError("thieu AGENT_COMPAT_BASE_URL")
        if not self.model:
            raise RuntimeError("thieu AGENT_COMPAT_MODEL")
        import requests
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        r = requests.post(self.base_url.rstrip("/") + "/chat/completions",
                          headers=headers,
                          json={"model": self.model, "temperature": 0.0,
                                "max_tokens": 160,
                                "messages": [{"role": "system", "content": system},
                                             {"role": "user", "content": user}]},
                          timeout=timeout)
        r.raise_for_status()
        js = r.json()
        usage = js.get("usage") or {}
        txt = str((js.get("choices") or [{}])[0].get("message", {}).get("content") or "")
        return {"text": txt.strip(),
                "tokens_in": _i(usage.get("prompt_tokens"), approx_tokens(system + user)),
                "tokens_out": _i(usage.get("completion_tokens"), 60)}




_PROVIDERS = {"stub": StubProvider, "openai": OpenAIProvider,
              "anthropic": AnthropicProvider, "copilot_cli": CopilotCliProvider,
              "vscode_lm": VscodeLmProvider, "openai_compatible": OpenAICompatProvider}


def build_provider(cfg=None, log=None):
    """Tao provider theo `cfg.agent_provider`. Loi/thieu key -> stub (fail-open).

    'copilot_cli' va 'vscode_lm' KHONG can API key (dung subscription Copilot);
    chung chi can CLI da cai / bridge dang chay — neu khong, loi duoc bat o
    `vote()` va tra NO_OPINION (bot van chay binh thuong).
    """
    name = str(getattr(cfg, "agent_provider", "stub") or "stub").lower()
    model = str(getattr(cfg, "agent_model", "") or "")
    if name in ("copilot_cli", "vscode_lm"):
        try:
            if name == "copilot_cli":
                args = _split_cmd(getattr(cfg, "agent_copilot_args", "")) or None
                return CopilotCliProvider(
                    model=model, bin_path=str(getattr(cfg, "agent_copilot_bin",
                                                      "copilot") or "copilot"),
                    args=args)
            return VscodeLmProvider(
                url=str(getattr(cfg, "agent_vscode_lm_url",
                                "http://127.0.0.1:8765/complete")),
                token=str(getattr(cfg, "agent_vscode_lm_token", "") or ""),
                model=model)
        except Exception as e:  # noqa: BLE001
            if log:
                log.warning("agents: khong tao duoc provider %s (%s) -> stub", name, e)
            return StubProvider()
    if name == "openai_compatible":
        try:
            p = OpenAICompatProvider(model=model)
            if not p.base_url or not p.model:
                if log:
                    log.warning("agents: openai_compatible thieu base_url/model -> stub")
                return StubProvider()
            return p
        except Exception as e:  # noqa: BLE001
            if log:
                log.warning("agents: openai_compatible loi (%s) -> stub", e)
            return StubProvider()
    cls = _PROVIDERS.get(name)
    if cls is None or cls is StubProvider:
        return StubProvider(model=model or "stub-rules")
    try:
        default_model = "gpt-4o-mini" if name == "openai" else "claude-3-5-haiku"
        p = cls(model=model or default_model)
        if not getattr(p, "api_key", ""):
            if log:
                log.warning("agents: %s thieu API key -> dung stub offline", name)
            return StubProvider()
        return p
    except Exception as e:  # noqa: BLE001
        if log:
            log.warning("agents: khong tao duoc provider %s (%s) -> stub", name, e)
        return StubProvider()

# ---- Ngan sach / circuit breaker ----------------------------------------------

class AgentBudget:
    """Tran cuoc goi + chi phi theo ngay (UTC), circuit breaker khi loi lien tiep.

    State luu file (mac dinh logs/agent_state.json) de cuoc goi va chi phi KHONG
    bi reset khi supervisor spawn lai (giong kill-switch cua risk.py).
    """

    def __init__(self, path: str = STATE_PATH, daily_calls: int = 200,
                 daily_budget_usd: float = 1.0, max_errors: int = 5,
                 now_fn=time.time):
        self.path = path
        self.daily_calls = max(1, int(daily_calls))
        self.daily_budget_usd = max(0.0, float(daily_budget_usd))
        self.max_errors = max(1, int(max_errors))
        self._now = now_fn
        self.state = self._load()
        self._roll()

    # -- state
    def _load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001
            return {}

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except Exception:  # noqa: BLE001
            pass

    def day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self._now()))

    def _roll(self) -> None:
        """Sang ngay moi -> reset calls/cost/errors/disabled (KHONG reset khi cung ngay)."""
        if str(self.state.get("day")) != self.day():
            self.state = {"day": self.day(), "calls": 0, "cost_usd": 0.0,
                          "errors": 0, "disabled": "", "last_ts": 0.0}
            self.save()

    # -- queries
    def calls(self) -> int:
        self._roll()
        return _i(self.state.get("calls"))

    def cost(self) -> float:
        self._roll()
        return _f(self.state.get("cost_usd"))

    def disabled(self) -> str:
        self._roll()
        return str(self.state.get("disabled") or "")

    def can_spend(self, est_cost: float = 0.0) -> tuple:
        """(ok, ly_do). ok=False thi KHONG goi provider."""
        self._roll()
        if self.disabled():
            return False, f"agent dang TAT: {self.disabled()}"
        if self.calls() >= self.daily_calls:
            return False, f"het tran cuoc goi/ngay ({self.daily_calls})"
        if self.cost() + max(0.0, float(est_cost)) > self.daily_budget_usd:
            return False, (f"het ngan sach/ngay (${self.cost():.4f}/"
                           f"${self.daily_budget_usd:.2f})")
        return True, ""

    # -- mutations
    def note(self, *, cost: float = 0.0, ok: bool = True, reason: str = "") -> None:
        self._roll()
        self.state["calls"] = self.calls() + 1
        self.state["cost_usd"] = round(self.cost() + max(0.0, float(cost)), 8)
        self.state["last_ts"] = self._now()
        if ok:
            self.state["errors"] = 0
        else:
            self.state["errors"] = _i(self.state.get("errors")) + 1
            if self.state["errors"] >= self.max_errors:
                self.state["disabled"] = f"loi lien tiep {self.state['errors']} lan ({reason})"[:120]
        self.save()

    def disable(self, reason: str) -> None:
        self._roll()
        self.state["disabled"] = str(reason)[:120]
        self.save()

    def enable(self) -> None:
        self._roll()
        self.state["disabled"] = ""
        self.state["errors"] = 0
        self.save()

    def snapshot(self) -> dict:
        self._roll()
        return dict(self.state)


# ---- Prompt ----------------------------------------------------------------

_SYSTEM = {
    "macro": ("Ban la chuyen gia vi mo cho crypto futures. Doc du lieu tin tuc/chi so "
              "duoc cho va tra ve DUY NHAT 1 JSON: {\"action\":\"ALLOW|VETO|NO_OPINION\","
              "\"confidence\":0..1,\"reasons\":[..],\"risk_flags\":[..]}. "
              "Chi VETO khi co ly do vi mo ro rang (tin khan cap / chi so xau)."),
    "critic": ("Ban la nguoi phan bien setup giao dich. Voi du lieu nen/dong luong duoc "
               "cho, chi ra vi sao lenh nay CO THE THUA. Neu payload co 'peer' (y kien "
               "cua agent khac), hay noi RO ban DONG Y hay PHAN DOI va vi sao. "
               "Tra ve DUY NHAT 1 JSON: "
               "{\"action\":\"ALLOW|VETO|NO_OPINION\",\"confidence\":0..1,"
               "\"reasons\":[..],\"risk_flags\":[..]}. Khong bia so lieu."),
    "arbiter": ("Ban la CHU TOA hoi dong (macro + critic da cho y kien trong payload "
                "['council']). Nhiem vu: quyet dinh CUOI CUNG cho lenh nay, co tinh den "
                "ca hai y kien va muc do dong thuan. Uu tien bao toan von: neu co ly do "
                "rui ro ro rang thi VETO. Tra ve DUY NHAT 1 JSON: "
                "{\"action\":\"ALLOW|VETO|NO_OPINION\",\"confidence\":0..1,"
                "\"reasons\":[..],\"risk_flags\":[..]}. Khong bia so lieu."),
    "review": ("Ban rut kinh nghiem sau khi 1 lenh dong. Tra ve DUY NHAT 1 JSON: "
               "{\"action\":\"ALLOW|VETO|NO_OPINION\",\"confidence\":0..1,"
               "\"reasons\":[..],\"risk_flags\":[..]}; reasons la bai hoc cu the, "
               "hanh dong duoc (vi du 'setup A nen tranh khi RSI>70')."),
    "reflect": ("Ban la kiem toan vien hieu suat giao dich. Doc bang thong ke theo "
                "strategy va de xuat toi da 2 thay doi TRONG PHAM VI: chi duoc "
                "block_strategy / unblock_strategy / watch_strategy / none cho cac "
                "target A_TREND_PULLBACK, B_BREAKOUT_RETEST, C_LIQ_SWEEP_RECLAIM, "
                "D_RANGE_REVERSAL. TUYET DOI khong de xuat cham vao risk/size/SL/TP/"
                "leverage/kill-switch. Tra ve DUY NHAT 1 JSON: {\"proposals\":"
                "[{\"type\":\"...\",\"target\":\"...\",\"reason\":\"...\","
                "\"evidence\":{\"n\":..,\"avg_r\":..}}],\"confidence\":0..1,"
                "\"reasons\":[..]}. Neu khong du bang chung thi tra proposals rong."),
}


def build_prompt(role: str, payload: dict, max_tokens: int = 1200) -> tuple:
    """(system, user) — payload JSON bi cat theo ngan sach token."""
    system = _SYSTEM.get(str(role), _SYSTEM["critic"])
    body = json.dumps({"role": role, **(payload or {})}, ensure_ascii=False,
                      sort_keys=True, default=str)
    limit = max(200, int(max_tokens) * 4)
    if len(body) > limit:
        body = body[:limit] + "...(cat bot)"
    return system, "DU LIEU (JSON):\n" + body + "\nTRA VE JSON, KHONG giai thich them."


# ---- Tang agent -------------------------------------------------------------

class AgentLayer:
    """Goi y kien tu nhieu agent (macro / critic / review) — CHI CO VAN.

    Lop nay KHONG import risk/portfolio/bot: khong the doi hanh vi trading
    (duoc kiem chung bang test). Nguoi goi tu quyet dinh co dung hay khong.
    """

    def __init__(self, cfg=None, provider=None, budget=None, log=None,
                 journal: str = JOURNAL_PATH, state_path: str = STATE_PATH,
                 now_fn=time.time):
        self.cfg = cfg
        self.log = log
        self.journal = journal
        self._now = now_fn
        get = (lambda k, d: getattr(cfg, k, d)) if cfg is not None else (lambda k, d: d)
        self.enabled_flag = bool(get("agents_enabled", False))
        self.shadow = bool(get("agents_shadow", True))
        self.cache_sec = max(0, _i(get("agent_cache_sec", 900)))
        self.timeout = max(1.0, _f(get("agent_timeout_sec", 6.0), 6.0))
        self.max_prompt_tokens = max(200, _i(get("agent_max_prompt_tokens", 1200)))
        self.provider = provider if provider is not None else build_provider(cfg, log)
        self.model = str(getattr(self.provider, "model", "") or "")
        self.budget = budget if budget is not None else AgentBudget(
            path=state_path, daily_calls=_i(get("agent_daily_calls", 200)),
            daily_budget_usd=_f(get("agent_daily_budget_usd", 1.0), 1.0),
            max_errors=_i(get("agent_max_errors", 5)), now_fn=now_fn)
        self._cache: dict = {}
        self.logged = 0

    # -- helpers
    def enabled(self) -> bool:
        return bool(self.enabled_flag)

    def _cached(self, key: str):
        item = self._cache.get(key)
        if not item:
            return None
        ts, dec = item
        if self.cache_sec and (self._now() - ts) <= self.cache_sec:
            return dec
        return None

    def stats(self) -> dict:
        return {"enabled": self.enabled(), "shadow": self.shadow,
                "provider": getattr(self.provider, "name", "?"), "model": self.model,
                "budget": self.budget.snapshot(), "logged": self.logged,
                "cache_size": len(self._cache)}

    # -- API chinh
    def vote(self, role: str, payload: dict) -> Decision:
        """Xin y kien 1 agent. LUON tra Decision (khong bao gio nem loi)."""
        role = str(role or "critic")
        base = Decision(role=role, agent=f"{role}_agent",
                        provider=getattr(self.provider, "name", "?"),
                        model=self.model, shadow=self.shadow, ts=self._now())
        if not self.enabled():
            base.note = "agents_enabled=false"
            return base
        key = _cache_key(role, self.model, payload or {})
        hit = self._cached(key)
        if hit is not None:
            d = hit.to_dict()
            d.update({"cache_hit": True, "ts": self._now(), "latency_ms": 0.0,
                      "cost_usd": 0.0})
            return Decision(**d)
        system, user = build_prompt(role, payload or {}, self.max_prompt_tokens)
        est = cost_usd(self.model, approx_tokens(system + user), 160)
        ok, why = self.budget.can_spend(est_cost=est)
        if not ok:
            base.note = why
            return base
        t0 = self._now()
        try:
            res = self.provider.complete(system, user, timeout=self.timeout)
            parsed = parse_decision(res.get("text", ""), role=role, agent=base.agent)
            base.action = parsed["action"]
            base.confidence = parsed["confidence"]
            base.reasons = parsed["reasons"]
            base.risk_flags = parsed["risk_flags"]
            base.tokens_in = _i(res.get("tokens_in"))
            base.tokens_out = _i(res.get("tokens_out"))
            base.cost_usd = cost_usd(self.model, base.tokens_in, base.tokens_out)
            base.note = "parse=" + str(parsed.get("parse"))
            base.raw_text = str(res.get("text") or "")[:4000]
            self.budget.note(cost=base.cost_usd, ok=True)
        except Exception as e:  # noqa: BLE001  (fail-open tuyet doi)
            base.action = "NO_OPINION"
            base.note = f"loi provider: {str(e)[:120]}"
            self.budget.note(cost=0.0, ok=False, reason=base.note)
            if self.log:
                self.log.warning("agents: %s loi (%s) -> NO_OPINION", role, base.note)
        base.latency_ms = round((self._now() - t0) * 1000.0, 2)
        base.ts = self._now()
        if self.cache_sec:
            self._cache[key] = (base.ts, Decision(**base.to_dict()))
        return base

    def log_decision(self, dec: Decision, extra: dict | None = None) -> dict:
        """Ghi y kien agent vao journal (event=AGENT) de do luong sau nay."""
        try:
            from journal import log_trade
            rec = {"event": "AGENT", **dec.to_dict()}
            rec.update(extra or {})
            rec = log_trade(self.journal, **rec)
            self.logged += 1
            return rec
        except Exception:  # noqa: BLE001
            return {}


# ---- Payload + CLI ----------------------------------------------------------

def setup_payload(symbol: str, direction: str, alpha: float, strat: str,
                  tech: dict | None = None, senti: dict | None = None,
                  regime: str = "", extra: dict | None = None) -> dict:
    """Payload cho agent critic/macro: CHI so lieu tong hop cua thi truong.

    KHONG gui thong tin tai khoan/vi the/API key. Gia tri duoc lam tron de cache
    hoat dong trong cung 1 nen (giam so cuoc goi).
    """
    t = tech or {}
    s = senti or {}
    p = {
        "symbol": symbol, "direction": str(direction).upper(),
        "alpha": round(_f(alpha), 3), "strategy": strat,
        "rsi": round(_f(t.get("rsi"), 50.0), 1),
        "atr_pct": round(_f(t.get("atr_pct")), 4),
        "vol_ratio": round(_f(t.get("vol_ratio"), 1.0), 2),
        "pattern": str(t.get("pattern") or ""),
        "regime": str(regime or ""),
        "news_score": round(_f(s.get("score")), 2),
        "urgent_bearish": _i(s.get("urgent_bearish")),
    }
    p.update(extra or {})
    return p


def review_payload(symbol: str, direction: str, r_multiple: float, won: bool,
                   reason: str, strat: str, extra: dict | None = None) -> dict:
    """Payload cho agent review (sau khi dong lenh)."""
    p = {"symbol": symbol, "direction": str(direction).upper(),
         "r_multiple": round(_f(r_multiple), 3), "won": bool(won),
         "exit_reason": str(reason), "strategy": strat}
    p.update(extra or {})
    return p


def agent_authority(journal: str = JOURNAL_PATH, *, min_n: int = 10,
                    min_gap: float = 0.15, horizon_h: float = 48.0,
                    status: str = "SETUP") -> dict:
    """Phase 4: co du bang chung SHADOW de cap quyen VETO that cho agent khong?

    Cach lam (tat dinh, khong LLM): doc journal ->
      * lay cac ban ghi event=AGENT status=`status` (mac dinh SETUP = macro/critic;
        dat status="COUNCIL" de do RIENG quyet dinh cua hoi dong/arbiter) co VETO/ALLOW;
      * ghep moi ban ghi voi lenh CLOSE DAU TIEN cung symbol/direction sau thoi diem
        do (trong `horizon_h` gio);
      * so sanh avgR nhom VETO vs nhom ALLOW.
    Cap quyen khi: n_veto >= min_n VA avgR_veto <= avgR_allow - min_gap
    (VETO phai thuc su te hon ro ret). Neu khong -> KHONG cap quyen (fail-safe).
    """
    try:
        from monitor_report import load_journal
        _opens, closes = load_journal(journal)
    except Exception:  # noqa: BLE001
        return {"granted": False, "reason": "khong doc duoc journal", "veto_n": 0}
    by_key: dict = {}
    for c in closes:
        k = (str(c.get("pair") or c.get("symbol") or ""), str(c.get("direction") or "").upper())
        by_key.setdefault(k, []).append(c)
    for v in by_key.values():
        v.sort(key=lambda c: float(c.get("ts") or 0))
    used: set = set()
    cohorts: dict = {"VETO": [], "ALLOW": []}
    try:
        with open(journal, encoding="utf-8") as f:
            recs = [json.loads(ln) for ln in f if ln.strip()]
    except Exception:  # noqa: BLE001
        recs = []
    for rec in recs:
        if rec.get("event") != "AGENT" or str(rec.get("status")) != str(status):
            continue
        act = str(rec.get("action") or "").upper()
        if act not in cohorts:
            continue
        k = (str(rec.get("symbol") or ""), str(rec.get("direction") or "").upper())
        t0 = float(rec.get("ts") or 0)
        for c in by_key.get(k, []):
            cid = id(c)
            if cid in used:
                continue
            tc = float(c.get("ts") or 0)
            if t0 <= tc <= t0 + horizon_h * 3600.0:
                used.add(cid)
                cohorts[act].append(_f(c.get("r")))
                break
    def _stat(rs):
        n = len(rs)
        return n, (round(sum(rs) / n, 4) if n else 0.0)
    nv, av = _stat(cohorts["VETO"])
    na, aa = _stat(cohorts["ALLOW"])
    gap = round(aa - av, 4)
    granted = bool(nv >= min_n and av <= aa - min_gap)
    reason = ("du bang chung: VETO te hon ALLOW %.3fR (n_veto=%d)" % (gap, nv)
              if granted else
              f"chua du bang chung (n_veto={nv}/{min_n}, gap={gap:+.3f}R/{min_gap})")
    return {"granted": granted, "reason": reason, "veto_n": nv, "veto_avg_r": av,
            "allow_n": na, "allow_avg_r": aa, "gap": gap, "status": str(status)}


# ---- HOI DONG (council): 2 vong + chu toa ------------------------------------

def consensus_of(macro: str, critic: str, final: str, arbiter: str = "NO_OPINION") -> str:
    """Nhan xet dong thuan (TAT DINH, chi de do luong + hien thi)."""
    m, c, f = str(macro).upper(), str(critic).upper(), str(final).upper()
    if m == "VETO" and c == "VETO":
        return "unanimous_veto"
    if m == "ALLOW" and c == "ALLOW":
        return "unanimous_allow"
    if m in ("ALLOW", "VETO") and c in ("ALLOW", "VETO"):
        return "split"
    if str(arbiter).upper() in ("ALLOW", "VETO") and f in ("ALLOW", "VETO"):
        return "arbiter_only"
    return "none"


def _final_from_council(macro, critic, arbiter) -> tuple:
    """Quy tac quorum TAT DINH (khong phu thuoc LLM): (action, conf, why).

    - Ca hai VETO  -> VETO (dong thuan chan, khong the ghi de).
    - Ca hai ALLOW -> ALLOW (chu toa khong the chan mot dong thuan cho phep).
    - Chia phieu (1 VETO / 1 ALLOW) -> CHU TOA quyet dinh.
    - Thieu phieu (NO_OPINION / loi) -> chu toa; neu chu toa cung khong co -> NO_OPINION.
    """
    m, c = str(getattr(macro, "action", "")).upper(), str(getattr(critic, "action", "")).upper()
    a = str(getattr(arbiter, "action", "")).upper()
    mc, cc, ac = (float(getattr(x, "confidence", 0.0) or 0.0)
                  for x in (macro, critic, arbiter))
    if m == "VETO" and c == "VETO":
        return "VETO", max(mc, cc), "macro+critic cung VETO"
    if m == "ALLOW" and c == "ALLOW":
        return "ALLOW", max(mc, cc), "macro+critic cung ALLOW"
    if m in ("ALLOW", "VETO") and c in ("ALLOW", "VETO"):
        if a in ("ALLOW", "VETO"):
            return a, ac, f"chia phieu -> chu toa quyet {a}"
        return "NO_OPINION", 0.0, "chia phieu nhung chu toa khong co y kien"
    if a in ("ALLOW", "VETO"):
        return a, ac, "thieu phieu -> chu toa quyet"
    return "NO_OPINION", 0.0, "khong du phieu"


def council_decision(layer, payload: dict, log=None) -> dict:
    """HOI DONG 2 vong + chu toa (SHADOW, chi co van).

    Vong 1: macro + critic doc CUNG du lieu -> critic con duoc doc y kien macro
            (`peer`) de dong y / phan doi tuong minh.
    Vong 2: arbiter doc ca hai y kien (`council`) -> quyet dinh cuoi theo quy tac
            quorum tat dinh o `_final_from_council`.

    Tra {stages, action, confidence, consensus, why}. Moi buoc deu di qua `layer.vote`
    nen VAN tuan thu ngan sach/cache/circuit-breaker va KHONG the doi hanh vi trading
    (nguoi goi quyet dinh co dung hay khong).
    """
    stages: dict = {}
    macro = layer.vote("macro", payload)
    stages["macro"] = macro
    peer = {"role": "macro", "action": macro.action,
            "confidence": round(float(macro.confidence or 0.0), 2),
            "reasons": [str(x) for x in list(macro.reasons or [])[:2]]}
    critic = layer.vote("critic", {**(payload or {}), "peer": peer})
    stages["critic"] = critic
    council = {
        "macro": peer,
        "critic": {"role": "critic", "action": critic.action,
                   "confidence": round(float(critic.confidence or 0.0), 2),
                   "reasons": [str(x) for x in list(critic.reasons or [])[:3]]},
    }
    arbiter = layer.vote("arbiter", {**(payload or {}), "council": council})
    stages["arbiter"] = arbiter
    action, conf, why = _final_from_council(macro, critic, arbiter)
    cons = consensus_of(macro.action, critic.action, action, arbiter.action)
    if log:
        log.info("COUNCIL %s %s -> %s (%.2f) [%s] %s",
                 (payload or {}).get("symbol", "?"), (payload or {}).get("direction", "?"),
                 action, conf, cons, why)
    return {"stages": stages, "action": action, "confidence": round(conf, 2),
            "consensus": cons, "why": why}


def council_summary_text(symbol: str, direction: str, res: dict) -> str:
    """Tom tat 1 tin Telegram cho 1 phien hop hoi dong (ngan, de doc)."""
    st = res.get("stages") or {}

    def _line(role: str) -> str:
        d = st.get(role)
        if d is None:
            return ""
        why = "; ".join(str(x) for x in list(getattr(d, "reasons", []) or [])[:1])[:70]
        return (f"{role}: {d.action} {float(d.confidence or 0.0):.2f}"
                + (f" | {why}" if why else ""))

    head = (f"🧠 COUNCIL {str(symbol).split('/')[0]} {str(direction).upper()} -> "
            f"{res.get('action')} ({res.get('consensus')})")
    return "\n".join([head] + [x for x in (_line(r) for r in COUNCIL_ROLES) if x])


def _council_models(cfg) -> list:
    raw = str(getattr(cfg, "agent_council_models", "") or "")
    models = [m.strip() for m in raw.split(",") if m.strip()]
    return models or list(COUNCIL_MULTI_MODELS)


class _CfgOverride:
    """Nhin xuyen qua 1 cfg goc, ghi de vai thuoc tinh — KHONG sua cfg that (Settings
    thuong la frozen dataclass). Dung de "tang ngan sach" chi cho 1 lan goi lai."""

    def __init__(self, base, **overrides):
        self._base = base
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._base, name)


def multi_model_council(cfg, payload: dict, role: str = "critic", log=None,
                        models: list | None = None, provider_factory=None) -> dict:
    """HOI DONG NHIEU MODEL THAT chay SONG SONG — khong chon 1 model "hop ly nhat".

    Moi model trong `models` (mac dinh COUNCIL_MULTI_MODELS) duoc hoi CUNG 1 cau hoi
    qua 1 AgentLayer/provider rieng, chay dong thoi (ThreadPoolExecutor). Model nao
    treo/loi -> AgentLayer.vote() da tu fail-open ve NO_OPINION sau agent_timeout_sec;
    o day coi do la PHIEU TRANG (bi loai khoi quorum), KHONG phai "khong duoc chon" —
    khong co buoc nao chon ra 1 cau tra loi dai dien ca nhom. Ket qua CUOI la quorum
    ALLOW/VETO cua CAC PHIEU THAT con lai (hoa phieu hoac khong ai tra loi -> NO_OPINION,
    tuc KHONG chan lenh — giu nguyen triet ly fail-open cua ca module).

    Ngan sach LINH HOAT (agent_budget_adaptive, mac dinh BAT): van de DE (da dong
    thuan, it phieu trang) -> dung nguyen ngan sach/timeout thuong, KHONG ton them.
    Van de KHO (hoa phieu HOAC >= agent_hard_abstain_ratio model bi treo) -> tu dong
    hoi LAI CAC MODEL TREO voi timeout/ngan sach "hard" (AGENT_*_HARD trong .env,
    mac dinh rat cao — co y bo qua chi phi de co cau tra loi dut khoat hon).
    """
    if not bool(getattr(cfg, "agents_enabled", False)):
        return {"votes": {}, "abstained": [], "action": "NO_OPINION",
               "confidence": 0.0, "why": "agents_enabled=false"}
    names = list(models) if models else _council_models(cfg)
    bin_path = str(getattr(cfg, "agent_copilot_bin", "copilot") or "copilot")
    args = _split_cmd(getattr(cfg, "agent_copilot_args", "")) or None
    make_provider = provider_factory or (
        lambda m: CopilotCliProvider(model=m, bin_path=bin_path, args=args))
    state_path = str(getattr(cfg, "agent_state_path", STATE_PATH) or STATE_PATH)

    def _run_round(ask: list, round_cfg, budget) -> dict:
        def _one(name: str) -> Decision:
            member = AgentLayer(round_cfg, provider=make_provider(name), budget=budget, log=log)
            return member.vote(role, payload)
        out: dict = {}
        with _fut.ThreadPoolExecutor(max_workers=max(1, len(ask))) as pool:
            futs = {pool.submit(_one, name): name for name in ask}
            for fut_ in _fut.as_completed(futs):
                name = futs[fut_]
                try:
                    out[name] = fut_.result()
                except Exception as e:  # noqa: BLE001 — 1 model loi khong duoc lam hong ca hoi dong
                    out[name] = Decision(role=role, agent=f"{role}_agent", action="NO_OPINION",
                                        note=f"loi luong: {str(e)[:100]}", ts=time.time())
        return out

    budget = AgentBudget(
        path=state_path, daily_calls=_i(getattr(cfg, "agent_daily_calls", 200)),
        daily_budget_usd=_f(getattr(cfg, "agent_daily_budget_usd", 1.0), 1.0),
        max_errors=_i(getattr(cfg, "agent_max_errors", 5)))
    decisions = _run_round(names, cfg, budget)

    def _tally(decs: dict) -> tuple:
        abst = sorted(m for m, d in decs.items() if d.action not in ("ALLOW", "VETO"))
        vts = {m: d for m, d in decs.items() if d.action in ("ALLOW", "VETO")}
        na = sum(1 for d in vts.values() if d.action == "ALLOW")
        nv = sum(1 for d in vts.values() if d.action == "VETO")
        act = "VETO" if nv > na else ("ALLOW" if na > nv else "NO_OPINION")
        return abst, vts, na, nv, act

    abstained, votes, n_allow, n_veto, action = _tally(decisions)
    escalated = False
    hard_ratio = _f(getattr(cfg, "agent_hard_abstain_ratio", 0.3), 0.3)
    is_hard = action == "NO_OPINION" or (abstained and len(abstained) / len(names) >= hard_ratio)
    if is_hard and bool(getattr(cfg, "agent_budget_adaptive", True)) and abstained:
        escalated = True
        hard_cfg = _CfgOverride(
            cfg, agent_timeout_sec=_f(getattr(cfg, "agent_timeout_sec_hard", 240.0), 240.0))
        hard_budget = AgentBudget(
            path=state_path, daily_calls=_i(getattr(cfg, "agent_daily_calls_hard", 2000)),
            daily_budget_usd=_f(getattr(cfg, "agent_daily_budget_usd_hard", 1000.0), 1000.0),
            max_errors=_i(getattr(cfg, "agent_max_errors", 5)))
        retry = _run_round(abstained, hard_cfg, hard_budget)
        decisions.update(retry)
        abstained, votes, n_allow, n_veto, action = _tally(decisions)
    why = (f"hoi dong {len(names)} model that: {n_allow} ALLOW / {n_veto} VETO "
          f"(bo qua {len(abstained)} phieu trang: {', '.join(abstained) or '-'})"
          + (" [da tang ngan sach/thoi gian cho vi vong dau kho/chia re]" if escalated else ""))
    conf = (sum(float(d.confidence or 0.0) for d in votes.values()) / len(votes)) if votes else 0.0
    if log:
        log.info("MULTI-MODEL COUNCIL role=%s -> %s (%.2f) [%s]", role, action, conf, why)
    return {"votes": {m: d.to_dict() for m, d in votes.items()},
           "abstained": abstained, "action": action, "confidence": round(conf, 2),
           "why": why, "escalated": escalated}


def veto_decision(cfg, layer, payload: dict) -> dict:
    """Phase 4 (opt-in): xin y kien DONG BO de chan 1 lenh sap mo.

    CHI duoc goi khi: agents_veto_enabled=true VA agent_authority da cap quyen.
    Thu tu uu tien: agents_council_multi_model=true -> HOI DONG NHIEU MODEL THAT
    (multi_model_council, khong chon 1 model dai dien); agents_council=true -> hoi
    dong 1 model 2 vong + chu toa (council_decision); con lai -> 1 phieu 'critic'.
    Tra {"block": bool, "decision": dict}. Loi/khong chac chan -> block=False
    (fail-open: quyen veto khong duoc phep lam bot bo lo co hoi vi loi ky thuat).
    """
    try:
        if bool(getattr(cfg, "agents_council_multi_model", False)):
            res = multi_model_council(cfg, payload, role="critic", log=getattr(layer, "log", None))
            action = str(res.get("action") or "NO_OPINION").upper()
            conf = float(res.get("confidence") or 0.0)
            info = {"role": "council_multi_model", "agent": "council_multi_model",
                    "action": action, "confidence": round(conf, 3),
                    "reasons": [str(res.get("why") or "")], "risk_flags": [],
                    "provider": "multi_model_council",
                    "model": ",".join(sorted(res.get("votes") or {})),
                    "shadow": bool(getattr(cfg, "agents_shadow", True)), "cache_hit": False,
                    "latency_ms": 0.0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0,
                    "ts": time.time(), "note": str(res.get("why") or ""), "raw_text": "",
                    "multi_model": True, "votes": res.get("votes"),
                    "abstained": res.get("abstained"), "final_action": action,
                    "final_confidence": round(conf, 3)}
        elif bool(getattr(cfg, "agents_council", False)):
            res = council_decision(layer, payload)
            dec = (res.get("stages") or {}).get("arbiter")
            action = str(res.get("action") or "NO_OPINION").upper()
            conf = float(res.get("confidence") or 0.0)
            info = dict(getattr(dec, "to_dict", lambda: {})() or {})
            info.update({"council": True, "consensus": res.get("consensus"),
                         "why": res.get("why"), "final_action": action,
                         "final_confidence": round(conf, 3)})
        else:
            dec = layer.vote("critic", payload)
            action = str(dec.action).upper()
            conf = float(dec.confidence or 0.0)
            info = dec.to_dict()
    except Exception as e:  # noqa: BLE001
        return {"block": False, "decision": {"error": str(e)[:120]}}
    min_conf = _f(getattr(cfg, "agent_veto_min_conf", 0.7), 0.7)
    block = (action == "VETO" and conf >= min_conf)
    return {"block": bool(block), "decision": info, "min_conf": min_conf}


def reflect_payload(digest: dict, blocked=()) -> dict:
    """Payload cho agent reflect: bang hieu qua theo strategy (da la so lieu tat dinh)."""
    d = dict(digest or {})
    d["role"] = "reflect"
    d["current_block"] = [str(x) for x in (blocked or d.get("current_block") or [])]
    return d


def run_reflection(cfg=None, layer=None, log=None, journal: str = JOURNAL_PATH,
                   proposals_path: str = PROPOSALS_PATH, save: bool = True) -> dict:
    """Phase 3: agent phan tich hieu qua -> de xuat -> GATE TAT DINH -> ghi file.

    KHONG BAO GIO tu ap dung cau hinh: `save=True` chi GHI de xuat ACCEPTED vao
    `logs/agent_proposals.jsonl`; doi cau hinh van la buoc rieng cua nguoi
    (`python agents.py --apply <id> --yes`).
    """
    blocked = tuple(getattr(cfg, "strategy_block", ()) or ())
    digest = build_digest(journal, blocked=blocked)
    layer = layer or AgentLayer(cfg, log=log, journal=journal)
    if not layer.enabled():
        return {"skipped": "agents_enabled=false", "digest": digest}
    dec = layer.vote("reflect", reflect_payload(digest, blocked))
    raw = getattr(dec, "raw_text", "") or ""
    parsed = parse_proposals(raw, role="reflect")
    validated = validate_proposals(parsed["proposals"], digest,
                                   min_n=int(getattr(cfg, "reflect_min_n", 20) or 20))
    rep = {"ts": time.time(), "digest": digest, "agent": dec.to_dict(),
           "confidence": parsed["confidence"], "parse": parsed["parse"],
           "proposals": validated,
           "accepted": [p for p in validated if p["status"] == "ACCEPTED"
                        and str(p.get("type")) != "none"]}
    if save and rep["accepted"]:
        try:
            os.makedirs(os.path.dirname(proposals_path) or ".", exist_ok=True)
            with open(proposals_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rep, ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001
            if log:
                log.warning("agents: khong ghi duoc proposals (%s)", e)
    return rep


def list_proposals(path: str = PROPOSALS_PATH, limit: int = 3) -> list:
    """Doc N ban ghi de xuat gan nhat (moi dong 1 JSON)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
    except Exception:  # noqa: BLE001
        return []
    out = []
    for ln in lines[-max(1, int(limit)):]:
        try:
            out.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            continue
    return out


def apply_proposal(rec: dict, env_path: str = ".env", dry_run: bool = True,
                   backup: bool = True) -> dict:
    """Ap dung 1 de xuat block/unblock vao STRATEGY_BLOCK trong .env.

    - Chi nhan type block_strategy / unblock_strategy, target trong allowlist.
    - dry_run=True (mac dinh) -> CHI in ra thay doi, khong ghi.
    - backup: tao .env.bak-<ts> truoc khi ghi; giu nguyen kieu xuong dong CRLF.
    """
    typ = str((rec or {}).get("type") or "").lower()
    tgt = str((rec or {}).get("target") or "").upper()
    if typ not in ("block_strategy", "unblock_strategy"):
        return {"ok": False, "error": f"type '{typ}' khong duoc phep ap dung tu dong"}
    if tgt not in PROPOSAL_TARGETS:
        return {"ok": False, "error": f"target '{tgt}' khong hop le"}
    try:
        with open(env_path, encoding="utf-8", newline="") as f:
            raw = f.read()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"khong doc duoc {env_path}: {e}"}
    crlf = "\r\n" in raw
    lines = raw.replace("\r\n", "\n").split("\n")
    cur: list = []
    idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("STRATEGY_BLOCK="):
            idx = i
            cur = [s.strip() for s in ln.split("=", 1)[1].split(",") if s.strip()]
            break
    new = list(cur)
    if typ == "block_strategy" and tgt not in new:
        new.append(tgt)
    elif typ == "unblock_strategy" and tgt in new:
        new.remove(tgt)
    line = "STRATEGY_BLOCK=" + ",".join(new)
    changed = new != cur
    out = {"ok": True, "changed": changed, "before": cur, "after": new,
           "line": line, "dry_run": bool(dry_run), "backup": None}
    if not changed or dry_run:
        return out
    if idx is None:
        lines.append(line)
    else:
        lines[idx] = line
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    if backup:
        bak = "%s.bak-%s" % (env_path, time.strftime("%Y%m%d-%H%M%S"))
        try:
            with open(bak, "w", encoding="utf-8", newline="") as f:
                f.write(raw)
            out["backup"] = bak
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"khong tao duoc backup: {e}"}
    try:
        with open(env_path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"khong ghi duoc {env_path}: {e}"}
    return out


def count_agent_events(journal: str = JOURNAL_PATH) -> dict:
    """Dem quyet dinh agent da ghi trong journal (theo role/action)."""
    out: dict = {}
    try:
        with open(journal, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or '"AGENT"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                if rec.get("event") != "AGENT":
                    continue
                k = f"{rec.get('role')}:{rec.get('action')}"
                out[k] = out.get(k, 0) + 1
    except Exception:  # noqa: BLE001
        pass
    return out


def doctor(cfg=None, log=None) -> int:
    """Chan doan provider Phase 2: da cai chua, da dang nhap chua, thong bao buoc thieu.

    DAY LA LENH NGUOI DUNG CHAY (`python agents.py --doctor`): voi copilot_cli no
    THUC SU goi 1 prompt ngan (ton chut AI credit) de biet chac da dang nhap.
    Tra 0 = san sang; 1 = thieu buoc (in huong dan).
    """
    cfg = cfg
    name = str(getattr(cfg, "agent_provider", "stub") or "stub")
    print("provider =", name)
    if name != "copilot_cli":
        print("  (khong phai copilot_cli — chay `python agents.py --doctor --provider copilot_cli`)")
        return 0
    bin_path = str(getattr(cfg, "agent_copilot_bin", "copilot") or "copilot")
    args = _split_cmd(getattr(cfg, "agent_copilot_args", "-p {prompt}") or "-p {prompt}")
    prov = CopilotCliProvider(model=str(getattr(cfg, "agent_model", "") or ""),
                              bin_path=bin_path, args=args)
    # 1) binary that chua? (tranh shim cua extension)
    ver = None
    try:
        rc, out, err = _subprocess_runner(prov._base + ["--version"], 30, cwd=None,
                                          env=None)
        ver = (out or err).strip().splitlines()[0] if (out or err).strip() else ""
        print("  binary: %s | rc=%s | %s" % (" ".join(prov._base), rc, ver[:80]))
        if any(m in (out + err) for m in _SHIM_MARKS):
            print("  [X] day la SHIM cua extension, khong phai CLI that.")
            print("      -> cai that:  npm install -g @github/copilot")
            print("      -> hoac tro AGENT_COPILOT_BIN toi <npm prefix>\\copilot.cmd")
            return 1
    except Exception as e:  # noqa: BLE001
        print("  [X] khong chay duoc %s: %s" % (bin_path, e))
        print("      -> cai that:  npm install -g @github/copilot")
        return 1
    # 2) da dang nhap chua? (goi 1 prompt ngan — ton chut AI credit)
    try:
        res = prov.complete("Tra loi ngan gon.", 'Tra ve DUY NHAT dong JSON: '
                            '{"action":"ALLOW","confidence":0.5}', timeout=120.0)
        print("  [OK] da xac thuc. Tra ve: %s" % str(res.get("text"))[:120].replace("\n", " "))
        print("  [OK] provider san sang: AGENT_PROVIDER=copilot_cli")
        # Dang nhap thanh cong => mo lai agent neu truoc do bi circuit breaker tat
        # (vi du truoc khi login: 5 lan loi lien tiep -> disabled "den het ngay").
        b = AgentBudget(path=str(getattr(cfg, "agent_state_path", STATE_PATH)),
                        daily_calls=_i(getattr(cfg, "agent_daily_calls", 200)),
                        daily_budget_usd=_f(getattr(cfg, "agent_daily_budget_usd", 1.0)),
                        max_errors=_i(getattr(cfg, "agent_max_errors", 5)))
        if b.disabled():
            b.enable()
            print("  [OK] da mo lai agent (xoa circuit breaker: '%s')" % "disabled")
        return 0
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        print("  [X] chua dung duoc: %s" % msg[:200])
        if "authentication" in msg.lower() or "dang nhap" in msg.lower():
            print("      -> dang nhap:  copilot login        (hoac)")
            print("      -> headless:   dat COPILOT_GITHUB_TOKEN = PAT v2 quyen "
                  "'Copilot Requests' vao .env")
        return 1


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Tang multi-AI agent (Phase 1: co van, mac dinh shadow)")
    ap.add_argument("--selftest", action="store_true",
                    help="chay thu voi provider stub (offline, khong can key)")
    ap.add_argument("--stats", action="store_true", help="in ngan sach/chi phi + dem AGENT")
    ap.add_argument("--doctor", action="store_true",
                    help="chan doan provider (copilot_cli: da cai? da dang nhap?)")
    ap.add_argument("--enable", action="store_true",
                    help="mo lai agent (xoa circuit breaker trong state)")
    ap.add_argument("--reflect", action="store_true",
                    help="Phase 3: phan tich hieu qua -> de xuat (qua gate tat dinh)")
    ap.add_argument("--proposals", type=int, default=0, metavar="N",
                    help="in N ban de xuat gan nhat (0 = tat)")
    ap.add_argument("--apply", type=int, default=-1, metavar="ID",
                    help="ap dung de xuat so ID (can --yes de ghi that; ID bat dau tu 0)")
    ap.add_argument("--yes", action="store_true", help="xac nhan ghi that (--apply)")
    ap.add_argument("--council-test", nargs=2, metavar=("SYMBOL", "DIRECTION"),
                    default=None,
                    help="chay thu 1 phien hoi dong THAT (macro/critic/arbiter) va in ket qua")
    ap.add_argument("--council-multi-test", nargs=2, metavar=("SYMBOL", "DIRECTION"),
                    default=None,
                    help="chay thu HOI DONG NHIEU MODEL THAT song song (AGENT_COUNCIL_MODELS) "
                         "va in tung phieu + ket qua quorum")
    ap.add_argument("--authority", action="store_true",
                    help="Phase 4: xem da du bang chung de cap quyen VETO cho agent chua")
    ap.add_argument("--auto-apply", action="store_true",
                    help="Phase 3/4: chay --reflect roi tu ap dung block/unblock duoc chap nhan "
                         "(can AGENT_AUTO_APPLY=true)")
    ap.add_argument("--journal", default=JOURNAL_PATH)
    ap.add_argument("--state", default=STATE_PATH)
    ap.add_argument("--provider", default="", help="stub|openai|anthropic|copilot_cli|vscode_lm|openai_compatible")
    args = ap.parse_args(argv)

    from config import Settings
    cfg = Settings()
    if args.provider:
        object.__setattr__(cfg, "agent_provider", args.provider)
    if args.selftest:   # selftest phai chay duoc ca khi .env chua bat agent
        object.__setattr__(cfg, "agents_enabled", True)
        object.__setattr__(cfg, "agents_shadow", True)
    if args.doctor:
        return doctor(cfg)
    if args.authority:
        print("Phase 4 — quyen VETO cho agent (do theo tung nguon bang chung):")
        for src in ("SETUP", "COUNCIL"):
            auth = agent_authority(args.journal, status=src,
                                   min_n=int(getattr(cfg, "agent_veto_min_n", 10) or 10),
                                   min_gap=float(getattr(cfg, "agent_veto_min_gap", 0.15) or 0.15))
            tag = "  (dang dung de cap quyen)" if src == getattr(
                cfg, "agent_veto_source", "SETUP") else ""
            print(f"[{src}]{tag}")
            print("  granted = %s | %s" % (auth.get("granted"), auth.get("reason")))
            print("  nhom VETO : n=%s avgR=%+.4f" % (auth.get("veto_n"), auth.get("veto_avg_r") or 0))
            print("  nhom ALLOW: n=%s avgR=%+.4f" % (auth.get("allow_n"), auth.get("allow_avg_r") or 0))
            print("  gap (ALLOW-VETO) = %+.4f  (can >= %s va n_veto >= %s)"
                  % (auth.get("gap") or 0, getattr(cfg, "agent_veto_min_gap", 0.15),
                 getattr(cfg, "agent_veto_min_n", 10)))
        print("  AGENTS_VETO_ENABLED trong .env = %s"
              % getattr(cfg, "agents_veto_enabled", False))
        print("  AGENT_VETO_SOURCE = %s (doi sang COUNCIL neu muon hoi dong lam nguon "
              "bang chung)" % getattr(cfg, "agent_veto_source", "SETUP"))
        _any = any(agent_authority(args.journal, status=s).get("granted")
                   for s in ("SETUP", "COUNCIL"))
        if not _any:
            print("  -> CHUA cap quyen: bot KHONG bi chan lenh nao boi agent.")
        elif not getattr(cfg, "agents_veto_enabled", False):
            print("  -> Du bang chung nhung veto dang TAT: dat AGENTS_VETO_ENABLED=true.")
        else:
            print("  -> Veto DANG BAT: lenh co the bi bo qua khi agent VETO (conf >= %s)."
                  % getattr(cfg, "agent_veto_min_conf", 0.7))
        return 0

    if args.council_test:
        # Hoi dong chay THAT (1 lan, ton ~3 cuoc goi): xem 3 vai + tom tat Telegram.
        object.__setattr__(cfg, "agents_enabled", True)
        layer = AgentLayer(cfg, journal=args.journal, state_path=args.state)
        sym = str(args.council_test[0])
        direction = str(args.council_test[1]).upper()
        pay = setup_payload(sym, direction, 0.42, "NONE",
                            {"rsi": 58.0, "atr_pct": 0.012, "vol_ratio": 1.1,
                             "pattern": "none"},
                            {"score": 0.1, "urgent_bearish": 0}, "UPTREND",
                            {"note": "council test (du lieu gia de thu)"})
        print(f"HOI DONG (test) — {sym} {direction} | provider={getattr(layer.provider, 'name', '?')}")
        res = council_decision(layer, pay, log=None)
        for role in COUNCIL_ROLES:
            d = (res.get("stages") or {}).get(role)
            if d is None:
                continue
            print(f"  {role:8} -> {d.action:11} conf={d.confidence:.2f} "
                  f"cache={d.cache_hit} {('| ' + '; '.join(d.reasons)[:90]) if d.reasons else ''}")
            layer.log_decision(d, extra={"symbol": sym, "direction": direction,
                                         "stage": role, "consensus": res.get("consensus"),
                                         "final_action": res.get("action"),
                                         "status": "COUNCIL" if role == "arbiter" else "SETUP"})
        print(f"  => KET LUAN: {res.get('action')} ({res.get('consensus')}) — {res.get('why')}")
        print("  --- Tin Telegram se gui (neu AGENT_TG_VOTES=true): ---")
        print(council_summary_text(sym, direction, res))
        return 0

    if args.council_multi_test:
        # Hoi dong NHIEU MODEL THAT song song (ton 1 cuoc goi CLI/model, chay dong thoi).
        object.__setattr__(cfg, "agents_enabled", True)
        sym = str(args.council_multi_test[0])
        direction = str(args.council_multi_test[1]).upper()
        pay = setup_payload(sym, direction, 0.42, "NONE",
                            {"rsi": 58.0, "atr_pct": 0.012, "vol_ratio": 1.1,
                             "pattern": "none"},
                            {"score": 0.1, "urgent_bearish": 0}, "UPTREND",
                            {"note": "council multi-model test (du lieu gia de thu)"})
        models = _council_models(cfg)
        print(f"HOI DONG NHIEU MODEL (test) — {sym} {direction} | models={', '.join(models)}")
        res = multi_model_council(cfg, pay, role="critic", log=None, models=models)
        for m in models:
            d = (res.get("votes") or {}).get(m)
            if d is None:
                print(f"  {m:20} -> (phieu trang / treo / NO_OPINION)")
                continue
            print(f"  {m:20} -> {d['action']:11} conf={d['confidence']:.2f} "
                  f"{('| ' + '; '.join(d.get('reasons') or [])[:70]) if d.get('reasons') else ''}")
        print(f"  => KET LUAN: {res.get('action')} ({res.get('why')})")
        return 0

    if args.auto_apply:
        if not bool(getattr(cfg, "agent_auto_apply", False)):
            print("AGENT_AUTO_APPLY != true -> KHONG tu dong ap dung (an toan).")
            print("Muon bat: dat AGENT_AUTO_APPLY=true trong .env, roi chay lai.")
            return 1
        layer = AgentLayer(cfg, journal=args.journal, state_path=args.state)
        rep = run_reflection(cfg, layer=layer, journal=args.journal,
                             proposals_path=str(getattr(cfg, "agent_proposals_path",
                                                       PROPOSALS_PATH)))
        acc = list(rep.get("accepted") or [])
        print("reflect xong: %d de xuat duoc chap nhan" % len(acc))
        rc = 0
        for p in acc:
            res = apply_proposal(p, env_path=".env", dry_run=False)
            print("auto-apply %-14s %-16s -> %s" % (p.get("type"), p.get("target"),
                                                    json.dumps(res, ensure_ascii=False)))
            if not res.get("ok"):
                rc = 1
            elif res.get("changed"):
                print("  DA GHI .env (backup %s)" % res.get("backup"))
                try:
                    from journal import log_trade
                    log_trade(args.journal, event="AGENT_APPLY", type=p.get("type"),
                              target=p.get("target"), reason=p.get("reason"),
                              before=res.get("before"), after=res.get("after"),
                              backup=res.get("backup"))
                except Exception:  # noqa: BLE001
                    pass
        print("(chi ap dung block/unblock; watch_strategy/none khong duoc phep)")
        return rc

    if args.reflect:
        layer = AgentLayer(cfg, journal=args.journal, state_path=args.state)
        print("digest (so lieu tat dinh gui cho agent):")
        rep = run_reflection(cfg, layer=layer, journal=args.journal,
                             proposals_path=str(getattr(cfg, "agent_proposals_path",
                                                       PROPOSALS_PATH)))
        d = rep.get("digest") or {}
        print("  n=%s sumR=%s | block hien tai: %s | vi the mo: %s"
              % (d.get("n"), d.get("sum_r"), d.get("current_block"),
                 d.get("open_positions")))
        for k, v in sorted((d.get("by_strategy") or {}).items()):
            print("  %-18s n=%3s WR=%5s%% avgR=%+7.3f" % (k, v.get("n"), v.get("wr"),
                                                          v.get("avg_r") or 0))
        ag = rep.get("agent") or {}
        print("\nagent: %s | conf=%.2f | %.1fs | %s"
              % (ag.get("action"), ag.get("confidence") or 0,
                 (ag.get("latency_ms") or 0) / 1000.0, ag.get("note", "")))
        print("de xuat (sau GATE TAT DINH):")
        if not rep.get("proposals"):
            print("  (khong co)")
        for i, p in enumerate(rep.get("proposals") or []):
            print("  #%d %-12s %-16s %-9s %s" % (i, p.get("type"), p.get("target"),
                                                 p.get("status"), p.get("why")))
        acc = rep.get("accepted") or []
        print("\nchap nhan: %d | ghi vao %s (khong tu ap dung)"
              % (len(acc), getattr(cfg, "agent_proposals_path", PROPOSALS_PATH)))
        print("muon ap dung: python agents.py --apply <ID> --yes")
        return 0
    if args.proposals:
        recs = list_proposals(str(getattr(cfg, "agent_proposals_path", PROPOSALS_PATH)),
                              limit=args.proposals)
        if not recs:
            print("(chua co de xuat nao)")
        for i, r in enumerate(recs):
            print("#%d %s | n=%s" % (i, time.strftime("%Y-%m-%d %H:%M",
                                                      time.gmtime(r.get("ts") or 0)),
                                     (r.get("digest") or {}).get("n")))
            for p in (r.get("accepted") or []):
                print("    ACCEPTED %-12s %-16s %s" % (p.get("type"), p.get("target"),
                                                       (p.get("reason") or "")[:80]))
        return 0
    if args.apply >= 0:
        recs = list_proposals(str(getattr(cfg, "agent_proposals_path", PROPOSALS_PATH)),
                              limit=99)
        if not recs:
            print("(chua co de xuat nao de ap dung)")
            return 1
        if args.apply >= len(recs):
            print("ID %d khong ton tai (co %d ban ghi)" % (args.apply, len(recs)))
            return 1
        rec = recs[args.apply]
        acc = rec.get("accepted") or []
        if not acc:
            print("ban ghi #%d khong co de xuat nao duoc chap nhan" % args.apply)
            return 1
        rc = 0
        for p in acc:
            res = apply_proposal(p, env_path=".env", dry_run=not args.yes)
            print("apply %-12s %-16s -> %s" % (p.get("type"), p.get("target"),
                                               json.dumps(res, ensure_ascii=False)))
            if not res.get("ok"):
                rc = 1
            elif res.get("changed") and args.yes:
                print("  da ghi .env (backup: %s) -> can restart bot de doc lai"
                      % res.get("backup"))
        if not args.yes:
            print("(DRY-RUN: chua ghi gi — them --yes de ghi that)")
        return rc
    if args.enable:
        b = AgentBudget(path=args.state,
                        daily_calls=_i(getattr(cfg, "agent_daily_calls", 200)),
                        daily_budget_usd=_f(getattr(cfg, "agent_daily_budget_usd", 1.0)),
                        max_errors=_i(getattr(cfg, "agent_max_errors", 5)))
        was = b.disabled()
        b.enable()
        print("da mo lai agent (truoc do: %s)" % (was or "khong bi tat"))
        print("stats:", json.dumps(b.snapshot(), ensure_ascii=False))
        return 0
    layer = AgentLayer(cfg, journal=args.journal, state_path=args.state)
    print("provider=%s model=%s shadow=%s enabled=%s"
          % (getattr(layer.provider, "name", "?"), layer.model, layer.shadow,
             layer.enabled()))
    if args.stats or not args.selftest:
        print("stats:", json.dumps(layer.stats(), ensure_ascii=False))
        ev = count_agent_events(args.journal)
        print("AGENT trong journal:", ev or "(chua co)")
    if args.selftest:
        cases = [
            ("VETO vi RSI (SHORT khi RSI 20)", "critic",
             setup_payload("SOL/USDT:USDT", "SHORT", 0.18, "A_TREND_PULLBACK",
                           {"rsi": 20.0, "atr_pct": 0.012, "vol_ratio": 1.2},
                           {"score": -0.1, "urgent_bearish": 2}, "COMPRESSION")),
            ("VETO vi vi mo (news -0.7)", "macro",
             setup_payload("ETH/USDT:USDT", "LONG", 0.22, "B_BREAKOUT_RETEST",
                           {"rsi": 58.0, "atr_pct": 0.011, "vol_ratio": 1.5},
                           {"score": -0.7, "urgent_bearish": 25}, "UPTREND")),
            ("ALLOW (news +, alpha manh)", "critic",
             setup_payload("BTC/USDT:USDT", "LONG", 0.30, "B_BREAKOUT_RETEST",
                           {"rsi": 60.0, "atr_pct": 0.009, "vol_ratio": 1.3},
                           {"score": 0.4, "urgent_bearish": 0}, "UPTREND")),
        ]
        for title, role, pay in cases:
            d = layer.vote(role, pay)
            print("  [%-28s] %-7s -> %-10s conf=%.2f cache=%-5s %.1fms | %s"
                  % (title, role, d.action, d.confidence, d.cache_hit, d.latency_ms,
                     "; ".join(d.reasons)[:70]))
            layer.log_decision(d, extra={"symbol": pay["symbol"],
                                         "direction": pay["direction"],
                                         "status": "SELFTEST"})
        d2 = layer.vote("critic", cases[0][2])       # lan 2 phai la cache hit
        print("  [cache] critic lap lai -> cache_hit=%s (mong doi True)" % d2.cache_hit)
        d3 = layer.vote("review", review_payload("SOL/USDT:USDT", "SHORT", 0.74, True,
                                                 "TP", "A_TREND_PULLBACK"))
        print("  [review] -> %-10s conf=%.2f | %s"
              % (d3.action, d3.confidence, "; ".join(d3.reasons)[:70]))
        print("stats sau selftest:", json.dumps(layer.stats(), ensure_ascii=False))
        print("AGENT trong journal:", count_agent_events(args.journal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


