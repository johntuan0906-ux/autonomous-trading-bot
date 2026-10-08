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