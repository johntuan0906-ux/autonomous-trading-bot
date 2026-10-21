"""HOI DONG CHAY NEN 24/7 ("nhan vien truc") — khac voi hoi dong trong vong lap giao dich.

Hai che do, dung chung 1 bo may:

    A. TRONG VONG LAP (da co tu truoc): `turbo_demo` goi `multi_model_council` moi khi co
       ung vien lenh => hoi dong chi lam viec khi CO lenh. 83 vong/7 phut tren LIVE.
    B. CHAY NEN (file nay): moi `--interval` giay tu thuc day, TU LAP CHUONG TRINH NGHI
       SU (agenda) tu bang chung that (journal, cau hoi ton dong, tai phat lop loi, cau
       hinh rui ro, cong tam dung), hoi y kien hoi dong, roi ghi ket qua ra outbox.

Vi sao can B (21/10, sau khi doc coworker.ai + open-cowork): "agent chay lien tuc" cua ho
la agent tren CLOUD co trigger theo su kien/lich; ban open-source thi **lich chay con nam
trong ROADMAP (v3.4.0)** — tuc la chua co. Bot cua ta thi da chay 24/7 (supervisor +
deadman + 3 task Scheduler) va hoi dong da duoc goi trong vong lap, nhung **khong ai lam
viec khi thi truong im** (khong co ung vien lenh ⇒ hoi dong ngu). Che do B lap dung cho
trong do: luon co nguoi truc, nhung KHONG duoc tieu tien vo han.

Nguyen tac an toan (co test chot):
  * **Chi de xuat, khong hanh dong**: khong import `exchange`/`bot`, khong dat/huy lenh,
    khong ghi `.env`. Ket qua chi vao `logs/council_outbox.json` + (tuy chon) cau hoi
    van hanh cho nguoi.
  * **Mac dinh DRY-RUN**: khong goi LLM neu thieu `--live`. Muon tieu tien phai bat tay.
  * **Tran chi phi**: `--max-usd-day`, `--max-cycles-day`, `--max-topics`, `--models N`;
    cham tran ⇒ ghi `budget_blocked` roi nghi, KHONG im lang.
  * **Khong lap lai vo ich**: moi chu de co `key` + TTL (`--ttl-hours`, mac dinh 24h) —
    cung mot van de khong bi dem lai moi 15 phut (dot tien + nhieu phieu rac).
  * **Mot tien trinh**: lock `logs/council_daemon.lock` (pid song ⇒ thoat, pid chet ⇒
    chiem quyen) — supervisor/Task Scheduler restart khong tao 2 hoi dong cung luc.
  * **Co the chung minh dang song**: `logs/council_heartbeat.json` ghi moi vong; khong
    ghi duoc thi `--status` noi ro (dung lop loi "im lang" cua du an).
  * **Crash-resume**: cursor journal chi nhay SAU khi ghi xong outbox/state; loi giua
    chung ⇒ vong sau lam lai dung phan do.

    python tools/council_daemon.py --once                 # dry-run: lap chuong trinh nghi su
    python tools/council_daemon.py --once --live          # goi LLM that (co tran chi phi)
    python tools/council_daemon.py --watch --interval 900 --live --max-usd-day 1.0
    python tools/council_daemon.py --status
    python tools/council_daemon.py --install-task --live --task-min 15
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atomic  # noqa: E402

LOG_DIR = ROOT / "logs"
STATE_PATH = LOG_DIR / "council_daemon.json"
HEARTBEAT_PATH = LOG_DIR / "council_heartbeat.json"
LOCK_PATH = LOG_DIR / "council_daemon.lock"
OUTBOX_PATH = LOG_DIR / "council_outbox.json"
JOURNAL_PATH = LOG_DIR / "journal.jsonl"
OPS_OPEN_PATH = LOG_DIR / "ops_questions.json"
REGRESS_PATH = LOG_DIR / "regress_watch.json"
HEARTBEAT_BOT = LOG_DIR / "heartbeat.json"
ENV_PATH = ROOT / ".env"
PAUSE_PATH = LOG_DIR / "entries_pause.json"

TASK_NAME = "ATB-Council"
DEFAULT_INTERVAL = 900.0
DEFAULT_MAX_USD_DAY = 0.60
DEFAULT_MAX_CYCLES_DAY = 48
DEFAULT_MAX_TOPICS = 3
DEFAULT_MODELS = 3
DEFAULT_TTL_H = 24.0
#: Uoc luong chi phi 1 phieu (model) — chi de CHAN, khong phai hoa don.
EST_USD_PER_VOTE = 0.004
#: Journal doc toi da bay nhieu byte tu cuoi (tranh doc ca file 50 MB).
TAIL_BYTES = 512 * 1024


# ------------------------------------------------------------------ ha tang nho

def read_json(path, default):
    """Doc JSON, thieu/hong -> `default` (khong nem)."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default
    return d if isinstance(d, type(default)) else default


