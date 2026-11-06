# -*- coding: utf-8 -*-
"""council_evals.py — Shadow A/B + eval dataset cho hoi dong (08/10/2026).

Y tuong tu overmind ("create_dataset_from_llm_calls", evals tu traces) + harness
("with-skill vs without-skill A/B"): ta da ghi moi quyet dinh AGENT vao journal
(event=AGENT) va moi ket qua lenh vao journal (event=CLOSE voi r/won/pnl). Module nay:

  * pair_cases()        — ghep moi quyet dinh AGENT (ALLOW/VETO) voi lenh CLOSE dau tien
                          cung symbol/direction trong cua so thoi gian.
  * council_ab_report() — bao cao A/B: nhom VETO vs ALLOW (n/wr/avgR) + veto_precision
                          (ty le VETO dung: lenh di theo sau do THUA).
  * build_eval_dataset()— xuat JSONL case (features + outcome) de danh gia offline sau
                          nay (doi model/provider -> chay lai tren cung bo case).

KHONG import risk/portfolio/bot — chi doc journal, offline-testable, fail-open.
CLI: python agents.py --ab-report | --eval-dataset PATH
"""
from __future__ import annotations

import json
import os

FEAT_KEYS = ("alpha", "rsi", "atr_pct", "news_score", "urgent_bearish", "vol_ratio",
             "ema_diff", "regime", "difficulty", "start_tier")


