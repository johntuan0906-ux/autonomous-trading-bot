"""TU VAN HANH: tu quyet dinh viec gi can lam roi TU CHAY (dry-run mac dinh).

    python tools\\selfops.py                     # in ke hoach (khong chay gi)
    python tools\\selfops.py --apply             # chay cac viec AN TOAN (tu hoc/tu kiem)
    python tools\\selfops.py --apply --instance live   # van KHONG dung state cua LIVE
    python tools\\selfops.py --apply --allow-live-state  # cho phep restart/reset tren LIVE

Vi sao co (09/11): nguoi van hanh yeu cau "hoi dong tu van hanh, nguoi chi xem va gop y".
Nguyen tac an toan (khong thuong luong duoc):
  * viec CHI DOC (gap analysis, drift tai lieu, golden set) -> tu chay;
  * viec GHI khong lien quan tien (refit learner, don lessons) -> tu chay khi du dieu kien;
  * viec DUNG/CHAY bot hoac GO KILL-SWITCH -> chi tu chay khi:
      - instance la TESTNET, VA
      - `--apply` duoc bat, VA
      - voi LIVE: phai co `--allow-live-state` (mac dinh TAT — con nguoi giu quyen nay).
  * moi hanh dong deu ghi `logs/autonomy.jsonl` (ly do + bang chung + ket qua) de doc lai duoc.
  * viec KHONG tu lam duoc (can quyet dinh chien luoc) -> day vao `tools/ops_queue.py` de
    nguoi doc va gop y, KHONG chan he thong.

Khong goi mang o day: moi viec nang deu la subprocess co timeout, va ham `plan()` la THUAN TUY
(kiem tra duoc bang test voi state gia).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "tools"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

JOURNAL = ROOT / "logs" / "journal.jsonl"
AUTONOMY_LOG = ROOT / "logs" / "autonomy.jsonl"
HEARTBEAT = ROOT / "logs" / "heartbeat.json"
RISK_STATE = ROOT / "logs" / "risk_state.json"
LEARNER_STATE = ROOT / "logs" / "learner.json"

#: Nguong cho tung quyet dinh (doi duoc bang tham so CLI/env, nhung mac dinh phai ro rang).
HB_STALE_SEC = 600.0        # nhip tim cu hon 10 phut = bot khong chay
REFIT_MIN_UPDATES = 200     # du mau moi refit
REFIT_EVERY_SEC = 12 * 3600.0


def _read_json(path, default=None):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
        return d if isinstance(d, dict) else (default if default is not None else {})
    except (OSError, ValueError):
        return default if default is not None else {}


def _positions_open(root: Path | None = None) -> int:
    """So vi the dang mo theo journal (OPEN chua co CLOSE) — khong goi san."""
    import council_evals as CE
    jp = Path(root or ROOT) / "logs" / "journal.jsonl"
    try:
        recs = CE.load_recs(str(jp))
    except Exception:  # noqa: BLE001
        return 0
    opened, closed = set(), set()
    for r in recs:
        pair = str(r.get("pair") or r.get("symbol") or "")
        if not pair:
            continue
        ev = str(r.get("event") or "").upper()
        if ev == "OPEN":
            opened.add(pair)
        elif ev == "CLOSE":
            closed.add(pair)
    return len(opened - closed)


def _last_action_ts(action: str, path=None) -> float:
    """Moc thoi gian lan CUOI chay `action` thanh cong (doc `logs/autonomy.jsonl`).

    Vi sao can: `learner_refit.py` khi ket luan "TRUNG TINH" thi KHONG ghi file ⇒ neu chi
    doc `learner.json` thi lan nao cung thay "chua refit bao gio" va se refit lai MOI vong
    (dot CPU + dao dong tam). Nhat ky tu van hanh la nguon su that cho "da lam hay chua".
    """
    p = Path(path or AUTONOMY_LOG)
    last = 0.0
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
    except OSError:
        return 0.0
    for ln in lines:
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if str(d.get("action")) == action and d.get("applied"):
            last = max(last, float(d.get("ts") or 0.0))
    return last


def state(now: float | None = None, root: Path | None = None) -> dict:
    """Doc trang thai THAT tu file (khong mang) — dau vao cua `plan()`.

    `root` cho phep doc INSTANCE khac (`atb-live`) thay vi repo dang chay.
    """
    import entries_gate
    base = Path(root or ROOT)
    t = float(now if now is not None else time.time())
    hb = _read_json(base / "logs" / "heartbeat.json", {})
    risk = _read_json(base / "logs" / "risk_state.json", {})
    learner = _read_json(base / "logs" / "learner.json", {})
    try:
        paused, why = entries_gate.paused(path=str(base / "logs" / "entries_pause.json"))
    except Exception:  # noqa: BLE001
        paused, why = False, ""
    refit = (learner.get("refit") or {})
    refit_ts = float(refit.get("ts") or 0.0) if isinstance(refit, dict) else 0.0
    return {
        "root": str(base), "now": t,
        "day": datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"),
        "heartbeat_ts": float(hb.get("ts") or 0.0),
        "heartbeat_age": (t - float(hb.get("ts") or 0.0)) if hb.get("ts") else None,
        "kill_tripped": bool(risk.get("tripped")),
        "kill_reason": str(risk.get("reason") or ""),
        "kill_day": str(risk.get("day") or ""),
        "open_positions": _positions_open(base),
        "entries_paused": bool(paused), "entries_reason": str(why or ""),
        "learner_n": int(learner.get("n") or 0),
        # (09/11) uu tien moc trong `learner.json`; neu chua co thi lay tu nhat ky tu van hanh
        "learner_refit_ts": max(refit_ts, _last_action_ts("refit", base / "logs"
                                                          / "autonomy.jsonl")),
    }


def plan(st: dict, gaps: list | None = None, instance: str = "testnet",
         now: float | None = None, hb_stale_sec: float = HB_STALE_SEC,
         refit_min: int = REFIT_MIN_UPDATES, refit_every: float = REFIT_EVERY_SEC,
         root: Path | None = None) -> list:
    """Danh sach viec CAN LAM tu trang thai + danh sach thieu hut (ham THUAN TUY).

    Moi muc: id, action (mo ta), cmd (list | None neu lam trong tien trinh), why, evidence,
    reason_code, auto (co tu chay duoc khong), live_state (co dung vao state cua LIVE khong).
    `root` = thu muc INSTANCE (de chay dung tool cua instance do, khong lay nham cua root).
    """
    s = st or {}
    base = Path(root or ROOT)
    t = float(now if now is not None else s.get("now") or time.time())
    out: list = []

    def add(**kw):
        kw.setdefault("auto", True)
        kw.setdefault("live_state", False)
        kw.setdefault("cmd", None)
        out.append(kw)

    add(id="gaps", action="phan tich thieu hut + ghi COUNCIL_GAPS.md",
        why="moi quyet dinh cua hoi dong phai dua tren so lieu do duoc, khong dua vao cam tinh",
        evidence={"gaps": len(gaps or [])}, reason_code="", inproc=True)
    add(id="drift_docs", action="so khop tai lieu <-> code",
        cmd=[sys.executable, str(base / "tools" / "drift_docs.py"), "--check"],
        why="tai lieu lech code lam ra quyet dinh tren so lieu cu", reason_code="")
    add(id="golden", action="chay golden set (hanh vi co doi khong)",
        cmd=[sys.executable, str(base / "tools" / "golden_set.py"), "--check"],
        why="sua code co the lam MAT hanh vi cu ma test van xanh", reason_code="")

    # --- refit learner: hoc lai tu du lieu THAT khi du mau va da lau ---
    n = int(s.get("learner_n") or 0)
    last = float(s.get("learner_refit_ts") or 0.0)
    if n >= int(refit_min) and (last <= 0 or (t - last) >= float(refit_every)):
        add(id="refit", action="hoc lai learner tren du lieu that (holdout 80/20)",
            cmd=[sys.executable, str(base / "tools" / "learner_refit.py")],
            why="du mau (%d cap nhat) va da >= %.0f gio tu lan refit truoc"
                % (n, float(refit_every) / 3600.0),
            evidence={"learner_n": n, "last_refit_age_h": round((t - last) / 3600.0, 1)
                      if last else None}, reason_code="MODEL_UNCALIBRATED")

    # --- nhip tim chet: bot khong chay (chi tu khoi dong lai khi KHONG phai LIVE) ---
    age = s.get("heartbeat_age")
    if age is not None and float(age) > float(hb_stale_sec):
        add(id="restart", action="khoi dong lai bot (nhip tim qua cu)",
            cmd=[sys.executable, str(base / "tools" / "restart_bot.py")],
            why="nhip tim cu %.0f giay > %.0f giay ⇒ bot khong chay"
                % (float(age), float(hb_stale_sec)),
            evidence={"heartbeat_age": round(float(age), 1),
                      "open_positions": s.get("open_positions")},
            reason_code="PROVIDER_DOWN", auto=(str(instance).lower() != "live"),
            live_state=True)

    # --- kill-switch: chi tu go khi TESTNET, sang ngay moi, khong con vi the ---
    if s.get("kill_tripped"):
        flat = int(s.get("open_positions") or 0) == 0
        new_day = str(s.get("kill_day") or "") not in ("", str(s.get("day")))
        if flat and new_day:
            add(id="kill_reset", action="go kill-switch (da sang ngay UTC, khong con vi the)",
                cmd=[sys.executable, str(base / "risk.py"), "--reset"],
                why="kill-switch trip ngay %s, hom nay %s, dang flat ⇒ du dieu kien mo lai"
                    % (s.get("kill_day"), s.get("day")),
                evidence={"kill_reason": s.get("kill_reason"),
                          "open_positions": s.get("open_positions")},
                reason_code="KILL_SWITCH", auto=(str(instance).lower() != "live"),
                live_state=True)
        else:
            add(id="kill_review", action="kill-switch dang trip — CHI bao cao, khong tu go",
                why="chua du dieu kien tu go (flat=%s, sang ngay moi=%s)"
                    % (flat, new_day),
                evidence={"kill_reason": s.get("kill_reason"),
                          "open_positions": s.get("open_positions"),
                          "kill_day": s.get("kill_day"), "today": s.get("day")},
                reason_code="KILL_SWITCH", auto=False, live_state=True)

    # --- entries pause: het han thi `entries_gate` tu mo; con han thi chi bao ---
    if s.get("entries_paused"):
        add(id="entries_paused", action="bao cao tam dung vao lenh",
            why="dang tam dung: %s" % (s.get("entries_reason") or ""),
            evidence={"reason": s.get("entries_reason")},
            reason_code="ENTRIES_PAUSED", auto=False)
    return out


def _run_cmd(cmd: list, timeout: float = 120.0, cwd=None) -> dict:
    """Chay 1 lenh con (khong shell) -> {rc, out} (out = 400 ky tu cuoi)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=float(timeout),
                           cwd=str(cwd or ROOT))
        tail = ((p.stdout or "") + (p.stderr or "")).strip()[-400:]
        return {"rc": int(p.returncode), "out": tail}
    except subprocess.TimeoutExpired:
        return {"rc": -9, "out": "timeout sau %.0f giay" % float(timeout)}
    except Exception as e:  # noqa: BLE001
        return {"rc": -1, "out": "%s: %s" % (type(e).__name__, str(e)[:200])}


