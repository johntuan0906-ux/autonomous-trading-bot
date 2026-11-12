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


def write_probe_cache(rows: list, path: str | None = None,
                      now: float | None = None) -> str:
    """Ghi ket qua do (rows cua `probe_copilot`) -> `logs/model_probe.json`.

    (12/11, B-052) Day la CACH hoi dong biet "goi Copilot da nang chua": `agents._council_models`
    doc cache nay (`agents.read_probe_cache`) va tu them candidate nao co `code == "OK"`.
    Nho vay nguoi van hanh KHONG phai sua `.env` / restart khi doi goi.
    """
    import json
    import os
    p = path or os.path.join(ROOT, "logs", "model_probe.json")
    results = {}
    for row in rows:
        mid, code = str(row[0]), str(row[1])
        results[mid] = {"code": code, "secs": row[2] if len(row) > 2 else ""}
    data = {"probed_at": float(now if now is not None else time.time()),
            "results": results}
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)          # ghi nguyen tu: hoi dong khong bao gio doc file do dang
    return p


def qwen_cmd(prompt: str, model: str = "", env: dict | None = None) -> list:
    """Lenh Qwen Code CLI headless cho 1 model (ham THUAN TUY, test duoc)."""
    import os
    env = env if env is not None else os.environ
    base = (env.get("AGENT_QWEN_BIN", "qwen") or "qwen").split()
    args = (env.get("AGENT_QWEN_ARGS", "-p {prompt}") or "-p {prompt}").split()
    parts = [prompt if a == "{prompt}" else a for a in args]
    if model and not any(a in ("--model", "-m") for a in parts):
        parts += ["-m", model]
    return base + parts


def probe_qwen(model: str, prompt: str = "Tra loi dung mot tu: OK",
               timeout: float = 150.0) -> tuple:
    """Goi Qwen CLI voi 1 model -> (model, ma_phan_loai, giay, thong_bao)."""
    import subprocess
    t0 = time.time()
    try:
        r = subprocess.run(qwen_cmd(prompt, model), capture_output=True, text=True,
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
        write = "--no-cache" not in argv
        if "--no-cache" in argv:
            argv.remove("--no-cache")
        import os
        if "--candidates" in argv:          # do dung danh sach du phong trong `.env`
            argv.remove("--candidates")
            raw = [os.environ.get("AGENT_COUNCIL_MODELS_CANDIDATES", "")]
        else:
            raw = argv or [os.environ.get("AGENT_COUNCIL_MODELS", "")]
        models = [m.strip() for item in raw for m in str(item).split(",") if m.strip()]
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
        if write:
            p = write_probe_cache(rows)
            print("Da ghi cache: %s (%d model) -> hoi dong tu them model OK o lan do sau."
                  % (p, len(rows)))
        if not ok:
            print("Goi y: dat AGENT_COUNCIL_MODELS=auto (tai khoan nay chi cho 'auto'),"
                  " va de hoi dong da dang bang AGENT_COUNCIL_CLINE.")
        return 0 if ok else 1
    if "--qwen" in argv:
        argv.remove("--qwen")
        models = [m.strip() for m in argv if m.strip()] or [""]
        t0 = time.time()
        for mid in models:
            m, code, secs, info = probe_qwen(mid)
            print("%-28s -> %-12s %-6s %s" % (mid or "(mac dinh)", code, secs, info))
        print("\nQwen CLI: %.0fs. `PAYMENT` = gateway het credit; `MODEL_GATED` = ten model"
              " sai dinh dang `openai/<id>` (id KHONG duoc chua dau '/')."
              % (time.time() - t0))
        return 0
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
