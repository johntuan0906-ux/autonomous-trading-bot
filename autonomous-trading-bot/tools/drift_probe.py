"""Do LECH giua KHAI BAO va HANH VI THUC, va LECH PHAN PHOI dau vao — bao vao `ops_queue`.

    python tools/drift_probe.py --target both            # 1 lan (Task Scheduler goi)
    python tools/drift_probe.py --check                  # exit 1 neu co lech vuot nguong
    python tools/drift_probe.py --hours 72 --baseline-days 30 --json
    python tools/drift_probe.py --install-task --task-time 08:30

Vi sao co (26/10, hoi dong **4 ALLOW / 0 VETO**, conf 0.72-0.95, tra loi 2 cau hoi dua tren
danh sach 50 repo + khoa hoc nguoi van hanh gui):
- Nguon y tuong: sach **Designing Machine Learning Systems** chuong 8 (data distribution shifts,
  drift detection, monitoring design) + cong cu **iFixAi** (goal drift: agent con lam dung muc tieu
  khai bao khong) + bai hoc **B-031** cua chinh repo nay.
- **B-031 la bang chung manh nhat**: journal TESTNET co 3342 ban ghi CLOSE nhung truong `r` SAI
  hoan toan (`r=793.07`, `r=+196.36` cho lenh LO) — **khong ai phat hien trong nhieu tuan**, va
  no lam moi bao cao (ke ca `STATE.md` bao PF(R)=5.345 trong khi PF that 1.013) thanh RAC.
  Phep do "khai bao vs thuc te" se bat ngay: `rr` trung vi THUC te 2.50 trong khi khai bao
  69/14 = 4.93; va sau khi doi hinh hoc 26/10 thi `rr` thuc te phai la 2.00.
- Hoi dong cung quyet (cau hoi 2): **chi MUON CO CHE, KHONG them phu thuoc ngoai** (khong
  firecrawl/browser-use/vLLM/langchain/crewAI/RAGFlow...) ⇒ file nay chi dung **stdlib**.

Do 2 nhom:
  (A) **Khai bao (.env) vs Thuc te (journal)** — bat duoc: sua `.env` nhung CHUA restart; hinh hoc
      khong duoc ap; leverage/risk lech; chot mot phan (partial) khong bao gio xay ra.
  (B) **Lech phan phoi dau vao** — PSI (Population Stability Index) tung dac trung trong journal
      OPEN so cua so gan day voi cua so NEN: <0.1 on dinh, 0.1-0.25 dich chuyen vua, >0.25 lon.

Nguyen tac (giong `review_due.py`): **n nho ⇒ KHONG ket luan**; chi HOI khi vuot nguong va cau hoi
phai KEM SO DO DUOC (khong hoi chung chung ⇒ tranh bao dong gia kieu B-030).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atomic          # noqa: E402

LOG_NAME = "logs/drift_probe.log"
STATE_NAME = "logs/drift_probe.json"
TASK_NAME = "ATB-DriftProbe"
#: Duoi nguong nay thi KHONG ket luan (khong du mau ⇒ moi so sanh deu la ngau nhien).
MIN_N = 10
#: Nguong PSI (kinh nghiem trong tai lieu monitoring drift): <0.1 on dinh, >0.25 dich chuyen LON.
PSI_WARN = 0.1
PSI_ALERT = 0.25
#: Dung sai tuong doi khi so khai bao vs thuc te (rr/risk/leverage).
TOL = 0.20



# ---------------------------------------------------------------- doc so lieu

def read_jsonl(path: Path) -> list:
    """Doc jsonl; dong hong -> bo qua (khong lam hong ca so)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def load_events(path: Path, event: str = "OPEN") -> list:
    """Cac ban ghi co `event` cho truoc (OPEN / CLOSE) trong journal."""
    return [r for r in read_jsonl(path) if str(r.get("event") or "") == event]