def save_json(path, obj) -> bool:
    """Ghi nguyen tu (atomic.py) — crash giua chung khong lam hong state."""
    try:
        atomic.write_json_atomic(path, obj, indent=1)
        return True
    except OSError:
        return False


def pid_alive(pid) -> bool:
    """Pid con song THAT khong (Windows: OpenProcess; khac: kill 0).

    Khong dung `os.kill(pid, 0)` tren Windows — ở đó nó là TerminateProcess.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return int(code.value) == STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(path=LOCK_PATH, *, pid=None, now=None) -> dict:
    """Lock 1 tien trinh. Pid cu con song -> tu choi; pid chet -> chiem quyen."""
    me = int(pid or os.getpid())
    old = read_json(path, {})
    old_pid = int((old or {}).get("pid") or 0) if isinstance(old, dict) else 0
    if old_pid and old_pid != me and pid_alive(old_pid):
        return {"ok": False, "reason": "da co tien trinh dang chay (pid %d)" % old_pid,
                "pid": old_pid, "took_over": False}
    rec = {"pid": me, "ts": float(now if now is not None else time.time())}
    ok = save_json(path, rec)
    return {"ok": bool(ok), "pid": me, "took_over": bool(old_pid and old_pid != me),
            "reason": "" if ok else "khong ghi duoc lock"}


def release_lock(path=LOCK_PATH, *, pid=None) -> bool:
    """Xoa lock neu CHINH minh dang giu (khong xoa lock cua nguoi khac)."""
    me = int(pid or os.getpid())
    old = read_json(path, {})
    if int((old or {}).get("pid") or 0) not in (0, me):
        return False
    try:
        Path(path).unlink(missing_ok=True)
        return True
    except OSError:
        return False


def tail_lines(path, max_bytes: int = TAIL_BYTES) -> tuple:
    """Doc toi da `max_bytes` tu CUOI file -> (dong, bi_cat)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - int(max_bytes))
            f.seek(start)
            data = f.read()
    except OSError:
        return [], False
    lines = data.decode("utf-8", errors="replace").splitlines()
    if start > 0 and lines:
        lines = lines[1:]          # dong dau bi cat giua
    return lines, start > 0


def _day(now) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(float(now)))


# ------------------------------------------------------------------ agenda

def journal_closes(path=JOURNAL_PATH, since: float = 0.0, max_bytes: int = TAIL_BYTES):
    """Cac lenh CLOSE trong journal co `ts > since`. Tra (list, max_ts, bi_cat)."""
    lines, cut = tail_lines(path, max_bytes)
    out, mx = [], float(since or 0.0)
    for ln in lines:
        try:
            d = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict):
            continue
        ts = float(d.get("ts") or 0.0)
        mx = max(mx, ts)
        if str(d.get("event") or "").upper() != "CLOSE" or ts <= float(since or 0.0):
            continue
        if bool(d.get("partial")):
            continue
        out.append(d)
    return out, mx, bool(cut)