def _log(rec: dict, path=None) -> None:
    """Ghi 1 dong `logs/autonomy.jsonl` (append, loi -> im lang: khong lam chet vong)."""
    p = Path(path or AUTONOMY_LOG)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def run(items: list, apply: bool = False, allow_live_state: bool = False,
        instance: str = "testnet", now: float | None = None, log_path=None,
        root: Path | None = None) -> dict:
    """Thuc thi ke hoach. `apply=False` -> chi bao cao (mac dinh).

    Chan cung: viec `live_state=True` tren instance LIVE chi chay khi `allow_live_state`
    duoc bat — con nguoi giu quyen voi state cua tai khoan that.
    """
    import council_gaps as CG
    t = float(now if now is not None else time.time())
    is_live = str(instance).lower() == "live"
    results: list = []
    for it in items or []:
        blocked = ""
        if not it.get("auto"):
            blocked = "khong tu lam duoc (can nguoi xem)"
        elif is_live and it.get("live_state") and not allow_live_state:
            blocked = "state cua LIVE: can `--allow-live-state` (mac dinh tat)"
        rec = {"ts": t, "instance": instance, "action": it.get("id"),
               "why": it.get("why"), "reason_code": it.get("reason_code") or "",
               "evidence": it.get("evidence") or {}, "applied": False, "skipped": blocked}
        if apply and not blocked:
            if it.get("inproc"):
                try:
                    _jp = str(Path(root or ROOT) / "logs" / "journal.jsonl")
                    data = CG.collect(_jp)
                    gaps = CG.gaps_from(data)
                    paths = CG.write_artifacts(gaps, data, root)
                    rec.update({"applied": True, "rc": 0 if paths.get("ok") else 1,
                                "out": paths.get("md")})
                except Exception as e:  # noqa: BLE001
                    rec.update({"rc": -1, "out": "%s: %s" % (type(e).__name__, str(e)[:150])})
            elif it.get("cmd"):
                r = _run_cmd(it["cmd"], cwd=str(root or ROOT))
                rec.update({"applied": True, "rc": r["rc"], "out": r["out"]})
        _log(rec, log_path)
        results.append(rec)
    return {"ts": t, "instance": instance, "applied": bool(apply),
            "n": len(results),
            "done": [r["action"] for r in results if r.get("applied")],
            "skipped": [r["action"] for r in results if r.get("skipped")],
            "failed": [r["action"] for r in results if r.get("applied") and r.get("rc")],
            "rows": results}