def read_env(path: Path) -> dict:
    """Doc `.env` cua 1 instance (KHONG thay the bien moi truong dang chay)."""
    out = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def declared(env: dict) -> dict:
    """Gia tri KHAI BAO trong `.env` (y dinh cua nguoi van hanh)."""
    sl, tp = _f(env.get("SL_ATR_MULT")), _f(env.get("TP_ATR_MULT"))
    return {"sl_atr": sl, "tp_atr": tp,
            "rr": (tp / sl) if (sl and tp and sl > 0) else None,
            "risk_pct": _f(env.get("RISK_PER_TRADE_PCT")),
            "leverage": _i(env.get("LEVERAGE")),
            "partial_at_r": _f(env.get("PARTIAL_AT_R")),
            "max_positions": _i(env.get("MAX_POSITIONS")),
            "max_daily_loss_pct": _f(env.get("MAX_DAILY_LOSS_PCT"))}


def rr_of(rec) -> float:
    """`rr` THUC tu gia = |tp-entry| / |entry-sl| (KHONG tin truong `rr` — xem B-031)."""
    try:
        e, s, t = float(rec["entry"]), float(rec["sl"]), float(rec["tp"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    sd = abs(e - s)
    return (abs(t - e) / sd) if sd > 0 else 0.0


def sl_pct_of(rec) -> float:
    """Khoang cach SL theo % gia vao (do ATR quyet dinh ⇒ phai BIEN THIEN theo thi truong)."""
    try:
        e, s = float(rec["entry"]), float(rec["sl"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    return (abs(e - s) / e * 100.0) if e > 0 else 0.0


def _median(vals) -> float:
    v = sorted(x for x in vals if isinstance(x, (int, float)))
    if not v:
        return 0.0
    return v[len(v) // 2]


def _cv(vals) -> float:
    """He so bien thien (do phan tan) — de kiem SL co THAT SU theo ATR khong.

    SL = k x ATR ⇒ `sl_pct` phai BIEN THIEN theo ATR. `cv ≈ 0` (moi lenh cung mot khoang cach)
    ⇒ SL dang la % CO DINH, KHONG phai ATR ⇒ khai bao khong khop hanh vi.
    """
    v = [x for x in vals if isinstance(x, (int, float)) and x > 0]
    if len(v) < 2:
        return 0.0
    m = sum(v) / len(v)
    if m <= 0:
        return 0.0
    var = sum((x - m) ** 2 for x in v) / (len(v) - 1)
    return math.sqrt(var) / m



# ------------------------------------------------------ (A) khai bao vs thuc te

def actual(opens, *, since, until=None) -> dict:
    """Hanh vi THUC do tu journal OPEN trong cua so (gia tri bot DANG chay)."""
    hi = float("inf") if until is None else float(until)
    rows = []
    for r in opens or []:
        try:
            t = float(r.get("ts") or 0.0)
        except (TypeError, ValueError):
            continue
        if float(since) <= t < hi:
            rows.append(r)
    rrs = [x for x in (rr_of(r) for r in rows) if x > 0]
    sls = [x for x in (sl_pct_of(r) for r in rows) if x > 0]
    lev = [x for x in (_i(r.get("leverage")) for r in rows) if x]
    risk = [x for x in (_f(r.get("risk_pct")) for r in rows) if x]
    return {"n": len(rows), "n_rr": len(rrs), "n_sl": len(sls),
            "rr": _median(rrs), "rr_mean": (sum(rrs) / len(rrs)) if rrs else 0.0,
            "sl_pct": _median(sls), "sl_pct_cv": _cv(sls),
            "leverage": (max(set(lev), key=lev.count) if lev else None),
            "risk_pct": _median(risk)}


def compare_declared(decl: dict, act: dict, *, tol: float = TOL, min_n: int = MIN_N,
                     cv_min: float = 0.05) -> dict:
    """So KHAI BAO (`.env`) voi THUC TE (journal). Tra {ok, n, findings, skipped}.

    `risk_pct`/`leverage` trong journal la gia tri bot **DANG CHAY** ⇒ lech voi `.env` nghia la
    "da sua .env nhung CHUA restart" (hoac cau hinh khong duoc doc).
    """
    n = int(act.get("n") or 0)
    if n < int(min_n):
        return {"ok": True, "n": n, "findings": [],
                "skipped": ("moi co %d lenh MO trong cua so (< %d) ⇒ CHUA ket luan"
                            % (n, min_n))}
    f = []

    def add(field, d, a, ok, why):
        f.append({"field": field, "declared": d, "actual": a, "ok": bool(ok), "why": why})

    d_rr, a_rr = decl.get("rr"), act.get("rr")
    if d_rr and a_rr:
        rel = abs(a_rr - d_rr) / d_rr
        add("rr (TP_ATR/SL_ATR)", round(d_rr, 3), round(a_rr, 3), rel <= tol,
            "lech %.0f%% (dung sai cho phep %.0f%%)" % (100 * rel, 100 * tol))
    d_rp, a_rp = decl.get("risk_pct"), act.get("risk_pct")
    if d_rp and a_rp:
        rel = abs(a_rp - d_rp) / d_rp
        add("risk_per_trade_pct", d_rp, round(a_rp, 3), rel <= tol,
            "lech %.0f%% ⇒ .env KHAC cau hinh DANG CHAY (sua roi chua restart?)" % (100 * rel))
    d_lv, a_lv = decl.get("leverage"), act.get("leverage")
    if d_lv and a_lv:
        add("leverage", d_lv, a_lv, int(a_lv) == int(d_lv),
            "khac ⇒ .env KHAC cau hinh dang chay")
    if int(act.get("n_sl") or 0) >= int(min_n):
        cv = float(act.get("sl_pct_cv") or 0.0)
        add("SL theo ATR (sl_pct phai bien thien)", "cv >= %.2f" % cv_min, round(cv, 3),
            cv >= cv_min, "sl_pct gan nhu CO DINH ⇒ SL khong theo ATR nhu khai bao")
    return {"ok": all(x["ok"] for x in f), "n": n, "findings": f, "skipped": ""}


# ------------------------------------------------- (B) lech phan phoi dau vao

#: Dac trung SO lay tu ban ghi OPEN (hoac tu `feats` neu khong co o muc ngoai).
NUM_FEATURES = ("score100", "volume_ratio", "ls_ratio", "funding", "oi_chg", "news_score",
                "alpha", "risk_usdt")
#: Dac trung PHAN LOAI (PSI theo tan suat).
CAT_FEATURES = ("market_regime", "setup_type", "strategy", "direction", "htf_bias",
                "btc_regime")


def _psi(pb, pr, *, eps: float = 1e-6) -> float:
    """PSI = sum (pr-pb) * ln((pr+eps)/(pb+eps)). 0 = giong het; >0.25 = dich chuyen LON."""
    return sum((pr[i] - pb[i]) * math.log((pr[i] + eps) / (pb[i] + eps))
               for i in range(len(pb)))


def psi_numeric(base, recent, *, bins: int = 10) -> float:
    """PSI giua 2 mau SO. -1.0 = khong du mau.

    Canh bin lay theo PHAN VI cua **MAU GOP** (khong phai chi mau nen): neu mau nen la HANG SO
    (vd dac trung luon = 0 trong 30 ngay roi doi) thi cach lay theo mau nen cho ra 1 bucket duy
    nhat ⇒ PSI = 0 va **bo sot dich chuyen** (da gap khi viet test: PSI 0.0 du 60 -> 90).
    """
    b = [float(x) for x in base if isinstance(x, (int, float))]
    r = [float(x) for x in recent if isinstance(x, (int, float))]
    if len(b) < MIN_N or len(r) < MIN_N:
        return -1.0
    comb = sorted(b + r)
    cuts = sorted({comb[int(len(comb) * i / bins)] for i in range(1, bins)})

    def dist(vals):
        out = [0] * (len(cuts) + 1)
        for v in vals:
            out[bisect_right(cuts, v)] += 1
        return [c / len(vals) for c in out]

    return _psi(dist(b), dist(r))


def psi_categorical(base, recent) -> float:
    """PSI giua 2 mau PHAN LOAI (theo tan suat tung nhom). -1.0 = khong du mau."""
    b = [str(x) for x in base if x is not None and x != ""]
    r = [str(x) for x in recent if x is not None and x != ""]
    if len(b) < MIN_N or len(r) < MIN_N:
        return -1.0
    cats = sorted(set(b) | set(r))
    return _psi([b.count(c) / len(b) for c in cats], [r.count(c) / len(r) for c in cats])


def feature_values(rows, key) -> list:
    """Lay 1 dac trung tu ban ghi (uu tien muc ngoai, roi den `feats`)."""
    out = []
    for r in rows or []:
        v = r.get(key)
        if v is None and isinstance(r.get("feats"), dict):
            v = r["feats"].get(key)
        if v is not None and not isinstance(v, (dict, list)):
            out.append(v)
    return out


def _in_window(rows, since, until) -> list:
    hi = float("inf") if until is None else float(until)
    out = []
    for r in rows or []:
        try:
            t = float(r.get("ts") or 0.0)
        except (TypeError, ValueError):
            continue
        if float(since) <= t < hi:
            out.append(r)
    return out


def input_drift(opens, *, since, baseline_since, baseline_until=None) -> dict:
    """PSI tung dac trung: cua so GAN DAY (`since..now`) vs cua so NEN. Tra {items, worst}."""
    recent = _in_window(opens, since, None)
    base = _in_window(opens, baseline_since, baseline_until)
    items = []
    for key in NUM_FEATURES:
        v = psi_numeric(feature_values(base, key), feature_values(recent, key))
        if v >= 0:
            items.append({"feature": key, "kind": "so", "psi": round(v, 4),
                          "n_base": len(feature_values(base, key)),
                          "n_recent": len(feature_values(recent, key))})
    for key in CAT_FEATURES:
        v = psi_categorical(feature_values(base, key), feature_values(recent, key))
        if v >= 0:
            items.append({"feature": key, "kind": "phan loai", "psi": round(v, 4),
                          "n_base": len(feature_values(base, key)),
                          "n_recent": len(feature_values(recent, key))})
    items.sort(key=lambda x: -x["psi"])
    return {"items": items, "n_recent": len(recent), "n_base": len(base),
            "worst": items[0] if items else None,
            "alert": [x for x in items if x["psi"] >= PSI_ALERT],
            "warn": [x for x in items if PSI_WARN <= x["psi"] < PSI_ALERT]}




# ------------------------------------------------------------- 1 instance + bao

def probe_instance(name: str, base: Path, *, now=None, hours: float = 24.0,
                   baseline_days: float = 30.0, min_n: int = MIN_N, tol: float = TOL,
                   journal_name: str = "logs/journal.jsonl",
                   env_name: str = ".env") -> dict:
    """Do 1 instance: (A) khai bao vs thuc te + (B) lech phan phoi dau vao."""
    now_t = float(now if now is not None else time.time())
    base = Path(base)
    opens = load_events(base / journal_name, "OPEN")
    decl = declared(read_env(base / env_name))
    since = now_t - float(hours) * 3600.0
    act = actual(opens, since=since)
    act["hours"] = float(hours)
    cmp = compare_declared(decl, act, tol=tol, min_n=min_n)
    drift = input_drift(opens, since=since,
                        baseline_since=now_t - float(baseline_days) * 86400.0,
                        baseline_until=since)
    return {"name": name, "dir": str(base), "declared": decl, "actual": act,
            "compare": cmp, "drift": drift,
            "ok": bool(cmp["ok"]) and not drift["alert"]}


def bad_findings(rep: dict) -> list:
    return [f for f in (rep.get("compare") or {}).get("findings") or [] if not f["ok"]]


def question_for(rep: dict) -> tuple:
    """(cau hoi, ly do, lua chon, do uu tien) hoac None neu khong vuot nguong.

    Cau hoi PHAI kem so do duoc (tranh bao dong gia kieu B-030).
    """
    bad = bad_findings(rep)
    alert = (rep.get("drift") or {}).get("alert") or []
    act = rep.get("actual") or {}
    if bad:
        txt = "; ".join("%s: khai bao %s vs thuc te %s (%s)"
                        % (f["field"], f["declared"], f["actual"], f["why"]) for f in bad)
        return ("%s: CAU HINH KHAI BAO KHONG KHOP HANH VI THUC — %s. Xu ly the nao?"
                % (rep["name"], txt[:260]),
                ("Do tu journal %s lenh MO trong %.0f gio. %s. Cau hoi: da sua .env nhung CHUA "
                 "restart? hinh hoc/tham so khong duoc ap? hay ATR bi lam phang?"
                 % (act.get("n") or 0, float(act.get("hours") or 0), txt)),
                ["restart de ap .env", "sua .env cho khop thuc te", "dieu tra truoc"],
                "high")
    if alert:
        w = alert[0]
        return ("%s: dau vao DICH CHUYEN (PSI %.2f >= %.2f) o dac trung '%s' — co nen hach lai "
                "nguong/learner?" % (rep["name"], w["psi"], PSI_ALERT, w["feature"]),
                ("PSI (Population Stability Index) cua '%s' = %.3f (nen %d mau, gan day %d mau). "
                 "Nguong canh bao >= %.2f. Cac dac trung lech: %s"
                 % (w["feature"], w["psi"], w["n_base"], w["n_recent"], PSI_ALERT,
                    ", ".join("%s=%.2f" % (x["feature"], x["psi"]) for x in alert[:5]))),
                ["theo doi them 3 ngay", "hach lai nguong theo du lieu moi",
                 "giam rui ro cho den khi on dinh"],
                "normal")
    return None


def _load_state(path) -> dict:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return d if isinstance(d, dict) else {}


def _save_state(state: dict, path) -> str:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_json_atomic(p, state, indent=1)
        return str(p)
    except OSError:
        return ""


def _cooldown_ok(state: dict, key: str, *, now: float, hours: float) -> bool:
    prev = (state.get("notified") or {}).get(key) or {}
    if not prev:
        return True
    return (float(now) - float(prev.get("ts") or 0.0)) >= float(hours) * 3600.0


def append_log(text: str, path=None) -> str:
    """Ghi 1 dong vet (khong nem loi)."""
    p = Path(path) if path else (ROOT / LOG_NAME)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), str(text).rstrip()))
        return str(p)
    except OSError:
        return ""



# ------------------------------------------------------------------- chay 1 lan

def live_dir() -> Path:
    """Thu muc instance LIVE (giong cac tool khac trong repo)."""
    try:
        import backup as BK
        return Path(BK.LIVE_DIR)
    except Exception:  # noqa: BLE001
        return ROOT.parent / "atb-live"


def line_for(rep: dict) -> str:
    """1 dong vet: so do duoc (khong phai loi khuyen chung)."""
    a = rep.get("actual") or {}
    w = (rep.get("drift") or {}).get("worst") or {}
    return ("%s [%s] n_mo=%s rr_khai_bao=%s rr_thuc=%s sl_pct=%s cv=%.3f | PSI lon nhat: %s=%.3f "
            "| %s"
            % (rep["name"], "OK" if rep.get("ok") else "CAN XEM", a.get("n") or 0,
               (rep.get("declared") or {}).get("rr"), a.get("rr"),
               round(float(a.get("sl_pct") or 0), 3), float(a.get("sl_pct_cv") or 0),
               w.get("feature") or "-", float(w.get("psi") or 0), rep.get("action") or ""))


def telegram(text: str, *, dirs, dry: bool = False) -> dict:
    """Gui Telegram (thieu token/chat ⇒ chi ghi log, KHONG im lang)."""
    try:
        import telegram_bridge as TB
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:120]}
    out = {}
    for name, base in (dirs or {}).items():
        try:
            cfg = TB.cfg_for(Path(base))
            out[name] = TB.send(text, token=cfg.get("token") or "", chat=cfg.get("chat") or "",
                                dry=dry, log_path=Path(base) / "logs" / "drift_probe.log")
        except Exception as e:  # noqa: BLE001
            out[name] = {"ok": False, "err": str(e)[:120]}
    return out


