"""Do CONTRAST HANH VI giua 2 BIEN THE HARNESS tren CUNG mot bo tinh huong.

    python tools/council_probe.py --cases logs/probe_cases.json            # chi in ke hoach
    python tools/council_probe.py --cases logs/probe_cases.json --live     # goi LLM that
    python tools/council_probe.py --cases logs/probe_cases.json --live --json

Vi sao (21/10, doc `google-research/harness2`): khi **khong co ground truth** (khong bao gio
biet PnL phan thuc cua mot lenh bi VETO) thi cach duy nhat de biet mot thay doi harness
(prompt / nhan lua chon / model) tot hon hay khong la do **contrast hanh vi tren CUNG dau
vao**: cung cau hoi, hai bien the A/B, roi so:

  * **phieu doi chieu** (action flip) theo tung model,
  * **ket luan co doi khong** (ALLOW <-> VETO),
  * **ly do co KHOP voi phieu khong** — do that 21/10: 2 model viet ly do "nang tran ngay"
    nhung bam VETO ⇒ cau hoi nhap nhang, phieu khong dang tin,
  * chi phi / do tre.

Case file (JSON):
    [{"name": "risk-tran-ngay",
      "a": {"question": "...", "allow": "...", "veto": "...", "context": ["..."]},
      "b": {"question": "...", "allow": "...", "veto": "...", "context": ["..."]}}]

`a` = ban dang chay, `b` = ban de xuat. Ket qua dung de ghi vao `tools/harness_ledger.py`
truong `--probe` truoc khi `--decision adopted`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

DEFAULT_CASES = ROOT / "logs" / "probe_cases.json"
STOP = {"khong", "nhieu", "duoc", "phai", "ngay", "cung", "theo", "trong", "hien", "tai",
        "chon", "phuong", "nhan", "thieu", "thong", "tin", "lenh", "thua", "tran"}


def load_cases(path=DEFAULT_CASES) -> tuple:
    """Doc case file -> (cases, err). Loi -> ([], 'ly do') (khong nem)."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        return [], "khong doc duoc %s: %s" % (path, str(e)[:120])
    except Exception as e:  # noqa: BLE001
        return [], "JSON hong: %s" % str(e)[:120]
    if not isinstance(raw, list) or not raw:
        return [], "case file phai la list khong rong"
    out = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict) or not isinstance(c.get("a"), dict):
            return [], "case #%d thieu 'a'" % i
        if not isinstance(c.get("b"), dict):
            return [], "case #%d thieu 'b'" % i
        out.append({"name": str(c.get("name") or "case-%d" % i), "a": c["a"], "b": c["b"]})
    return out, ""


def _keywords(text) -> set:
    """Tu co nghia (>=4 ky tu) de do 'ly do co khop phieu khong'."""
    words = re.findall(r"[0-9A-Za-z_%.]+", str(text or "").lower())
    return {w for w in words if len(w) >= 4 and w not in STOP}


def reason_matches(reason, action, case) -> object:
    """Ly do co ung ho DUNG phuong an da chon khong -> True/False/None (khong du tin hieu).

    Do that 21/10 (LIVE): phieu VETO nhung ly do viet "nang tran ngay de chiu >=3 lenh thua"
    (ung ho ALLOW) ⇒ `False` = NGUOC, `None` = khong du tin hieu de ket luan.

    (22/10, sau lan probe dau) Chi tinh tu **RIENG CUA TUNG phuong an** (`allow-only` /
    `veto-only`): tu chung cho ca hai ("tran ngay", "lenh thua") khong noi len dieu gi ⇒ truoc
    day dem ca tu chung nen bao "khong khop" gia.
    """
    act = str(action or "").upper()
    if act not in ("ALLOW", "VETO"):
        return None
    txt = _keywords(reason)
    if not txt:
        return None
    wa = _keywords((case or {}).get("allow"))
    wv = _keywords((case or {}).get("veto"))
    sa = len(txt & (wa - wv))
    sv = len(txt & (wv - wa))
    if sa == sv:
        return None
    pick = "ALLOW" if sa > sv else "VETO"
    return pick == act


