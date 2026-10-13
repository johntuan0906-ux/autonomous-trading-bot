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
    """File chay duoc: uu tien llamafile TU CHUA (`.llamafile*`), roi den binary thin
    (`llamafile-0.10.6-thin.exe` — chay voi GGUF ngoai qua `-m`)."""
    try:
        cands = sorted(list(models_dir.glob("*.llamafile*")) +
                       list(models_dir.glob("*.exe")))
    except OSError:
        return None
    for p in cands:                      # tu chua (co san trong khoi model)
        if "llamafile-" not in p.name.lower():
            return p
    for p in cands:                      # binary thin
        if "llamafile-" in p.name.lower() and "thin" in p.name.lower():
            return p
    return None


def find_gguf(models_dir: Path = MODELS) -> Path | None:
    """File trong so GGUF di kem (dung voi binary thin)."""
    try:
        for p in sorted(models_dir.glob("*.gguf")):
            return p
    except OSError:
        return None
    return None


def pick_runner(models_dir: Path = MODELS) -> tuple:
    """(binary, gguf) nen chay: uu tien **thin + GGUF** khi co GGUF trong `models/`.

    (13/10) Loi that: `find_binary` uu tien file tu chua -> no chon nham llamafile 0.8B
    trong khi da co GGUF 3B + binary thin => chay sai model. Nay: co GGUF thi dung thin.
    """
    g = find_gguf(models_dir)
    try:
        exes = sorted(models_dir.glob("*.exe"))
    except OSError:
        exes = []
    thin = next((p for p in exes if "thin" in p.name.lower()), None)
    if g is not None and thin is not None:
        return thin, g
    for p in sorted(list(models_dir.glob("*.llamafile*")) + exes):
        if "llamafile-" not in p.name.lower():
            return p, None
    return (thin, None) if thin is not None else (None, None)


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
    """Trang thai cai dat: co file? dung luong? vuot gioi han Windows? co GGUF khong?"""
    b, g = pick_runner(models_dir)
    out = {"dir": str(models_dir), "exists": b is not None,
           "file": str(b) if b else "", "size_gb": size_gb(b) if b else 0.0,
           "gguf": str(g) if g else "", "gguf_gb": size_gb(g) if g else 0.0,
           "windows_ok": True, "ok": False}
    if b:
        # Gioi han 4 GB cua Windows: binary thin luon nho; llamafile tu chua co the vuot
        out["windows_ok"] = out["size_gb"] < WIN_LIMIT_GB
        out["ok"] = bool(out["windows_ok"] and (g is not None or "thin" not in b.name.lower()))
    return out


def stop(models_dir: Path = MODELS) -> list:
    """Tat MOI server llamafile cua repo (theo PID da luu + ten file trong models/).

    (13/10) Loi that: `taskkill /IM llamafile.exe` KHONG khop vi file ten
    `Qwen3.5-0.8B-Q8_0.llamafile.exe` / `llamafile-0.10.6-thin.exe` -> server cu van
    giu port 8080, server moi khong khoi dong duoc (port busy) ma KHONG ai bao.
    Tra danh sach ket qua tung buoc.
    """
    import subprocess
    out: list = []
    pidf = models_dir / "llamafile.pid"
    try:
        pid = int(pidf.read_text(encoding="utf-8").strip())
        r = subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True, text=True, timeout=30)
        out.append("pid %s -> rc=%s" % (pid, r.returncode))
        pidf.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        out.append("khong co file pid (bo qua)")
    try:
        names = sorted({p.name for p in models_dir.glob("*.exe")})
    except OSError:
        names = []
    for n in names:
        try:
            r = subprocess.run(["taskkill", "/F", "/IM", n],
                               capture_output=True, text=True, timeout=30)
            out.append("%s -> rc=%s" % (n, r.returncode))
        except Exception as e:  # noqa: BLE001
            out.append("%s -> loi %s" % (n, str(e)[:60]))
    return out


