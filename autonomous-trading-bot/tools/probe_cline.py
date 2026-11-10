"""Do model hoi dong qua CHINH code cua bot (ClineProvider) — chay SONG SONG.

    python tools/_probe_cline.py                      # bo mac dinh
    python tools/_probe_cline.py cline-pass/x cline-pass/y

Dung de chon danh sach tuong minh cho AGENT_COUNCIL_CLINE: chi giu model tra JSON that.
"""
from __future__ import annotations

import concurrent.futures as _fut
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:                      # doc .env (COPILOT_GITHUB_TOKEN, AGENT_COPILOT_*) nhu runtime
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT / ".env")
except Exception:  # noqa: BLE001
    pass

PROMPT = ('Ban la chuyen gia rui ro giao dich. Tra loi DUNG mot JSON:\n'
          '{"action":"ALLOW","confidence":0.7,"reasons":["ok"]}')
DEFAULT = ["cline-pass/mimo-v2.6-pro", "cline-pass/qwen3.7-plus",
           "cline-pass/qwen3.7-max", "cline-pass/qwen3.8-max",
           "cline-pass/deepseek-v4-pro", "cline-pass/minimax-m3",
           "cline-pass/mimo-v2.5-pro", "cline-pass/muse-spark-1.3-contributor"]


def probe(mid: str, timeout: float = 75.0) -> tuple:
    from agents import ClineProvider
    p = ClineProvider(model=mid)
    t0 = time.time()
    try:
        out = p.complete("Ban la chuyen gia rui ro. Tra loi DUNG JSON.", PROMPT,
                         timeout=timeout)
        return (mid, p.api_model, True, "%.0fs" % (time.time() - t0),
                out["text"][:60].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        return (mid, p.api_model, False, "%.0fs" % (time.time() - t0), str(e)[:70])


def copilot_cmd(model: str, prompt: str, env: dict | None = None) -> list:
    """Ghep lenh Copilot CLI cho 1 model (ham THUAN TUY, test duoc).

    `{prompt}` phai la MOT doi so — tach theo khoang trang se lam CLI hieu sai
    ("Invalid command format. It looks like your prompt was not quoted").
    """
    import os
    env = env if env is not None else os.environ
    bin_ = env.get("AGENT_COPILOT_BIN", "copilot")
    args = env.get("AGENT_COPILOT_ARGS", "-p {prompt}")
    parts = [prompt if a == "{prompt}" else a for a in args.split()]
    if not any(a in ("--model", "-m") for a in parts):
        parts += ["--model", model]
    return bin_.split() + parts


def probe_copilot(model: str, prompt: str = "Tra loi dung mot tu: OK",
                  timeout: float = 150.0) -> tuple:
    """Goi Copilot CLI voi 1 model -> (model, ma_phan_loai, giay, thong_bao)."""
    import subprocess
    t0 = time.time()
    try:
        r = subprocess.run(copilot_cmd(model, prompt), capture_output=True, text=True,
                           timeout=timeout)
        txt = ((r.stdout or "") + " " + (r.stderr or "")).strip().replace("\n", " ")
        from agents import classify_provider_error
        return (model, classify_provider_error(r.returncode, txt),
                "%.0fs" % (time.time() - t0), txt[:100])
    except Exception as e:  # noqa: BLE001
        return (model, "ERR", "%.0fs" % (time.time() - t0), str(e)[:100])


def main(argv: list | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--copilot" in argv:
        argv.remove("--copilot")
        import os
        models = argv or [m.strip() for m in
                          os.environ.get("AGENT_COUNCIL_MODELS", "").split(",") if m.strip()]
        models = models or ["auto"]
        t0 = time.time()
        rows = [probe_copilot(m) for m in models]
        ok = []
        for mid, code, secs, info in rows:
            print("%-24s -> %-12s %-6s %s" % (mid, code, secs, info))
            if code == "OK":
                ok.append(mid)
        print("\nDUNG DUOC (%d/%d) sau %.0fs: %s"
              % (len(ok), len(models), time.time() - t0, ",".join(ok) or "(khong co)"))
        if not ok:
            print("Goi y: dat AGENT_COUNCIL_MODELS=auto (tai khoan nay chi cho 'auto'),"
                  " va de hoi dong da dang bang AGENT_COUNCIL_CLINE.")
        return 0 if ok else 1
    models = argv or DEFAULT
    t0 = time.time()
    with _fut.ThreadPoolExecutor(max_workers=len(models)) as ex:
        rows = list(ex.map(probe, models))
    ok = []
    for mid, api, good, secs, info in rows:
        print("%-34s -> %-4s %-6s gui=%-26s %s"
              % (mid, "OK" if good else "LOI", secs, api, info))
        if good:
            ok.append(mid)
    print("\nCHAY DUOC (%d/%d) sau %.0fs: %s" % (len(ok), len(models), time.time() - t0,
                                                 ",".join(ok)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
