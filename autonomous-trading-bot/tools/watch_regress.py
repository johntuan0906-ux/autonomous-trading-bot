"""Theo doi TAI PHAT cua lop loi DA VA + SU SONG/CON cua 2 tien trinh (bot + LIVE).

    python tools/watch_regress.py                       # 1 lan: 2 instance + dau hieu tai phat
    python tools/watch_regress.py --check               # exit 1 neu co tai phat / co van de
    python tools/watch_regress.py --watch --interval 300    # chay NEN lien tuc
    python tools/watch_regress.py --json
    python tools/watch_regress.py --mark-fixed B-023    # dat moc "da va" = BAY GIO
    python tools/watch_regress.py --install-task --task-min 10   # Task Scheduler (khong can VS Code)

Vi sao (20/10): sau khi va B-023 (`-2022`) thi cau hoi that la "**no co TAI XUAT HIEN khong**",
va cau tra loi phai do MAY tra loi — khong phai nguoi ngoi doc log. Do that 20/10: **157 lan
`-2022`** trong 1 ngay, 13 lan `monitor ... failed` ⇒ kill-switch TESTNET **trip oan**; neu chi
nhin bang mat thi khong ai thay.

Cach lam: moi lop loi da va = 1 **SIGNATURE** (mau van ban trong log loi) + **MOC THOI GIAN DA VA**.
Chi dem dong log co timestamp `>= moc`. Nho vay "0 lan ke tu khi va" la **bang chung kiem chung
duoc** (va tu dong thanh SAI ngay khi no tai xuat hien). Dong thoi theo doi **tien trinh**:
supervisor/con con co CON chay khong (theo pid THAT, khong chi doc file), nhip tim, kill-switch,
so vi the, cong tam dung.

Khi phat hien tai phat: ghi vet `logs/regress_watch.log` + **them cau hoi vao
`tools/ops_queue.py`** (priority high, moi signature/instance chi 1 lan) — khong im lang.

Trang thai: `logs/regress_watch.json` (moc da va + da bao chua).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import ops as OPS          # noqa: E402

STATE_NAME = "logs/regress_watch.json"
LOG_NAME = "logs/regress_watch.log"
TAIL_BYTES = 8 * 1024 * 1024      # du cho nhieu ngay log (log co dong dai hang KB)
MAX_HB_SEC = 900.0
#: Nhip tim HOI DONG NEN duoc coi la cu khi qua 3 lan chu ky task (task 15 phut => 45 phut).
MAX_COUNCIL_HB_SEC = 2700.0
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

# Lop loi DA VA can theo doi tai phat (them vao day khi va lop loi moi).
# LUU Y mau: dung `"code":-2022` (dang JSON cua LOI tu san), KHONG dung `-2022` tran —
# vi chinh dong INFO THANH CONG cua ban va cung co chuoi `-2022`
# (`INFO CLOSE X: san tu choi reduceOnly (-2022) -> da dong bang qty THAT...`)
# ⇒ neu de rong se tu bao dong gia moi lan bot dong lenh dung.
SIGNATURES = (
    {"code": "B-023", "pattern": '"code":-2022',
     "title": "`-2022` reduceOnly bi san tu choi / vi the da dong (exchange.close_position)"},
)
TASK_NAME = "ATB-WatchRegress"



# ---------------------------------------------------------------- ham THUAN TUY (test duoc)

def parse_ts(line: str):
    """Timestamp (epoch) cua 1 dong log `YYYY-mm-dd HH:MM:SS`; None neu khong co."""
    m = TS_RE.match(str(line or ""))
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return None


def scan_text(lines, pattern: str, since: float = 0.0, until=None) -> dict:
    """Dem dong chua `pattern` co timestamp trong `[since, until]`.

    Tra {n, first_ts, last_ts, sample} — `sample` = toi da 3 dong dau (de doc vet).
    """
    out: dict = {"n": 0, "first_ts": None, "last_ts": None, "sample": []}
    for ln in lines or []:
        if str(pattern) not in ln:
            continue
        ts = parse_ts(ln)
        if ts is None or ts < float(since or 0.0):
            continue
        if until is not None and ts > float(until):
            continue
        out["n"] += 1
        if out["first_ts"] is None:
            out["first_ts"] = ts
        out["last_ts"] = ts
        if len(out["sample"]) < 3:
            out["sample"].append(ln.strip()[:200])
    return out


def read_tail_lines(path: Path, max_bytes: int = TAIL_BYTES) -> tuple:
    """Doc toi da `max_bytes` tu CUOI file -> (cac dong, co_bi_cat_khong)."""
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
        lines = lines[1:]          # dong dau co the bi cat giua => bo
    return lines, start > 0


def list_pids(run=None) -> set:
    """Tap pid dang chay THAT tren may (`tasklist`). Loi -> set() rong (khong doan).

    (21/10) `**winproc.hide_kwargs()`: neu thieu, `tasklist.exe` (chuong trinh CONSOLE)
    duoc spawn tu `pythonw.exe` (Task Scheduler `ATB-WatchRegress` moi 10 phut) ⇒ Windows
    **tu mo 1 cua so cmd den** nhay len giua man hinh — dung nhu nguoi dung bao.
    """
    import winproc
    r = subprocess.run if run is None else run
    try:
        p = r(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
              timeout=30, **winproc.hide_kwargs())
        text = getattr(p, "stdout", "") or ""
    except Exception:  # noqa: BLE001
        return set()
    out: set = set()
    for ln in text.splitlines():
        parts = [x.strip('"') for x in ln.split('","')]
        if len(parts) < 2:
            continue
        try:
            out.add(int(parts[1]))
        except (TypeError, ValueError):
            continue
    return out


def health(name: str, rep: dict, pids=None, *, max_hb_sec: float = MAX_HB_SEC,
           max_council_hb_sec: float = MAX_COUNCIL_HB_SEC) -> list:
    """Van de cua 1 tien trinh (ham THUAN TUY): tra list[str] (rong = khoe)."""
    bad: list = []
    pid = int((rep or {}).get("pid") or 0)
    sup = int((rep or {}).get("supervisor_pid") or 0)
    age = (rep or {}).get("hb_age_s")
    if (rep or {}).get("hb_err") and age is None:
        bad.append("%s: khong doc duoc nhip tim (%s)" % (name, rep.get("hb_err")))
    elif age is not None and float(age) > float(max_hb_sec):
        bad.append("%s: nhip tim cu %.0fs > %.0fs" % (name, float(age), max_hb_sec))
    if not sup:
        bad.append("%s: khong co supervisor (lock trong = bot da dung?)" % name)
    if pids is not None:
        if sup and sup not in pids:
            bad.append("%s: supervisor pid %d KHONG chay" % (name, sup))
        if pid and pid not in pids:
            bad.append("%s: tien trinh con pid %d KHONG chay (nhip tim la so CU)"
                       % (name, pid))
    if (rep or {}).get("kill_tripped"):
        bad.append("%s: KILL-SWITCH dang ngung (%s)" % (name, rep.get("kill_reason") or "?"))
    # (22/10) Do PHU BAO VE: truoc day khong ai kiem dinh ky nen lenh bao ve TRUNG tich tu
    # (B-013) den khi cham tran stop-order (`-4045`) moi biet — dung luc can nhat. Vi the
    # TRAN (khong SL/TP, khong phai bui) la loi NANG: khong co gi chan lo.
    nk = [str(x) for x in ((rep or {}).get("naked") or ())]
    if nk:
        bad.append("%s: %d vi the TRAN (khong SL/TP): %s"
                   % (name, len(nk), ", ".join(nk[:3])))
    try:
        dp = int((rep or {}).get("dupes") or 0)
    except (TypeError, ValueError):
        dp = 0
    if dp:
        bad.append("%s: %d cap lenh bao ve TRUNG -> gom lai "
                   "(python tools/orders_audit.py --dedupe)" % (name, dp))
    # (21/10) Hoi dong nen: "bi chan" (cham tran) KHONG phai loi, nhung "im lang" thi phai bao.
    if (rep or {}).get("council_installed"):
        age_c = (rep or {}).get("council_hb_age_s")
        if age_c is None:
            bad.append("%s: hoi dong nen co file nhip tim nhung KHONG doc duoc moc thoi gian"
                       % name)
        elif float(age_c) > float(max_council_hb_sec):
            bad.append("%s: hoi dong NEN im lang %.0fs > %.0fs (task ATB-Council con chay?)"
                       % (name, float(age_c), float(max_council_hb_sec)))
    return bad


def verdict(instances) -> dict:
    """Ket luan chung tu ket qua tung instance (ham THUAN TUY)."""
    problems: list = []
    hits: list = []
    for i in instances or []:
        name = i.get("name")
        problems.extend(i.get("problems") or [])
        for code, s in (i.get("sightings") or {}).items():
            if int((s or {}).get("n") or 0) > 0:
                hits.append("%s: %s (%s) x%d — lan cuoi %s"
                            % (name, code, (s or {}).get("pattern"), s["n"],
                               time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.localtime(s.get("last_ts") or 0))))
    return {"ok": not problems and not hits, "problems": problems, "regressions": hits}


# ---------------------------------------------------------------- trang thai / vet

def load_state(path=None) -> dict:
    """Doc trang thai (moc da va + da bao). File hong/thieu -> {} (fail-open)."""
    p = Path(path) if path else (ROOT / STATE_NAME)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return d if isinstance(d, dict) else {}


def save_state(state: dict, path=None) -> str:
    """Ghi trang thai nguyen tu (tmp + replace). Tra duong dan (rong neu loi)."""
    p = Path(path) if path else (ROOT / STATE_NAME)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
        return str(p)
    except OSError:
        return ""


def mark_fixed(code: str, state=None, now=None, path=None) -> dict:
    """Dat moc "da va" cho 1 lop loi = BAY GIO (tu do moi dong log duoc tinh la tai phat)."""
    st = dict(state if state is not None else load_state(path))
    base = dict(st.get("fixed_at") or {})
    base[str(code)] = float(now() if callable(now) else (now or time.time()))
    st["fixed_at"] = base
    st["saved"] = save_state(st, path)
    return {"ok": bool(st["saved"]), "code": str(code), "ts": base[str(code)],
            "path": st["saved"]}


def append_log(text: str, path=None) -> str:
    """Ghi 1 dong vet vao `logs/regress_watch.log` (khong nem loi)."""
    p = Path(path) if path else (ROOT / LOG_NAME)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(str(text).rstrip() + "\n")
        return str(p)
    except OSError:
        return ""


# ---------------------------------------------------------------- quet instance

def refresh_orders(base: Path, *, client=None, write: bool = True) -> dict:
    """Kiem ke bao ve tren san (CHI DOC) + ghi `logs/orders_snapshot.json`.

    Vi sao (22/10): khong co gi dinh ky kiem "moi vi the co du 1 SL + 1 TP" ⇒ lenh bao
    ve TRUNG (B-013) tich tu den khi cham tran stop-order (`-4045`) thi moi biet — dung
    luc can nhat. Do that 22/10 tren LIVE: BICO co **4** lenh bao ve (du 2).

    Loi API => tra `{"err": ...}` (KHONG lam hong vong theo doi tien trinh).
    `client` tiem duoc de test (khong goi san).
    """
    base = Path(base)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import orders_audit as OA
        if client is None:
            env = OA.read_env(base / ".env")
            if not (env.get("BINANCE_API_KEY") and env.get("BINANCE_API_SECRET")):
                return {}
            live = str(env.get("BINANCE_TESTNET", "true")).lower() in ("false", "0", "no")
            client = OA.build_client(env, live)
        else:
            live = bool(getattr(client, "testnet", False) is False)
        poss = [p for p in (client.fetch_positions() or [])
                if float(p.get("contracts") or 0) != 0]
        orders, _err = OA.all_orders(client, [str(p.get("symbol")) for p in poss])
        s = OA.summarize(orders, poss, dust=OA.load_dust(base))
        s["target"] = "live" if live else "testnet"
        s["live"] = live
        if write:
            p = base / "logs" / "orders_snapshot.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(p)
        return s
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:140]}


def scan_instance(name: str, base: Path, *, baseline=None, minutes: float = 7.0,
                  pids=None, max_bytes: int = TAIL_BYTES, until=None,
                  orders: bool = False, client=None) -> dict:
    """Bao cao 1 instance: tien trinh + dau hieu tai phat ke tu moc da va.

    Dung lai `ops._instance()` (mot nguon su that cho nhip tim/kill/vi the/supervisor) roi
    them 3 thu ma ops.py khong co: pid CON con chay khong, cong tam dung, va so lan tai phat.
    """
    base = Path(base)
    snap = refresh_orders(base, client=client) if orders else {}
    rep = dict(OPS._instance(name, base, minutes))
    rep["name"] = name
    rep["dir"] = str(base)
    if orders:
        rep["orders_checked"] = not bool(snap.get("err"))
        rep["dupes"] = len(snap.get("dupes") or {}) if not snap.get("err") else None
        rep["naked"] = list(snap.get("naked") or [])
        if snap.get("err"):
            rep["orders_err"] = snap["err"]
    try:
        rep["child_pid"] = int(rep.get("pid") or 0)
    except (TypeError, ValueError):
        rep["child_pid"] = 0
    if pids is not None:
        rep["supervisor_alive"] = int(rep.get("supervisor_pid") or 0) in pids
        rep["child_alive"] = bool(rep.get("child_pid")) and rep["child_pid"] in pids
    try:
        pz = json.loads((base / "logs" / "entries_pause.json").read_text(encoding="utf-8"))
        paused = bool(pz.get("paused"))
        rep["paused_until"] = float(pz.get("until") or 0) if paused else 0.0
        rep["paused_reason"] = str(pz.get("reason") or "")[:160] if paused else ""
    except Exception:  # noqa: BLE001
        rep["paused_until"] = 0.0
    lines, cut = read_tail_lines(base / "logs" / "turbo_err.log", max_bytes)
    rep["log_truncated"] = bool(cut)
    # (21/10) HOI DONG NEN: doc nhip tim cua `tools/council_daemon.py` (neu da lap). Neu no
    # chet that ma khong ai doc thi "chay 24/7" chi la loi hua — dung lop loi B-027.
    chb = {}
    try:
        chb = json.loads((base / "logs" / "council_heartbeat.json").read_text(encoding="utf-8"))
        chb = chb if isinstance(chb, dict) else {}
    except Exception:  # noqa: BLE001
        chb = {}
    rep["council_installed"] = bool(chb)
    if chb:
        try:
            rep["council_hb_age_s"] = round(float(until or time.time())
                                            - float(chb.get("ts") or 0.0), 1)
        except (TypeError, ValueError):
            rep["council_hb_age_s"] = None
        rep["council_mode"] = str(chb.get("mode") or "")
        rep["council_blocked"] = bool(chb.get("blocked"))
        rep["council_spend_today"] = chb.get("spend_today")
        rep["council_topics"] = chb.get("topics")
    base_ts = dict((baseline or {}).get("fixed_at") or {})
    rep["sightings"] = {}
    for sig in SIGNATURES:
        code = sig["code"]
        s = scan_text(lines, sig["pattern"], since=base_ts.get(code, 0.0), until=until)
        s["pattern"] = sig["pattern"]
        s["title"] = sig["title"]
        s["since"] = base_ts.get(code, 0.0)
        rep["sightings"][code] = s
    rep["problems"] = health(name, rep, pids)
    return rep


def build_report(*, dirs=None, baseline=None, minutes: float = 7.0, pids=None,
                 max_bytes: int = TAIL_BYTES, until=None, orders: bool = False,
                 clients=None) -> dict:
    """Bao cao CA 2 instance (hoac `dirs` tuy y — de test). `pids=None` -> doc tu may."""
    dirs = dirs or {"TESTNET": ROOT, "LIVE": LIVE_DIR}
    pids = list_pids() if pids is None else pids
    inst = [scan_instance(n, d, baseline=baseline, minutes=minutes, pids=pids,
                          max_bytes=max_bytes, until=until, orders=orders,
                          client=(clients or {}).get(n))
            for n, d in dirs.items()]
    v = verdict(inst)
    return {"ts": time.time(), "pids": len(pids), "instances": inst, **v}


def touch_state(rep: dict, state=None, path=None) -> dict:
    """Ghi VET lan kiem tra (`last_check`, `last_ok`, `last_problems`) vao state.

    Vi sao can: neu chi ghi khi CO vi pham thi khong co cach nao chung minh watcher
    **thuc su dang chay** (task Scheduler chet im lang cung deu khong ai biet) — dung lop
    loi "im lang" cua du an. Nhin `last_check` la biet no con song va moi may phut.
    """
    st = dict(state if state is not None else load_state(path))
    st["last_check"] = float((rep or {}).get("ts") or time.time())
    st["last_ok"] = bool((rep or {}).get("ok"))
    st["last_problems"] = (list((rep or {}).get("problems") or [])
                           + list((rep or {}).get("regressions") or []))
    st["saved"] = save_state(st, path)
    return st


PROBLEM_KINDS = (
    ("KILL-SWITCH", "kill"),
    ("TRAN (khong SL/TP)", "naked"),
    ("bao ve TRUNG", "dupes"),
    ("khong co supervisor", "supervisor"),
    ("supervisor pid", "supervisor"),
    ("tien trinh con pid", "child"),
    ("hoi dong NEN im lang", "council"),
    ("nhip tim cu", "heartbeat"),
    ("khong doc duoc nhip tim", "heartbeat"),
    ("TAM DUNG", "pause"),
)


def problem_kind(text: str) -> str:
    """Ma ON DINH cho 1 van de tien trinh (de chong spam ma khong im lang).

    Van de chua SO thay doi tung lan (vd `nhip tim cu 620s`) ⇒ neu lay ca chuoi lam khoa
    thi moi lan la 1 khoa moi ⇒ spam. Lay theo LOAI van de.
    """
    t = str(text or "")
    for marker, code in PROBLEM_KINDS:
        if marker in t:
            return code
    return "khac"


def notify(rep: dict, *, state=None, enqueue=None, now=None, path=None,
           cooldown_s: float = 3600.0) -> dict:
    """Bao DONG khi co tai phat: ghi vet + cau hoi van hanh.

    Chong SPAM nhung KHONG im lang vinh vien: bao lai khi so lan tai phat **tang len**
    VA da qua `cooldown_s` (mac dinh 1h) ke tu lan bao truoc. (Ban dau chi bao 1 lan
    duy nhat ⇒ mot bao dong GIA se lam tat moi canh bao that ve sau — do that 20/10.)

    `enqueue` tiem duoc (test khong dung den `ops_queue` that). Tra {sent, state}.
    """
    st = dict(state if state is not None else load_state(path))
    done = dict(st.get("notified") or {})
    now_t = float(now() if callable(now) else (now or time.time()))
    sent: list = []
    for i in rep.get("instances") or []:
        for code, s in (i.get("sightings") or {}).items():
            if int((s or {}).get("n") or 0) <= 0:
                continue
            key = "%s/%s" % (i.get("name"), code)
            prev = done.get(key) or {}
            if isinstance(prev, dict) and prev:
                prev_n = int(prev.get("n") or 0)
                prev_ts = float(prev.get("ts") or 0.0)
                if int(s["n"]) <= prev_n or (now_t - prev_ts) < float(cooldown_s):
                    continue
            why = ("Tai phat %s (%s) tai %s: %d lan, lan cuoi %s. Mau: %s"
                   % (code, s.get("pattern"), i.get("name"), s["n"],
                      time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.localtime(s.get("last_ts") or 0)),
                      " | ".join(s.get("sample") or [])[:600]))
            append_log("%s TAI PHAT %s @ %s: %s"
                       % (time.strftime("%Y-%m-%d %H:%M:%S"), code, i.get("name"), why),
                       path=(Path(path).parent / LOG_NAME) if path else None)
            rec = {"ok": True, "key": key}
            if enqueue is not None:
                rec = enqueue("Lop loi %s TAI XUAT HIEN (%s) — xu ly tiep"
                              % (code, i.get("name")), why=why,
                              options=["dieu tra ngay", "tam chap nhan + theo doi them"],
                              priority="high")
            done[key] = {"ts": now_t, "n": int(s["n"])}
            sent.append({"key": key, "record": rec})
    # (22/10) VAN DE TIEN TRINH / AN TOAN: truoc day chi IN ra roi thoi (khong vao
    # `ops_queue`) ⇒ dung lop loi "im lang": kill-switch TRIPPED, supervisor chet, vi the
    # TRAN, lenh bao ve TRUNG... deu khong ai duoc hoi. Nay day vao hang doi theo LOAI
    # van de: bao lai moi `cooldown_s` khi van con ⇒ khong spam nhung cung khong tat.
    for i in rep.get("instances") or []:
        for p in (i.get("problems") or []):
            kind = problem_kind(p)
            key = "%s/PROBLEM/%s" % (i.get("name"), kind)
            prev = done.get(key) or {}
            if isinstance(prev, dict) and prev:
                if (now_t - float(prev.get("ts") or 0.0)) < float(cooldown_s):
                    continue
            why = ("Van de tien trinh/an toan tai %s (loai %s): %s"
                   % (i.get("name"), kind, p))
            append_log("%s VAN DE %s @ %s: %s"
                       % (time.strftime("%Y-%m-%d %H:%M:%S"), kind, i.get("name"), p),
                       path=(Path(path).parent / LOG_NAME) if path else None)
            rec = {"ok": True, "key": key}
            if enqueue is not None:
                kw = {"why": why, "options": ["da xu ly / khong can", "can sua tiep"],
                      "priority": "high"}
                # (26/10) Cau hoi phai vao DUNG hang doi cua instance (LIVE -> atb-live):
                # task chay `--target both` tu repo TESTNET, khong co duong dan thi cau hoi
                # cua LIVE se nam trong hang doi TESTNET (nguoi van hanh LIVE khong thay).
                if i.get("dir"):
                    kw["open_path"] = Path(str(i["dir"])) / "logs" / "ops_questions.json"
                rec = enqueue("Van de tien trinh/an toan tai %s: %s" % (i.get("name"), p),
                              **kw)
                if isinstance(rec, dict) and rec.get("ok") is False:
                    append_log("%s KHONG GHI DUOC HANG DOI cho %s: %s"
                               % (time.strftime("%Y-%m-%d %H:%M:%S"), i.get("name"),
                                  str(rec.get("path") or "?")),
                               path=(Path(path).parent / LOG_NAME) if path else None)
            done[key] = {"ts": now_t, "kind": kind, "text": str(p)[:200]}
            sent.append({"key": key, "record": rec})
    st["notified"] = done
    st["saved"] = save_state(st, path)
    return {"sent": sent, "state": st}




# ---------------------------------------------------------------- CLI

def task_command(python_exe=None, script=None, target: str = "both") -> str:
    """Lenh Task Scheduler se chay (duong dan TUYET DOI + nhay kep; task chay cwd khac)."""
    py = python_exe or sys.executable
    try:
        import backup as BK
        py = BK.hidden_python(py)      # pythonw: khong hien cua so console moi 10 phut
    except Exception:  # noqa: BLE001
        pass
    s = str(script or Path(__file__).resolve())
    return '"%s" "%s" --target %s --check --orders' % (py, s, target)


def _print(rep: dict) -> None:
    print("=== THEO DOI TAI PHAT | %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    for i in rep["instances"]:
        age = i.get("hb_age_s")
        print("%-8s round=%-4s phase=%-14s hb=%-7s supervisor=%-10s con=%-10s kill=%-8s vi the=%s"
              % (i["name"], i.get("round"), i.get("phase"),
                 ("%.0fs" % float(age)) if age is not None else "?",
                 ("%d%s" % (i.get("supervisor_pid") or 0,
                            "" if i.get("supervisor_alive", True) else "(CHET)"))
                 if i.get("supervisor_pid") else "KHONG",
                 ("%d%s" % (i.get("child_pid") or 0,
                            "" if i.get("child_alive", True) else "(CHET)"))
                 if i.get("child_pid") else "KHONG",
                 "TRIPPED" if i.get("kill_tripped") else "-", i.get("positions")))
        if i.get("orders_checked"):
            print("         bao ve: %s vi the / %s lenh cho / %s mo coi / %s cap TRUNG / %s TRAN"
                  % (i.get("positions"), i.get("orders"), i.get("orphans") or 0,
                     i.get("dupes") if i.get("dupes") is not None else "?",
                     len(i.get("naked") or [])))
        elif i.get("orders_err"):
            print("         bao ve: khong doc duoc san (%s)" % i.get("orders_err"))
        if i.get("paused_until"):
            print("         TAM DUNG toi %s: %s"
                  % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(i["paused_until"])),
                     i.get("paused_reason") or ""))
        for code, s in (i.get("sightings") or {}).items():
            moc = (time.strftime("%H:%M %d/%m", time.localtime(s.get("since") or 0))
                   if s.get("since") else "CHUA DAT MOC")
            print("         %-6s %-8s tu %-14s: %d lan%s"
                  % (code, s.get("pattern"), moc, s["n"], "" if s["n"] else "  (sach)"))
            for ln in (s.get("sample") or [])[:1]:
                print("            %s" % ln)
        if i.get("log_truncated"):
            print("         (log dai hon vung doc -> so lan la NGUONG DUOI)")
    print("KET LUAN: %s" % ("OK — tien trinh khoe, khong tai phat" if rep["ok"]
                            else "CAN XEM"))
    for p in rep.get("problems") or []:
        print("  - %s" % p)


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Theo doi tai phat lop loi da va + tien trinh")
    ap.add_argument("--target", choices=("both", "testnet", "live"), default="both")
    ap.add_argument("--minutes", type=float, default=7.0, help="cua so dem loi cua ops.py")
    ap.add_argument("--max-hb-sec", type=float, default=MAX_HB_SEC)
    ap.add_argument("--mark-fixed", metavar="CODE", help="dat moc 'da va' = bay gio")
    ap.add_argument("--watch", action="store_true", help="chay lien tuc (nen)")
    ap.add_argument("--interval", type=float, default=300.0, help="giay giua 2 lan (mac dinh 300)")
    ap.add_argument("--check", action="store_true", help="exit 1 neu co tai phat/co van de")
    ap.add_argument("--orders", action="store_true",
                    help="kiem ke bao ve tren san (goi API, ghi snapshot) + canh bao TRAN/TRUNG")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="chi in khi CO van de (dung cho --watch)")
    ap.add_argument("--no-notify", action="store_true", help="khong them cau hoi van hanh")
    ap.add_argument("--install-task", action="store_true")
    ap.add_argument("--uninstall-task", action="store_true")
    ap.add_argument("--task-status", action="store_true")
    ap.add_argument("--task-min", type=int, default=10)
    args = ap.parse_args(argv)

    if args.install_task or args.uninstall_task or args.task_status:
        import backup as BK
        action = ("install" if args.install_task else
                  "uninstall" if args.uninstall_task else "status")
        cmd = task_command(target=args.target)
        res = BK.run_schtasks(BK.schtasks_argv(action, TASK_NAME, command=cmd,
                                              sched="MINUTE", mod=args.task_min))
        res.update({"action": action, "task": TASK_NAME, "command": cmd})
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            print("task %s: %s" % (TASK_NAME, "OK" if res["ok"] else "LOI (%s)" % res["code"]))
            print("  lenh: %s  (moi %d phut)" % (cmd, args.task_min))
            if res.get("out"):
                print("  %s" % res["out"].replace("\n", "\n  ")[:300])
        return 0 if res["ok"] else 1

    if args.mark_fixed:
        r = mark_fixed(args.mark_fixed)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        else:
            print("moc da va %s = %s (%s)"
                  % (r["code"], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ts"])),
                     r["path"] or "GHI LOI"))
        return 0 if r["ok"] else 1

    dirs = {"TESTNET": ROOT, "LIVE": LIVE_DIR}
    if args.target == "testnet":
        dirs = {"TESTNET": ROOT}
    elif args.target == "live":
        dirs = {"LIVE": LIVE_DIR}

    def once() -> dict:
        st = load_state()
        rep = build_report(dirs=dirs, baseline=st, minutes=args.minutes,
                           orders=args.orders)
        st = touch_state(rep, state=st)          # vet lan kiem tra (chung minh con chay)
        # (22/10) Khong chi tai phat LOG: van de tien trinh/an toan (kill-switch TRIPPED,
        # supervisor chet, vi the TRAN, lenh bao ve TRUNG) cung phai vao `ops_queue`.
        if not args.no_notify and (rep["regressions"] or rep["problems"]):
            import ops_queue as OQ
            rep["notify"] = notify(rep, state=st, enqueue=OQ.add)
        else:
            rep["state_saved"] = st.get("saved")
        return rep

    if not args.watch:
        rep = once()
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        elif not (args.quiet and rep["ok"]):
            _print(rep)
        return 0 if (rep["ok"] or not args.check) else 1

    append_log("%s WATCH bat dau (moi %.0fs, target=%s)"
               % (time.strftime("%Y-%m-%d %H:%M:%S"), args.interval, args.target))
    while True:
        rep = once()
        if rep["ok"]:
            if not args.quiet:
                print("%s OK — tien trinh khoe, 0 tai phat" % time.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            _print(rep)
            append_log("%s WATCH phat hien van de: %s"
                       % (time.strftime("%Y-%m-%d %H:%M:%S"),
                          "; ".join(list(rep.get("problems") or [])
                                    + list(rep.get("regressions") or []))))
        time.sleep(max(30.0, float(args.interval)))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:      # pythonw (Task Scheduler): loi phai vao FILE, khong duoc im
        import traceback
        append_log(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc())
        raise SystemExit(1)

    for r in rep.get("regressions") or []:
        print("  - TAI PHAT: %s" % r)

