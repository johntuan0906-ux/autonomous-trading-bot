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
        parts.append("## Tham so dang chay (.env.example — KHONG co secret)\n```text\n"
                     + _read(ROOT / ".env.example", 2500) + "\n```")
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


def build_cmd(args, bundle: Path | None, task_file: Path) -> list:
    """Len lenh cho harness (tach rieng de test duoc, khong chay that)."""
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
        for m in (args.model or []):
            cmd += ["--model", str(m)]
    for f in (args.file or []):
        cmd += ["--context", str(f)]
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


def preflight(args, task_file: Path) -> str:
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
    if not task_file.is_file():
        return f"Khong thay file nhiem vu: {task_file}"
    if args.engine == "clinepass" and args.provider == "clinepass" \
            and not os.getenv("CLINE_API_KEY", "").strip():
        return ("Thieu CLINE_API_KEY trong .env. Lay key tai app.cline.bot -> Settings -> "
                "API Keys (dung cho ca multi-AI 14 model). Hoac chay --provider mock.")
    if args.engine == "lab" and args.provider == "openai" \
            and not os.getenv("OPENAI_API_KEY", "").strip():
        return "Thieu OPENAI_API_KEY trong .env (hoac chay --provider mock)."
    return ""


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
    ap.add_argument("--tg", action="store_true", help="gui tom tat ket qua len Telegram")
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

    task_file = TASKS / TASK_FILES[args.task]
    err = preflight(args, task_file)
    if err:
        print("[LOI] " + err, file=sys.stderr)
        return 2
    bundle = build_bundle(args.bundle)
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
