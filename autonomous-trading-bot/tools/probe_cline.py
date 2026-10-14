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


def main(argv: list | None = None) -> int:
    models = list(argv if argv is not None else sys.argv[1:]) or DEFAULT
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