def names_other_option(reason, action, case) -> bool:
    """Ly do co **nhac toi phuong an KHAC** nhieu hon phuong an da chon khong.

    (22/10) CANH BAO ve y nghia: day la chi so **THONG TIN**, KHONG phai loi. Do that trong
    probe: model bam VETO va viet "nang MAX_DAILY_LOSS_PCT ... lam tang rui ro" — tuc la
    *nêu phương án ra để phản đối*. Vi vay chi dung chi so nay de doc, khong dung de ket toi.
    """
    m = reason_matches(reason, action, case)
    return m is False


def run_case(case: dict, variant: str, council_fn) -> dict:
    """Hoi hoi dong 1 bien the cua 1 case -> {rows, verdict, cost, seconds, reason_mismatch}."""
    from council_vote import build_payload, tally
    spec = (case or {}).get(variant) or {}
    payload = build_payload(spec.get("question", ""), spec.get("allow", ""),
                            spec.get("veto", ""), spec.get("context") or [])
    t0 = time.time()
    res = council_fn(payload) or {}
    votes = (res.get("votes") or res.get("decisions") or {}) if isinstance(res, dict) else {}
    tal = tally(votes or {})
    cost = 0.0
    for d in (votes or {}).values():
        try:
            cost += (float(d.get("cost_usd") or 0.0) if isinstance(d, dict)
                     else float(getattr(d, "cost_usd", 0.0) or 0.0))
        except (TypeError, ValueError):
            continue
    out = {"variant": variant, "verdict": tal.get("verdict"), "n": tal.get("n"),
           "n_allow": tal.get("n_allow"), "n_veto": tal.get("n_veto"),
           "cost_usd": round(cost, 6), "seconds": round(time.time() - t0, 1),
           "rows": tal.get("rows") or []}
    bad = 0
    for r in out["rows"]:
        m = reason_matches(r.get("reason"), r.get("action"), spec)
        r["reason_matches"] = m
        if m is False:
            bad += 1
    out["names_other_option"] = bad
    out["reason_mismatch"] = bad      # giu ten cu (tuong thich) — xem `names_other_option`
    return out


def contrast(a: dict, b: dict) -> dict:
    """So 2 bien the: phieu doi chieu theo model, ket luan doi, ly do khong khop."""
    ma = {str(r.get("model")): str(r.get("action")) for r in (a.get("rows") or [])}
    mb = {str(r.get("model")): str(r.get("action")) for r in (b.get("rows") or [])}
    shared = sorted(set(ma) & set(mb))
    flips = [m for m in shared if ma[m] != mb[m]]
    return {"verdict_a": a.get("verdict"), "verdict_b": b.get("verdict"),
            "verdict_changed": bool(a.get("verdict") != b.get("verdict")),
            "models_shared": len(shared), "flips": flips,
            "flip_rate": round(len(flips) / max(1, len(shared)), 3),
            "reason_mismatch_a": int(a.get("reason_mismatch") or 0),
            "reason_mismatch_b": int(b.get("reason_mismatch") or 0),
            "cost_usd": round(float(a.get("cost_usd") or 0)
                              + float(b.get("cost_usd") or 0), 6)}


