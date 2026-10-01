"""Chay hoi dong multi-AI (ClinePass 14 model / Multi_AI_Agent lab) TREN DU LIEU THAT cua bot.

Vi sao can wrapper nay (thay vi goi truc tiep Multi_AI_Agent/cline_multi.py):
  1) Gom du lieu THAT cua bot thanh 1 file context .md (harness chi nhan file .py/.md/
     .txt/.json/.toml/.yaml/.yml/.csv, khong nhan .jsonl; gioi han 20.000 ky tu).
  2) Dung CHUNG 1 file .env cua bot: CLINE_API_KEY + cac gioi han CLINE_* duoc truyen
     qua bien moi truong cho tien trinh con (bien moi truong uu tien hon .env cua harness).
  3) Chay san cac "task template" cua du an (tasks/*.txt) va luu ket qua vao
     logs/clinepass/outputs/ (da bi .gitignore chan).
  4) Tuy chon gui tom tat ket qua len Telegram (--tg).

Vi du:
    python clinepass_review.py --list
    python clinepass_review.py --task safety_audit --bundle safety --provider mock   # thu offline
    python clinepass_review.py --task code_review --bundle bot_state --file turbo_demo.py
    python clinepass_review.py --task strategy_review --bundle strategy --group all --tg
    python clinepass_review.py --engine lab --mode consensus --task live_readiness --provider openai

Luu y an toan: harness CHI gui van ban, KHONG chay code AI sinh ra, KHONG tu sua file.
Ket qua tra ve la de xuat -> nguoi dung dan vao Cline de trien khai (xem README muc Multi-AI).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:  # doc cung .env voi bot
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent
MAA = ROOT / "Multi_AI_Agent"
TASKS = ROOT / "tasks"
BUNDLE_DIR = ROOT / "logs" / "clinepass"
DEFAULT_OUT = BUNDLE_DIR / "outputs"
MAX_BUNDLE_CHARS = 18000          # harness gioi han CLINE_MAX_CONTEXT_CHARS (mac dinh 20000)

TASK_FILES = {
    "code_review": "code_review.txt",
    "strategy_review": "strategy_review.txt",
    "safety_audit": "safety_audit.txt",
    "live_readiness": "live_readiness.txt",
}
KINDS = ("none", "bot_state", "strategy", "safety")

# Ràng buộc độ dài (thêm tự động vào nhiệm vụ) — rút ra từ phiên thật 01/10:
# model glm-5.3 trả lời dài -> `finish_reason=length` -> nhánh bị coi là lỗi, và
# finalizer (cùng model) đọc quá nhiều văn bản nên cũng bị cắt/thời gian chờ.
LENGTH_FOOTER = (
    "\n\nGIỚI HẠN ĐỘ DÀI (bắt buộc): mỗi chuyên gia trả lời TỐI ĐA 450 từ, "
    "trình bày dạng gạch đầu dòng: phát hiện → bằng chứng trong dữ liệu → cách vá. "
    "Không lặp lại nội dung context, không viết lan man; trả lời ngắn để không bị cắt."
)



def _read(path: Path, limit: int | None = None) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return txt if (limit is None or len(txt) <= limit) else txt[:limit] + "\n...(cat bot)"


def _tail(path: Path, n_lines: int = 40) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n_lines:])


def _journal_stats() -> dict:
    """n/WR/PF/E(R)/by_strategy tu journal — cung nguon voi monitor_report."""
    try:
        from monitor_report import load_journal, match_pairs, stats
        opens, closes = load_journal(str(ROOT / "logs" / "journal.jsonl"))
        pairs, still = match_pairs(opens, closes)
        st = stats(pairs)
        recent = list(closes[-8:])
        return {"stats": {k: st.get(k) for k in ("n", "wr", "pf_r", "e_r", "pnl")},
                "by_strategy": st.get("by_strategy"), "by_direction": st.get("by_direction"),
                "open_unmatched": len(still),
                "recent_closes": [{"ts": c.get("ts"), "pair": c.get("pair"),
                                   "direction": c.get("direction"), "r": c.get("r"),
                                   "won": c.get("won"), "reason": c.get("reason")}
                                  for c in recent]}
    except Exception as e:  # noqa: BLE001
        return {"error": f"khong doc duoc journal: {str(e)[:120]}"}


def _agent_stats() -> dict:
    """Dem phieu agent theo vai/action + ngan sach (KHONG gom secret)."""
    out: dict = {}
    try:
        out["state"] = json.loads((ROOT / "logs" / "agent_state.json")
                                 .read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        out["state"] = {}
    counts: dict = {}
    try:
        text = (ROOT / "logs" / "journal.jsonl").read_text(encoding="utf-8", errors="replace")
        for ln in text.splitlines():
            if '"AGENT"' not in ln:
                continue
            try:
                rec = json.loads(ln)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("event") != "AGENT":
                continue
            k = f"{rec.get('role')}:{rec.get('action')}"
            counts[k] = counts.get(k, 0) + 1
    except OSError:
        pass
    out["votes"] = counts
    return out


def build_task_file(task_file: Path) -> Path:
    """Nhiệm vụ gửi harness = nội dung gốc + ràng buộc độ dài (LENGTH_FOOTER).

    Vì sao: phiên thật 01/10 cho thấy model trả lời dài bị `finish_reason=length`
    (nhánh tính là lỗi) và finalizer bị quá tải. Giới hạn 450 từ/chuyên gia giúp
    mọi nhánh kết thúc gọn. Nếu nhiệm vụ đã có ràng buộc thì giữ nguyên file gốc.
    """
    base = _read(task_file, 5000)
    if not base.strip() or "GIỚI HẠN ĐỘ DÀI" in base:
        return task_file
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    out = BUNDLE_DIR / f"task_{task_file.stem}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    out.write_text(base + LENGTH_FOOTER, encoding="utf-8")
    return out


def _runtime_params() -> dict:
    """Tham so AN TOAN dang chay THAT (khong gom secret) — de hoi dong khong doc nham
    gia tri mau trong .env.example (da gap: hoi dong ket luan sai vi thay MAX_POSITIONS=1
    va MAX_TOTAL_RISK_PCT=3% cua file mau)."""
    keys = ("symbols", "extra_symbols", "max_positions", "allow_hedge_opposite",
            "max_total_risk_pct", "risk_per_trade_pct", "leverage", "max_daily_loss_pct",
            "max_atr_pct", "min_notional_usdt", "adopt_positions", "partial_at_r",
            "partial_pct", "be_at_r", "trail_atr_mult", "sl_atr_mult", "tp_atr_mult",
            "cooldown_sec", "strategy_gate", "agents_enabled", "agents_shadow",
            "agents_council", "agents_veto_enabled", "agent_veto_source",
            "live_confirm", "testnet", "dry_run")
    out: dict = {}
    try:
        from config import Settings
        cfg = Settings()
        for k in keys:
            v = getattr(cfg, k, "<khong co>")
            out[k] = str(v) if isinstance(v, (list, tuple, set)) else v
    except Exception as e:  # noqa: BLE001
        out["error"] = f"khong doc duoc Settings: {str(e)[:120]}"
    return out


def build_bundle(kind: str) -> Path | None:
    """Gom du lieu THAT cua bot -> 1 file .md lam context cho hoi dong.

    KHONG bao gio gom .env / API key: chi so lieu van hanh (journal, risk, agent
    votes, log tail) va cac tham so da cong khai trong .env.example.
    """
    if kind == "none":
        return None
    parts: list = [f"# DU LIEU BOT (bundle={kind}) — {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    if kind in ("bot_state", "strategy"):
        parts.append("## Journal (nguon su that ve ket qua giao dich)\n```json\n"
                     + json.dumps(_journal_stats(), ensure_ascii=False, indent=1) + "\n```")
        for name in ("monitor_report.json", "strategy_stats.json", "learner.json"):
            body = _read(ROOT / "logs" / name, 4000)
            if body:
                parts.append(f"## logs/{name}\n```json\n{body}\n```")
    if kind in ("bot_state", "safety"):
        parts.append("## Trang thai rui ro / vi the\n```text\nrisk_state:\n"
                     + (_read(ROOT / "logs" / "risk_state.json", 1200) or "(khong co / da reset)")
                     + "\n\nmanaged_state:\n"
                     + _read(ROOT / "logs" / "managed_state.json", 3000) + "\n```")
        parts.append("## Phieu agent (multi-AI noi bo cua bot)\n```json\n"
                     + json.dumps(_agent_stats(), ensure_ascii=False, indent=1) + "\n```")
    if kind in ("bot_state", "safety"):
        parts.append("## THAM SO AN TOAN DANG CHAY THAT (nguon: config.Settings — "
                     "KHONG co secret; dung cai nay thay vi doc .env.example)\n```json\n"
                     + json.dumps(_runtime_params(), ensure_ascii=False, indent=1) + "\n```")
        parts.append("## Cau hinh mau (.env.example — CHI LA MAU, khong phai dang chay)\n```text\n"
                     + _read(ROOT / ".env.example", 1800) + "\n```")
    if kind in ("bot_state", "strategy"):
        parts.append("## 40 dong log cuoi (logs/turbo_err.log)\n```text\n"
                     + _tail(ROOT / "logs" / "turbo_err.log", 40) + "\n```")
    text = "\n\n".join(parts)
    if len(text) > MAX_BUNDLE_CHARS:
        text = text[:MAX_BUNDLE_CHARS] + "\n\n...(bundle bi cat bot)"
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    path = BUNDLE_DIR / f"bundle_{kind}_{time.strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text(text, encoding="utf-8")
    return path


def _abs_file(p) -> Path:
    """Duong dan nguoi dung nhap (co the tuong doi) -> TUYET DOI theo goc du an.

    Vi sao: harness chay voi cwd=Multi_AI_Agent nen `--file bot.py` se bi hieu thanh
    Multi_AI_Agent/bot.py -> "Loi cau hinh/file" (da gap khi chay thu 02/10).
    """
    q = Path(str(p)).expanduser()
    if not q.is_absolute():
        q = ROOT / q
    return q.resolve()


def _catalog_models() -> list:
    """Danh sach model trong catalog (dung de loai model chay cham/hay treo)."""
    try:
        data = json.loads((MAA / "models.clinepass.json").read_text(encoding="utf-8-sig"))
        return [str(a.get("model")) for a in (data.get("agents") or [])]
    except Exception:  # noqa: BLE001
        return []


def _skip_models() -> list:
    """Model bo qua khi chay `--group all` (env CLINE_SKIP_MODELS, comma-separated).

    Ly do (02/10): `cline-pass/glm-5.3-flash` treo/timeout o CA HAI phien 14 model voi
    prompt lon -> `status=timeout` va finalizer khong bao gio chay (harness chi tong hop
    khi MOI nhanh xong). Bo qua model nay giup phien 14 model chay tron ven.
    """
    raw = os.getenv("CLINE_SKIP_MODELS", "").strip()
    return [m.strip() for m in raw.split(",") if m.strip()]


def build_cmd(args, bundle: Path | None, task_file: Path) -> list:
    """Len lenh cho harness (tach rieng de test duoc, khong chay that)."""
    if getattr(args, "check", False):
        # `check` KHONG nhan task/context (harness tu choi) — chi kiem tra ket noi model.
        cmd = [sys.executable, str(MAA / "cline_multi.py"), "check",
               "--provider", str(args.provider), "--group", str(args.group),
               "--output-dir", str(args.output_dir)]
        if args.concurrency:
            cmd += ["--concurrency", str(args.concurrency)]
        for m in (args.model or []):
            cmd += ["--model", str(m)]
        return cmd
    if args.engine == "lab":
        cmd = [sys.executable, str(MAA / "main.py"), "run",
               "--mode", str(args.mode), "--provider", str(args.provider),
               "--task-file", str(task_file), "--output-dir", str(args.output_dir)]
    else:
        cmd = [sys.executable, str(MAA / "cline_multi.py"), "run",
               "--provider", str(args.provider), "--group", str(args.group),
               "--task-file", str(task_file), "--output-dir", str(args.output_dir)]
        if args.concurrency:
            cmd += ["--concurrency", str(args.concurrency)]
        models = list(args.model or [])
        if not models and args.group == "all":
            skip = set(_skip_models())
            models = [m for m in _catalog_models() if m not in skip]
            if skip and models:
                print(f"[info] bo qua model cham: {sorted(skip)} -> con {len(models)} model")
        for m in models:
            cmd += ["--model", str(m)]
    for f in (args.file or []):
        cmd += ["--context", str(_abs_file(f))]
    if bundle is not None:
        cmd += ["--context", str(bundle)]
    return cmd


def child_env(args) -> dict:
    """Bien moi truong cho tien trinh con: dung CHUNG .env cua bot.

    Bien moi truong uu tien hon .env cua harness (theo CLINEPASS.md) nen chi can
    CLINE_API_KEY / OPENAI_API_KEY nam trong .env cua bot la du.
    """
    env = dict(os.environ)
    key = os.getenv("CLINE_API_KEY", "").strip()
    if key:
        env["CLINE_API_KEY"] = key
    if args.provider == "openai":
        ok = os.getenv("OPENAI_API_KEY", "").strip()
        if ok:
            env["OPENAI_API_KEY"] = ok
    for k in ("CLINE_CONCURRENCY", "CLINE_REQUEST_TIMEOUT", "CLINE_RUN_TIMEOUT",
              "CLINE_MAX_RETRIES", "CLINE_MAX_CALLS", "CLINE_MAX_CONTEXT_CHARS",
              "CLINE_SUMMARY_CHARS_PER_AGENT"):
        v = os.getenv(k, "").strip()
        if v:
            env[k] = v
    if getattr(args, "max_context", None):
        env["CLINE_MAX_CONTEXT_CHARS"] = str(int(args.max_context))
    return env


def summarize_report(report: Path, limit: int = 2600) -> str:
    """Lay phan '## Tổng hợp' cua report.md (ket qua finalizer) de in/gui Telegram."""
    body = _read(report, 400000)
    if not body:
        return ""
    idx = body.find("## Tổng hợp")
    if idx < 0:
        return body[:limit]
    tail = body[idx + len("## Tổng hợp"):]
    end = tail.find("\n## Trạng thái từng lượt")
    if end > 0:
        tail = tail[:end]
    return tail.strip()[:limit]


def preflight(args, task_file: Path, need_task: bool = True, bundle: Path | None = None) -> str:
    """Kiem tra truoc khi chay: tra ve thong bao loi ('' = san sang)."""
    try:
        import httpx  # noqa: F401
    except ImportError:
        return ("Thieu httpx. Chay: python -m pip install -r "
                "Multi_AI_Agent/requirements-clinepass.txt")
    if args.engine == "lab":
        try:
            import openai  # noqa: F401
        except ImportError:
            return ("Engine lab can openai + pydantic. Chay: python -m pip install -r "
                    "Multi_AI_Agent/requirements.txt")
    if need_task and not task_file.is_file():
        return f"Khong thay file nhiem vu: {task_file}"
    for f in (getattr(args, "file", None) or []):
        if not _abs_file(f).is_file():
            return f"Khong thay file context: {f} (da thu {_abs_file(f)})"
    # Tong dung luong context: harness (va 02/10: 2 file code + bundle = 45k > 20k) se
    # tu choi -> kiem tra TRUOC de bao ro rang, kem cach xu ly.
    if need_task:
        limit = int(getattr(args, "max_context", None)
                    or os.getenv("CLINE_MAX_CONTEXT_CHARS", "20000") or 20000)
        total = len(_read(task_file)) + sum(len(_read(_abs_file(f)))
                                            for f in (getattr(args, "file", None) or []))
        if bundle is not None:
            total += len(_read(bundle))
        if total > limit:
            return (f"Context {total} ky tu > gioi han {limit}. Chon it file hon, hoac tang "
                    f"CLINE_MAX_CONTEXT_CHARS (vi du --max-context {int(total * 1.2) // 1000 * 1000}).")
    if args.engine == "clinepass" and args.provider == "clinepass" \
            and not os.getenv("CLINE_API_KEY", "").strip():
        return ("Thieu CLINE_API_KEY trong .env. Lay key tai app.cline.bot -> Settings -> "
                "API Keys (dung cho ca multi-AI 14 model). Hoac chay --provider mock.")
    if args.engine == "lab" and args.provider == "openai" \
            and not os.getenv("OPENAI_API_KEY", "").strip():
        return "Thieu OPENAI_API_KEY trong .env (hoac chay --provider mock)."
    return ""


def _print_check_table(run_dir: Path) -> None:
    """In bang trang thai tung model tu run.json (sau lenh --check/run)."""
    try:
        data = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("[warn] khong doc duoc run.json:", e)
        return
    rows = list(data.get("agents") or []) + ([data["finalizer"]] if data.get("finalizer") else [])
    ok = [r for r in rows if r.get("status") == "ok"]
    bad = [r for r in rows if r.get("status") != "ok"]
    print(f"— Trang thai model: {len(ok)}/{len(rows)} OK | status tong: {data.get('status')}")
    for r in bad:
        print(f"   [LOI] {r.get('model')}: {str(r.get('error') or r.get('status'))[:110]}")
    for r in ok:
        print(f"   [OK ] {r.get('model')} ({r.get('label')})")


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Chay hoi dong multi-AI (ClinePass/lab) tren du lieu that cua bot")
    ap.add_argument("--task", choices=sorted(TASK_FILES), default="code_review")
    ap.add_argument("--bundle", choices=KINDS, default="bot_state",
                    help="du lieu bot dua vao context (none = khong gom)")
    ap.add_argument("--file", action="append", default=[],
                    help="them file context (lap lai duoc), vi du --file turbo_demo.py")
    ap.add_argument("--engine", choices=("clinepass", "lab"), default="clinepass")
    ap.add_argument("--mode", choices=("group", "handoff", "parallel", "consensus"),
                    default="consensus", help="chi dung cho --engine lab")
    ap.add_argument("--provider", choices=("mock", "clinepass", "openai"), default="mock",
                    help="mock = offline, khong ton quota (mac dinh)")
    ap.add_argument("--group", choices=("core", "all"), default="core")
    ap.add_argument("--model", action="append", help="chon model cline-pass/... (lap lai duoc)")
    ap.add_argument("--concurrency", type=int)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-context", type=int, default=None,
                    help="ghi de CLINE_MAX_CONTEXT_CHARS cho lan chay nay (ky tu)")
    ap.add_argument("--tg", action="store_true", help="gui tom tat ket qua len Telegram")
    ap.add_argument("--check", action="store_true",
                    help="kiem tra ket noi tung model ClinePass (KHONG goi finalizer, ton quota)")
    ap.add_argument("--list", action="store_true", help="in cac task/bundle co san roi thoat")
    ap.add_argument("--print-cmd", action="store_true", help="chi in lenh se chay (dry-run)")
    args = ap.parse_args(argv)

    if args.list:
        print("Task co san (tasks/*.txt):")
        for k, v in sorted(TASK_FILES.items()):
            p = TASKS / v
            print(f"  {k:16} -> {v:24} {'OK' if p.is_file() else 'THIEU FILE'}")
        print("Bundle du lieu: " + ", ".join(KINDS))
        print("Harness: Multi_AI_Agent/cline_multi.py (14 model ClinePass + finalizer) | "
              "Multi_AI_Agent/main.py (lab: group/handoff/parallel/consensus)")
        return 0

    if args.check:
        args.bundle = "none"
        if args.provider == "mock":
            args.provider = "clinepass"      # check mock la vo nghia
    task_file = TASKS / TASK_FILES[args.task]
    bundle = None if args.check else build_bundle(args.bundle)
    if not args.check:
        task_file = build_task_file(task_file)
    err = preflight(args, task_file, need_task=not args.check, bundle=bundle)
    if err:
        print("[LOI] " + err, file=sys.stderr)
        return 2
    cmd = build_cmd(args, bundle, task_file)
    print("Task   :", args.task, "| bundle:", args.bundle,
          f"({bundle.name})" if bundle else "")
    print("Lenh   :", " ".join(cmd))
    if args.print_cmd:
        return 0
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(MAA), env=child_env(args))
    rc = int(proc.returncode)
    print(f"[xong] rc={rc} sau {time.time() - t0:.0f}s")
    # Tim report moi nhat trong output-dir de tom tat/gui Telegram.
    try:
        runs = sorted([p for p in Path(args.output_dir).glob("*") if p.is_dir()],
                      key=lambda p: p.stat().st_mtime)
        if runs:
            rep = runs[-1] / "report.md"
            print("Report :", rep.resolve())
            if args.check:
                _print_check_table(runs[-1])
            if args.tg:
                head = summarize_report(rep)
                import notify  # gui Telegram bang chinh bot cua du an
                from config import Settings
                c = Settings()
                txt = (f"🧠 MULTI-AI [{args.task}/{args.bundle}] rc={rc}\n"
                       + (head or "(khong co phan tong hop)"))
                ok = notify.send(c.tg_token, c.tg_chat, txt[:3900])
                print("Telegram:", "DA GUI" if ok else "GUI THAT BAI")
    except Exception as e:  # noqa: BLE001
        print("[warn] khong tom tat duoc report:", e)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