def push_to_queue(items: list, cfg=None) -> list:
    """Day viec KHONG tu lam duoc vao `tools/ops_queue.py` (nguoi doc + gop y, khong chan)."""
    import ops_queue as OQ
    pushed: list = []
    for it in items or []:
        if it.get("auto"):
            continue
        try:
            r = OQ.add("Tu van hanh: %s" % (it.get("action") or it.get("id")),
                       why="%s | bang chung: %s" % (it.get("why") or "",
                                                    json.dumps(it.get("evidence") or {},
                                                               ensure_ascii=False)),
                       options=["dong y", "khong dong y", "de sau"],
                       priority="normal")
            pushed.append(r)
        except Exception:  # noqa: BLE001
            continue
    return pushed


def render(rep: dict, items: list) -> str:
    out = ["=== TU VAN HANH | instance=%s | %s | viec %d ==="
           % (rep.get("instance"), "APPLY" if rep.get("applied") else "DRY-RUN",
              int(rep.get("n") or 0))]
    for it in items:
        tag = "tu lam" if it.get("auto") else "can nguoi"
        if it.get("live_state"):
            tag += "/state"
        out.append("  [%-9s] %-14s %s" % (tag, it.get("id"), it.get("action")))
        out.append("        vi sao: %s" % (it.get("why") or ""))
    if rep.get("done"):
        out.append("  DA CHAY: %s" % ", ".join(rep["done"]))
    if rep.get("skipped"):
        out.append("  BO QUA: %s" % ", ".join(rep["skipped"]))
    if rep.get("failed"):
        out.append("  LOI: %s" % ", ".join(rep["failed"]))
    return "\n".join(out)


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Tu van hanh: tu hoc + tu kiem + tu sua (co gioi han)")
    ap.add_argument("--instance", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--root", default="", help="thu muc instance (mac dinh: theo --instance)")
    ap.add_argument("--apply", action="store_true", help="chay that (mac dinh chi in ke hoach)")
    ap.add_argument("--allow-live-state", action="store_true",
                    help="cho phep restart/reset tren LIVE (mac dinh TAT)")
    ap.add_argument("--queue", action="store_true",
                    help="day viec 'can nguoi' vao tools/ops_queue.py")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    import council_gaps as CG
    # (09/11) LIVE nam o thu muc khac (`atb-live`): doc SAI instance thi ke hoach vo nghia
    # (vd doc heartbeat cua TESTNET roi tu restart LIVE).
    base = Path(args.root) if args.root else (
        ROOT.parent / "atb-live" if args.instance == "live" else ROOT)
    if args.instance == "live" and not base.exists():
        print("KHONG thay thu muc instance LIVE: %s" % base)
        return 2
    data = CG.collect(str(base / "logs" / "journal.jsonl"))
    gaps = CG.gaps_from(data)
    st = state(root=base)
    items = plan(st, gaps, instance=args.instance, root=base)
    rep = run(items, apply=args.apply, allow_live_state=args.allow_live_state,
              instance=args.instance, root=base)
    if args.queue and args.apply:
        push_to_queue(items)
    if args.json:
        print(json.dumps({"plan": items, "result": rep}, ensure_ascii=False, indent=1,
                         default=str))
    else:
        print(render(rep, items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



