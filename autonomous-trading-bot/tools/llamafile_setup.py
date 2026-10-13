"""Thay Ollama bang **llamafile** cho model LOCAL cua hoi dong (1 file, khong daemon).

    python tools/llamafile_setup.py --check          # dang co gi, can lam gi
    python tools/llamafile_setup.py --download       # tai llamafile mau (~1 GB) vao models/
    python tools/llamafile_setup.py --start          # chay server (an cua so), port 8080
    python tools/llamafile_setup.py --probe          # kiem tra /v1/models
    python tools/llamafile_setup.py --env            # in cac dong .env can dien
    python tools/llamafile_setup.py --stop           # tat server

Vi sao (13/10, y tuong tu mozilla-ai/llamafile): model local cua hoi dong
(`AGENT_COUNCIL_LOCAL=llama3.2:3b`) dang chay qua **Ollama** — mot dich vu nen phai
cai va phai dang chay; may khoi dong lai la hoi dong mat 1 phieu (khong ai bao).
llamafile = llama.cpp + Cosmopolitan trong **1 file thuc thi**: khong can cai, va
**phuc vu API tuong thich OpenAI** (`/v1/chat/completions`) nen **khong phai sua code**
— chi doi `AGENT_LOCAL_BASE_URL`/ten model trong `.env`.

Luu y Windows: chi chay duoc file **< 4 GB** (them duoi `.exe`).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
PORT = 8080
# Model mau nho nhat (tu README mozilla-ai) — du de chay thu; doi `--url` khi can model khac.
DEFAULT_URL = ("https://huggingface.co/mozilla-ai/llamafile_0.10/resolve/main/"
               "Qwen3.5-0.8B-Q8_0.llamafile")
WIN_LIMIT_GB = 4.0


def find_binary(models_dir: Path = MODELS) -> Path | None:
    """File llamafile da tai (bo qua file `llamafile.exe` tran = binary goc)."""
    try:
        cands = sorted(list(models_dir.glob("*.llamafile*")) +
                       list(models_dir.glob("*.exe")))
    except OSError:
        return None
    for p in cands:
        if p.name.lower().startswith("llamafile"):
            continue
        return p
    return None


def env_lines(port: int = PORT, model: str = "local") -> list:
    """Cac dong `.env` de hoi dong dung llamafile thay Ollama (ham thuan)."""
    return [
        "AGENT_COUNCIL_LOCAL=%s" % model,
        "AGENT_LOCAL_BASE_URL=http://127.0.0.1:%d/v1" % port,
        "AGENT_LOCAL_API_KEY=llamafile",
    ]


def parse_models_response(txt: str) -> list:
    """Doc `GET /v1/models` -> danh sach id model (rong neu khong doc duoc)."""
    try:
        d = json.loads(txt)
    except (TypeError, ValueError):
        return []
    out = []
    for m in (d.get("data") or []):
        mid = str((m or {}).get("id") or "").strip()
        if mid:
            out.append(mid)
    return out


def pick_model_id(ids: list, fallback: str = "local") -> str:
    """Chon id model de dien vao `.env` (llamafile thuong tra ten file)."""
    for i in (ids or []):
        if i and i.lower() not in ("default", "local", "gpt-3.5-turbo"):
            return i
    return (ids or [fallback])[0]


def size_gb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024 ** 3)
    except OSError:
        return 0.0


def check(models_dir: Path = MODELS) -> dict:
    """Trang thai cai dat: co file? dung luong? vuot gioi han Windows?"""
    b = find_binary(models_dir)
    out = {"dir": str(models_dir), "exists": b is not None,
           "file": str(b) if b else "", "size_gb": size_gb(b) if b else 0.0,
           "windows_ok": True, "ok": False}
    if b:
        out["windows_ok"] = out["size_gb"] < WIN_LIMIT_GB
        out["ok"] = out["windows_ok"]
    return out


def start(binary: Path, port: int = PORT, log_path: Path | None = None) -> int:
    """Chay llamafile o cua so an. Tra PID (0 = loi)."""
    import subprocess
    try:
        import winproc
        kw = winproc.hide_kwargs()
    except Exception:  # noqa: BLE001
        kw = {}
    args = [str(binary), "-ngl", "0", "--host", "127.0.0.1", "--port", str(port)]
    try:
        if log_path:
            f = open(log_path, "ab")
            p = subprocess.Popen(args, cwd=str(binary.parent), stdout=f,
                                 stderr=subprocess.STDOUT, **kw)
        else:
            p = subprocess.Popen(args, cwd=str(binary.parent), **kw)
        return int(p.pid)
    except Exception as e:  # noqa: BLE001
        print("[LOI] khong chay duoc %s: %s" % (binary, str(e)[:150]))
        return 0


def probe(port: int = PORT, timeout: float = 5.0) -> dict:
    """Goi `GET /v1/models` -> {'ok', 'ids', 'error'}."""
    import urllib.request
    url = "http://127.0.0.1:%d/v1/models" % port
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            txt = r.read().decode("utf-8", errors="replace")
        return {"ok": True, "ids": parse_models_response(txt), "error": ""}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "ids": [], "error": str(e)[:150]}


def download(url: str, dest: Path) -> bool:
    """Tai file (bao tien do theo %). Tra True neu xong."""
    import urllib.request
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    print("\r  %.0f%% (%.2f GB)" % (100.0 * got / total,
                                                    got / (1024 ** 3)), end="")
        print()
        return True
    except Exception as e:  # noqa: BLE001
        print("[LOI] tai that bai: %s" % str(e)[:200])
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="llamafile cho model local cua hoi dong")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--env", action="store_true")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))

    if args.env:
        print("# Thay Ollama bang llamafile — dien vao .env:")
        for ln in env_lines(args.port):
            print(ln)
        return 0

    if args.download:
        dest = MODELS / Path(args.url).name
        if dest.exists():
            print("da co: %s (%.2f GB)" % (dest, size_gb(dest)))
        else:
            print("tai %s\n  -> %s" % (args.url, dest))
            if not download(args.url, dest):
                return 1
        if os.name == "nt" and dest.suffix != ".exe":
            newp = dest.with_suffix(dest.suffix + ".exe")
            if not newp.exists():
                dest.rename(newp)
                print("Windows: doi ten thanh %s (can duoi .exe de chay)" % newp.name)
        return 0

    if args.stop:
        import subprocess
        try:
            out = subprocess.run(["taskkill", "/F", "/IM", "llamafile.exe"],
                                 capture_output=True, text=True, timeout=30).stdout
            print(out.strip() or "khong co tien trinh llamafile")
        except Exception as e:  # noqa: BLE001
            print("[LOI] %s" % str(e)[:120])
        return 0

    st = check()
    if args.start:
        if not st["exists"]:
            print("[LOI] chua co llamafile trong %s — chay --download truoc" % st["dir"])
            return 1
        if not st["windows_ok"]:
            print("[LOI] file %.2f GB >= %.0f GB: Windows KHONG chay duoc"
                  % (st["size_gb"], WIN_LIMIT_GB))
            return 1
        pid = start(Path(st["file"]), args.port, MODELS / "llamafile.log")
        print("da chay PID=%s (log: models/llamafile.log)" % pid)
        return 0

    if args.probe:
        r = probe(args.port)
        print("probe:", json.dumps(r, ensure_ascii=False))
        if r["ok"]:
            print("dien vao .env: AGENT_COUNCIL_LOCAL=%s" % pick_model_id(r["ids"]))
        return 0 if r["ok"] else 1

    print("=== LLAMAFILE ===")
    print("  thu muc   : %s" % st["dir"])
    if not st["exists"]:
        print("  trang thai: CHUA co -> python tools/llamafile_setup.py --download")
    else:
        print("  file      : %s (%.2f GB)" % (st["file"], st["size_gb"]))
        print("  Windows   : %s" % ("OK (< 4 GB)" if st["windows_ok"]
                                     else "KHONG chay duoc (>= 4 GB)"))
    p = probe(args.port)
    print("  server    : %s" % ("dang chay, models=%s" % p["ids"] if p["ok"]
                                else "chua chay (%s)" % p["error"][:60]))
    print("  .env can dien:")
    for ln in env_lines(args.port):
        print("    %s" % ln)
    return 0 if st["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
