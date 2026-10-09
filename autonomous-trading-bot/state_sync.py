"""Đồng bộ "bộ nhớ dự án" vào repo (STATE.md) + TUỲ CHỌN tự động sang LIVE.

Chạy định kỳ (supervisor gọi, `STATE_SYNC_SEC`) hoặc chạy tay:

    python state_sync.py                  # cập nhật STATE.md + logs/state_snapshot.json
    python state_sync.py --git            # + git add/commit/push STATE.md lên GitHub
    python state_sync.py --auto-live      # + kiểm tra cổng, tự sang LIVE nếu đủ điều kiện

Tất định 100%: chỉ ĐỌC file state + journal (không gọi LLM). Chỉ GHI:
`STATE.md`, `logs/state_snapshot.json`, `logs/state_sync.log`, và (chỉ khi --auto-live
đủ điều kiện) sửa `.env` + kết thúc tiến trình con để supervisor restart với config mới.

**TỰ ĐỘNG SANG LIVE — 5 chốt an toàn** (đây là tiền thật, không được tắt chốt nào):

1. `AUTO_LIVE_ARMED=true` trong `.env` — mặc định **false**, phải bật 1 lần.
2. `live_ready.check()` OK — PF(R)≥1.2 **và** PF($)≥1.1 ở **mọi** cửa sổ 7/14/30 ngày,
   n≥300, chiến lược âm phải bị block, đủ mẫu 2 hướng.
3. `live_guard.check()` OK — n≥50, PF≥1.2, risk≤2%, lev≤10, kill-switch sạch.
4. **Ví THẬT** (endpoint live, chỉ đọc) ≥ `AUTO_LIVE_MIN_EQUITY` USDT (mặc định 100);
   **không đọc được ⇒ KHÔNG đổi** (fail-safe).
5. Chỉ đổi **1 lần** (marker `logs/.live_flipped`) + tự hạ rủi ro khởi đầu
   (`RISK_PER_TRADE_PCT=0.5`, `MAX_POSITIONS=3`) + ghi log/Telegram + ghi vào STATE.md.
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

try:  # đọc cùng .env với runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent
STATE_MD = ROOT / "STATE.md"
SNAPSHOT = ROOT / "logs" / "state_snapshot.json"
SYNC_LOG = ROOT / "logs" / "state_sync.log"
FLIP_MARKER = ROOT / "logs" / ".live_flipped"
HEARTBEAT = ROOT / "logs" / "heartbeat.json"
MANAGED = ROOT / "logs" / "managed_state.json"
LEARNER = ROOT / "logs" / "learner.json"
JOURNAL = ROOT / "logs" / "journal.jsonl"

DEFAULT_EQUITY_MIN = 100.0     # USDT thật tối thiểu để cho phép sang LIVE
START_RISK_PCT = 0.5           # rủi ro khởi đầu khi sang LIVE (20-30 lệnh đầu)
START_MAX_POS = 3


def log(msg: str) -> None:
    """Ghi 1 dòng vào logs/state_sync.log (và stdout khi chạy tay)."""
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        SYNC_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(SYNC_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    if sys.stdout and sys.stdout.isatty():
        print(line)


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return default


def set_env_values(text: str, updates: dict) -> str:
    """Thay `KEY=...` trong nội dung .env; key chưa có thì thêm vào cuối. HÀM THUẦN."""
    out = text
    for key, val in updates.items():
        pat = re.compile(r"^%s=.*$" % re.escape(key), re.M)
        if pat.search(out):
            out = pat.sub("%s=%s" % (key, val), out)
        else:
            if not out.endswith("\n"):
                out += "\n"
            out += "%s=%s\n" % (key, val)
    return out


def git_head() -> str:
    """Hash commit ngắn hiện tại (rỗng nếu không đọc được)."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def council_models(cfg) -> list:
    """Danh sách model hội đồng (rỗng nếu lỗi — không được làm hỏng snapshot)."""
    try:
        import agents
        return list(agents._council_models(cfg))
    except Exception:  # noqa: BLE001
        return []