def run(*, dirs=None, now=None, hours: float = 24.0, baseline_days: float = 30.0,
        min_n: int = MIN_N, tol: float = TOL, cooldown_h: float = 24.0, enqueue=None,
        notify: bool = True, dry_run: bool = False, state_path=None, log_path=None) -> dict:
    """Do moi instance; chi HOI khi vuot nguong (kem so do duoc). Tra {ok, instances, ...}."""
    now_t = float(now if now is not None else time.time())
    dirs = {"TESTNET": ROOT, "LIVE": live_dir()} if dirs is None else dict(dirs)
    spath = Path(state_path) if state_path else (ROOT / STATE_NAME)
    st = _load_state(spath)
    reps, need = [], []
    for name, base in dirs.items():
        rep = probe_instance(name, base, now=now_t, hours=hours, baseline_days=baseline_days,
                             min_n=min_n, tol=tol)
        q = question_for(rep)
        rep["action"] = "khong vuot nguong"
        if q:
            question, why, opts, prio = q
            kind = "cau_hinh" if bad_findings(rep) else "dau_vao"
            key = "%s/%s" % (name, kind)
            if dry_run:
                # (26/10) `--dry-run` KHONG duoc day cau hoi (truoc day van day ⇒ sai nghia
                # "khong ghi gi" — test bat duoc).
                rep["action"] = "dry-run: SE hoi (%s)" % kind
            elif not _cooldown_ok(st, key, now=now_t, hours=cooldown_h):
                rep["action"] = "da hoi truoc do (trong cooldown)"
            else:
                rec = {"ok": True, "skipped": True}
                if enqueue is not None:
                    rec = enqueue(question, why=why, options=opts, priority=prio,
                                  open_path=Path(base) / "logs" / "ops_questions.json")
                if isinstance(rec, dict) and rec.get("ok") is False:
                    append_log("KHONG GHI DUOC HANG DOI %s: %s" % (key, str(rec)[:160]),
                               path=log_path)
                    rep["action"] = "ghi hang doi THAT BAI"
                else:
                    rep["action"] = "da hoi nguoi van hanh"
                    need.append(key)
                    st.setdefault("notified", {})[key] = {"ts": now_t, "kind": kind,
                                                          "why": why[:200]}
        reps.append(rep)
        if not dry_run:
            append_log(line_for(rep), path=log_path)
    st["last_run"] = now_t
    if not dry_run:
        st["saved"] = _save_state(st, spath)
    if notify and reps and not dry_run and need:
        text = ("DO LECH (drift) %s:\n%s"
                % (time.strftime("%d/%m %H:%M", time.localtime(now_t)),
                   "\n".join("- %s" % line_for(r)[:300] for r in reps)))
        telegram(text, dirs=dirs)
    return {"ok": all(r.get("ok") for r in reps), "instances": reps, "need_human": need,
            "state": st}



