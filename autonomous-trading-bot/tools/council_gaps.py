"""Liet ke THIEU HUT cua hoi dong + ke hoach TU HOC (offline, chi doc journal).

    python tools\\council_gaps.py              # in danh sach thieu hut + viec can lam
    python tools\\council_gaps.py --write      # ghi logs/council_gaps.json + COUNCIL_GAPS.md
    python tools\\council_gaps.py --check      # exit 1 neu con thieu hut muc CAO
    python tools\\council_gaps.py --json

Vi sao co (09/11): hoi dong KHONG du thong minh de tu biet minh thieu gi — do that:
`brier 0.341`, chi ghep duoc **0 phieu chinh xac** (chua co `decision_id`), va mot so model
co `value_r <= 0`. Nhung "khong du thong minh" khong duoc bien thanh "ngoi cho nguoi van
hanh": moi thieu hut o day duoc RUT RA TU SO LIEU, va moi thieu hut bat buoc kem:
  * `metric`/`value`/`target` — do cai gi, dang bao nhieu, can bao nhieu;
  * `needs`  — THONG TIN CHI TIET con thieu (danh sach de TU DI THU, khong phai cau hoi
               cho nguoi: moi muc la 1 lenh/tool chay duoc);
  * `action` — viec cu the phai lam (thuong la 1 dong lenh hoac 1 test);
  * `auto`   — co tu lam duoc khong (khong can nguoi).
Danh sach nay la dau vao cua `tools/selfops.py` (tu van hanh) va cua harness ledger.

Nguyen tac: ham THUAN TUY `gaps_from(data)` -> test duoc voi so lieu gia; phan `collect()`
chi doc file, khong goi mang.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

#: Muc do nghiem trong.
SEV_HIGH, SEV_MED, SEV_LOW = "high", "med", "low"
MIN_N_MODEL = 8           # cung nguong voi `council_eval --min-n`
TARGET_BRIER = 0.25       # > 0.25 = doan bua
TARGET_EXACT_MATCH = 0.8  # >= 80% phieu phai ghep CHINH XAC (decision_id)
MAX_BLOCK_SHARE = 0.7     # 1 ly do chiem > 70% so lan bi chan = nghi chan qua tay


def journal_stats(path) -> dict:
    """Dem so lieu THAT trong journal (1 lan doc): phieu, ma ly do, tuoi du lieu, khoa ghep."""
    st = {"rows": 0, "agent": 0, "agent_with_did": 0, "open": 0, "open_stale": 0,
          "codes": {}, "bad_rows": 0}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return st
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            st["bad_rows"] += 1
            continue
        if not isinstance(d, dict):
            continue
        st["rows"] += 1
        ev = str(d.get("event") or "").upper()
        code = str(d.get("reason_code") or "")
        if code:
            st["codes"][code] = int(st["codes"].get(code, 0)) + 1
        if ev == "AGENT":
            st["agent"] += 1
            if d.get("decision_id"):
                st["agent_with_did"] += 1
        elif ev == "OPEN" or (not ev and d.get("pair")):
            st["open"] += 1
            for v in (d.get("data_age") or {}).values():
                if isinstance(v, dict) and str(v.get("level")) in ("stale", "dead"):
                    st["open_stale"] += 1
                    break
    return st


def _skip_codes(stats: dict) -> dict:
    """Cac ma KHONG phai 'vao lenh' (bo TAKE) — de tim ly do bi chan chiem uu the."""
    return {k: v for k, v in (stats.get("codes") or {}).items()
            if str(k) not in ("TAKE", "")}


def collect(journal_path=None, hours: float = 720.0, now: float | None = None) -> dict:
    """Thu thap so lieu cho phan tich (CHI doc). Loi -> tra phan rong, khong nem."""
    import council_evals as CE
    jp = str(journal_path or (ROOT / "logs" / "journal.jsonl"))
    out: dict = {"journal": jp, "ts": float(now or time.time()), "hours": hours}
    try:
        out["council"] = CE.model_leaderboard(jp, hours=hours, min_n=MIN_N_MODEL,
                                              now=out["ts"])
    except Exception as e:  # noqa: BLE001
        out["council"] = {"per_model": {}, "cases": 0, "match": {},
                          "calibration": {}, "error": str(e)[:160]}
    out["stats"] = journal_stats(jp)
    return out


def gaps_from(data: dict, min_n: int = MIN_N_MODEL) -> list:
    """Danh sach thieu hut tu so lieu (ham THUAN TUY — test duoc voi dict gia).

    Moi muc: id, severity, metric, value, target, needs[], action, auto.
    """
    gaps: list = []
    rep = (data or {}).get("council") or {}
    st = (data or {}).get("stats") or {}
    match = rep.get("match") or {}
    cal = rep.get("calibration") or {}
    per = rep.get("per_model") or {}

    # 1) GHEP PHIEU <-> LENH: neu khong chinh xac thi moi chi so ben duoi deu la DOAN.
    exact = match.get("exact_rate")
    if match.get("matched") and (exact is None or float(exact) < TARGET_EXACT_MATCH):
        gaps.append({
            "id": "match_exact", "severity": SEV_HIGH,
            "metric": "ty le ghep CHINH XAC (decision_id)", "value": exact,
            "target": TARGET_EXACT_MATCH,
            "needs": [
                "journal co `decision_id` o CA `AGENT` va `OPEN` (code da san, phai restart)",
                ">= 30 phieu/model co `decision_id` de so sanh",
                "10 cap ghep mau (phieu -> lenh) de kiem tay bang `tools/trace_trade.py`",
            ],
            "action": "restart 2 instance roi chay lai `python tools/council_eval.py`",
            "auto": True,
        })
    if not match.get("matched"):
        gaps.append({
            "id": "data_absent", "severity": SEV_HIGH,
            "metric": "so phieu ghep duoc lenh", "value": match.get("matched"),
            "target": ">= 30",
            "needs": ["journal co ban ghi `CLOSE` kem `r` hoac `won`",
                      "phieu `AGENT` bo TRUOC khi vao lenh (khong phai review)"],
            "action": "kiem tra instance/journal: `python tools/journal_tail.py -n 50`",
            "auto": True,
        })

    # 2) HIEU CHUAN: brier > 0.25 = hoi dong tu tin hon thuc te.
    brier = cal.get("brier")
    if brier is None or float(brier) > TARGET_BRIER:
        gaps.append({
            "id": "calibration", "severity": SEV_HIGH,
            "metric": "brier", "value": brier, "target": "<= %s" % TARGET_BRIER,
            "needs": [
                ">= 30 phieu co `confidence` VA co ket qua that",
                "phan bo confidence theo khoang (calibration bins) de biet lech o dau",
                "so mau `lessons_hint` (n) di kem moi phieu — de biet co bang chung hay khong",
            ],
            "action": "giu `AGENT_CALIB_CAP=true`; do lai brier sau >= 30 phieu moi",
            "auto": True,
        })

    # 3) MODEL THIEU MAU hoac GIA TRI AM: chua ket luan duoc / nen bo.
    thin = sorted(rep.get("thin") or [])
    if thin:
        gaps.append({
            "id": "thin_models", "severity": SEV_MED,
            "metric": "so model co n_ghep < min_n", "value": len(thin), "target": 0,
            "needs": ["n_ghep >= %d cho tung model (dang thieu: %s)" % (min_n, ", ".join(thin)),
                      "1 lan chay `tools/council_probe.py --live` de do A/B co kiem soat"],
            "action": "chay them phien (hoac bo model treo) roi do lai",
            "auto": True,
        })
    bad_value = sorted(m for m, b in per.items()
                       if b.get("value_r") is not None and float(b["value_r"]) <= 0)
    if bad_value:
        gaps.append({
            "id": "value_negative", "severity": SEV_MED,
            "metric": "model co value_r <= 0", "value": len(bad_value), "target": 0,
            "needs": ["value_r + n cua tung model (%s)" % ", ".join(bad_value),
                      "xac nhan khong phai do ghep nham (xem `match_exact`)"],
            "action": "sau khi ghep chinh xac: them vao `CLINE_SKIP_MODELS`/`LOCAL_SKIP_MODELS`",
            "auto": False,
        })

    # 4) LY DO BI CHAN chiem uu the: nghi chan qua tay (mat co hoi) hoac 1 cong hong.
    codes = _skip_codes(st)
    total = sum(codes.values())
    if total >= 100 and codes:
        top, n = max(codes.items(), key=lambda kv: kv[1])
        share = n / float(total)
        if share > MAX_BLOCK_SHARE:
            gaps.append({
                "id": "block_dominance", "severity": SEV_MED,
                "metric": "ty le 1 ma ly do tren tong so lan bi chan",
                "value": round(share, 3), "target": "<= %s" % MAX_BLOCK_SHARE,
                "needs": ["ma `%s` xuat hien %d/%d lan — lay 20 ban ghi mau" % (top, n, total),
                          "doi chieu nguong tuong ung trong config (vd MAX_TOTAL_RISK_PCT)"],
                "action": "doc 20 mau + so nguong: `python tools/journal_tail.py -n 200`",
                "auto": True,
            })

    # 5) TUOI DU LIEU: co lenh mo khi nguon stale/dead ⇒ quyet dinh tren du lieu cu.
    if int(st.get("open_stale") or 0) > 0:
        gaps.append({
            "id": "stale_data", "severity": SEV_MED,
            "metric": "so lenh mo khi co nguon du lieu stale/dead",
            "value": int(st["open_stale"]), "target": 0,
            "needs": ["phan bo `data_age` theo nguon trong journal",
                      "TTL hien tai (`DATA_TTL_SEC`) vs chu ky fetch that"],
            "action": "chinh `DATA_TTL_SEC`/`DATA_TTL_HARD_MULT` trong `.env`",
            "auto": True,
        })

    # 6) JOURNAL HONG: ban ghi khong parse duoc ⇒ moi thong ke deu thieu.
    if int(st.get("bad_rows") or 0) > 0:
        gaps.append({
            "id": "journal_bad_rows", "severity": SEV_MED,
            "metric": "so dong journal khong parse duoc", "value": int(st["bad_rows"]),
            "target": 0,
            "needs": ["vi tri + noi dung 5 dong hong", "nguyen nhan (ghi ngang / het dia)"],
            "action": "`python tools/drift_probe.py` + kiem tra dung luong dia",
            "auto": True,
        })
    return gaps


def study_plan(gaps: list) -> str:
    """Ke hoach TU HOC dang markdown: moi thieu hut -> hoc gi, lay thong tin o dau."""
    ordered = sorted(gaps or [], key=lambda g: (g.get("severity") != SEV_HIGH, str(g.get("id"))))
    lines = ["# KE HOACH TU HOC CUA HOI DONG (tu sinh tu so lieu, khong phai y kien)",
             "", "| # | Thieu hut | Do (hien tai -> can) | Tu lam |", "|---|---|---|---|"]
    for i, g in enumerate(ordered, 1):
        lines.append("| %d | %s | %s: %s -> %s | %s |"
                     % (i, g.get("id"), g.get("metric"), g.get("value"), g.get("target"),
                        "co" if g.get("auto") else "KHONG (can nguoi)"))
    lines.append("")
    for g in ordered:
        lines.append("## %s (%s)" % (g.get("id"), g.get("severity")))
        lines.append("- Do: **%s = %s** (can: %s)"
                     % (g.get("metric"), g.get("value"), g.get("target")))
        lines.append("- Can thu thap / lam:")
        for n in g.get("needs") or []:
            lines.append("  - [ ] %s" % n)
        lines.append("- Viec phai lam: %s" % g.get("action"))
        lines.append("- Tu lam duoc: %s" % ("CO" if g.get("auto") else
                                            "KHONG — phai co nguoi (ghi vao `tools/ops_queue.py`)"))
        lines.append("")
    return "\n".join(lines)


def render(gaps: list, data: dict | None = None) -> str:
    """Ban in gon cho terminal."""
    d = data or {}
    rep = d.get("council") or {}
    st = d.get("stats") or {}
    mt = rep.get("match") or {}
    out = ["=== THIEU HUT CUA HOI DONG | %d muc | journal %d dong (%d AGENT co decision_id) ==="
           % (len(gaps), int(st.get("rows") or 0), int(st.get("agent_with_did") or 0))]
    if mt:
        out.append("  ghep phieu->lenh: %s/%s | chinh xac %s | brier %s"
                   % (mt.get("matched"), mt.get("n"), mt.get("exact_rate"),
                      (rep.get("calibration") or {}).get("brier")))
    for g in sorted(gaps, key=lambda x: (x.get("severity") != SEV_HIGH, str(x.get("id")))):
        out.append("  [%s] %-18s %s: %s -> %s  (%s)"
                   % (str(g.get("severity")).upper(), g.get("id"), g.get("metric"),
                      g.get("value"), g.get("target"),
                      "tu lam" if g.get("auto") else "can nguoi"))
        for n in (g.get("needs") or [])[:3]:
            out.append("        - can: %s" % n)
    if not gaps:
        out.append("  KHONG co thieu hut muc nao (moi chi so dat nguong)")
    return "\n".join(out)


def write_artifacts(gaps: list, data: dict, root: Path | None = None) -> dict:
    """Ghi `logs/council_gaps.json` + `COUNCIL_GAPS.md` (nguyen tu). Tra duong dan."""
    base = Path(root or ROOT)
    logs = base / "logs"
    try:
        logs.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    jp = logs / "council_gaps.json"
    mp = base / "COUNCIL_GAPS.md"
    payload = {"ts": (data or {}).get("ts"), "journal": (data or {}).get("journal"),
               "n": len(gaps), "gaps": gaps,
               "high": [g["id"] for g in gaps if g.get("severity") == SEV_HIGH]}
    ok = True
    try:
        jp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        mp.write_text(study_plan(gaps), encoding="utf-8")
    except OSError:
        ok = False
    return {"json": str(jp), "md": str(mp), "ok": ok}


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Liet ke thieu hut cua hoi dong + ke hoach tu hoc")
    ap.add_argument("--journal", default=str(ROOT / "logs" / "journal.jsonl"))
    ap.add_argument("--hours", type=float, default=720.0)
    ap.add_argument("--min-n", type=int, default=MIN_N_MODEL)
    ap.add_argument("--write", action="store_true", help="ghi logs/council_gaps.json + COUNCIL_GAPS.md")
    ap.add_argument("--check", action="store_true", help="exit 1 neu con thieu hut muc CAO")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    data = collect(args.journal, hours=args.hours)
    gaps = gaps_from(data, min_n=args.min_n)
    if args.write:
        paths = write_artifacts(gaps, data)
        if not args.json:
            print("da ghi: %s" % paths["json"])
            print("da ghi: %s" % paths["md"])
    if args.json:
        print(json.dumps({"ts": data["ts"], "gaps": gaps}, ensure_ascii=False, indent=1))
    else:
        print(render(gaps, data))
    if args.check:
        return 1 if any(g.get("severity") == SEV_HIGH for g in gaps) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