def collect(cfg, journal=JOURNAL, now=None) -> dict:
    """Gom trạng thái hiện tại thành dict (chỉ đọc file — không gọi sàn/LLM)."""
    now = float(now or time.time())
    hb = read_json(HEARTBEAT, {}) or {}
    hb_ts = float(hb.get("ts") or 0.0)
    age = round(now - hb_ts, 1) if hb_ts else None
    watchdog = int(os.getenv("WATCHDOG_SEC", "180"))
    managed = (read_json(MANAGED, {}) or {}).get("trades") or {}
    positions = [{"symbol": s, "direction": t.get("direction"), "qty": t.get("qty"),
                  "entry": t.get("entry"), "sl": t.get("sl"), "tp": t.get("tp"),
                  "partial_done": bool(t.get("partial_done")),
                  "be_done": bool(t.get("be_done")),
                  "mfe_r": round(float(t.get("mfe_r") or 0.0), 3)}
                 for s, t in sorted(managed.items())]
    risk = read_json(getattr(cfg, "risk_state_path", "logs/risk_state.json"), {}) or {}
    learner = read_json(LEARNER, {}) or {}

    import live_guard
    import live_ready
    import risk_tier
    rep_ready = live_ready.check(cfg, journal_path=str(journal))
    rep_guard = live_guard.check(cfg, journal_path=str(journal))
    models = council_models(cfg)
    st = rep_ready.get("all") or {}
    tier = risk_tier.tier_for(hb.get("equity"))

    wins = {str(k): {"n": v.get("n"), "wr": v.get("wr"), "pf_r": v.get("pf_r"),
                     "pf_pnl": v.get("pf_pnl"), "e_r": v.get("e_r"), "pnl": v.get("pnl")}
            for k, v in (rep_ready.get("windows") or {}).items()}
    return {
        "ts": now, "ts_human": time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(now)),
        "git_head": git_head(),
        "bot": {"pid": hb.get("pid"), "round": hb.get("round"), "phase": hb.get("phase"),
                "heartbeat_age_s": age, "watchdog_sec": watchdog,
                "alive": bool(age is not None and age <= watchdog)},
        "equity_demo": hb.get("equity"),
        "positions": positions,
        "config": {"testnet": bool(getattr(cfg, "testnet", True)),
                   "dry_run": bool(getattr(cfg, "dry_run", True)),
                   "live_confirm": bool(getattr(cfg, "live_confirm", False)),
                   "risk_pct": float(getattr(cfg, "risk_per_trade_pct", 0.0) or 0.0),
                   "max_total_risk_pct": float(getattr(cfg, "max_total_risk_pct", 0.0) or 0.0),
                   "leverage": int(getattr(cfg, "leverage", 0) or 0),
                   "max_positions": int(getattr(cfg, "max_positions", 0) or 0),
                   "balance_usdt": float(getattr(cfg, "balance_usdt", 0.0) or 0.0)},
        "journal": {"n": st.get("n"), "wr": st.get("wr"), "pf_r": st.get("pf_r"),
                    "pf_pnl": st.get("pf_pnl"), "e_r": st.get("e_r"), "pnl": st.get("pnl")},
        "windows": wins,
        "live_ready": {"ok": bool(rep_ready.get("ok")),
                       "verdict": rep_ready.get("verdict"),
                       "blockers": list(rep_ready.get("blockers") or [])},
        "live_guard": {"ok": bool(rep_guard.get("ok")), "live": bool(rep_guard.get("live")),
                       "blockers": list(rep_guard.get("blockers") or [])},
        "kill_switch": {"tripped": bool(risk.get("tripped")),
                        "reason": str(risk.get("reason") or "")},
        "learner": {"n_updates": int(learner.get("n") or 0), "ts": learner.get("ts")},
        "council": {"n_models": len(models), "models": models},
        "auto_live": {"armed": bool(getattr(cfg, "auto_live_armed", False)),
                      "flipped": FLIP_MARKER.exists(),
                      "min_equity": float(getattr(cfg, "auto_live_min_equity",
                                                  DEFAULT_EQUITY_MIN) or DEFAULT_EQUITY_MIN)},
        "tier": {"name": tier.get("name"), "label": tier.get("label"),
                 "risk_pct": tier.get("risk_pct"),
                 "max_positions": tier.get("max_positions"),
                 "note": tier.get("note"),
                 "table_md": risk_tier.table_md(hb.get("equity"))},
    }


