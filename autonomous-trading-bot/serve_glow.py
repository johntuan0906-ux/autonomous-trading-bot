# -*- coding: utf-8 -*-
"""serve_glow.py - server LIVE cho cac ban do: file tinh + API tin hieu + SSE.

  python serve_glow.py [--port 8765] [--watch] [--rebuild]

- GET  /                        -> glow_map.html (ban Canvas2D)
- GET  /glow_map_webgl.html     -> ban WebGL (cung snapshot + signature)
- GET  /api/snapshot            -> glow_signals.json moi nhat (2 map poll 15s)
- GET  /api/stream              -> SSE: event / snapshot / reload
- GET  /api/files?n=...         -> token tung file (cho baseline chinh xac)
- POST /api/event                -> nhan 1 event tu agent/tool (nhu retrieval_hook)
- POST /api/rebuild              -> chay lai build_glow.py, phat reload cho map
- --watch: theo doi graph_memory.json/memory_map_data.json/retrieval_log.jsonl,
  thay doi -> rebuild + snapshot moi + phat reload (cap nhat lien tuc).

Chi dung stdlib (http.server). Khong can khi mo file:// (map dung snapshot nhung).
"""
from __future__ import annotations

import argparse
import copy
import json
import queue
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import glow_retrieval as R

WATCH_FILES = ["graph_memory.json", "memory_map_data.json", "cross_index.json",
               "retrieval_log.jsonl", "glow_agents.py", "glow_retrieval.py"]

SUBS: list[queue.Queue] = []
SUBS_LOCK = threading.Lock()
STATE = {"signature": "", "snapshot": None, "snapshot_at": 0.0,
         "log_size": 0, "building": False}


def broadcast(kind, data):
    msg = "event: %s\ndata: %s\n\n" % (kind, json.dumps(data, ensure_ascii=False))
    with SUBS_LOCK:
        dead = []
        for q in SUBS:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            SUBS.remove(q)


def build_snapshot():
    events = R.read_events(R.LOG_PATH)
    all_docs = R.load_all_docs(ROOT)
    sig = R.fingerprint({n: (d, l) for n, (d, l, _f) in all_docs.items()})
    info = [{"name": n, "nodes": len(d), "edges": len(l),
             "tokens": sum(max(R.MIN_DOC_TOKENS, x["tokens"]) for x in d)}
            for n, (d, l, _f) in all_docs.items()]
    snap = R.snapshot(events, copy.deepcopy(R.AGENTS), info, sig)
    STATE.update(signature=sig, snapshot=snap, snapshot_at=time.time())
    try:
        with open(R.SNAPSHOT_PATH, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False)
    except OSError:
        pass
    return snap


def file_tokens(names):
    out = {}
    for f in names:
        f = str(f)
        if f in out:
            continue
        p = (ROOT / f) if not Path(f).is_absolute() else Path(f)
        try:
            if p.is_file():
                out[f] = max(1, int(p.stat().st_size * R.TOKENS_PER_CHAR))
        except OSError:
            continue
    return out


class Handler(SimpleHTTPRequestHandler):
    server_version = "GlowServe/1.0"

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _need_snapshot(self):
        if not STATE["snapshot"]:
            build_snapshot()
        return STATE["snapshot"]

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/snapshot":
            return self._json(self._need_snapshot())
        if u.path == "/api/files":
            qs = parse_qs(u.query)
            names = []
            for v in qs.get("name", []):
                names += [x for x in v.split(",") if x]
            return self._json({"tokens": file_tokens(names[:400])})
        if u.path == "/api/stream":
            return self._stream()
        if u.path in ("/", "/index.html"):
            self.path = "/glow_map.html"
        return super().do_GET()

    def _stream(self):
        q: queue.Queue = queue.Queue(maxsize=64)
        with SUBS_LOCK:
            SUBS.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(("event: snapshot\ndata: %s\n\n" % json.dumps(
                self._need_snapshot(), ensure_ascii=False)).encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=20)
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with SUBS_LOCK:
                if q in SUBS:
                    SUBS.remove(q)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(max(0, n)) if n else b""
        if u.path == "/api/event":
            try:
                ev = json.loads(raw.decode("utf-8"))
            except ValueError:
                return self._json({"ok": False, "error": "JSON khong hop le"}, 400)
            ev.setdefault("t", round(time.time(), 3))
            ev.setdefault("ok", True)
            try:
                R.append_event(R.LOG_PATH, ev)
            except OSError as e:
                return self._json({"ok": False, "error": str(e)}, 500)
            build_snapshot()
            broadcast("event", ev)
            return self._json({"ok": True, "saved": ev.get("tokens_saved", 0)})
        if u.path == "/api/rebuild":
            ok = run_build()
            build_snapshot()
            broadcast("reload", {"signature": STATE["signature"], "at": time.time()})
            return self._json({"ok": ok, "signature": STATE["signature"]})
        return self._json({"ok": False, "error": "unknown endpoint"}, 404)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            sys.stderr.write("[api] %s\n" % (fmt % args))


def run_build():
    if STATE["building"]:
        return False
    STATE["building"] = True
    try:
        r = subprocess.run([sys.executable, "build_glow.py"], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=300)
        sys.stderr.write(r.stdout[-1500:] + ("\n" + r.stderr[-500:] if r.stderr else ""))
        return r.returncode == 0
    except Exception as e:
        sys.stderr.write("[build] loi: %s\n" % e)
        return False
    finally:
        STATE["building"] = False


def watch_loop(interval=3.0):
    seen = {}

    def stamp():
        out = {}
        for name in WATCH_FILES:
            p = ROOT / name
            try:
                st = p.stat()
                out[name] = (st.st_mtime_ns, st.st_size)
            except OSError:
                out[name] = None
        return out

    seen.update(stamp())
    while True:
        time.sleep(interval)
        cur = stamp()
        if cur == seen:
            continue
        changed = sorted(k for k in cur if cur[k] != seen.get(k))
        seen.update(cur)
        sys.stderr.write("[watch] doi: %s -> rebuild\n" % ",".join(changed))
        if "retrieval_log.jsonl" in changed and not any(
                c in changed for c in ("graph_memory.json", "memory_map_data.json")):
            build_snapshot()
            broadcast("snapshot", STATE["snapshot"])
        else:
            if run_build():
                build_snapshot()
                broadcast("reload", {"signature": STATE["signature"], "at": time.time()})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Server LIVE cho cac ban do glow_map.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--watch", action="store_true",
                    help="theo doi du lieu/log -> rebuild + snapshot + reload lien tuc")
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild 1 lan khi khoi dong roi moi serve")
    args = ap.parse_args(argv)

    import os
    os.chdir(str(ROOT))
    if args.rebuild:
        run_build()
    build_snapshot()
    if args.watch:
        t = threading.Thread(target=watch_loop, daemon=True)
        t.start()
        print("[serve] watch: ON (%s)" % ", ".join(WATCH_FILES))
    print("[serve] http://%s:%d/  (Canvas2D)  +  /glow_map_webgl.html (WebGL)" % (
        args.host, args.port))
    print("[serve] api: /api/snapshot /api/stream /api/event /api/rebuild /api/files")
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

