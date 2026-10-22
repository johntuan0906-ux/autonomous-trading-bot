"""Chấm điểm "setup" của bot bằng 1 lệnh — tất định, đọc file, KHÔNG gọi mạng.

    python tools/harness_audit.py                 # instance hiện tại (TESTNET)
    python tools/harness_audit.py --target live    # instance LIVE (../atb-live)
    python tools/harness_audit.py --both           # cả 2 + so khớp code
    python tools/harness_audit.py --json           # cho máy đọc
    python tools/harness_audit.py --with-exchange  # thêm kiểm tra lệnh bảo vệ (gọi sàn)

Vì sao có (13/10): hôm nay phải chạy 3 lệnh thủ công mới phát hiện ra LIVE có **3 vị thế
trần không SL/TP** và bot đã quên chúng. Ý tưởng lấy từ ruflo/MetaHarness: "chấm điểm
setup agent, quét cấu hình, phát hiện thay đổi giữa các lần chạy".

Triết lý: mỗi tiêu chí phải **tất định và có cách sửa cụ thể** (in ra lệnh cần chạy).
Điểm số chỉ để nhìn nhanh; giá trị thật nằm ở danh sách FAIL/WARN kèm việc cần làm.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT.parent / "atb-live"
LEVELS = ("OK", "WARN", "FAIL")
MARK = {"OK": "  ", "WARN": "??", "FAIL": "!!"}
# (19/10) So model toi thieu phai TRA PHIEU trong 48h de coi hoi dong la "dang song".
# Duoi nguong nay thi moi ket luan ve veto/allow la vo nghia (xem AGENTS.md).
MIN_COUNCIL_MODELS = 3


def read_env(path: Path) -> dict:
    """Doc `.env` -> dict (bo comment, cat khoang trang, bo dau ngoac)."""
    out: dict = {}
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def flag(env: dict, key: str, default: bool = False) -> bool:
    """Doc co kieu bool tu `.env` ('true/1/yes' = True)."""
    return str(env.get(key, "true" if default else "false")).lower() in ("1", "true", "yes")


def count_test_funcs(tests_dir: Path) -> tuple:
    """(so file test, so ham test) — dem tinh, khong chay."""
    files = n = 0
    try:
        for p in tests_dir.glob("test_*.py"):
            files += 1
            n += p.read_text(encoding="utf-8", errors="replace").count("def test_")
    except OSError:
        pass
    return files, n


def journal_balance(path: Path) -> dict:
    """Dem OPEN/CLOSE trong journal -> {open, close, orphan}.

    `orphan` = OPEN khong co CLOSE tuong ung (theo so luong) — dau hieu vi the mo coi
    hoac dong lenh bi thieu ghi chep (WR/PF se sai).
    """
    o = c = 0
    try:
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if '"event": "OPEN"' in ln or '"event":"OPEN"' in ln:
                o += 1
            elif '"event": "CLOSE"' in ln or '"event":"CLOSE"' in ln:
                c += 1
    except OSError:
        return {"open": 0, "close": 0, "orphan": 0}
    return {"open": o, "close": c, "orphan": max(0, o - c)}


def council_models(path: Path, hours: float = 48.0, now=None) -> dict:
    """So MODEL khac nhau THUC SU tra phieu hoi dong trong `hours` gio.

    Tra `{n, models, votes}`. Doc tu `logs/journal.jsonl` (cac dong `status=COUNCIL`
    co `model`) — CUNG nguon voi `agents.py --council-health`, khong goi mang.

    (19/10) Lop loi "hoi dong IM LANG" (da gap that: 402 het credit, provider 500,
    tier `lite` => 0 phieu): truoc day `harness_audit` chi doc `AGENT_VETO_SOURCE`
    nen van bao OK trong khi **khong model nao tra phieu** => moi ket luan ve veto
    la vo nghia (AGENTS.md canh bao dung ca nay). Dong thieu/hong `ts` duoc TINH
    (fail-open: khong vi 1 dong hong ma bao dong gia).
    """
    t0 = float(now() if callable(now) else time.time()) - float(hours) * 3600.0
    models: set = set()
    votes = 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {"n": 0, "models": [], "votes": 0}
    for ln in lines:
        if "COUNCIL" not in ln:
            continue
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(d, dict) or str(d.get("status") or "").upper() != "COUNCIL":
            continue
        try:
            ts = float(d.get("ts") or 0)
        except (TypeError, ValueError):
            ts = 0.0
        if ts and ts < t0:
            continue
        m = str(d.get("model") or "").strip()
        if m:
            models.add(m)
            votes += 1
    return {"n": len(models), "models": sorted(models), "votes": votes}


def hash_py(d: Path, names) -> dict:
    """sha1 cua cac file code chinh -> so khop giua 2 instance."""
    out: dict = {}
    for name in names:
        p = d / name
        try:
            out[name] = hashlib.sha1(p.read_bytes()).hexdigest()[:12]
        except OSError:
            out[name] = "-"
    return out


def code_parity(main: Path, live: Path, names) -> dict:
    """So sanh code 2 instance -> {file: (main_hash, live_hash, khop?)}."""
    a, b = hash_py(main, names), hash_py(live, names)
    return {n: (a[n], b[n], a[n] == b[n]) for n in names}


def add(checks: list, level: str, name: str, detail: str, fix: str = "") -> None:
    """Them 1 tieu chi (giu dung thu tu LEVELS de tinh diem)."""
    checks.append({"level": level, "name": name, "detail": detail, "fix": fix})


def score(checks: list) -> int:
    """Diem 0-100: FAIL tru 12, WARN tru 4 (khong am)."""
    s = 100
    for c in checks or []:
        if c.get("level") == "FAIL":
            s -= 12
        elif c.get("level") == "WARN":
            s -= 4
    return max(0, s)


def summarize(checks: list) -> dict:
    """Dem theo muc + ket luan 1 dong."""
    n = {lv: 0 for lv in LEVELS}
    for c in checks or []:
        n[c.get("level", "WARN")] = n.get(c.get("level", "WARN"), 0) + 1
    sc = score(checks)
    if n["FAIL"]:
        verdict = "CAN SUA NGAY (%d muc FAIL)" % n["FAIL"]
    elif n["WARN"]:
        verdict = "chap nhan duoc nhung nen xem (%d muc WARN)" % n["WARN"]
    else:
        verdict = "sach"
    return {"ok": n["FAIL"], "warn": n["WARN"], "passed": n["OK"],
            "score": sc, "verdict": verdict}


CODE_FILES = ("exchange.py", "bot.py", "turbo_demo.py", "position_sync.py",
              "trade_mgmt.py", "risk.py", "run_forever.py", "learner.py")


def _chk_core(checks: list, base: Path, label: str) -> dict:
    """Nhom 1: code-parity, test, kill-switch, nhip tim, journal. Tra env da doc."""
    env = read_env(base / ".env")
    logs = base / "logs"
    par = code_parity(ROOT, LIVE_DIR, CODE_FILES)
    diff = [n for n, (_a, _b, same) in par.items() if not same]
    if diff:
        add(checks, "WARN", "code-parity", "code 2 instance KHAC nhau: %s" % ", ".join(diff),
            "robocopy autonomous-trading-bot atb-live *.py /E")
    else:
        add(checks, "OK", "code-parity", "code 2 instance giong nhau")

    files, n = count_test_funcs(ROOT / "tests")
    if n >= 100:
        add(checks, "OK", "tests", "%d file / %d ham test" % (files, n))
    else:
        add(checks, "FAIL", "tests", "chi %d ham test" % n,
            "python -m unittest discover -s tests")

    rs = logs / "risk_state.json"
    if rs.exists():
        try:
            st = json.loads(rs.read_text(encoding="utf-8"))
            if st.get("tripped"):
                add(checks, "FAIL", "kill-switch", "DANG NGUNG: %s" % str(st.get("reason"))[:90],
                    "python risk.py --reset (chi khi bot DA DUNG)")
            else:
                add(checks, "OK", "kill-switch", "khong tripped")
        except Exception:  # noqa: BLE001
            add(checks, "FAIL", "kill-switch", "risk_state.json doc KHONG duoc (fail-closed)",
                "xem risk.py: file hong bi coi la dang tripped")
    else:
        add(checks, "OK", "kill-switch", "chua co risk_state.json")

    hb = logs / "heartbeat.json"
    if hb.exists():
        try:
            d = json.loads(hb.read_text(encoding="utf-8"))
            age = time.time() - float(d.get("ts") or 0)
            add(checks, "OK" if age < 600 else "FAIL", "heartbeat",
                "nhip cuoi %.0fs truoc" % age,
                "python tools/restart_bot.py --target %s" % label.lower())
        except Exception:  # noqa: BLE001
            add(checks, "WARN", "heartbeat", "khong doc duoc heartbeat.json")
    else:
        add(checks, "WARN", "heartbeat", "chua co heartbeat.json")

    jb = journal_balance(logs / "journal.jsonl")
    if jb["orphan"] > 5:
        add(checks, "WARN", "journal", "%d OPEN khong co CLOSE" % jb["orphan"],
            "python reconcile.py")
    else:
        add(checks, "OK", "journal", "%d OPEN / %d CLOSE" % (jb["open"], jb["close"]))
    return env


def _chk_config(checks: list, env: dict, label: str) -> None:
    """Nhom 2: tran rui ro, interlock LIVE, whitelist, trang thai veto."""
    try:
        lev = int(float(env.get("LEVERAGE", 0) or 0))
        risk = float(env.get("MAX_TOTAL_RISK_PCT", 0) or 0)
        live = not flag(env, "BINANCE_TESTNET", True)
        confirm = flag(env, "LIVE_CONFIRM", False)
        if lev > 10:
            add(checks, "FAIL", "risk-caps", "LEVERAGE=%d > 10" % lev, "ha LEVERAGE <= 10")
        elif risk > 2.0:
            add(checks, "FAIL", "risk-caps", "MAX_TOTAL_RISK_PCT=%.1f > 2.0" % risk,
                "ha ve <= 2.0")
        else:
            add(checks, "OK", "risk-caps", "LEVERAGE=%d risk=%.1f%%" % (lev, risk))
        if live and not confirm:
            add(checks, "FAIL", "live-interlock",
                "BINANCE_TESTNET=false nhung LIVE_CONFIRM!=true",
                "dat LIVE_CONFIRM=true hoac quay ve demo")
        elif (not live) and confirm:
            add(checks, "WARN", "live-interlock",
                "LIVE_CONFIRM=true tren instance DEMO (vo hai, nen dat false)")
        else:
            add(checks, "OK", "live-interlock", "%s (LIVE_CONFIRM=%s)"
                % ("LIVE THAT" if live else "DEMO", confirm))
        if flag(env, "DRY_RUN", False):
            add(checks, "WARN", "dry-run", "DRY_RUN=true — bot KHONG dat lenh that")
        if not float(env.get("MIN_TP_PCT", 0) or 0):
            add(checks, "WARN", "min-tp", "MIN_TP_PCT trong/0")
    except Exception as e:  # noqa: BLE001
        add(checks, "WARN", "risk-caps", "doc cau hinh loi: %s" % str(e)[:80])

    try:
        n_sym = len([s for s in str(env.get("SYMBOLS", "")).split(",") if s.strip()])
        lst = ROOT / "symbols_all.txt"
        n_list = 0
        if lst.exists():
            n_list = len([t for t in lst.read_text(encoding="utf-8")
                          .replace("\n", ",").split(",") if t.strip()])
        if n_sym <= 0:
            add(checks, "FAIL", "whitelist", "SYMBOLS trong .env",
                "python tools/apply_symbols.py --target %s" % label.lower())
        else:
            add(checks, "OK", "whitelist", "%d cap trong .env (danh sach goc %d)"
                % (n_sym, n_list))
    except Exception as e:  # noqa: BLE001
        add(checks, "WARN", "whitelist", "doc loi: %s" % str(e)[:80])

    src = str(env.get("AGENT_VETO_SOURCE", "")).upper()
    if src in ("COUNCIL", "SETUP") and flag(env, "AGENTS_VETO_ENABLED", False):
        add(checks, "WARN", "council-veto",
            "veto THAT dang bat (%s) — can bang chung granted=True" % src,
            "python agents.py --authority")
    else:
        add(checks, "OK", "council-veto", "hoi dong o che do SHADOW (chi co van)")


def _chk_council(checks: list, logs: Path) -> None:
    """Nhom 3: hoi dong co THUC SU tra phieu khong (48h) — chong lop loi "im lang".

    Khong co phieu => bot van chay nhung **quyet dinh dua tren hoi dong la vo nghia**
    (va `council_vote`/`trace_trade` se in "0 phieu"). Canh bao thay vi FAIL vi bot
    van an toan: veto dang o che do SHADOW.
    """
    rep = council_models(logs / "journal.jsonl")
    if rep["n"] >= MIN_COUNCIL_MODELS:
        add(checks, "OK", "council-models",
            "%d model tra phieu / 48h (%d phieu)" % (rep["n"], rep["votes"]))
    elif rep["n"]:
        add(checks, "WARN", "council-models",
            "chi %d model tra phieu / 48h — hoi dong mo mong" % rep["n"],
            "python agents.py --council-health --hours 48")
    else:
        add(checks, "WARN", "council-models",
            "hoi dong IM LANG 48h (0 phieu) — moi ket luan ve veto la vo nghia",
            "python agents.py --council-health --hours 48")


def audit_one(base: Path, label: str, *, with_exchange: bool = False) -> dict:
    """Cham diem 1 instance. Tra {label, checks, summary, dir}."""
    checks: list = []
    if not read_env(base / ".env"):
        add(checks, "FAIL", "env", "khong doc duoc %s" % (base / ".env"),
            "kiem tra file .env cua instance")
        return {"label": label, "checks": checks, "summary": summarize(checks),
                "dir": str(base)}
    env = _chk_core(checks, base, label)
    _chk_config(checks, env, label)
    _chk_council(checks, base / "logs")
    _chk_local_model(checks, env)
    if with_exchange:
        _chk_protection(checks, env, label, base)
    else:
        add(checks, "OK", "bao-ve", "bo qua (them --with-exchange de kiem tra that)")
    return {"label": label, "checks": checks, "summary": summarize(checks),
            "dir": str(base)}


def probe_local_model(env: dict, timeout: float = 5.0) -> dict:
    """Model LOCAL cua hoi dong con song khong? -> {'ok', 'url', 'ids', 'error'}.

    Hoi dong co 1 phieu LOCAL mien phi (Ollama hoac llamafile). Neu dich vu chet thi
    phieu do IM LANG mat (fail-open) — khong ai bao. Ham nay doc
    `AGENT_LOCAL_BASE_URL` trong `.env` va goi `/v1/models` (hoac `/api/tags` cua Ollama).
    """
    import urllib.request
    base = str(env.get("AGENT_LOCAL_BASE_URL") or "").rstrip("/")
    out = {"ok": False, "url": base, "ids": [], "error": ""}
    if not base:
        out["error"] = "AGENT_LOCAL_BASE_URL trong"
        return out
    for path in ("/models", "/api/tags"):
        try:
            with urllib.request.urlopen(base + path, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8", errors="replace"))
            ids = [str((m or {}).get("id") or (m or {}).get("name") or "")
                   for m in (d.get("data") or d.get("models") or [])]
            ids = [i for i in ids if i]
            out.update({"ok": True, "ids": ids})
            return out
        except Exception as e:  # noqa: BLE001
            out["error"] = str(e)[:110]
    return out


def _chk_local_model(checks: list, env: dict) -> None:
    """Nhom 3: phieu LOCAL cua hoi dong (mien phi) co con hoat dong khong?"""
    model = str(env.get("AGENT_COUNCIL_LOCAL") or "").strip()
    if not model:
        add(checks, "OK", "model-local", "khong dung model local (chi cloud)")
        return
    r = probe_local_model(env)
    if r["ok"]:
        add(checks, "OK", "model-local", "%s tai %s (co %d model)"
            % (model, r["url"], len(r["ids"])))
    else:
        add(checks, "WARN", "model-local",
            "%s KHONG tra loi (%s) -> hoi dong mat 1 phieu mien phi" % (model, r["error"]),
            "chay lai dich vu local: `ollama serve` hoac "
            "`python tools/llamafile_setup.py --start`")


def _chk_protection(checks: list, env: dict, label: str, base=None) -> None:
    """Do phu bao ve tren san: moi vi the phai co dung 1 SL + 1 TP (khong mo coi)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import orders_audit as OA
        cli = OA.build_client(env, not flag(env, "BINANCE_TESTNET", True))
        poss = [p for p in cli.fetch_positions() if float(p.get("contracts") or 0) != 0]
        # (22/10) Tru vi the BUI da ghi `dust_skip.json` (khong the dat SL/TP duoc) ra khoi
        # ket luan: neu khong thi cong cu vua bao dong gia vua che mat vi the TRAN that.
        s = OA.summarize(OA.algo_orders(cli), poss,
                         dust=OA.load_dust(Path(base) if base else ROOT))
        if s["positions"] == 0 and s["orders"] == 0:
            add(checks, "OK", "bao-ve", "khong co vi the/lenh treo")
        elif s.get("naked"):
            add(checks, "FAIL", "bao-ve",
                "%d vi the TRAN (khong SL/TP): %s"
                % (len(s["naked"]), ", ".join(s["naked"][:3])),
                "python tools/orders_audit.py --target %s" % label.lower())
        elif s["to_cancel"] or s["orphans"]:
            add(checks, "FAIL", "bao-ve",
                "%d vi the, %d lenh cho, %d lenh thua/mo coi"
                % (s["positions"], s["orders"], s["to_cancel"]),
                "python tools/orders_audit.py --target %s --dedupe" % label.lower())
        elif s.get("dupes"):
            add(checks, "WARN", "bao-ve",
                "%d cap lenh bao ve TRUNG -> gom lai con 1 SL + 1 TP" % len(s["dupes"]),
                "python tools/orders_audit.py --target %s --dedupe" % label.lower())
        else:
            add(checks, "OK", "bao-ve", "%d vi the = %d lenh bao ve (dung 2/vi the)"
                % (s["positions"], s["orders"]))
    except Exception as e:  # noqa: BLE001
        add(checks, "WARN", "bao-ve", "khong doc duoc san: %s" % str(e)[:90])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cham diem setup bot (tat dinh, offline)")
    ap.add_argument("--target", choices=("testnet", "live"), default="testnet")
    ap.add_argument("--both", action="store_true", help="cham ca 2 instance + so code")
    ap.add_argument("--with-exchange", action="store_true",
                    help="them kiem tra lenh bao ve tren san (goi API)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.both:
        reps = [audit_one(ROOT, "TESTNET", with_exchange=args.with_exchange),
                audit_one(LIVE_DIR, "LIVE", with_exchange=args.with_exchange)]
    else:
        base = ROOT if args.target == "testnet" else LIVE_DIR
        reps = [audit_one(base, args.target.upper(), with_exchange=args.with_exchange)]

    if args.json:
        print(json.dumps(reps, ensure_ascii=False, indent=2))
    else:
        for r in reps:
            s = r["summary"]
            print("=== HARNESS AUDIT %s | diem %d/100 | %s ==="
                  % (r["label"], s["score"], s["verdict"]))
            for c in r["checks"]:
                print("%s %-16s %s" % (MARK.get(c["level"], "  "), c["name"], c["detail"]))
                if c["fix"] and c["level"] != "OK":
                    print("     -> %s" % c["fix"])
        if len(reps) > 1:
            avg = sum(r["summary"]["score"] for r in reps) // len(reps)
            print("TONG: diem trung binh %d/100" % avg)
    return 2 if any(r["summary"]["ok"] for r in reps) else 0


if __name__ == "__main__":
    raise SystemExit(main())