def risk_drift(env_path=ENV_PATH, *, max_ratio: float = 3.0):
    """Bat cau hinh rui ro TU MAU THUAN (doc `.env`, chi doc).

    (21/10) Do that: `RISK_PER_TRADE_PCT=1.2` + `MAX_DAILY_LOSS_PCT=2.0` ⇒ **2 lenh thua
    lien tiep la trip kill-switch** (phai reset tay). Do la quyet dinh cua nguoi van
    hanh, nhung phai duoc NHAC LAI moi khi cau hinh con nhu vay — khong im lang.
    """
    vals = {}
    try:
        for ln in Path(env_path).read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            vals[k.strip().upper()] = v.strip().strip('"').strip("'")
    except OSError:
        return None
    def _f(k):
        try:
            return float(vals.get(k) or 0.0)
        except ValueError:
            return 0.0
    per = _f("RISK_PER_TRADE_PCT")
    day = _f("MAX_DAILY_LOSS_PCT")
    total = _f("MAX_TOTAL_RISK_PCT")
    if per <= 0 or day <= 0:
        return None
    ratio = day / per
    if ratio >= float(max_ratio):
        return None
    return {"per": per, "day": day, "total": total, "ratio": round(ratio, 2),
            "losses_to_trip": int(math.ceil(ratio))}
# ------------------------------------------------------------------ agenda

SEVERITY_ORDER = {"high": 0, "normal": 1, "low": 2}


def _topic(key, kind, severity, question, allow, veto, context) -> dict:
    return {"key": key, "kind": kind, "severity": severity, "question": question,
            "allow": allow, "veto": veto, "context": [str(c)[:400] for c in context]}