def render_md(snap: dict) -> str:
    """Sinh nội dung STATE.md từ snapshot (markdown cho người đọc)."""
    b, c, j = snap["bot"], snap["config"], snap["journal"]
    lr, lg, al = snap["live_ready"], snap["live_guard"], snap["auto_live"]
    mode = "TESTNET (demo)" if c["testnet"] else "**LIVE (TIỀN THẬT)**"
    lines = [
        "# STATE.md — trạng thái dự án (TỰ ĐỘNG SINH, ĐỪNG SỬA TAY)",
        "",
        "> File này do `state_sync.py` sinh (định kỳ qua supervisor). Muốn đổi nội dung:",
        "> sửa `state_sync.py` rồi chạy lại `python state_sync.py`. Ngữ cảnh dài hạn: `CONTEXT.md`.",
        "",
        "- **Cập nhật**: %s · commit `%s`" % (snap["ts_human"], snap["git_head"] or "?"),
        "- **Chế độ**: %s · `DRY_RUN=%s` · `LIVE_CONFIRM=%s`"
        % (mode, c["dry_run"], c["live_confirm"]),
        "- **Bot**: pid `%s` · round `%s` · nhịp tim cách đây %ss (watchdog %ss) → %s"
        % (b["pid"], b["round"], b["heartbeat_age_s"], b["watchdog_sec"],
           "ĐANG CHẠY" if b["alive"] else "⚠️ KHÔNG THẤY NHỊP TIM"),
        "- **Ví demo**: %s USDT" % ("?" if snap["equity_demo"] is None else snap["equity_demo"]),
        "- **Kill-switch**: %s" % ("⚠️ TRIPPED — " + snap["kill_switch"]["reason"]
                                   if snap["kill_switch"]["tripped"] else "bình thường"),
        "",
        "## Hiệu suất (journal: %s lệnh đóng, WR %s%%, E(R) %s, PnL %s$)"
        % (j["n"], j["wr"], j["e_r"], j["pnl"]),
        "",
        "| Cửa sổ | n | WR% | PF(R) | PF($) | E(R) | PnL$ |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in sorted(snap["windows"], key=lambda x: int(x)):
        w = snap["windows"][d]
        lines.append("| %s ngày | %s | %s | %s | %s | %s | %s |"
                     % (d, w["n"], w["wr"], w["pf_r"], w["pf_pnl"], w["e_r"], w["pnl"]))
    lines += [
        "",
        "## Cổng sang LIVE",
        "",
        "- `live_ready.py`: **%s**%s" % (lr["verdict"],
                                         (" — " + "; ".join(lr["blockers"])) if lr["blockers"] else ""),
        "- `live_guard.py`: %s%s" % ("OK" if lg["ok"] else "CHẶN",
                                     (" — " + "; ".join(lg["blockers"])) if lg["blockers"] else ""),
        "- Tự động sang LIVE: **%s**%s"
        % ("BẬT" if al["armed"] else "TẮT (`AUTO_LIVE_ARMED=false`)",
           " · ĐÃ ĐỔI 1 LẦN" if al["flipped"] else ""),
        "",
        "## Cấu hình rủi ro",
        "",
        "- risk/lệnh `%s%%` · trần tổng `%s%%` · leverage `%s` · MAX_POSITIONS `%s` · trần size `%s` USDT"
        % (c["risk_pct"], c["max_total_risk_pct"], c["leverage"], c["max_positions"],
           c["balance_usdt"]),
        "- Learner: %s lần cập nhật trọng số · Hội đồng AI: **%s model**"
        % (snap["learner"]["n_updates"], snap["council"]["n_models"]),
        "",
        "## Ngưỡng rủi ro theo ví THẬT (3 mức)",
        "",
        snap["tier"]["table_md"],
        "",
        "_Mức đánh dấu ở trên tính theo **ví demo** — khi sang LIVE, `state_sync.py` sẽ áp"
        " đúng mức theo **ví thật** (risk%, MAX_POSITIONS, danh sách cặp)._",
        "",
        "## Vị thế đang quản lý (%s)" % len(snap["positions"]),
        "",
    ]
    if snap["positions"]:
        lines += ["| Cặp | Hướng | qty | entry | SL | TP | partial | BE | mfe_R |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for p in snap["positions"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                         % (p["symbol"], p["direction"], p["qty"], p["entry"], p["sl"],
                            p["tp"], p["partial_done"], p["be_done"], p["mfe_r"]))
    else:
        lines.append("_không có vị thế nào trong `managed_state.json`_")
    lines += ["", "---", "",
              "Làm mới: `python state_sync.py` · Kiến thức dài hạn: `CONTEXT.md` · "
              "Số liệu thô: `logs/state_snapshot.json`"]
    return "\n".join(lines) + "\n"


