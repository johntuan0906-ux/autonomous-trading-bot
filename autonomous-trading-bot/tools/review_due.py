"""Ra soat lai thay doi DA AP sau vai ngay — bang CHUNG THAT, khong ket luan khi `n` nho.

    python tools/review_due.py --target both              # chay 1 lan (Task Scheduler goi)
    python tools/review_due.py --list                     # xem muc den han ra soat
    python tools/review_due.py --force H-20261026-007     # ra soat NGAY (bo qua ngay hen)
    python tools/review_due.py --check                    # exit 1 neu CO muc can nguoi quyet
    python tools/review_due.py --install-task --task-time 09:00

Vi sao co (26/10 — yeu cau nguoi van hanh: *"theo doi tiep, vai ngay sau xac nhan lai"*):
- Hinh hoc SL/TP **14xATR/69xATR -> 6xATR/12xATR** da AP luc 13:50 26/10 dua tren
  **BACKTEST** (10 cap x 60 ngay). Backtest chi la GIA THUYET; chi du lieu THAT moi xac nhan.
  Neu ket luan do chi nam trong docs/ghi chu thi khong ai nhac ⇒ "va roi de do" — dung lop
  loi B-028 ("in ra khong phai la bao cao"). Nen ngay hen ra soat phai nam trong SO
  (`harness_ledger.jsonl`, truong `review_at`) va duoc tool nay doc moi ngay.
- Do that 26/10 (ngay doi hinh hoc): TESTNET co **0 lenh CLOSE** ke tu 13:50 (lenh cuoi
  24/10 05:54) ⇒ **chua the xac nhan gi**. Vi vay tool **KHONG duoc phep ket luan bang n nho**:
  `n < --min-n` (mac dinh 30) ⇒ tu HOAN lai `+--resched-days` (mac dinh 7 ngay) va ghi vet.
- Du mau ⇒ so cua so MOI (tu luc ap) voi cua so NEN (truoc luc ap): `avgR`, `PF`, `WR`, roi
  day cau hoi vao `ops_queue` (**dung hang doi tung instance**) + Telegram.

Nguyen tac: **khong tu y doi tham so** — tool chi do va hoi; nguoi van hanh (hoac hoi dong)
quyet. Duong lui luon co trong so: `H-20261026-007` (ve `14/69` = sua 3 dong `.env` + restart).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atomic            # noqa: E402
import harness_ledger as HL   # noqa: E402

LOG_NAME = "logs/review_due.log"
STATE_NAME = "logs/review_due.json"
JOURNAL_NAME = "logs/journal.jsonl"
TASK_NAME = "ATB-ReviewDue"
#: Duoi nguong nay thi KHONG duoc ket luan (n nho ⇒ moi ket luan deu la ngau nhien).
DEFAULT_MIN_N = 30
DEFAULT_RESCHED_DAYS = 7.0
DEFAULT_LOOKBACK_DAYS = 14.0
DEFAULT_COOLDOWN_H = 72.0
#: Chenh lech avgR nho hon nguong nay = "chua ro" (nhieu do luong), khong phai "tot/xau hon".
MARGIN_R = 0.05


def live_dir() -> Path:
    """Thu muc instance LIVE (giong cac tool khac trong repo)."""
    try:
        import backup as BK
        return Path(BK.LIVE_DIR)
    except Exception:  # noqa: BLE001
        return ROOT.parent / "atb-live"


def load_closed(path: Path) -> list:
    """Cac ban ghi `event=CLOSE` trong journal (dong hong -> bo qua, khong lam hong ca so)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or '"CLOSE"' not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and str(d.get("event") or "") == "CLOSE":
            out.append(d)
    return out