def probe(cases: list, council_fn=None, *, live: bool = False) -> dict:
    """Chay probe. `live=False` -> chi tra KE HOACH (KHONG goi LLM, 0 dong)."""
    rep = {"ok": True, "live": bool(live), "n_cases": len(cases), "cases": [],
           "verdict_changed": 0, "total_flips": 0, "models_compared": 0,
           "reason_mismatch": 0, "cost_usd": 0.0}
    if not live or council_fn is None:
        rep["plan"] = [{"name": c["name"], "a": str((c["a"] or {}).get("question"))[:120],
                        "b": str((c["b"] or {}).get("question"))[:120]} for c in cases]
        return rep
    for c in cases:
        a = run_case(c, "a", council_fn)
        b = run_case(c, "b", council_fn)
        ct = contrast(a, b)
        rep["cases"].append({"name": c["name"], "a": a, "b": b, "contrast": ct})
        rep["verdict_changed"] += 1 if ct["verdict_changed"] else 0
        rep["total_flips"] += len(ct["flips"])
        rep["models_compared"] += ct["models_shared"]
        rep["reason_mismatch"] += (ct["reason_mismatch_a"] + ct["reason_mismatch_b"])
        rep["cost_usd"] = round(rep["cost_usd"] + ct["cost_usd"], 6)
    rep["flip_rate"] = round(rep["total_flips"] / max(1, rep["models_compared"]), 3)
    # (22/10) Ket luan chi dua tren THAY DOI HANH VI (ket luan/phiếu). Chi so "nhac phuong an
    # khac" la thong tin — mot ly do phan doi mot phuong an thi tat nhien phai neu ten no.
    rep["ket_luan"] = ("HAI BIEN THE KHAC NHAU -> can xem lai" if (rep["verdict_changed"]
                       or rep["total_flips"]) else "dong nhat (khong co khac biet hanh vi)")
    return rep



def _print(rep: dict) -> None:
    if not rep.get("live"):
        print("=== PROBE (KE HOACH — khong goi LLM, 0 dong) | %d case ===" % rep["n_cases"])
        for p in rep.get("plan") or []:
            print("  %-22s A: %s" % (p["name"], p["a"]))
            print("  %-22s B: %s" % ("", p["b"]))
        print("  Them --live de do that (co tran chi phi o daemon; o day chay truc tiep).")
        return
    print("=== PROBE CONTRAST | %d case | %.3f USD ===" % (rep["n_cases"], rep["cost_usd"]))
    for c in rep.get("cases") or []:
        ct = c["contrast"]
        print("  %s: A=%s (%d phieu, nhac PA khac %d) | B=%s (%d phieu, nhac PA khac %d)"
              % (c["name"], ct["verdict_a"], c["a"]["n"], ct["reason_mismatch_a"],
                 ct["verdict_b"], c["b"]["n"], ct["reason_mismatch_b"]))
        if ct["flips"]:
            print("      doi phieu: %s" % ", ".join(ct["flips"]))
        if ct["verdict_changed"]:
            print("      KET LUAN DOI: %s -> %s" % (ct["verdict_a"], ct["verdict_b"]))
    print("  tong: doi ket luan %d case, doi phieu %d/%d luot, nhac phuong an khac %d (thong tin)"
          % (rep["verdict_changed"], rep["total_flips"], rep["models_compared"],
             rep["reason_mismatch"]))
    print("  KET LUAN: %s" % rep.get("ket_luan"))


def save_report(rep: dict, outdir=None, *, now=None) -> str:
    """Luu ket qua probe ra `logs/ops/probe-<ts>.json` (bang chung de ghi vao ledger)."""
    d = Path(outdir) if outdir else (ROOT / "logs" / "ops")
    name = "probe-%s.json" % time.strftime("%Y%m%d-%H%M%S",
                                           time.localtime(float(now or time.time())))
    try:
        import atomic
        atomic.write_json_atomic(d / name, rep, indent=1)
        return str(d / name)
    except OSError:
        return ""


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Do contrast hanh vi giua 2 bien the harness")
    ap.add_argument("--cases", default=str(DEFAULT_CASES))
    ap.add_argument("--live", action="store_true", help="goi LLM THAT (mac dinh chi in ke hoach)")
    ap.add_argument("--models", default="", help="gioi han model (phay)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cases, err = load_cases(args.cases)
    if err:
        print("LOI: %s" % err)
        return 1
    council_fn = None
    if args.live:
        import council_daemon as CD
        council_fn, _ms = CD.default_council(3, args.models)
    rep = probe(cases, council_fn, live=bool(args.live))
    if args.live:
        rep["saved"] = save_report(rep)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        _print(rep)
        if rep.get("saved"):
            print("  da luu bang chung: %s" % rep["saved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