# ---- Tự động sang LIVE: quyết định (hàm thuần) + thực thi --------------------

def decide_go_live(rep_ready: dict, rep_guard: dict, real_equity, armed: bool,
                   already_flipped: bool, min_equity: float = DEFAULT_EQUITY_MIN,
                   live_keys: bool = True) -> tuple:
    """Có tự sang LIVE không? Trả (bool, lý do). HÀM THUẦN — test được."""
    if already_flipped:
        return False, "da doi 1 lan truoc do (marker logs/.live_flipped)"
    if not armed:
        return False, "AUTO_LIVE_ARMED=false (chua bat)"
    if not live_keys:
        return False, ("chua co BINANCE_LIVE_API_KEY/BINANCE_LIVE_API_SECRET trong .env "
                       "(dien key LIVE truoc: xem `python check_live_key.py`)")
    if not rep_ready.get("ok"):
        return False, "live_ready CHUA dat: " + "; ".join(rep_ready.get("blockers") or [])
    if not rep_guard.get("ok"):
        return False, "live_guard CHAN: " + "; ".join(rep_guard.get("blockers") or [])
    if real_equity is None:
        return False, "khong doc duoc vi THAT (fail-safe: KHONG doi)"
    if float(real_equity) < float(min_equity):
        return False, ("vi THAT %.2f USDT < %.2f USDT toi thieu"
                       % (float(real_equity), float(min_equity)))
    return True, ("du dieu kien: vi that %.2f USDT + live_ready + live_guard OK"
                  % float(real_equity))


def key_pair(cfg) -> tuple:
    """(api_key, api_secret, nguon) — ưu tiên cặp LIVE riêng nếu đã điền.

    Vì sao: testnet đang chạy bằng key demo (`BINANCE_API_KEY`). Muốn kiểm tra/sang
    LIVE mà không đụng testnet ⇒ điền `BINANCE_LIVE_API_KEY`/`_SECRET`; khi đó mọi
    thao tác "ví thật" dùng cặp này, còn bot vẫn chạy demo bằng cặp cũ.
    """
    lk = str(getattr(cfg, "live_api_key", "") or "").strip()
    ls = str(getattr(cfg, "live_api_secret", "") or "").strip()
    if lk and ls:
        return lk, ls, "live"
    return (str(getattr(cfg, "api_key", "") or ""),
            str(getattr(cfg, "api_secret", "") or ""), "api")


def has_live_keys(cfg) -> bool:
    """Đã có cặp key LIVE riêng chưa (điều kiện để có thể sang LIVE)."""
    return key_pair(cfg)[2] == "live"