# ------------------------------------------------------------------------- CLI

def task_command(python_exe=None, script=None, target: str = "both") -> str:
    """Lenh Task Scheduler se chay (duong dan TUYET DOI + nhay kep; task chay cwd khac)."""
    py = python_exe or sys.executable
    try:
        import backup as BK
        py = BK.hidden_python(py)      # pythonw: khong nhay cua so console moi ngay
    except Exception:  # noqa: BLE001
        pass
    s = str(script or Path(__file__).resolve())
    return '"%s" "%s" --target %s --quiet' % (py, s, target)


def _print_report(res: dict) -> None:
    print("=== DO LECH KHAI BAO vs THUC TE + LECH DAU VAO | %s ==="
          % time.strftime("%Y-%m-%d %H:%M:%S"))
    for r in res.get("instances") or []:
        a, c = r["actual"], r["compare"]
        print("  %s [%s] lenh MO trong cua so: %d"
              % (r["name"], "OK" if r["ok"] else "CAN XEM", a.get("n") or 0))
        print("     rr: khai bao %s vs thuc te %s | sl_pct %s%% (cv=%.3f) | leverage %s vs %s"
              % (r["declared"].get("rr"), a.get("rr"), round(float(a.get("sl_pct") or 0), 3),
                 float(a.get("sl_pct_cv") or 0), r["declared"].get("leverage"),
                 a.get("leverage")))
        if c.get("skipped"):
            print("     (A) %s" % c["skipped"])
        for f in c.get("findings") or []:
            print("     (A) %s %s: khai bao %s vs thuc te %s — %s"
                  % ("OK " if f["ok"] else "LECH", f["field"], f["declared"], f["actual"],
                     f["why"]))
        d = r["drift"]
        print("     (B) PSI: nen %d mau, gan day %d mau | canh bao %d, vua %d"
              % (d.get("n_base") or 0, d.get("n_recent") or 0, len(d.get("alert") or []),
                 len(d.get("warn") or [])))
        for it in (d.get("items") or [])[:5]:
            print("         %-14s PSI=%.3f (%s)" % (it["feature"], it["psi"], it["kind"]))
        print("     => %s" % r.get("action"))
    if res.get("need_human"):
        print("  CAN NGUOI VAN HANH QUYET: %s" % ", ".join(res["need_human"]))
    else:
        print("  (khong co muc nao can nguoi van hanh quyet)")


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(
        description="Do lech khai bao vs thuc te + lech phan phoi dau vao (drift)")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--hours", type=float, default=24.0,
                    help="cua so kiem tra khai bao-vs-thuc te (gio)")
    ap.add_argument("--baseline-days", type=float, default=30.0, help="nen cho PSI (ngay)")
    ap.add_argument("--min-n", type=int, default=MIN_N,
                    help="duoi nguong nay thi KHONG ket luan (mac dinh 10)")
    ap.add_argument("--tol", type=float, default=TOL, help="dung sai tuong doi (mac dinh 0.20)")
    ap.add_argument("--cooldown-hours", type=float, default=24.0, help="chong hoi lai lien tuc")
    ap.add_argument("--check", action="store_true", help="exit 1 neu co muc can nguoi quyet")
    ap.add_argument("--dry-run", action="store_true", help="khong ghi gi")
    ap.add_argument("--no-notify", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="chi in khi co van de (cho task)")
    ap.add_argument("--state", default="")
    ap.add_argument("--log", default="")
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--uninstall-task", action="store_true")
    ap.add_argument("--task-status", action="store_true")
    ap.add_argument("--task-time", default="08:30", help="gio chay hang ngay (mac dinh 08:30)")
    args = ap.parse_args(argv)

    if args.install_task or args.uninstall_task or args.task_status:
        import backup as BK
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = task_command(target=args.target)
        res = BK.run_schtasks(BK.schtasks_argv(action, TASK_NAME, time_str=args.task_time,
                                               command=cmd, sched="DAILY"))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME,
                                   "OK" if res["ok"] else "LOI (%s)" % res.get("code")))
            print("  lenh: %s  (moi ngay luc %s)" % (cmd, args.task_time))
            if res.get("out"):
                print("  %s" % str(res["out"]).replace("\n", "\n  ")[:300])
        return 0 if res["ok"] else 1

    dirs = {"TESTNET": ROOT, "LIVE": live_dir()}
    if args.target == "testnet":
        dirs = {"TESTNET": ROOT}
    elif args.target == "live":
        dirs = {"LIVE": live_dir()}

    import ops_queue as OQ
    res = run(dirs=dirs, hours=args.hours, baseline_days=args.baseline_days, min_n=args.min_n,
              tol=args.tol, cooldown_h=args.cooldown_hours, enqueue=OQ.add,
              notify=not args.no_notify, dry_run=args.dry_run,
              state_path=(args.state or None), log_path=(args.log or None))
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    elif not args.quiet or not res.get("ok") or res.get("need_human"):
        _print_report(res)
    if args.check and res.get("need_human"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
