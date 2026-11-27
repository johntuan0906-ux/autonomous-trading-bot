"""Mot lan: DUNG bot LIVE -> danh dau OPEN trung (B-073) -> CHAY lai bot.

Chay tu workspace root: python logs\\_void_live.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "atb-live"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import restart_bot as RB  # noqa: E402
import journal  # noqa: E402
import monitor_report as mr  # noqa: E402


def main() -> int:
    d = RB.instance_dir("live")
    print("instance:", d)
    pid = RB.read_supervisor_pid(d)
    alive = RB.pid_alive(pid)
    print("supervisor pid=%s alive=%s" % (pid, alive))
    if alive:
        print("kill:", RB.kill_tree(pid))
        time.sleep(3.0)
    os.chdir(d)
    path = "logs/journal.jsonl"
    opens, closes = mr.load_journal(path)
    res = journal.find_duplicate_opens(opens, closes)
    print("OPEN=%d CLOSE=%d trung=%d review=%d"
          % (len(opens), len(closes), len(res["dupes"]), len(res["review"])))
    rep = journal.void_records(path, [x["open"] for x in res["dupes"]], apply=True)
    print("void:", rep)
    o2, c2 = mr.load_journal(path)
    _p, still = mr.match_pairs(o2, c2)
    print("sau khi sua: OPEN=%d CLOSE=%d -> chua CLOSE (FIFO)=%d" % (len(o2), len(c2), len(still)))
    new_pid = RB.start(d)
    print("started supervisor pid=%s" % new_pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