def real_equity_usdt(cfg) -> float | None:
    """Đọc số dư USDT của ví THẬT (endpoint live, CHỈ ĐỌC). None nếu không đọc được."""
    key, secret, src = key_pair(cfg)
    try:
        from exchange import BinanceFutures
        ex = BinanceFutures(api_key=key, api_secret=secret, testnet=False, dry_run=False)
        bal = ex.fetch_balance_usdt()
        if bal is None:
            log("real_equity: khong doc duoc (nguon key=%s)" % src)
            return None
        return float(bal)
    except Exception as e:  # noqa: BLE001
        log("real_equity: loi %s (nguon key=%s)" % (str(e)[:120], src))
        return None


def go_live(cfg, reason: str, env_path=None, tier: dict | None = None) -> dict:
    """Đổi `.env` sang LIVE + áp mức rủi ro theo ví thật + ghi marker.

    `tier` = dict từ `risk_tier.tier_for(equity)` (None -> dùng mức an toàn mặc định).
    KHÔNG tự kill process (xem `restart_bot`).
    """
    import risk_tier
    path = Path(env_path) if env_path else (ROOT / ".env")
    tier = tier or risk_tier.tier_for(None)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"ok": False, "err": "khong doc duoc .env: %s" % e}
    upd = {"BINANCE_TESTNET": "false", "LIVE_CONFIRM": "true"}
    upd.update(risk_tier.env_updates(tier))
    # (09/10) Dua cap KEY LIVE vao BINANCE_API_KEY/SECRET de bot dung key that sau khi
    # restart (key demo cu duoc giu nguyen trong .env.bak-live).
    key, secret, src = key_pair(cfg)
    if src == "live":
        upd["BINANCE_API_KEY"] = key
        upd["BINANCE_API_SECRET"] = secret
    new = set_env_values(text, upd)
    backup = path.with_name(path.name + ".bak-live")
    try:
        backup.write_text(text, encoding="utf-8")
        path.write_text(new, encoding="utf-8")
        FLIP_MARKER.parent.mkdir(parents=True, exist_ok=True)
        FLIP_MARKER.write_text(json.dumps({"ts": time.time(), "reason": reason,
                                           "tier": tier.get("name"),
                                           "updates": upd}, ensure_ascii=False),
                               encoding="utf-8")
    except OSError as e:
        return {"ok": False, "err": "khong ghi duoc: %s" % e}
    return {"ok": True, "updates": upd, "backup": str(backup), "tier": tier.get("name")}


def restart_bot() -> dict:
    """Kết thúc tiến trình con (turbo_demo) để supervisor tự restart với .env mới."""
    hb = read_json(HEARTBEAT, {}) or {}
    pid = int(hb.get("pid") or 0)
    if not pid:
        return {"ok": False, "err": "khong biet pid con (heartbeat thieu)"}
    try:
        r = subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True, text=True, timeout=30)
        return {"ok": r.returncode == 0, "pid": pid,
                "out": (r.stdout + r.stderr).strip()[:160]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:160]}


def notify_tg(cfg, text: str) -> bool:
    """Gửi Telegram (nếu có token/chat) — lỗi không được làm hỏng luồng."""
    try:
        from notify import send as tg_send
        tok = str(getattr(cfg, "tg_token", "") or "")
        chat = str(getattr(cfg, "tg_chat", "") or "")
        return bool(tok and chat and tg_send(tok, chat, text))
    except Exception:  # noqa: BLE001
        return False


def write_state(md: str, snap: dict) -> dict:
    """Ghi STATE.md + logs/state_snapshot.json."""
    try:
        STATE_MD.write_text(md, encoding="utf-8")
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "state_md": str(STATE_MD)}
    except OSError as e:
        log("write_state loi: %s" % e)
        return {"ok": False, "err": str(e)}