def start(binary: Path, port: int = PORT, log_path: Path | None = None,
          gguf: Path | None = None) -> int:
    """Chay llamafile o cua so an (kem `-m <gguf>` khi dung binary thin). Tra PID."""
    import subprocess
    try:
        import winproc
        kw = winproc.hide_kwargs()
    except Exception:  # noqa: BLE001
        kw = {}
    args = [str(binary), "-ngl", "0", "--host", "127.0.0.1", "--port", str(port)]
    if gguf is not None:
        # (13/10) PHAI dung `--model` (khong phai `-m`): binary THIN da co `-m` mac dinh
        # ben trong -> `-m` lan 2 gay "specified multiple times" va no nap nham model
        # mmproj cua chinh no ("mismatch between text model n_embd=3072 and mmproj=1024")
        # => server chet ma khong ro ly do. `--model` ghi de dung file GGUF chi dinh.
        args += ["--model", str(gguf)]
    try:
        if log_path:
            f = open(log_path, "ab")
            p = subprocess.Popen(args, cwd=str(binary.parent), stdout=f,
                                 stderr=subprocess.STDOUT, **kw)
        else:
            p = subprocess.Popen(args, cwd=str(binary.parent), **kw)
        try:                              # luu PID de `--stop` tat DUNG tien trinh nay
            (binary.parent / "llamafile.pid").write_text(str(p.pid), encoding="utf-8")
        except OSError:
            pass
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


def chat_probe(port: int = PORT, prompt: str = "Tra loi dung mot tu: OK",
               timeout: float = 90.0) -> dict:
    """Goi thu `/v1/chat/completions` -> {'ok', 'text', 'error'} (kiem tra THAT)."""
    import urllib.request
    body = json.dumps({"model": "local", "max_tokens": 16,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port,
                                 data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer llamafile"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", errors="replace"))
        txt = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return {"ok": bool(txt.strip()), "text": txt.strip()[:200], "error": ""}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "text": "", "error": str(e)[:200]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="llamafile cho model local cua hoi dong")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--chat", action="store_true",
                    help="goi thu /v1/chat/completions (kiem tra THAT, khong chi /models)")
    ap.add_argument("--env", action="store_true")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    try:                      # console Windows mac dinh cp1252 -> khong in duoc tieng Viet
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

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
        if os.name == "nt" and dest.suffix != ".exe" and dest.suffix != ".gguf":
            newp = dest.with_suffix(dest.suffix + ".exe")
            if not newp.exists():
                dest.rename(newp)
                print("Windows: doi ten thanh %s (can duoi .exe de chay)" % newp.name)
        return 0

    if args.stop:
        for ln in stop():
            print("  %s" % ln)
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
        pid = start(Path(st["file"]), args.port, MODELS / "llamafile.log",
                    Path(st["gguf"]) if st["gguf"] else None)
        print("da chay PID=%s (log: models/llamafile.log)" % pid)
        return 0

    if args.probe:
        r = probe(args.port)
        print("probe:", json.dumps(r, ensure_ascii=False))
        if r["ok"]:
            print("dien vao .env: AGENT_COUNCIL_LOCAL=%s" % pick_model_id(r["ids"]))
        return 0 if r["ok"] else 1

    if args.chat:
        r = chat_probe(args.port)
        print("chat ok=%s | tra loi: %s | loi: %s"
              % (r["ok"], r["text"].replace("\n", " ")[:120], r["error"]))
        return 0 if r["ok"] else 1

    print("=== LLAMAFILE ===")
    print("  thu muc   : %s" % st["dir"])
    if not st["exists"]:
        print("  trang thai: CHUA co -> python tools/llamafile_setup.py --download")
    else:
        print("  binary    : %s (%.2f GB)" % (st["file"], st["size_gb"]))
        if st["gguf"]:
            print("  trong so  : %s (%.2f GB)" % (st["gguf"], st["gguf_gb"]))
        elif "thin" in Path(st["file"]).name.lower():
            print("  trong so  : CHUA co GGUF -> binary thin can `-m <file.gguf>`")
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
