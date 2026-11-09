"""GOLDEN SET — bo ca KIEM DINH HANH VI (case-based) cho cac cong quyet dinh, chay OFFLINE.

    python tools/golden_build.py                 # sinh golden/cases.jsonl (viet tay + tu journal)
    python tools/golden_set.py                   # chay tat ca ca
    python tools/golden_set.py --verbose         # in tung ca
    python tools/golden_set.py --check           # exit 1 neu co ca FAIL hoac DRIFT so voi baseline
    python tools/golden_set.py --write-baseline  # chot hanh vi hien tai (sau khi da xem xet tung ca)
    python tools/golden_set.py --only risk_cap --json

Vi sao co (09/11 — 3 tai lieu "Golden-Set Eval", "Decision Log", "Measured Context"):
repo DA co `tools/council_eval.py` (do chat luong hoi dong theo KET QUA that) va `tests/`
(unit test theo tung ham). Thieu dung lop o giua: **bo ca CO DINH, CO DAP AN, chay duoc TRUOC
khi doi code** — de tra loi "ban moi co lam MAT hanh vi cu khong" bang so, va de biet 1 ca vo
thuoc nhom nao (normal / edge / failure).

3 loai ca (theo tai lieu):
- `normal`  : du lieu that tu journal (chinh `feats` bot da ghi) -> hanh vi phai ON DINH;
- `edge`    : bien (clip, thieu mau, b = 0, tran risk vua cham);
- `failure` : du lieu hong / mau thuan -> phai TU CHOI hoac CHAN, khong duoc "doan bua".

Moi ca goi THANG ham that (`learner.extract_features`, `learner.OnlineLearner.edge`,
`strategy.classify_strategy/gate_check`, `lessons.gate_list`, `portfolio.can_add_risk`,
`PortfolioManager.can_open`) — KHONG mo phong lai logic: mo phong thi eval luon xanh trong khi
bot sai (dung lop loi B-033 "model dung cong thuc nhung chay sai chuoi").

Dinh dang 1 dong `golden/cases.jsonl`:
    {"id":"syn-risk-cap-blocked","kind":"failure","component":"risk_cap","title":"...",
     "input":{...},"expect":{"output":{"ok":false},"must":["reason:contains:tran risk"]},
     "source":"synthetic"}

`expect.output` la SO KHOP MOT PHAN (chi kiem tra key co mat); `must`/`must_not` la rule
dang `duong.dan:toan_tu:gia_tri` (==, !=, <, <=, >, >=, contains, not_contains, in).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

CASES_PATH = ROOT / "golden" / "cases.jsonl"
BASELINE_PATH = ROOT / "golden" / "baseline.json"
#: Cac "cong" duoc kiem dinh. Them cong moi = them adapter + ca (khong doi runner).
COMPONENTS = ("feats", "learner_edge", "strategy_classify", "strategy_gate",
              "lessons_gate", "risk_cap", "portfolio_open", "journal_feats")
OPS = ("==", "!=", "<", "<=", ">", ">=", "contains", "not_contains", "in")
#: Sai so so sanh so thuc (float) — 6 chu so thap phan la du cho cac cong nay.
TOL = 1e-6
REQUIRED = ("id", "kind", "component", "input", "expect")
KINDS = ("normal", "edge", "failure")


def _r6(v):
    """Lam tron float 6 chu so (dict/list di qua deu duoc) — de so sanh & lam digest."""
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return str(v)
        return round(v, 6)
    if isinstance(v, dict):
        return {str(k): _r6(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_r6(x) for x in v]
    return v


def _digest(obj) -> str:
    """SHA1 cua bieu dien JSON da sap xep — dung de phat hien DRIFT giua 2 phien ban."""
    raw = json.dumps(_r6(obj), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _subset_diff(got, want, path: str = "") -> list:
    """DANH SACH khac biet khi `want` phai la SUBSET cua `got` (so khop 1 phan)."""
    out = []
    if isinstance(want, dict):
        if not isinstance(got, dict):
            return ["%s: can dict, nhan %r" % (path or "<root>", type(got).__name__)]
        for k, wv in want.items():
            if k not in got:
                out.append("%s.%s: THIEU" % (path, k))
                continue
            out += _subset_diff(got[k], wv, "%s.%s" % (path, k))
        return out
    if isinstance(want, (list, tuple)):
        if not isinstance(got, (list, tuple)) or len(got) != len(want):
            return ["%s: can list %r, nhan %r" % (path, want, got)]
        for i, (gv, wv) in enumerate(zip(got, want)):
            out += _subset_diff(gv, wv, "%s[%d]" % (path, i))
        return out
    if isinstance(want, bool) or isinstance(got, bool):
        if bool(got) != bool(want):
            out.append("%s: can %r, nhan %r" % (path, want, got))
        return out
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        if abs(float(got) - float(want)) > TOL:
            out.append("%s: can %r, nhan %r" % (path, want, got))
        return out
    if got != want:
        out.append("%s: can %r, nhan %r" % (path, want, got))
    return out


def _eval_rule(out: dict, rule) -> tuple:
    """Danh gia 1 rule `duong.dan:toan_tu:gia_tri` -> (dieu_kien_DUNG?, thong_diep).

    Tach khoi `_check_rules` de `must` va `must_not` dung CUNG mot phep danh gia (ban dau
    gop lam mot ⇒ `must_not` bi dao nghia: rule DUNG lai bi bao la vi pham).
    """
    try:
        path, op, raw = str(rule).split(":", 2)
    except ValueError:
        return False, "rule sai dinh dang (can duong:toan_tu:gia_tri): %r" % (rule,)
    op = op.strip()
    if op not in OPS:
        return False, "toan tu la %r (hop le: %s)" % (op, ", ".join(OPS))
    try:
        val = json.loads(raw)
    except ValueError:
        val = raw
    try:
        got = _resolve(out, path)
    except (KeyError, IndexError, ValueError):
        return False, "%s: khong co trong output (rule %s)" % (path, rule)
    try:
        if op == "==":
            holds = _subset_diff(got, val, path) == []
        elif op == "!=":
            holds = _subset_diff(got, val, path) != []
        elif op == "<":
            holds = float(got) < float(val)
        elif op == "<=":
            holds = float(got) <= float(val)
        elif op == ">":
            holds = float(got) > float(val)
        elif op == ">=":
            holds = float(got) >= float(val)
        elif op == "contains":
            holds = str(val) in str(got)
        elif op == "not_contains":
            holds = str(val) not in str(got)
        else:                                   # "in"
            holds = got in (val if isinstance(val, (list, tuple)) else [val])
    except (TypeError, ValueError) as e:
        return False, "%s: khong so sanh duoc voi %r (%s)" % (path, val, e)
    return holds, "%s %s %r (nhan %r)" % (path, op, val, got)


def _check_rules(out: dict, rules, want: bool = True) -> list:
    """Kiem tra danh sach rule. `want=True`: phai DUNG; `want=False`: phai KHONG dung."""
    fails = []
    for rule in (rules or []):
        holds, msg = _eval_rule(out, rule)
        if holds != bool(want):
            fails.append(("phai dung: " if want else "phai KHONG dung: ") + msg)
    return fails



# --------------------------------------------------------------- adapters
# Moi adapter: nhan `input` cua ca -> goi HAM THAT -> tra dict JSON-serializable.
def _pos(d: dict, sym: str):
    """Dung `portfolio.Position` tu dict trong ca (thieu `tp` thi lay = entry)."""
    import portfolio as P
    return P.Position(symbol=sym, direction=str(d.get("direction") or "LONG"),
                      entry=float(d["entry"]), qty=float(d["qty"]),
                      sl=float(d["sl"]), tp=float(d.get("tp") or d["entry"]))


def _ad_feats(inp: dict) -> dict:
    """`learner.extract_features`: kiem tra clip/cong thuc feature (Measured Context).

    2 tham so DAU la bat buoc (`tech_score`, `sent`) — ca co the bo trong ⇒ mac dinh 0.0
    (trung tinh), nho vay ca van doc duoc nhu "khong co tin hieu".
    """
    import learner as L
    kw = dict(inp)
    kw.setdefault("tech_score", 0.0)
    kw.setdefault("sent", 0.0)
    return dict(L.extract_features(**kw))


def _ad_learner_edge(inp: dict) -> dict:
    """`OnlineLearner.edge`: trong so dat tu ca ⇒ tach hanh vi khoi file `learner.json`."""
    import learner as L
    tmp = os.path.join(tempfile.mkdtemp(prefix="gs_"), "khong_ton_tai.json")
    lyr = L.OnlineLearner(path=tmp)
    lyr.w.update({str(k): float(v) for k, v in (inp.get("weights") or {}).items()})
    lyr.b = float(inp.get("b", 0.0))
    feats = dict(inp.get("feats") or {})
    direction = str(inp.get("direction") or "LONG").upper()
    return {"edge": lyr.edge(feats, direction),
            "p_long": lyr.predict(feats),
            "n_updates": int(lyr.n_updates)}


def _ad_strategy_classify(inp: dict) -> dict:
    import strategy as S
    kw = {k: v for k, v in inp.items() if k != "direction"}
    return {"strategy": S.classify_strategy(inp.get("direction") or "LONG", **kw)}


def _ad_strategy_gate(inp: dict) -> dict:
    import strategy as S
    r = S.gate_check(str(inp.get("code") or "NONE"),
                     min_n=int(inp.get("min_n", 10)),
                     avg_r=float(inp.get("avg_r", 0.10)),
                     stats=inp.get("stats"),
                     blocklist=tuple(inp.get("blocklist") or ()))
    return {"blocked": bool(r.get("blocked")), "reason": str(r.get("reason") or ""),
            "n": int(r.get("n") or 0), "avg_r": float(r.get("avg_r") or 0.0)}


def _ad_lessons_gate(inp: dict) -> dict:
    import lessons as LS
    g = LS.gate_list(inp.get("buckets") or {},
                     min_n=int(inp.get("min_n", 20)),
                     max_avg_r=float(inp.get("max_avg_r", -0.30)))
    return {"n_gates": len(g),
            "keys": [str(x.get("key")) for x in g],
            "codes": [str(x.get("code")) for x in g]}


def _ad_risk_cap(inp: dict) -> dict:
    import portfolio as P
    equity = float(inp.get("equity") or 0.0)
    pos = {sym: _pos(d, sym) for sym, d in (inp.get("positions") or {}).items()}
    ok, why = P.can_add_risk(pos, equity, float(inp.get("cap_pct", 2.0)),
                             float(inp.get("new_risk_usd") or 0.0),
                             inp.get("initial_sl"))
    return {"ok": bool(ok), "reason": str(why),
            "cur_pct": float(P.total_risk_pct(pos, equity, inp.get("initial_sl")))}


def _ad_portfolio_open(inp: dict) -> dict:
    import portfolio as P
    pm = P.PortfolioManager(max_positions=int(inp.get("max_positions", 1)),
                            allow_hedge_opposite=bool(inp.get("allow_hedge_opposite", False)))
    for sym, d in (inp.get("positions") or {}).items():
        pm.positions[sym] = _pos(d, sym)
    ok, why = pm.can_open(str(inp.get("symbol") or ""), str(inp.get("direction") or "LONG"))
    return {"ok": bool(ok), "reason": str(why), "n_open": len(pm.positions)}


def _ad_journal_feats(inp: dict) -> dict:
    """Do TINH TOAN VEN cua `feats` that trong journal (thieu key / NaN / ngoai [-1,1])."""
    import learner as L
    path = Path(inp.get("journal") or "logs/journal.jsonl")
    if not path.is_absolute():
        path = ROOT / path
    limit = int(inp.get("limit", 500))
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"n_checked": 0, "violations": ["khong doc duoc %s: %s" % (path, e)]}
    rows = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("event") == "OPEN" and isinstance(d.get("feats"), dict):
            rows.append(d)
    stride = max(1, len(rows) // max(limit, 1))
    sample = rows[::stride][:limit]
    violations = []
    for r in sample:
        f = r["feats"]
        miss = [k for k in L.FEATURES if k not in f]
        band, junk = [], []
        for k in L.FEATURES:
            v = f.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                junk.append(k)
                continue
            if v != v:                      # NaN
                junk.append(k)
            elif not (-1.000001 <= float(v) <= 1.000001):
                band.append(k)
        if miss or junk or band:
            violations.append({"pair": r.get("pair"), "ts": r.get("ts"),
                               "miss": miss, "junk": junk, "out_of_band": band})
    return {"n_checked": len(sample), "n_open_rows": len(rows),
            "n_violations": len(violations), "violations": violations[:20]}


ADAPTERS = {
    "feats": _ad_feats,
    "learner_edge": _ad_learner_edge,
    "strategy_classify": _ad_strategy_classify,
    "strategy_gate": _ad_strategy_gate,
    "lessons_gate": _ad_lessons_gate,
    "risk_cap": _ad_risk_cap,
    "portfolio_open": _ad_portfolio_open,
    "journal_feats": _ad_journal_feats,
}




def _resolve(obj, path: str):
    """Lay gia tri theo duong dan `a.b.c`; thieu -> nem KeyError (ca se FAIL, dung y do)."""
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, (list, tuple)):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


# ----------------------------------------------------------------- runner
def validate_case(c: dict) -> str:
    """Schema ca. Tra '' neu hop le, nguoc lai tra ly do (ca hong phai HIEN, khong bi bo qua)."""
    if not isinstance(c, dict):
        return "khong phai object JSON"
    for k in REQUIRED:
        if k not in c:
            return "thieu truong %r" % k
    if str(c["kind"]) not in KINDS:
        return "kind la %r (hop le: %s)" % (c["kind"], ", ".join(KINDS))
    if str(c["component"]) not in COMPONENTS:
        return "component la %r (hop le: %s)" % (c["component"], ", ".join(COMPONENTS))
    if not isinstance(c["input"], dict):
        return "input phai la object"
    if not isinstance(c["expect"], dict):
        return "expect phai la object"
    for key in ("output", "must", "must_not"):
        if key in c["expect"] and key != "output" and not isinstance(c["expect"][key], list):
            return "expect.%s phai la list" % key
    return ""


def load_cases(path=None):
    """Doc `cases.jsonl` -> (cases, errors). File thieu/dong hong deu thanh `errors`."""
    path = Path(path or CASES_PATH)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [], ["khong doc duoc %s: %s" % (path, e)]
    cases, errors, seen = [], [], set()
    for i, ln in enumerate(text.splitlines(), 1):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        try:
            c = json.loads(ln)
        except ValueError as e:
            errors.append("dong %d: JSON hong (%s)" % (i, str(e)[:70]))
            continue
        why = validate_case(c)
        if why:
            errors.append("dong %d (%s): %s" % (i, (c or {}).get("id", "?"), why))
            continue
        cid = str(c["id"])
        if cid in seen:
            errors.append("dong %d: id TRUNG %r (khong the doi chieu baseline)" % (i, cid))
            continue
        seen.add(cid)
        cases.append(c)
    return cases, errors


def run_case(case: dict) -> dict:
    """Chay 1 ca: adapter -> so khop `expect.output` -> rule must/must_not."""
    comp = str(case.get("component"))
    out, why = {}, []
    ad = ADAPTERS.get(comp)
    if ad is None:
        why.append("khong co adapter cho component %r" % comp)
    else:
        try:
            out = ad(dict(case.get("input") or {}))
        except Exception as e:  # noqa: BLE001 - ca hong phai bao ro, khong lam chet runner
            why.append("adapter nem loi: %s: %s" % (type(e).__name__, str(e)[:160]))
    exp = case.get("expect") or {}
    if not why:
        out6 = _r6(out)
        why += _subset_diff(out6, exp.get("output") or {})
        why += _check_rules(out6, exp.get("must"), True)
        why += _check_rules(out6, exp.get("must_not"), False)
    return {"id": str(case.get("id")), "kind": str(case.get("kind")),
            "component": comp, "title": str(case.get("title") or ""),
            "source": str(case.get("source") or ""), "ok": not why, "why": why,
            "output": _r6(out), "digest": _digest(out)}


def evaluate(cases, baseline: dict | None = None) -> dict:
    """Chay het bo ca + so voi baseline (neu co) -> report tong hop."""
    t0 = time.time()
    rows = [run_case(c) for c in cases]
    by_kind, by_comp = {}, {}
    for r in rows:
        for bucket, key in ((by_kind, r["kind"]), (by_comp, r["component"])):
            b = bucket.setdefault(key, {"n": 0, "ok": 0})
            b["n"] += 1
            b["ok"] += 1 if r["ok"] else 0
    drift = []
    base = (baseline or {}).get("digest") or {}
    if base:
        for r in rows:
            old = base.get(r["id"])
            if old and old != r["digest"]:
                drift.append({"id": r["id"], "component": r["component"]})
    failed = [r for r in rows if not r["ok"]]
    return {"ok": not failed and not drift, "n": len(rows),
            "passed": len(rows) - len(failed), "failed": len(failed),
            "by_kind": by_kind, "by_component": by_comp,
            "failures": [{"id": r["id"], "why": r["why"]} for r in failed],
            "drift": drift, "digest": {r["id"]: r["digest"] for r in rows},
            "secs": round(time.time() - t0, 3), "rows": rows,
            "baseline_used": bool(base)}


# ------------------------------------------------------------------ CLI
def load_baseline(path=None) -> dict:
    """Baseline (digest tung ca). Hong/thieu -> {} (lan dau chay: khong co drift)."""
    try:
        with open(Path(path or BASELINE_PATH), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def write_baseline(report: dict, path=None) -> str:
    """Chot hanh vi hien tai. Dung `atomic` (file trang thai cua repo) + chi ghi khi 100% PASS."""
    import atomic
    p = str(path or BASELINE_PATH)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    atomic.write_json_atomic(p, {"ts": time.time(),
                                 "n": report.get("n"),
                                 "digest": report.get("digest") or {}})
    return p


def format_report(rep: dict, verbose: bool = False) -> str:
    """Bang bao cao cho nguoi doc (khong phai JSON)."""
    lines = ["GOLDEN SET — %d ca | PASS %d | FAIL %d | %.3fs%s"
             % (rep["n"], rep["passed"], rep["failed"], rep["secs"],
                "  [baseline]" if rep.get("baseline_used") else "")]
    for kind in KINDS:
        b = (rep.get("by_kind") or {}).get(kind)
        if b:
            lines.append("  %-8s %2d/%2d dat" % (kind, b["ok"], b["n"]))
    for comp, b in sorted((rep.get("by_component") or {}).items()):
        lines.append("  - %-18s %2d/%2d" % (comp, b["ok"], b["n"]))
    if verbose:
        for r in rep.get("rows") or []:
            lines.append("  [%s] %-28s %-16s %s"
                         % ("OK  " if r["ok"] else "FAIL", r["id"], r["component"],
                            r.get("title") or ""))
    for f in rep.get("failures") or []:
        lines.append("  FAIL %s" % f["id"])
        for w in f["why"][:6]:
            lines.append("       - %s" % w)
    if rep.get("drift"):
        lines.append("  DRIFT so voi baseline (%d ca doi hanh vi):" % len(rep["drift"]))
        for d in rep["drift"][:12]:
            lines.append("       - %s (%s)" % (d["id"], d["component"]))
        lines.append("       (xem lai tung ca roi moi `--write-baseline` neu thay doi la DUNG)")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Golden-set eval cho cac cong quyet dinh (offline)")
    ap.add_argument("--cases", default=str(CASES_PATH), help="file cases.jsonl")
    ap.add_argument("--baseline", default=str(BASELINE_PATH), help="file baseline.json")
    ap.add_argument("--only", default="", help="chi chay component nay (vd risk_cap)")
    ap.add_argument("--verbose", action="store_true", help="in tung ca")
    ap.add_argument("--json", action="store_true", help="in JSON (cho tool khac doc)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 neu co ca FAIL hoac DRIFT (dung trong watcher/CI)")
    ap.add_argument("--no-baseline", action="store_true", help="bo qua baseline")
    ap.add_argument("--write-baseline", action="store_true",
                    help="chot hanh vi hien tai (chi khi 100%% PASS)")
    args = ap.parse_args(argv)

    cases, errors = load_cases(args.cases)
    if args.only:
        cases = [c for c in cases if str(c["component"]) == args.only]
    if not cases:
        print("GOLDEN SET — KHONG CO CA NAO%s"
              % ("" if not errors else " (loi schema: %s)" % "; ".join(errors[:5])))
        return 2
    baseline = {} if args.no_baseline else load_baseline(args.baseline)
    rep = evaluate(cases, baseline)
    rep["schema_errors"] = errors
    if args.write_baseline:
        if rep["ok"]:
            p = write_baseline(rep, args.baseline)
            if not args.json:
                print("da chot baseline: %s (%d ca)" % (p, rep["n"]))
        elif not args.json:
            print("KHONG chot baseline: con %d ca FAIL / %d ca DRIFT"
                  % (rep["failed"], len(rep["drift"])))
    if args.json:
        print(json.dumps({k: v for k, v in rep.items() if k != "rows"},
                         ensure_ascii=False, indent=2, default=str))
    else:
        print(format_report(rep, args.verbose))
        if errors:
            print("  SCHEMA ERRORS (%d):" % len(errors))
            for e in errors[:8]:
                print("       - %s" % e)
    if errors:
        return 2
    return 0 if (rep["ok"] or not args.check) else 1


if __name__ == "__main__":
    sys.exit(main())