def build_agenda(*, state=None, now=None, journal_path=JOURNAL_PATH, ops_path=OPS_OPEN_PATH,
                 regress_path=REGRESS_PATH, env_path=ENV_PATH, pause_path=PAUSE_PATH,
                 bot_heartbeat=HEARTBEAT_BOT, first_run_hours: float = 6.0,
                 min_closes: int = 3, loss_sum_r: float = -2.5, worst_r: float = -3.0,
                 stale_q_hours: float = 24.0, hb_stale_s: float = 600.0) -> dict:
    """Lap CHUONG TRINH NGHI SU tu bang chung THAT (khong goi LLM). Ham thuan tuy.

    Tra {topics, cursor_to, journal_truncated, seeded}. Moi topic du dieu kien de hoi
    hoi dong 1 cau NHI PHAN (ALLOW/VETO) — dung dinh dang `council_vote.build_payload`.
    """
    st = dict(state or {})
    now_t = float(now if now is not None else time.time())
    cursor = float(((st.get("cursor") or {}) or {}).get("journal_ts") or 0.0)
    seeded = bool(cursor)
    if not cursor:
        cursor = now_t - float(first_run_hours) * 3600.0
    topics: list = []

    closes, mx, cut = journal_closes(journal_path, since=cursor)
    if closes:
        rs = [float(c.get("r") or 0.0) for c in closes]
        total = round(sum(rs), 3)
        worst = min(rs)
        wins = sum(1 for r in rs if r > 0)
        bad = (len(closes) >= int(min_closes) or total <= float(loss_sum_r)
               or worst <= float(worst_r))
        if bad:
            ctx = ["%d lenh dong: tong %.2fR, thang %d/%d, te nhat %.2fR"
                   % (len(closes), total, wins, len(closes), worst)]
            for c in sorted(closes, key=lambda x: float(x.get("r") or 0.0))[:3]:
                ctx.append("%s %s: %.2fR (%s)"
                           % (c.get("pair"), str(c.get("direction") or "").upper(),
                              float(c.get("r") or 0.0), c.get("reason") or ""))
            if cut:
                ctx.append("(journal dai hon vung doc — so lenh la NGUONG DUOI)")
            topics.append(_topic(
                "perf:%d%.1f" % (len(closes), total), "perf", "high",
                "Ket qua %d lenh vua dong (tong %.2fR) co phai bat thuong can dung vao lenh?"
                % (len(closes), total),
                "tiep tuc binh thuong, khong doi tham so",
                "tam dung vao lenh moi de dieu tra (vi the dang mo van duoc quan ly)", ctx))

    qs = read_json(ops_path, [])
    if isinstance(qs, list):
        old = []
        for q in qs:
            try:
                age_h = (now_t - float((q or {}).get("ts") or 0.0)) / 3600.0
            except (TypeError, ValueError):
                continue
            if age_h >= float(stale_q_hours):
                old.append((age_h, q))
        if old:
            old.sort(key=lambda x: -x[0])
            ctx = ["%d cau hoi cho qua %.0fh; lau nhat %.0fh: %s"
                   % (len(old), float(stale_q_hours), old[0][0],
                      str(old[0][1].get("question") or "")[:160])]
            for age_h, q in old[1:4]:
                ctx.append("  %.0fh: %s" % (age_h, str(q.get("question") or "")[:140]))
            topics.append(_topic(
                "ops:%d" % len(old), "ops", "normal",
                "Co %d cau hoi van hanh ton dong qua %.0f gio — xu ly hay ha uu tien?"
                % (len(old), float(stale_q_hours)),
                "xu ly ngay trong phien lam viec toi",
                "ha uu tien / dong cac cau hoi khong con can thiet", ctx))

    rg = read_json(regress_path, {})
    probs = list((rg or {}).get("last_problems") or []) if isinstance(rg, dict) else []
    if probs:
        topics.append(_topic(
            "regress:%d" % len(probs), "regress", "high",
            "Watcher bao %d van de (tai phat lop loi / tien trinh chet) — sua ngay hay "
            "theo doi them?" % len(probs),
            "sua ngay (uu tien cao nhat)",
            "theo doi them 1 chu ky, chua sua", probs[:4]))


    drift = risk_drift(env_path)
    if drift:
        topics.append(_topic(
            "risk:daily-vs-trade", "risk", "high",
            "Cau hinh rui ro: %d lenh thua lien tiep la trip kill-switch (risk %.2f%%/lenh, "
            "tran ngay %.2f%%) — co can nang tran ngay?" % (drift["losses_to_trip"],
                                                            drift["per"], drift["day"]),
            "nang MAX_DAILY_LOSS_PCT de chiu duoc >= 3 lenh thua",
            "giu nguyen (chap nhan phai reset kill-switch sau 2 lenh thua)",
            ["tran ngay / risk moi lenh = %.2f (lam tron len: %d)"
             % (drift["ratio"], drift["losses_to_trip"]),
             "tran tong %.2f%%, risk/lenh %.2f%%" % (drift["total"], drift["per"])]))

    pz = read_json(pause_path, {})
    if isinstance(pz, dict) and bool(pz.get("paused")) and not pz.get("until"):
        topics.append(_topic(
            "pause:no-until", "pause", "normal",
            "Cong tam dung vao lenh dang BAT va KHONG co han (%s) — mo lai hay dat han?"
            % str(pz.get("reason") or "")[:120],
            "mo lai vao lenh", "giu tam dung va dat han cu the",
            ["day la lop loi 'tam dung roi quen mo lai' (BTW 16-18/10)"]))

    hb = read_json(bot_heartbeat, {})
    try:
        age = now_t - float((hb or {}).get("ts") or 0.0)
    except (TypeError, ValueError):
        age = 0.0
    if age > float(hb_stale_s):
        topics.append(_topic(
            "bot:heartbeat", "bot", "high",
            "Nhip tim bot cu %.0f giay (> %.0f) — bot dang dung hay chi cham?"
            % (age, float(hb_stale_s)),
            "dieu tra ngay (co the bot da chet)", "chap nhan (dang restart co ke hoach)",
            ["phase=%s round=%s" % ((hb or {}).get("phase"), (hb or {}).get("round"))]))

    topics.sort(key=lambda t: SEVERITY_ORDER.get(t.get("severity"), 9))
    return {"topics": topics, "cursor_to": mx if mx > cursor else cursor,
            "journal_truncated": cut, "seeded": seeded}