def load_opened(path: Path) -> list:
    """Cac ban ghi `event=OPEN` (de kiem chung cua so that su tach 2 hinh hoc qua `rr`)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or '"OPEN"' not in ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and str(d.get("event") or "") == "OPEN":
            out.append(d)
    return out


def load_journal(path: Path) -> tuple:
    """(lenh MO, lenh DONG) cua 1 journal — dung de GHEP cap va tinh R THAT."""
    return load_opened(path), load_closed(path)


#: Dai hop ly cua 1 lenh theo R. SL = 6..14xATR, TP = 12..69xATR ⇒ 1 lenh KHONG the
#: vuot ~5R (hinh hoc cu) va khong the lo qua ~1.6R (truot gia khi SL). Ngoai dai = ban ghi
#: hong ⇒ loai (do that 26/10: co ban ghi r=793 va r=+196 cho lenh lo).
R_BAND = (-1.6, 5.0)


def pair_trades(opens, closes, *, band=R_BAND) -> dict:
    """Ghep OPEN -> CLOSE theo (pair, direction) va tinh **R THAT tu gia**.

    Vi sao KHONG dung truong `r` san co (do that 26/10/2026 tren journal that):
      - `DASH` entry 49.32 -> exit 48.84 (lo) nhung ghi `r=+196.36`;
      - `BNB` ghi `r=793.07`; 315 ban ghi FLATTEN co |r| > 5; median `r` toan so = +0.076
        (le ra phai ~0 chi khi WR ~50%) ⇒ **`r` la du lieu rac** (chia cho SL distance sai).
    Dung `r` do de ket luan "hinh hoc moi tot/xau hon" la ket luan RAC. Nen tu tinh:

        r = (exit - entry) / |entry - sl|   × (+1 neu LONG, -1 neu SHORT)

    Tra {trades, n_closes, n_dropped}: `n_dropped` = ban ghi ngoai dai hop ly / thieu gia.
    """
    lo, hi = float(band[0]), float(band[1])
    by_key: dict = {}
    for o in sorted(opens or [], key=lambda r: float(r.get("ts") or 0.0)):
        key = (str(o.get("pair")), str(o.get("direction")))
        try:
            entry, sl, tp = float(o.get("entry")), float(o.get("sl")), float(o.get("tp"))
            ts = float(o.get("ts"))
        except (TypeError, ValueError):
            continue
        if entry <= 0 or entry == sl:
            continue
        by_key.setdefault(key, []).append({"ts": ts, "entry": entry, "sl": sl, "tp": tp})
    used: set = set()
    out, dropped, n_closes = [], 0, 0
    for c in sorted(closes or [], key=lambda r: float(r.get("ts") or 0.0)):
        n_closes += 1
        key = (str(c.get("pair")), str(c.get("direction")))
        try:
            ts = float(c.get("ts"))
            exit_p = float(c.get("exit_price"))
        except (TypeError, ValueError):
            dropped += 1
            continue
        cand = by_key.get(key) or []
        pick = None
        for i in range(len(cand) - 1, -1, -1):
            if cand[i]["ts"] <= ts and (key, i) not in used:
                pick = (i, cand[i])
                break
        if pick is None:
            dropped += 1          # khong co lenh MO tuong ung ⇒ khong biet SL ⇒ khong tinh duoc R
            continue
        i, o = pick
        used.add((key, i))
        d = 1.0 if str(c.get("direction")).upper() == "LONG" else -1.0
        sd = abs(o["entry"] - o["sl"])
        r = d * (exit_p - o["entry"]) / sd
        if not (lo <= r <= hi):
            dropped += 1          # ngoai dai hop ly ⇒ ban ghi hong
            continue
        out.append({"ts": ts, "pair": key[0], "direction": key[1], "entry": o["entry"],
                    "sl": o["sl"], "tp": o["tp"], "exit": exit_p,
                    "reason": str(c.get("reason") or ""), "r": r, "won": r > 0,
                    "rr": abs(o["tp"] - o["entry"]) / sd})
    return {"trades": out, "n_closes": n_closes, "n_dropped": dropped}


def stats(rows, *, since: float = 0.0, until=None) -> dict:
    """Thong ke 1 cua so thoi gian: n, wins, wr, pf, avg_r, sum_r.

    `pf` = tong R thang / |tong R thua| (PF theo R). Dau vao la cac lenh DA GHEP CAP
    (`pair_trades`) — tuc `r` la R THAT tinh tu gia, KHONG phai truong `r` trong journal.
    """
    hi = float("inf") if until is None else float(until)
    rs = []
    for r in rows or []:
        try:
            t = float(r.get("ts") or 0.0)
        except (TypeError, ValueError):
            continue
        if not (float(since) <= t < hi):
            continue
        try:
            rs.append((float(r.get("r") or 0.0), bool(r.get("won"))))
        except (TypeError, ValueError):
            continue
    n = len(rs)
    if not n:
        return {"n": 0, "wins": 0, "wr": 0.0, "pf": 0.0, "avg_r": 0.0, "sum_r": 0.0,
                "pos": 0.0, "neg": 0.0}
    wins = sum(1 for _r, w in rs if w)
    pos = sum(r for r, _w in rs if r > 0)
    neg = abs(sum(r for r, _w in rs if r < 0))
    sum_r = sum(r for r, _w in rs)
    return {"n": n, "wins": wins, "wr": wins / n,
            "pf": (pos / neg) if neg > 0 else (float("inf") if pos > 0 else 0.0),
            "avg_r": sum_r / n, "sum_r": sum_r, "pos": pos, "neg": neg}


def merge(a: dict, b: dict) -> dict:
    """Gop 2 cua so (TESTNET + LIVE) — cung mot thay doi thi gop lai moi du mau.

    PF gop theo R goc (`pos`/`neg`), KHONG trung binh 2 PF (trung binh PF la sai so).
    """
    n = int(a.get("n") or 0) + int(b.get("n") or 0)
    if not n:
        return {"n": 0, "wins": 0, "wr": 0.0, "pf": 0.0, "avg_r": 0.0, "sum_r": 0.0,
                "pos": 0.0, "neg": 0.0}
    wins = int(a.get("wins") or 0) + int(b.get("wins") or 0)
    sum_r = float(a.get("sum_r") or 0.0) + float(b.get("sum_r") or 0.0)
    pos = float(a.get("pos") or 0.0) + float(b.get("pos") or 0.0)
    neg = float(a.get("neg") or 0.0) + float(b.get("neg") or 0.0)
    return {"n": n, "wins": wins, "wr": wins / n,
            "pf": (pos / neg) if neg > 0 else (float("inf") if pos > 0 else 0.0),
            "avg_r": sum_r / n, "sum_r": sum_r, "pos": pos, "neg": neg}

def verdict(base: dict, new: dict, *, min_n: int = DEFAULT_MIN_N,
            margin: float = MARGIN_R) -> dict:
    """Ket luan CO KY LUAT: `n` nho ⇒ KHONG ket luan, phai HOAN tiep va do them.

    Tra {state, why, need_human}:
      - `chua-du`  : n < `min_n` ⇒ hoan lai (khong hoi nguoi — hoi khi chua co gi la nhieu);
      - `tot-hon`  : avgR moi > nen + `margin`;
      - `xau-hon`  : avgR moi < nen - `margin`;
      - `khong-ro` : chenh trong nguong nhieu, hoac khong co cua so nen de so.
    """
    nn = int(new.get("n") or 0)
    nb = int(base.get("n") or 0)
    if nn < int(min_n):
        return {"state": "chua-du", "need_human": False,
                "why": ("moi co %d lenh da dong trong cua so moi (< %d) ⇒ CHUA du ket luan"
                        % (nn, int(min_n)))}
    if nb < 5:
        return {"state": "khong-ro", "need_human": True,
                "why": "cua so moi n=%d nhung cua so NEN chi n=%d (khong du de so)"
                       % (nn, nb)}
    d = float(new.get("avg_r") or 0.0) - float(base.get("avg_r") or 0.0)
    txt = ("avgR moi %+.3f vs nen %+.3f (chenh %+.3f) tren n=%d"
           % (float(new.get("avg_r") or 0.0), float(base.get("avg_r") or 0.0), d, nn))
    if d > float(margin):
        return {"state": "tot-hon", "need_human": True, "why": txt}
    if d < -float(margin):
        return {"state": "xau-hon", "need_human": True, "why": txt}
    return {"state": "khong-ro", "need_human": True,
            "why": "%s — trong nguong nhieu ±%.2fR" % (txt, float(margin))}


def rr_median(opens, *, since: float = 0.0, until=None) -> float:
    """Trung vi `rr` THUC cua lenh MO trong cua so — KIEM CHUNG cua so tach dung 2 hinh hoc.

    `rr` = |tp-entry| / |entry-sl| = TP_ATR/SL_ATR ⇒ hinh hoc cu 69/14 ≈ 4.93, moi 12/6 = 2.0.
    Tinh TU GIA (khong tin truong `rr` san co — xem `pair_trades`). Cua so "moi" van ra rr
    ≈ 4.9 ⇒ **cua so bi sai** (moc ap sai) ⇒ bang chung do duoc khong dung de ket luan.
    Tra 0.0 khi khong co lenh mo nao.
    """
    hi = float("inf") if until is None else float(until)
    vals = []
    for r in opens or []:
        try:
            t = float(r.get("ts") or 0.0)
        except (TypeError, ValueError):
            continue
        if not (float(since) <= t < hi):
            continue
        try:
            entry, sl, tp = float(r.get("entry")), float(r.get("sl")), float(r.get("tp"))
            sd = abs(entry - sl)
            v = abs(tp - entry) / sd if sd > 0 else 0.0
        except (TypeError, ValueError):
            v = 0.0
        if v <= 0:
            try:
                v = float(r.get("rr"))
            except (TypeError, ValueError):
                v = 0.0
        if v > 0:
            vals.append(v)
    if not vals:
        return 0.0
    vals.sort()
    return vals[len(vals) // 2]


def windows(rec, *, now, lookback_days: float = DEFAULT_LOOKBACK_DAYS) -> tuple:
    """Moc AP thay doi + 2 cua so: moi `[ap, now]`, nen `[ap-lookback, ap)`.

    Moc ap lay tu `applied_at` (neu co) → `decided_at` → `ts` (luc ghi so).
    """
    ap = float(rec.get("applied_at") or rec.get("decided_at") or rec.get("ts") or 0.0)
    return ap, float(now), ap - float(lookback_days) * 86400.0, ap


# ---------------------------------------------------- vet, trang thai, bao dong

def append_log(text: str, path=None) -> str:
    """Ghi 1 dong vet (khong nem loi) — de doc lai duoc LICH SU ra soat."""
    p = Path(path) if path else (ROOT / LOG_NAME)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), str(text).rstrip()))
        return str(p)
    except OSError:
        return ""


def load_state(path=None) -> dict:
    try:
        d = json.loads(Path(path or (ROOT / STATE_NAME)).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return d if isinstance(d, dict) else {}


def save_state(state: dict, path=None) -> str:
    p = Path(path or (ROOT / STATE_NAME))
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_json_atomic(p, state, indent=1)
        return str(p)
    except OSError:
        return ""


def should_push(state: dict, key: str, *, now: float, cooldown_s: float, status: str) -> bool:
    """Chong SPAM nhung KHONG im lang vinh vien.

    Gui lai khi **trang thai ket luan DOI** (vd `chua-du` -> `xau-hon`), hoac da qua
    `cooldown_s`. (Bai hoc 20/10: chi bao 1 lan duy nhat thi mot bao dong gia se tat
    moi canh bao that ve sau.)
    """
    prev = (state.get("pushed") or {}).get(key) or {}
    if not isinstance(prev, dict) or not prev:
        return True
    if str(prev.get("status") or "") != str(status):
        return True
    return (float(now) - float(prev.get("ts") or 0.0)) >= float(cooldown_s)


def question_text(rep: dict) -> tuple:
    """(cau hoi, ly do, lua chon, do uu tien) — tuy TRANG THAI ket luan."""
    v = rep["verdict"]
    st = v["state"]
    nw, bs = rep["new"], rep["base"]
    why = ("Ra soat lai %s [%s]: %s. Cua so MOI: n=%d avgR=%+.3f PF=%.2f WR=%.0f%% | "
           "cua so NEN: n=%d avgR=%+.3f PF=%.2f. Thay doi: %s"
           % (rep["id"], st.upper(), v["why"], nw["n"], nw["avg_r"], nw["pf"],
              100.0 * nw["wr"], bs["n"], bs["avg_r"], bs["pf"],
              str(rep["change"])[:140]))
    if st == "xau-hon":
        return ("Ra soat %s: ket qua THAT XAU HON nen — ve hinh hoc cu hay siet rui ro?"
                % rep["id"], why,
                ["ve 14/69 (duong lui)", "giam risk/lenh", "theo doi them 3 ngay"], "high")
    if st == "tot-hon":
        return ("Ra soat %s: ket qua THAT TOT HON nen — giu nguyen va chot 'da xac nhan'?"
                % rep["id"], why, ["giu nguyen (da xac nhan)", "van ve 14/69"], "normal")
    return ("Ra soat %s: ket qua KHONG RO (n=%d) — giu tiep hay lui ve 14/69?"
            % (rep["id"], nw["n"]), why,
            ["giu tiep + theo doi them", "ve 14/69 (duong lui)"], "normal")



def push_questions(rep: dict, *, dirs, enqueue=None, now=None, state=None,
                   cooldown_s: float = DEFAULT_COOLDOWN_H * 3600.0) -> list:
    """Day cau hoi vao hang doi TUNG instance (co duong dan ⇒ LIVE khong bi lan sang TESTNET)."""
    q, why, opts, prio = question_text(rep)
    st = state if state is not None else {}
    pushed = st.setdefault("pushed", {})
    out = []
    for name, base in (dirs or {}).items():
        key = "%s/%s" % (rep["id"], name)
        if not should_push(st, key, now=float(now), cooldown_s=cooldown_s,
                           status=rep["verdict"]["state"]):
            out.append({"instance": name, "key": key, "sent": False, "why": "trong cooldown"})
            continue
        rec = {"ok": True, "skipped": True}
        if enqueue is not None:
            rec = enqueue(q, why=why, options=opts, priority=prio,
                          open_path=Path(base) / "logs" / "ops_questions.json")
        if isinstance(rec, dict) and rec.get("ok") is False:
            append_log("KHONG GHI DUOC HANG DOI %s: %s" % (key, str(rec)[:160]))
            out.append({"instance": name, "key": key, "sent": False,
                        "why": "ghi hang doi that bai", "record": rec})
            continue
        pushed[key] = {"ts": float(now), "status": rep["verdict"]["state"]}
        out.append({"instance": name, "key": key, "sent": True, "record": rec})
    return out


def notify_telegram(text: str, *, dirs, dry: bool = False) -> dict:
    """Gui Telegram cho tung instance (thieu token/chat ⇒ chi ghi log, KHONG im lang)."""
    try:
        import telegram_bridge as TB
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:120]}
    sent = {}
    for name, base in (dirs or {}).items():
        try:
            cfg = TB.cfg_for(Path(base))
            sent[name] = TB.send(text, token=cfg.get("token") or "",
                                 chat=cfg.get("chat") or "", dry=dry,
                                 log_path=Path(base) / "logs" / "review_due.log")
        except Exception as e:  # noqa: BLE001
            sent[name] = {"ok": False, "err": str(e)[:120]}
    return sent


def report_text(rep: dict, *, action: str) -> str:
    """Tom tat 1 dong de doc trong log/Telegram."""
    nw, bs = rep["new"], rep["base"]
    return ("%s [%s] n=%d avgR=%+.3f PF=%.2f | nen n=%d avgR=%+.3f PF=%.2f | %s | %s"
            % (rep["id"], rep["verdict"]["state"], nw["n"], nw["avg_r"], nw["pf"],
               bs["n"], bs["avg_r"], bs["pf"], action, rep["verdict"]["why"]))



def review_one(rec, *, dirs, now, min_n: int = DEFAULT_MIN_N,
               lookback_days: float = DEFAULT_LOOKBACK_DAYS,
               journal_name: str = JOURNAL_NAME) -> dict:
    """Do 1 muc da ap tren TAT CA instance (gop lai cho du mau) — tra bang chung day du."""
    ap, hi, b0, b1 = windows(rec, now=now, lookback_days=lookback_days)
    zero = {"n": 0, "wins": 0, "wr": 0.0, "pf": 0.0, "avg_r": 0.0, "sum_r": 0.0,
            "pos": 0.0, "neg": 0.0}
    new_all, base_all, per = dict(zero), dict(zero), {}
    for name, base in (dirs or {}).items():
        jp = Path(base) / journal_name
        opens, closes = load_journal(jp)
        paired = pair_trades(opens, closes)
        trades = paired["trades"]
        s_new = stats(trades, since=ap, until=hi)
        s_base = stats(trades, since=b0, until=b1)
        per[name] = {"new": s_new, "base": s_base, "journal": str(jp),
                     "n_closes": paired["n_closes"], "n_trades": len(trades),
                     "n_dropped": paired["n_dropped"],
                     "rr_open_new": rr_median(opens, since=ap, until=hi),
                     "rr_open_base": rr_median(opens, since=b0, until=b1)}
        new_all = merge(new_all, s_new)
        base_all = merge(base_all, s_base)
    return {"id": rec.get("id"), "change": str(rec.get("change") or "")[:200],
            "kind": str(rec.get("kind") or ""), "applied_at": ap,
            "window": {"new": [ap, hi], "base": [b0, b1]},
            "per": per, "new": new_all, "base": base_all,
            "verdict": verdict(base_all, new_all, min_n=min_n)}


def run(*, dirs=None, now=None, min_n: int = DEFAULT_MIN_N,
        lookback_days: float = DEFAULT_LOOKBACK_DAYS,
        resched_days: float = DEFAULT_RESCHED_DAYS,
        cooldown_h: float = DEFAULT_COOLDOWN_H, force=None, ledger_path=None,
        enqueue=None, notify: bool = True, dry_run: bool = False, state_path=None,
        log_path=None) -> dict:
    """Ra soat moi muc den han. Tra {ok, n_due, reviews, need_human, state}.

    KHONG tu doi tham so: chi DO va HOI (hoac tu hoan tiep khi chua du mau).
    """
    now_t = float(now if now is not None else time.time())
    dirs = {"TESTNET": ROOT, "LIVE": live_dir()} if dirs is None else dict(dirs)
    lpath = Path(ledger_path) if ledger_path else HL.PATH
    rows = HL.read_all(lpath)
    items = HL.due(rows, now=now_t)
    if force:
        items = [r for r in rows if str(r.get("id")) == str(force)]
        if not items:
            return {"ok": False, "err": "khong tim thay id %r trong so" % force,
                    "n_due": 0, "reviews": [], "need_human": []}
    st = load_state(state_path)
    reviews, need = [], []
    for rec in items:
        rep = review_one(rec, dirs=dirs, now=now_t, min_n=min_n,
                         lookback_days=lookback_days)
        state = rep["verdict"]["state"]
        action = "bao cao"
        if state == "chua-du" and not force:
            # Chua du mau ⇒ HOAN lai (khong hoi nguoi, khong ket luan bang n nho).
            if not dry_run:
                HL.schedule(str(rec.get("id")), resched_days, path=lpath, now=now_t)
            action = "hoan lai %.0f ngay" % float(resched_days)
        elif state == "chua-du":
            action = "bao cao (chua du mau — giu nguyen ngay hen)"
        if rep["verdict"]["need_human"]:
            pushed = push_questions(rep, dirs=dirs, enqueue=enqueue, now=now_t, state=st,
                                    cooldown_s=float(cooldown_h) * 3600.0)
            rep["pushed"] = pushed
            if any(p.get("sent") for p in pushed):
                need.append(rep["id"])
                action = "da hoi nguoi van hanh"
            else:
                action = "cau hoi da co trong hang doi (khong gui lai)"
        rep["action"] = action
        reviews.append(rep)
        if not dry_run:
            append_log(report_text(rep, action=action), path=log_path)
    st["last_run"] = now_t
    st["saved"] = "" if dry_run else save_state(st, state_path)
    if notify and reviews and not dry_run:
        text = "RA SOAT LAI thay doi da ap (%s):\n%s" % (
            time.strftime("%d/%m %H:%M", time.localtime(now_t)),
            "\n".join("- %s" % report_text(r, action=r["action"])[:300] for r in reviews))
        notify_telegram(text, dirs=dirs)
    return {"ok": True, "n_due": len(items), "reviews": reviews, "need_human": need,
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


def _t(ts) -> str:
    try:
        return time.strftime("%d/%m %H:%M", time.localtime(float(ts)))
    except (TypeError, ValueError):
        return "-"


def _print_report(res: dict) -> None:
    print("=== RA SOAT LAI THAY DOI DA AP | %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    if not res.get("ok"):
        print("  LOI: %s" % res.get("err"))
        return
    if not res["reviews"]:
        print("  (khong co muc nao den han ra soat)")
    for r in res["reviews"]:
        w = r["window"]
        nw, bs = r["new"], r["base"]
        print("  %s [%s] %s" % (r["id"], r["verdict"]["state"], str(r["change"])[:90]))
        print("     cua so MOI %s -> %s: n=%d avgR=%+.3f PF=%.2f WR=%.0f%%"
              % (_t(w["new"][0]), _t(w["new"][1]), nw["n"], nw["avg_r"], nw["pf"],
                 100.0 * nw["wr"]))
        print("     cua so NEN %s -> %s: n=%d avgR=%+.3f PF=%.2f WR=%.0f%%"
              % (_t(w["base"][0]), _t(w["base"][1]), bs["n"], bs["avg_r"], bs["pf"],
                 100.0 * bs["wr"]))
        for name, p in (r.get("per") or {}).items():
            print("     %-8s rr_lenh_moi=%.2f rr_lenh_nen=%.2f | ghep duoc %d/%d lenh (bo %d)"
                  " | %s"
                  % (name, p.get("rr_open_new") or 0.0, p.get("rr_open_base") or 0.0,
                     p.get("n_trades") or 0, p.get("n_closes") or 0,
                     p.get("n_dropped") or 0, p.get("journal")))
        print("     => %s | %s" % (r["action"], r["verdict"]["why"]))
    if res.get("need_human"):
        print("  CAN NGUOI VAN HANH QUYET: %s" % ", ".join(res["need_human"]))
    else:
        print("  (khong co muc nao can nguoi van hanh quyet ngay)")



def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(
        description="Ra soat lai thay doi DA AP sau vai ngay (bang chung THAT)")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--list", action="store_true", help="chi liet ke muc den han")
    ap.add_argument("--force", metavar="ID", help="ra soat NGAY muc ID (bo qua ngay hen)")
    ap.add_argument("--min-n", type=int, default=DEFAULT_MIN_N,
                    help="duoi nguong nay thi KHONG ket luan (mac dinh 30)")
    ap.add_argument("--lookback-days", type=float, default=DEFAULT_LOOKBACK_DAYS)
    ap.add_argument("--resched-days", type=float, default=DEFAULT_RESCHED_DAYS)
    ap.add_argument("--cooldown-hours", type=float, default=DEFAULT_COOLDOWN_H)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 neu co muc CAN NGUOI VAN HANH quyet")
    ap.add_argument("--dry-run", action="store_true", help="khong ghi gi (chi in)")
    ap.add_argument("--no-notify", action="store_true", help="khong gui Telegram")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="chi in khi co van de (cho task)")
    ap.add_argument("--ledger", default=str(HL.PATH))
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--uninstall-task", action="store_true")
    ap.add_argument("--task-status", action="store_true")
    ap.add_argument("--task-time", default="09:00", help="gio chay hang ngay (mac dinh 09:00)")
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

    if args.list:
        items = HL.due(HL.read_all(Path(args.ledger)))
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=1))
        else:
            print("=== DEN HAN RA SOAT | %d muc ===" % len(items))
            for r in items:
                print("  %-14s hen %s | %s" % (r.get("id"), _t(r.get("review_at")),
                                               str(r.get("change") or "")[:80]))
            if not items:
                print("  (khong co muc nao den han)")
        return 0

    import ops_queue as OQ
    res = run(dirs=dirs, min_n=args.min_n, lookback_days=args.lookback_days,
              resched_days=args.resched_days, cooldown_h=args.cooldown_hours,
              force=args.force, ledger_path=Path(args.ledger), enqueue=OQ.add,
              notify=not args.no_notify, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    elif not args.quiet or not res.get("ok") or res.get("need_human"):
        _print_report(res)
    if not res.get("ok"):
        return 1
    if args.check and res.get("need_human"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
