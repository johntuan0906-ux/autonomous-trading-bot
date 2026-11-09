"""Liet ke cac KEY thuc te trong logs/journal.jsonl theo tung loai ban ghi."""
import collections
import json

out = []
for path in ("logs/journal.jsonl", "../atb-live/logs/journal.jsonl"):
    try:
        f = open(path, encoding="utf-8")
    except OSError as e:
        out.append("== %s -> KHONG DOC DUOC (%s)" % (path, e))
        continue
    seen = collections.defaultdict(collections.Counter)
    n = bad = 0
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                bad += 1
                continue
            n += 1
            ev = str(d.get("event") or d.get("status") or "?")
            for k in d:
                seen[ev][k] += 1
    out.append("\n===== %s  lines=%d  bad=%d  kinds=%d" % (path, n, bad, len(seen)))
    for ev, cnt in sorted(seen.items(), key=lambda kv: -sum(kv[1].values())):
        out.append("-- %-12s rows=%-5d keys: %s"
                   % (ev, max(cnt.values()), ", ".join(k for k, _ in cnt.most_common(45))))

open("_keys.txt", "w", encoding="utf-8").write("\n".join(out))
print("WROTE _keys.txt")