def filter_dedup(topics, seen, *, now, ttl_s: float = DEFAULT_TTL_H * 3600.0):
    """Bo chu de da hoi trong TTL (chong dot tien + phieu rac). Tra (giu, bo)."""
    keep, skipped = [], []
    for t in topics or []:
        try:
            ts = float((seen or {}).get(t.get("key")) or 0.0)
        except (TypeError, ValueError):
            ts = 0.0
        if ts > 0 and (float(now) - ts) < float(ttl_s):
            skipped.append({"key": t.get("key"), "age_s": round(float(now) - ts)})
            continue
        keep.append(t)
    return keep, skipped


def budget_of(state, now) -> dict:
    """(chi phi, so chu ky, so phieu) trong NGAY theo gio may."""
    d = _day(now)
    st = dict(state or {})
    return {"day": d,
            "spend": round(float((st.get("spend") or {}).get(d) or 0.0), 4),
            "cycles": int((st.get("cycles") or {}).get(d) or 0),
            "votes": int((st.get("votes") or {}).get(d) or 0)}




# ------------------------------------------------------------------ vong chay

def _votes_cost(res) -> float:
    """Tong chi phi uoc tinh tu phieu (Decision.cost_usd / dict cost_usd)."""
    tot = 0.0
    votes = (res or {}).get("votes") if isinstance(res, dict) else None
    for d in (votes or {}).values():
        try:
            tot += float(d.get("cost_usd") or 0.0) if isinstance(d, dict) \
                else float(getattr(d, "cost_usd", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
    return round(tot, 6)


def default_council(max_models: int = DEFAULT_MODELS):
    """(ask, models): dung dung bo may cua bot, GIOI HAN so model de chan chi phi."""
    import agents as AG
    from config import Settings
    cfg = Settings()
    ms = [m.strip() for m in AG._council_models(cfg) if m.strip()][:max(1, int(max_models))]
    object.__setattr__(cfg, "council_rounds", 1)      # 1 vong: nhanh, du phieu
    object.__setattr__(cfg, "agents_council", True)
    object.__setattr__(cfg, "agents_enabled", True)

    def ask(payload):
        return AG.multi_model_council(cfg, payload, role="critic", models=ms or None)
    return ask, ms


def _append_outbox(path, entries: list, cap: int = 200) -> bool:
    """Noi ket qua vao outbox (giu `cap` muc moi nhat) — nguyen tu."""
    old = read_json(path, [])
    items = list(old) if isinstance(old, list) else []
    items.extend(entries)
    return save_json(path, items[-int(cap):])


def run_cycle(*, live: bool = False, now=None, max_usd_day: float = DEFAULT_MAX_USD_DAY,
              max_cycles_day: int = DEFAULT_MAX_CYCLES_DAY,
              max_topics: int = DEFAULT_MAX_TOPICS, max_models: int = DEFAULT_MODELS,
              ttl_s: float = DEFAULT_TTL_H * 3600.0, state_path=STATE_PATH,
              heartbeat_path=HEARTBEAT_PATH, lock_path=LOCK_PATH, outbox_path=OUTBOX_PATH,
              journal_path=JOURNAL_PATH, ops_path=OPS_OPEN_PATH, regress_path=REGRESS_PATH,
              env_path=ENV_PATH, pause_path=PAUSE_PATH, bot_heartbeat=HEARTBEAT_BOT,
              council_fn=None, write: bool = True) -> dict:
    """1 chu ky: lock -> tran -> agenda -> dedup -> (live) hoi dong -> outbox/heartbeat.

    KHONG BAO GIO: dat/huy lenh, ghi `.env`, sua tham so. Chi de xuat + ghi vet.
    `council_fn(payload)` tiem duoc de test khong goi LLM.
    """
    now_t = float(now if now is not None else time.time())
    state = read_json(state_path, {})
    lock = acquire_lock(lock_path, now=now_t)
    rep = {"ts": now_t, "mode": "locked" if not lock["ok"] else "dry-run",
           "live": bool(live), "topics": [], "skipped": [], "results": [],
           "lock": lock, "budget": budget_of(state, now_t), "heartbeat": ""}
    if not lock["ok"]:
        return rep
    try:
        bud = rep["budget"]
        if bud["cycles"] >= int(max_cycles_day):
            rep["mode"] = "cycles_blocked"
            rep["reason"] = ("da chay %d/%d chu ky hom nay" % (bud["cycles"], max_cycles_day))
            return rep
        ag = build_agenda(state=state, now=now_t, journal_path=journal_path,
                          ops_path=ops_path, regress_path=regress_path, env_path=env_path,
                          pause_path=pause_path, bot_heartbeat=bot_heartbeat)
        keep, skipped = filter_dedup(ag["topics"], (state.get("seen") or {}),
                                     now=now_t, ttl_s=ttl_s)
        rep["skipped"] = skipped
        topics = keep[:max(1, int(max_topics))]
        rep["agenda_total"] = len(ag["topics"])
        models_n = max(1, int(max_models))
        est = round(len(topics) * models_n * EST_USD_PER_VOTE, 4)
        rep["est_usd"] = est if live else 0.0
        if live and topics and (bud["spend"] + est) > float(max_usd_day):
            rep["mode"] = "budget_blocked"
            rep["reason"] = ("chi phi hom nay %.3f + uoc %.3f > tran %.3f USD"
                             % (bud["spend"], est, float(max_usd_day)))
            rep["topics"] = topics
            return rep
        rep["mode"] = "live" if live else "dry-run"
        rep["topics"] = topics
        cost_total, votes_total = 0.0, 0
        for t in topics:
            entry = {"ts": now_t, "mode": rep["mode"], "key": t["key"], "kind": t["kind"],
                     "question": t["question"], "context": t["context"],
                     "verdict": "DRY_RUN" if not live else "", "rows": [],
                     "n_allow": 0, "n_veto": 0, "n_abstain": 0, "cost_usd": 0.0}
            if live and council_fn is not None:
                try:
                    from council_vote import build_payload, tally
                    payload = build_payload(t["question"], t["allow"], t["veto"], t["context"])
                    res = council_fn(payload) or {}
                    decs = (res.get("votes") or res.get("decisions") or {}) \
                        if isinstance(res, dict) else {}
                    tal = tally(decs)
                    entry.update(tal)
                    entry["verdict"] = tal.get("verdict") or "NO_OPINION"
                    entry["cost_usd"] = _votes_cost(res)
                except Exception as e:  # noqa: BLE001  (1 chu de loi khong lam chet vong)
                    entry["verdict"] = "ERROR"
                    entry["error"] = str(e)[:200]
            cost_total += float(entry.get("cost_usd") or 0.0)
            votes_total += int(entry.get("n") or 0)
            rep["results"].append(entry)
            if live:
                state.setdefault("seen", {})[t["key"]] = now_t
        rep["cost_usd"] = round(cost_total, 6)
        if live:
            state.setdefault("cursor", {})["journal_ts"] = ag["cursor_to"]
        d = _day(now_t)
        state.setdefault("spend", {})[d] = round(
            float((state.get("spend") or {}).get(d) or 0.0) + cost_total, 6)
        state.setdefault("votes", {})[d] = int(
            (state.get("votes") or {}).get(d) or 0) + votes_total
        state.setdefault("cycles", {})[d] = int((state.get("cycles") or {}).get(d) or 0) + 1
        state["last_cycle"] = now_t
        state["last_mode"] = rep["mode"]
        state["last_topics"] = [t["key"] for t in topics]
        state["last_results"] = (list(state.get("last_results") or []) + rep["results"])[-20:]
        rep["budget"] = budget_of(state, now_t)
        if write:
            if rep["results"]:
                ok = _append_outbox(outbox_path, rep["results"])
                rep["outbox"] = str(outbox_path) if ok else "GHI LOI"
            rep["state_saved"] = save_json(state_path, state)
        hb = {"ts": now_t, "mode": rep["mode"], "ok": True, "cycle": rep["budget"]["cycles"],
              "topics": len(topics), "spend_today": rep["budget"]["spend"],
              "cycles_today": rep["budget"]["cycles"], "pid": os.getpid(),
              "locked": False}
        if write:
            rep["heartbeat"] = str(heartbeat_path) if save_json(heartbeat_path, hb) else "GHI LOI"
        rep["hb"] = hb
        return rep
    finally:
        release_lock(lock_path)



# ------------------------------------------------------------------ CLI

STOP_FILE = LOG_DIR / "council_stop"


def task_command(*, live: bool = False, python_exe=None, script=None) -> str:
    """Lenh Task Scheduler chay 1 chu ky (pythonw => khong hien cua so console)."""
    py = python_exe or sys.executable
    try:
        import backup as BK
        py = BK.hidden_python(py)
    except Exception:  # noqa: BLE001
        pass
    s = str(script or Path(__file__).resolve())
    cmd = '"%s" "%s" --once' % (py, s)
    return cmd + (" --live" if live else "")


def status(state_path=STATE_PATH, heartbeat_path=HEARTBEAT_PATH, now=None) -> dict:
    """Tinh trang daemon: con song khong, hom nay tieu bao nhieu, vong cuoi lam gi."""
    now_t = float(now if now is not None else time.time())
    st = read_json(state_path, {})
    hb = read_json(heartbeat_path, {})
    hb_age = None
    if isinstance(hb, dict) and hb.get("ts"):
        try:
            hb_age = round(now_t - float(hb["ts"]), 1)
        except (TypeError, ValueError):
            hb_age = None
    bud = budget_of(st, now_t)
    last = (st.get("last_results") or [])[-1:] if isinstance(st, dict) else []
    return {"now": now_t, "heartbeat_age_s": hb_age, "heartbeat": hb,
            "spend_today": bud["spend"], "cycles_today": bud["cycles"],
            "votes_today": bud["votes"], "last_cycle": (st or {}).get("last_cycle"),
            "last_mode": (st or {}).get("last_mode"),
            "last_topics": (st or {}).get("last_topics") or [],
            "last_result": last[0] if last else None,
            "seen": len((st or {}).get("seen") or {}),
            "alive": bool(hb_age is not None and hb_age <= max(120.0, 3 * DEFAULT_INTERVAL))}


def _print_status(s: dict) -> None:
    print("=== HOI DONG NEN | %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    print("  heartbeat: %s" % (("cu %.0f giay" % s["heartbeat_age_s"])
                               if s.get("heartbeat_age_s") is not None else "CHUA CO"))
    print("  hom nay : %d chu ky, %.3f USD, %d phieu | chu de da hoi (TTL): %d"
          % (s["cycles_today"], s["spend_today"], s["votes_today"], s["seen"]))
    if s.get("last_cycle"):
        print("  vong cuoi: %s (%s) - %s"
              % (time.strftime("%H:%M:%S", time.localtime(s["last_cycle"])),
                 s.get("last_mode"), ", ".join(s.get("last_topics") or [])[:120] or "khong co chu de"))
    lr = s.get("last_result") or {}
    if lr:
        print("  ket qua moi nhat: %s -> %s" % (lr.get("key"), lr.get("verdict")))
    print("  KET LUAN: %s" % ("DANG SONG" if s.get("alive") else "KHONG CO NHIP (daemon chua chay?)"))



def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")     # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Hoi dong chay nen 24/7 (mac dinh dry-run)")
    ap.add_argument("--once", action="store_true", help="chay 1 chu ky roi thoat (mac dinh)")
    ap.add_argument("--watch", action="store_true", help="chay lien tuc")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                    help="giay giua 2 chu ky (mac dinh 900)")
    ap.add_argument("--live", action="store_true",
                    help="GOI LLM THAT (mac dinh chi lap chuong trinh nghi su)")
    ap.add_argument("--max-usd-day", type=float, default=DEFAULT_MAX_USD_DAY)
    ap.add_argument("--max-cycles-day", type=int, default=DEFAULT_MAX_CYCLES_DAY)
    ap.add_argument("--max-topics", type=int, default=DEFAULT_MAX_TOPICS)
    ap.add_argument("--max-models", type=int, default=DEFAULT_MODELS)
    ap.add_argument("--ttl-hours", type=float, default=DEFAULT_TTL_H)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="chi in khi CO chu de / loi")
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--uninstall-task", action="store_true")
    ap.add_argument("--task-status", action="store_true")
    ap.add_argument("--task-min", type=int, default=15)
    args = ap.parse_args(argv)

    if args.install_task or args.uninstall_task or args.task_status:
        import backup as BK
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = task_command(live=args.live)
        res = BK.run_schtasks(BK.schtasks_argv(action, TASK_NAME, command=cmd,
                                              sched="MINUTE", mod=args.task_min))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME,
                                   "OK" if res.get("ok") else "LOI (%s)" % res.get("code")))
            print("  lenh: %s  (moi %d phut)" % (cmd, args.task_min))
            if res.get("out"):
                print("  %s" % str(res["out"]).replace("\n", "\n  ")[:300])
        return 0 if res.get("ok") else 1

    if args.status:
        s = status()
        print(json.dumps(s, ensure_ascii=False, indent=1)) if args.json else _print_status(s)
        return 0

    def _one():
        return run_cycle(live=bool(args.live), max_usd_day=args.max_usd_day,
                         max_cycles_day=args.max_cycles_day, max_topics=args.max_topics,
                         max_models=args.max_models,
                         ttl_s=max(0.0, float(args.ttl_hours)) * 3600.0,
                         council_fn=default_council(args.max_models)[0] if args.live else None)

    if not args.watch:
        rep = _one()
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        elif not args.quiet or rep["results"] or rep["mode"] != "dry-run":
            print("=== HOI DONG NEN | %s | %s ===" % (time.strftime("%H:%M:%S"), rep["mode"]))
            print("  chu de: %d (agenda %d, bo qua TTL %d) | chi phi hom nay %.3f USD"
                  % (len(rep["topics"]), rep.get("agenda_total") or 0,
                     len(rep["skipped"]), rep["budget"]["spend"]))
            for t in rep["topics"]:
                print("  - [%s] %s" % (t["severity"], t["question"][:150]))
                for c in t["context"][:3]:
                    print("      %s" % c[:150])
            for r in rep["results"]:
                print("  => %s: %s (%d ALLOW / %d VETO)"
                      % (r["key"], r["verdict"], r["n_allow"], r["n_veto"]))
            if rep.get("reason"):
                print("  ! %s" % rep["reason"])
            if not rep["topics"]:
                print("  (khong co gi bat thuong -- hoi dong khong ton tien)")
        return 0

    STOP_FILE.unlink(missing_ok=True)
    print("[COUNCIL] chay lien tuc moi %.0fs | live=%s | tran %.2f USD/ngay"
          % (args.interval, bool(args.live), args.max_usd_day), flush=True)
    while not STOP_FILE.exists():
        try:
            rep = _one()
            print("[COUNCIL] %s %s chu de=%d chi phi=%.3f (hom nay %.3f)"
                  % (time.strftime("%H:%M:%S"), rep["mode"], len(rep["topics"]),
                     float(rep.get("cost_usd") or 0.0), rep["budget"]["spend"]), flush=True)
        except Exception as e:  # noqa: BLE001
            print("[COUNCIL] loi chu ky: %s" % str(e)[:200], flush=True)
        time.sleep(max(30.0, float(args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

