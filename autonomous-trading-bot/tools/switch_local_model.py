"""Doi 3 dong cau hinh model LOCAL trong .env (idempotent) — dung Ollama <-> llamafile.

    python tools/_switch_local.py <duong_dan_.env> llamafile|ollama
"""
from __future__ import annotations

import io
import sys

SETS = {
    # (13/10) llamafile: 1 file, KHONG can daemon; model 3B Q4 (cung ho voi llama3.2:3b)
    "llamafile": {
        "AGENT_COUNCIL_LOCAL": "llama3.2-3b-local",
        "AGENT_LOCAL_BASE_URL": "http://127.0.0.1:8080/v1",
        "AGENT_LOCAL_API_KEY": "llamafile",
    },
    "ollama": {
        "AGENT_COUNCIL_LOCAL": "llama3.2:3b",
        "AGENT_LOCAL_BASE_URL": "http://127.0.0.1:11434/v1",
        "AGENT_LOCAL_API_KEY": "ollama",
    },
}


def main() -> int:
    p, which = sys.argv[1], sys.argv[2].lower()
    want = SETS[which]
    lines = io.open(p, encoding="utf-8").read().splitlines()
    seen = set()
    out = []
    for ln in lines:
        k = ln.split("=", 1)[0].strip() if "=" in ln and not ln.startswith("#") else ""
        if k in want:
            if k in seen:
                continue                      # bo dong trung lap
            out.append("%s=%s" % (k, want[k]))
            seen.add(k)
        else:
            out.append(ln)
    for k, v in want.items():
        if k not in seen:
            out.append("%s=%s" % (k, v))
    io.open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("OK %s -> %s" % (p, which))
    for k, v in want.items():
        print("   %s=%s" % (k, v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