def load_recs(journal_path: str) -> list:
    """Doc toan bo ban ghi JSONL (ban ghi hong -> bo qua, khong bao gio nem loi)."""
    recs: list = []
    try:
        with open(journal_path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    recs.append(json.loads(ln))
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return recs


# (15/10) Phieu HAU KIEM (`status=CLOSED` / vai `review`) duoc bo SAU khi lenh da dong
# => no DA BIET ket qua. Neu tinh vao `value_r`/`veto_precision` thi thien lech nhin truoc
# (do that: bang diem cu co dong `claude-sonnet-5.5` +0.044 — chinh la model cua agent
# review). Chi cham diem phieu bo TRUOC khi vao lenh.
POST_TRADE_STATUS = ("CLOSED", "REVIEW")
POST_TRADE_ROLES = ("review", "review_agent")


def is_pre_trade(rec: dict) -> bool:
    """Phieu duoc bo TRUOC khi vao lenh? (loai phieu hau kiem) — ham THUAN TUY."""
    r = rec or {}
    if str(r.get("status") or "").upper() in POST_TRADE_STATUS:
        return False
    role = str(r.get("role") or r.get("agent") or "").lower()
    return role not in POST_TRADE_ROLES


def pair_cases(journal_path: str, window_sec: float = 3600.0) -> list:
    """Ghep quyet dinh AGENT voi lenh CLOSE dau tien cung symbol/direction trong cua so.

    Moi lenh CLOSE chi duoc ghep 1 lan (dung `id()` de danh dau) — giong agent_authority().
    """
    recs = load_recs(journal_path)
    closes: dict = {}
    for r in recs:
        if r.get("event") == "AGENT":
            continue
        pair = str(r.get("pair") or r.get("symbol") or "")
        if not pair or ("r" not in r and "won" not in r and "pnl" not in r):
            continue
        k = (pair.upper(), str(r.get("direction") or "").upper())
        closes.setdefault(k, []).append(r)
    for v in closes.values():
        v.sort(key=lambda c: float(c.get("ts") or 0))
    used: set = set()
    cases: list = []
    for r in recs:
        if r.get("event") != "AGENT":
            continue
        if not is_pre_trade(r):        # bo phieu HAU KIEM (thien lech nhin truoc)
            continue
        act = str(r.get("action") or "").upper()
        if act not in ("ALLOW", "VETO"):
            continue
        k = (str(r.get("symbol") or "").upper(), str(r.get("direction") or "").upper())
        t0 = float(r.get("ts") or 0)
        matched = None
        for c in closes.get(k, []):
            if id(c) in used:
                continue
            tc = float(c.get("ts") or 0)
            if t0 <= tc <= t0 + window_sec:
                used.add(id(c))
                matched = c
                break
        feats = {fk: r.get(fk) for fk in FEAT_KEYS if r.get(fk) is not None}
        outcome = None
        if matched is not None:
            if matched.get("won") is not None:
                won = bool(matched.get("won"))
            else:
                won = float(matched.get("r") or 0) > 0
            outcome = {"won": won, "r": float(matched.get("r") or 0),
                       "pnl": float(matched.get("pnl") or 0)}
        cases.append({
            "ts": t0, "symbol": r.get("symbol"), "direction": r.get("direction"),
            "action": act, "confidence": float(r.get("confidence") or 0),
            "role": r.get("role"), "provider": r.get("provider"),
            "model": r.get("model"), "status": r.get("status"),
            "features": feats, "matched_close": outcome is not None,
            "outcome": outcome,
        })
    return cases


def _stat(cs: list) -> dict:
    matched = [c for c in cs if c.get("matched_close")]
    wins = [c for c in matched if (c.get("outcome") or {}).get("won")]
    n = len(matched)
    return {
        "n": len(cs),
        "matched": n,
        "wins": len(wins),
        "wr": round(len(wins) / n, 4) if n else None,
        "avg_r": round(sum((c.get("outcome") or {}).get("r", 0.0)
                           for c in matched) / n, 4) if n else None,
    }


def council_ab_report(journal_path: str, window_sec: float = 3600.0) -> dict:
    """Bao cao shadow A/B cua hoi dong: chat luong nhom VETO vs nhom ALLOW.

    veto_precision = ty le quyet dinh VETO DUNG (lenh cung symbol/direction di theo
    sau do trong cua so THUA) — xap xi, khong phai counterfactual that su.
    """
    cases = pair_cases(journal_path, window_sec)
    veto = [c for c in cases if c["action"] == "VETO"]
    allow = [c for c in cases if c["action"] == "ALLOW"]
    veto_matched = [c for c in veto if c.get("matched_close")]
    precision = None
    if veto_matched:
        avoided = sum(1 for c in veto_matched if not (c.get("outcome") or {}).get("won"))
        precision = round(avoided / len(veto_matched), 4)
    return {
        "cases": len(cases),
        "veto": _stat(veto),
        "allow": _stat(allow),
        "veto_precision": precision,
        "window_sec": window_sec,
    }


def build_eval_dataset(journal_path: str, out_path: str,
                       window_sec: float = 3600.0) -> int:
    """Xuat bo du lieu eval (case + outcome) ra JSONL de danh gia offline sau nay.

    Tra so case da ghi. Dung de chay lai tren CUNG bo case khi doi model/provider
    (hoc tu overmind: dataset tu traces).
    """
    cases = pair_cases(journal_path, window_sec)
    try:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for c in cases:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        return len(cases)
    except Exception:  # noqa: BLE001
        return 0


# ---- Eval theo TUNG MODEL (14/10, y tuong tu ai-engineering-from-scratch phase G) ----
# Truoc day chi co bao cao A/B GOP (VETO vs ALLOW) -> khong biet model NAO dong gop.
# Ham duoi day cham diem tung model bang ket qua THAT trong journal.

ROLE_LIKE = ("review_agent", "macro_agent", "critic_agent", "arbiter_agent",
             "setup", "council", "selftest")

# ---- (06/11, B-035) CHUAN HOA TEN MODEL --------------------------------------
# Journal ghi CUNG 1 model duoi NHIEU ten (doi `.env`, doi cach goi: tag ollama vs
# alias llamafile, thieu/thua tien to provider) ⇒ bang diem bi CHIA NHO thanh nhieu
# dong, moi dong qua it mau de ket luan (va `skip_lines` de xuat bo 1 nua model).
# Do that tren journal TESTNET (06/11):
#   `local/llama3.2:3b` (83 phieu) + `local/llama3.2-3b-local` (73) = MOT model;
#   `mimo-v2.6-pro` (77) + `cline-pass/mimo-v2.6-pro` (105) = MOT model;
#   `qwen/cline-pass/qwen3.7-plus` (tien to lap), 135 ban ghi `model` RONG.
# Ten chuan = ten dang dung trong `.env` (de `skip_lines` copy duoc thang vao .env).
MODEL_CANON = {
    # local: tag ollama (`llama3.2:3b`) <-> alias llamafile (`llama3.2-3b-local`)
    "local/llama3.2:3b": "local/llama3.2-3b-local",
    "local/llama3.2:3b-local": "local/llama3.2-3b-local",
    "llama3.2:3b": "local/llama3.2-3b-local",
    "llama3.2:3b-local": "local/llama3.2-3b-local",
    "llama3.2-3b-local": "local/llama3.2-3b-local",
    "llama3.2:3b-instruct": "local/llama3.2-3b-local",
}
#: Model `cline-pass/...` DA BIET, viet KHONG tien to (journal cu ghi thieu) —
#: ten goc duoi gateway (`model_aliases`), khong tinh hau to provider.
CLINE_MODELS = ("mimo-v2.6-pro", "qwen3.7-plus", "qwen3.8-max", "glm-5.3",
                "kimi-k3", "claude-sonnet-5.5", "claude-sonnet-5")
#: Cac chuoi KHONG phai ten model (ban ghi thieu truong `model`).
EMPTY_NAMES = ("", "none", "null", "nil", "?", "-", "unknown", "n/a", "na")


def normalize_model(name) -> str:
    """Ten CHUAN cua 1 model — gop MOI cach viet cua CUNG 1 model (B-035).

    Quy tac (theo thu tu):
      1. rong / `None` / chuoi `"None"` / `"?"` -> `""` (= journal thieu du lieu,
         KHONG phai mot model ten la "?" nhu truoc day);
      2. alias khai bao trong `MODEL_CANON`;
      3. bo tien to provider bi LAP (`qwen/cline-pass/x` -> `cline-pass/x`,
         `clinepass/x` -> `cline-pass/x`);
      4. them `cline-pass/` cho ten da biet nhung journal ghi thieu tien to.

    Ham THUAN TUY (khong doc file, khong mang) ⇒ dung duoc o CA noi GHI
    (`agents.log_decision`) lan noi DOC (`_model_of`, bang diem, `skip_lines`).
    """
    n = str(name if name is not None else "").strip()
    if n.lower() in EMPTY_NAMES:
        return ""
    if n in MODEL_CANON:
        return MODEL_CANON[n]
    low = n.lower()
    if low.startswith("qwen/cline-pass/"):
        n = "cline-pass/" + n.split("cline-pass/", 1)[1]
    elif low.startswith("clinepass/"):
        n = "cline-pass/" + n.split("/", 1)[1]
    if "/" not in n and n.lower() in CLINE_MODELS:
        n = "cline-pass/" + n
    return MODEL_CANON.get(n, n)


def _model_of(case: dict) -> str:
    """Ten model CHUAN (khong phai VAI nhu `critic_agent`); `""` = thieu du lieu."""
    raw = case.get("model")
    if raw is None or str(raw).strip() == "":
        raw = case.get("agent") or case.get("provider") or ""
    return normalize_model(raw)


def _avg_r(cases: list):
    vals = [float((c.get("outcome") or {}).get("r") or 0.0) for c in cases]
    return (sum(vals) / len(vals)) if vals else None


def calibration(cases: list, buckets: int = 5) -> dict:
    """Calibration: `confidence` co khop voi ty le thang THAT khong (eval framework).

    brier = trung binh (confidence - won)^2 tren cac case DA ghep duoc lenh CLOSE
    (0 = hoan hao, 0.25 = nhu doan bua 50/50). `buckets` = so o do tin cay.
    """
    matched = [c for c in cases if c.get("matched_close")]
    if not matched:
        return {"n": 0, "brier": None, "bins": []}
    n = len(matched)
    brier = sum((float(c.get("confidence") or 0.0)
                 - (1.0 if (c.get("outcome") or {}).get("won") else 0.0)) ** 2
                for c in matched) / n
    bins = []
    step = 1.0 / max(1, int(buckets))
    for i in range(int(buckets)):
        lo, hi = i * step, (i + 1) * step
        grp = [c for c in matched
               if lo <= float(c.get("confidence") or 0.0) < (hi + (1e-9 if i == int(buckets) - 1 else 0))]
        if grp:
            wins = sum(1 for c in grp if (c.get("outcome") or {}).get("won"))
            bins.append({"lo": round(lo, 2), "hi": round(hi, 2), "n": len(grp),
                         "win_rate": round(wins / len(grp), 3),
                         "conf_avg": round(sum(float(c.get("confidence") or 0.0)
                                               for c in grp) / len(grp), 3)})
    return {"n": n, "brier": round(brier, 4), "bins": bins}


def skip_lines(models: list) -> list:
    """Dong `.env` de bo model (giong `agents.council_health` -> nhat quan cho nguoi van hanh).

    CHI voi ten model that: `review_agent`/`critic_agent`... la VAI, khong phai model.
    (06/11, B-035) Ban ghi THIEU `model` (`""`) cung bi loai — truoc day `""` khong co
    dau `/` nen bi coi la model Cline ⇒ sinh dong `CLINE_SKIP_MODELS=,mimo-...`
    (phan tu rong, khong ai doc duoc).
    """
    names = [m for m in models
             if str(m).strip() and str(m).lower() not in ROLE_LIKE]
    cline = [m for m in names if m.startswith("cline-pass/") or "/" not in m]
    local = [m for m in names if m.startswith("local/")]
    qwen = [m for m in names if m.startswith("qwen/")]
    out = []
    if cline:
        out.append("CLINE_SKIP_MODELS=%s" % ",".join(cline))
    if local:
        out.append("LOCAL_SKIP_MODELS=%s" % ",".join(local))
    if qwen:
        out.append("QWEN_SKIP_MODELS=%s" % ",".join(qwen))
    return out


def model_leaderboard(journal_path: str, *, window_sec: float = 3600.0,
                      hours: float | None = None, min_n: int = 8,
                      now: float | None = None) -> dict:
    """Bang xep hang TUNG MODEL hoi dong theo ket qua THAT (khong phai theo so phieu).

    Voi moi model (ghep phieu -> lenh CLOSE dau tien cung symbol/direction):
      * `allow_avg_r` — avgR cac lenh model CHO PHEP;
      * `veto_avg_r`  — avgR cac lenh model dinh CHAN (counterfactual gan dung);
      * `value_r` = allow_avg_r - veto_avg_r: **>0** = phan biet duoc lenh tot/xau
        (dang giu); **<=0** = khong phan biet duoc (nen bo);
      * `veto_precision` — ty le VETO dung (lenh do THUA);
      * `brier` — calibration cua `confidence`.

    Tra {window_h, cases, per_model, keep, drop, thin, skip_lines, calibration}.
    `thin` = chua du mau (n_ghep < min_n) -> KHONG ket luan.
    """
    import time as _t
    t_now = float(now if now is not None else _t.time())
    cases = pair_cases(journal_path, window_sec)
    if hours:
        cut = t_now - max(1.0, float(hours)) * 3600.0
        cases = [c for c in cases if float(c.get("ts") or 0) >= cut]
    per: dict = {}
    for c in cases:
        m = _model_of(c)
        b = per.setdefault(m, {"votes": 0, "matched": 0, "allow": [], "veto": [],
                               "conf": []})
        b["votes"] += 1
        b["conf"].append(float(c.get("confidence") or 0.0))
        if c.get("matched_close"):
            b["matched"] += 1
            (b["allow"] if c.get("action") == "ALLOW" else b["veto"]).append(c)
    out: dict = {}
    keep, drop, thin = [], [], []
    for m, b in per.items():
        aa, va = _avg_r(b["allow"]), _avg_r(b["veto"])
        veto_n = len(b["veto"])
        prec = (round(sum(1 for c in b["veto"]
                          if not (c.get("outcome") or {}).get("won")) / veto_n, 3)
                if veto_n else None)
        value = round(aa - va, 4) if (aa is not None and va is not None) else None
        cal = calibration([c for c in cases if _model_of(c) == m])
        row = {"votes": b["votes"], "matched": b["matched"],
               "allow_n": len(b["allow"]), "veto_n": veto_n,
               "allow_avg_r": None if aa is None else round(aa, 4),
               "veto_avg_r": None if va is None else round(va, 4),
               "value_r": value, "veto_precision": prec, "brier": cal["brier"]}
        out[m] = row
        if b["matched"] < int(min_n):
            thin.append(m)
        elif value is not None and value <= 0:
            drop.append(m)
        elif value is not None:
            keep.append(m)
    return {"window_h": hours, "cases": len(cases), "per_model": out,
            "keep": sorted(keep), "drop": sorted(drop), "thin": sorted(thin),
            "skip_lines": skip_lines(sorted(drop)),
            "calibration": calibration(cases)}