def _git_bin() -> str:
    """Đường dẫn đầy đủ của git.

    Vì sao cần: process do supervisor spawn (pythonw) có thể thiếu PATHEXT/PATH nên
    `subprocess.run(["git", ...])` báo `[WinError 2]` dù `shutil.which("git")` tìm thấy
    (bug thật gặp 09/10 khi hook tự động chạy). Dùng đường dẫn tuyệt đối là an toàn nhất.
    """
    import shutil
    cands = [shutil.which("git"),
             r"C:\Program Files\Git\cmd\git.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
             r"C:\Program Files (x86)\Git\cmd\git.exe"]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return "git"


def git_commit_push(msg: str) -> dict:
    """Commit STATE.md rồi push nhánh hiện tại (dùng cho --git)."""
    git = _git_bin()

    def _run(args, timeout=60):
        return subprocess.run([git] + args, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=timeout)
    try:
        _run(["add", "STATE.md"], 30)
        c = _run(["commit", "-m", msg], 30)
        if c.returncode != 0:
            return {"ok": False, "stage": "commit", "git": git,
                    "out": (c.stdout + c.stderr).strip()[:200]}
        p = _run(["push", "origin", "HEAD"], 120)
        return {"ok": p.returncode == 0, "stage": "push", "git": git,
                "out": (p.stdout + p.stderr).strip()[-200:]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:200], "git": git}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dong bo STATE.md + (tuy chon) tu dong sang LIVE")
    ap.add_argument("--git", action="store_true", help="commit + push STATE.md len GitHub")
    ap.add_argument("--auto-live", action="store_true",
                    help="kiem tra cong, tu sang LIVE neu du dieu kien (AUTO_LIVE_ARMED)")
    args = ap.parse_args(argv)

    from config import Settings
    cfg = Settings()
    snap = collect(cfg)
    write_state(render_md(snap), snap)
    log("STATE.md: n=%s PF(R)=%s PF($)=%s | live_ready=%s | vi demo=%s | vi the=%d"
        % (snap["journal"]["n"], snap["journal"]["pf_r"], snap["journal"]["pf_pnl"],
           snap["live_ready"]["verdict"], snap["equity_demo"], len(snap["positions"])))
    if args.git:
        res = git_commit_push("chore(state): cap nhat STATE.md %s (n=%s, PF(R)=%s, %s)"
                              % (snap["ts_human"], snap["journal"]["n"], snap["journal"]["pf_r"],
                                 "TESTNET" if snap["config"]["testnet"] else "LIVE"))
        log("git: %s" % res)
    if not args.auto_live:
        return 0

    import risk_tier
    eq = real_equity_usdt(cfg)
    tier = risk_tier.tier_for(eq)
    ok, why = decide_go_live(snap["live_ready"], snap["live_guard"], eq,
                             snap["auto_live"]["armed"], snap["auto_live"]["flipped"],
                             snap["auto_live"]["min_equity"],
                             live_keys=has_live_keys(cfg))
    log("auto-live: %s | %s | vi that=%s | nguon key=%s | muc=%s (risk %s%%, %s vi the)"
        % ("DOI SANG LIVE" if ok else "KHONG DOI", why, eq, key_pair(cfg)[2], tier["name"],
           tier["risk_pct"], tier["max_positions"]))
    if not ok:
        return 0
    res = go_live(cfg, why, tier=tier)
    log("auto-live ket qua: %s" % res)
    if not res.get("ok"):
        return 2
    notify_tg(cfg, "🚀 TỰ ĐỘNG SANG LIVE\n%s\nMức: %s — risk %s%% · %s vị thế · cặp: %s\n%s"
              % (why, tier["label"], tier["risk_pct"], tier["max_positions"],
                 tier["symbols"], snap["ts_human"]))
    log("restart bot: %s" % restart_bot())
    snap2 = collect(Settings())
    write_state(render_md(snap2), snap2)
    if args.git:
        log("git: %s" % git_commit_push(
            "feat(live): TU DONG SANG LIVE (vi that %s USDT, live_ready+live_guard OK) - risk 0.5%%, 3 vi the" % eq))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


