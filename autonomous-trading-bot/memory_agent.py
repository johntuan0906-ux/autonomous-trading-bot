"""memory_agent.py — Port openbrain-master engines -> memory-graph (Python/SQLite).

Áp dụng openbrain-master (OpenCode memory plugin) vào dự án để:
  * TỰ ĐỘNG GHI LẠI  : mọi lần sync/reflect/observe -> Memory (SQLite)
  * PHÂN TÍCH        : ReflectionEngine trích mistake/lesson/pattern/decision
  * CHẠY NGẦM        : DreamEngine + SyncEngine (watcher) tự lưu khi file đổi
  * ĐỒNG BỘ DỰ ÁN    : file thay đổi -> rebuild graph_memory.json -> reseed memory.db
  * GIẢM TOKEN       : ContextEngine.build_context(query) trả block NGẮN

CLI:
  python memory_agent.py sync | watch | reflect | dream | context "q" | skill ... | stats
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from memory_graph import DB_PATH, ROOT, MemoryGraph, observe

EPISODIC, SEMANTIC, PROCEDURAL = "episodic", "semantic", "procedural"
DECISION, BUG, WORKSPACE, PROJECT = "decision", "bug", "workspace", "project"
REFLECTION, SKILL = "reflection", "skill"


class MemoryEngine:
    """openbrain MemoryEngine (save/get/search/create_*) trên MemoryGraph."""

    def __init__(self, g: MemoryGraph):
        self.g = g

    def save(self, memory: dict) -> str:
        return self.g.store_memory(memory)

    def get(self, mid: str) -> dict | None:
        return self.g.get_memory(mid)

    def get_all(self, mtype: str | None = None) -> list[dict]:
        return self.g.search_memories({"types": [mtype] if mtype else [], "limit": 1000})

    def search(self, query: str, mtype: str | None = None, limit: int = 20) -> list[dict]:
        return self.g.search_memories({"query": query,
                                       "types": [mtype] if mtype else [], "limit": limit})

    def delete(self, mid: str) -> bool:
        return self.g.delete_memory(mid)

    def get_by_tags(self, tags: list[str], mtype: str | None = None) -> list[dict]:
        rows = self.get_all(mtype)
        want = {t.lower() for t in tags}
        return [m for m in rows if want & {t.lower() for t in (m.get("tags") or [])}]

    def create(self, mtype: str, content: str, tags: list[str], confidence: float = 0.8,
               title: str | None = None, importance: float = 0.6,
               metadata: dict | None = None) -> str:
        md = metadata or {}
        auto = md.get("skill_name") or md.get("concept") or content[:80].replace("\n", " ")
        return self.save({"type": mtype, "title": (title or auto)[:200],
                          "content": content, "tags": tags, "confidence": confidence,
                          "importance": importance,
                          "context": {"project_path": str(ROOT),
                                      "additional_metadata": md}})

    def create_episodic(self, content, metadata, tags, confidence=0.8):
        return self.create(EPISODIC, content, tags, confidence, metadata=metadata)

    def create_semantic(self, content, metadata, tags, confidence=0.9):
        return self.create(SEMANTIC, content, tags, confidence, metadata=metadata)

    def create_procedural(self, content, metadata, tags, confidence=0.8):
        return self.create(PROCEDURAL, content, tags, confidence, metadata=metadata)

    def create_decision(self, content, metadata, tags, confidence=0.9):
        return self.create(DECISION, content, tags, confidence, metadata=metadata)

    def create_bug(self, content, metadata, tags, confidence=0.9):
        return self.create(BUG, content, tags, confidence, metadata=metadata)

    def create_workspace(self, content, metadata, tags, confidence=0.8):
        return self.create(WORKSPACE, content, tags, confidence, metadata=metadata)

    def create_project(self, content, metadata, tags, confidence=0.9):
        return self.create(PROJECT, content, tags, confidence, metadata=metadata)
# ===AGENT2===


class ReflectionEngine:
    """openbrain ReflectionEngine: phân tích -> mistake/lesson/pattern/decision memories."""

    def __init__(self, mem: MemoryEngine):
        self.mem = mem

    def reflect(self, content: str, metadata: dict | None = None,
                mistakes: list[str] | None = None, lessons: list[str] | None = None,
                patterns: list[str] | None = None, anti_patterns: list[str] | None = None,
                decisions: list[str] | None = None, user_preferences: list[str] | None = None,
                reusable_workflows: list[str] | None = None,
                session_id: str | None = None) -> dict:
        mistakes = mistakes or []; lessons = lessons or []; patterns = patterns or []
        anti_patterns = anti_patterns or []; decisions = decisions or []
        user_preferences = user_preferences or []; reusable_workflows = reusable_workflows or []
        ref = {"id": f"ref-{int(time.time() * 1000)}", "content": content,
               "session_id": session_id, "mistakes": mistakes, "lessons": lessons,
               "patterns": patterns, "anti_patterns": anti_patterns,
               "decisions": decisions, "user_preferences": user_preferences,
               "reusable_workflows": reusable_workflows,
               "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        tags = [REFLECTION] + ([session_id] if session_id else [])
        self.mem.create_semantic(json.dumps(ref, ensure_ascii=False),
                                 {"concept": "reflection", "source": "ReflectionEngine"},
                                 tags, 0.9)
        if mistakes:
            self.mem.create_semantic("\n".join(mistakes),
                                     {"concept": "mistake", "source": "ReflectionEngine"},
                                     ["mistake"], 0.9)
        if lessons:
            self.mem.create_semantic("\n".join(lessons),
                                     {"concept": "lesson", "source": "ReflectionEngine"},
                                     ["lesson"], 0.9)
        for d in decisions:
            self.mem.create_decision(d, {"context": "reflection", "outcome": "recorded",
                                         "reasoning": "reflection"}, ["decision"], 0.9)
        if patterns:
            self.mem.create_semantic("\n".join(patterns),
                                     {"concept": "pattern"}, ["pattern"], 0.85)
        if anti_patterns:
            self.mem.create_semantic("\n".join(anti_patterns),
                                     {"concept": "anti-pattern"}, ["anti-pattern"], 0.85)
        if user_preferences:
            self.mem.create_semantic("\n".join(user_preferences),
                                     {"concept": "user-preference"}, ["user-preference"], 0.9)
        for wf in reusable_workflows:
            self.mem.create_procedural(wf, {"steps": wf.split(";")}, ["workflow"], 0.85)
        return ref

    def get_reflections(self, limit: int = 20) -> list[dict]:
        return self.mem.search(REFLECTION, None, limit)
# ===AGENT2B===

    def analyze_logs(self, max_lines: int = 400) -> dict:
        """Tự trích insight từ logs/*.log (SL hits, strategy WR, lỗi) -> memories."""
        logdir = ROOT / "logs"
        mistakes, lessons, patterns, decisions = [], [], [], []
        sl_hits: dict[str, int] = {}
        strat_wr: dict[str, list[int]] = {}
        if logdir.exists():
            for f in sorted(logdir.glob("*.log")):
                try:
                    lines = f.read_text(errors="ignore").splitlines()[-max_lines:]
                except Exception:
                    continue
                for ln in lines:
                    if "SL hit" in ln or "EXIT_SL" in ln:
                        m = re.search(r"(\w+)/USDT", ln)
                        sym = m.group(1) if m else "?"
                        sl_hits[sym] = sl_hits.get(sym, 0) + 1
                    m2 = re.search(r"STRAT (\w+) n=(\d+) WR=(\d+)%", ln)
                    if m2:
                        strat_wr.setdefault(m2.group(1), []).append(int(m2.group(3)))
                    if "ReduceOnly" in ln:
                        mistakes.append("reduceonly reject: " + ln.strip()[:140])
                    elif "Traceback" in ln:
                        mistakes.append("traceback: " + ln.strip()[:140])
        for sym, n in sorted(sl_hits.items(), key=lambda kv: -kv[1]):
            if n >= 2:
                patterns.append(f"{sym}: {n}x SL hit -> cân nhắc SL rộng hơn/tránh re-entry")
        for strat, wrs in strat_wr.items():
            avg = sum(wrs) / len(wrs)
            if avg < 45:
                lessons.append(f"strategy {strat} WR {avg:.0f}% -> hạ ưu tiên")
            elif avg >= 65:
                decisions.append(f"tăng ưu tiên strategy {strat} (WR {avg:.0f}%)")
        return self.reflect(content=f"auto-analyze logs: {len(strat_wr)} strat, "
                                    f"{sum(sl_hits.values())} SL hits",
                            mistakes=mistakes[:12], lessons=lessons[:8],
                            patterns=patterns[:8], decisions=decisions[:8],
                            session_id="bot-logs")


class LearningEngine:
    """openbrain LearningEngine: skill có usage_count + success_rate; hạ skill lỗi."""

    def __init__(self, mem: MemoryEngine):
        self.mem = mem

    def create_skill(self, name: str, description: str, steps: list[str],
                     prompt: str = "") -> str:
        content = json.dumps({"name": name, "description": description,
                              "steps": steps, "prompt": prompt,
                              "usage_count": 0, "success_rate": 1.0}, ensure_ascii=False)
        return self.mem.create_procedural(content, {"skill_name": name, "steps": steps},
                                          [SKILL, name], 0.9)

    def list_skills(self, limit: int = 50) -> list[dict]:
        rows = self.mem.get_by_tags([SKILL])
        out = []
        for r in rows:
            try:
                out.append(json.loads(r["content"]))
            except Exception:
                out.append({"name": r["title"], "description": r["content"][:80],
                            "usage_count": r["usage_count"],
                            "success_rate": r["confidence"]})
        out.sort(key=lambda s: (s.get("success_rate", 0), s.get("usage_count", 0)),
                 reverse=True)
        return out[:limit]

    def record_skill_result(self, name: str, success: bool) -> bool:
        rows = self.mem.get_by_tags([SKILL, name])
        if not rows:
            return False
        r = rows[0]
        try:
            data = json.loads(r["content"])
        except Exception:
            return False
        n = int(data.get("usage_count", 0)) + 1
        prev = float(data.get("success_rate", 1.0))
        data["usage_count"] = n
        data["success_rate"] = round((prev * (n - 1) + (1.0 if success else 0.0)) / n, 4)
        self.mem.g.update_memory(r["id"], {"content": json.dumps(data, ensure_ascii=False),
                                           "confidence": data["success_rate"]})
        return True
# ===AGENT3===


class ContextEngine:
    """openbrain ContextEngine: dựng block ngữ cảnh NGẮN để tiết kiệm token."""

    def __init__(self, mem: MemoryEngine, learn: LearningEngine):
        self.mem = mem
        self.learn = learn

    def get_context(self, query: str = "", limit: int = 12) -> dict:
        recent = self.mem.get_all()[:limit]
        relevant = self.mem.search(query, None, limit) if query else recent
        return {"recent": recent, "relevant": relevant,
                "skills": self.learn.list_skills(6),
                "prefs": self.mem.get_by_tags(["user-preference"])[:5]}

    def build_context(self, query: str = "", limit: int = 12) -> str:
        """Trả text ngắn (~20-40 dòng) thay vì phải đọc lại nhiều file nguồn."""
        ctx = self.get_context(query, limit)
        out = ["## MEMORY CONTEXT" + (f' (query="{query}")' if query else "")]
        if ctx["relevant"]:
            out.append("### Relevant")
            for m in ctx["relevant"]:
                out.append(f"- [{m['type']}] {m['title'][:90]} :: {str(m['content'])[:120]}")
        if ctx["skills"]:
            out.append("### Skills")
            for s in ctx["skills"][:6]:
                out.append(f"- {s.get('name')}: {str(s.get('description'))[:80]} "
                           f"(used={s.get('usage_count')}, sr={s.get('success_rate')})")
        if ctx["prefs"]:
            out.append("### Prefs")
            for p in ctx["prefs"]:
                out.append(f"- {str(p['content'])[:100]}")
        return "\n".join(out)


class DreamEngine:
    """openbrain DreamEngine: dedupe / compress / promote / archive (bảo trì ngầm)."""

    def __init__(self, mem: MemoryEngine):
        self.mem = mem

    def deduplicate(self) -> int:
        seen: dict[tuple, dict] = {}
        dups = []
        for m in self.mem.get_all():
            key = (m["type"], m["content"])
            if key in seen:
                keep = seen[key]
                if float(m["confidence"]) > float(keep["confidence"]):
                    dups.append(keep["id"]); seen[key] = m
                else:
                    dups.append(m["id"])
            else:
                seen[key] = m
        for mid in dups:
            self.mem.delete(mid)
        return len(dups)

    def compress_old(self, days: int = 7) -> int:
        cutoff = time.time() - days * 86400
        n = 0
        for m in self.mem.get_all():
            ts = _iso_to_epoch(m.get("created_at"))
            if ts and ts < cutoff and not str(m["content"]).startswith("[Compressed]"):
                self.mem.g.update_memory(m["id"], {
                    "content": "[Compressed] " + str(m["content"])[:100] + "..."})
                n += 1
        return n

    def promote(self, threshold: float = 0.95) -> int:
        n = 0
        for m in self.mem.get_all():
            if float(m["confidence"]) >= threshold and "promoted" not in (m["tags"] or []):
                tags = list(m["tags"] or []) + ["promoted"]
                self.mem.g.update_memory(m["id"], {"tags": tags, "confidence": 1.0})
                n += 1
        return n

    def archive(self, days: int = 30) -> int:
        cutoff = time.time() - days * 86400
        n = 0
        for m in self.mem.get_all():
            ts = _iso_to_epoch(m.get("created_at"))
            if ts and ts < cutoff and "archived" not in (m["tags"] or []):
                tags = list(m["tags"] or []) + ["archived"]
                self.mem.g.update_memory(m["id"], {"tags": tags})
                n += 1
        return n

    def run_once(self) -> dict:
        return {"deduped": self.deduplicate(), "compressed": self.compress_old(),
                "promoted": self.promote(), "archived": self.archive()}
# ===AGENT4===

IGNORE_PARTS = {"__pycache__", ".git", "logs", "node_modules", "venv", "dist",
                "media", "assets", "vendor", "archive", ".venv", ".env",
                "openbrain-master", "memory-mcp", "memory-graph",
                "binance_futures_ai_bot", "binance", "_archive", ".github",
                ".pytest_cache", "data", "dist"}
WATCH_EXT = {".py", ".env", ".md", ".json", ".ts", ".yaml", ".yml", ".toml"}
WATCH_MAX_BYTES = 512 * 1024  # CBM parity: bỏ qua file đơn > 512 KiB


def _iso_to_epoch(s: str | None) -> float:
    if not s:
        return 0.0
    try:
        return time.mktime(time.strptime(str(s)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0.0


class SyncEngine:
    """Watcher: file đổi -> rebuild graph_memory.json -> reseed memory.db -> reflect."""

    def __init__(self, mem: MemoryEngine, reflect: ReflectionEngine):
        self.mem = mem
        self.reflect = reflect

    def snapshot(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for p in ROOT.rglob("*"):
            if not p.is_file() or p.suffix not in WATCH_EXT:
                continue
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            if rel in ("memory.db", "memory.db-wal", "memory.db-shm",
                       "graph_memory.json", "memory_map_data.json"):
                continue  # generated local state: không watch (tránh vòng lặp sync)
            if any(part in IGNORE_PARTS for part in p.parts):
                continue
            try:
                if p.stat().st_size > WATCH_MAX_BYTES:
                    continue
                out[rel] = p.stat().st_mtime
            except OSError:
                continue
        return out

    def diff(self, old: dict[str, float], new: dict[str, float]) -> list[str]:
        changed = [k for k, v in new.items() if old.get(k) != v]
        changed += [k for k in old if k not in new]
        return changed

    def sync(self, changed: list[str] | None = None) -> dict:
        """Đồng bộ: rebuild graph + reseed + rebuild map + reflect. Ghi 1 memory 'sync'."""
        import graph_memory
        res: dict = {"changed": len(changed or [])}
        try:
            g2 = graph_memory.build_graph()
            from pathlib import Path as _P
            _P(ROOT, "graph_memory.json").write_text(
                json.dumps(g2, ensure_ascii=False), encoding="utf-8")
            res["graph_nodes"] = g2["meta"]["n"]
            res["graph_edges"] = g2["meta"]["e"]
            res["excluded"] = g2["meta"].get("excluded_count", 0)
            res["ignored"] = g2["meta"].get("ignored_total", 0)
        except Exception as e:  # noqa: BLE001
            res["graph_error"] = str(e)[:160]
        try:
            from memory_graph import seed_from_graph
            res.update(seed_from_graph(self.mem.g))
        except Exception as e:  # noqa: BLE001
            res["seed_error"] = str(e)[:160]
        try:
            import memory_map
            m = memory_map.sync_all()
            res["map_nodes"] = m["meta"]["nodes"]
            res["map_links"] = m["meta"]["links"]
            res["map_bridges"] = m["meta"].get("code_memory_bridges", 0)
        except Exception as e:  # noqa: BLE001
            res["map_error"] = str(e)[:160]
        try:
            self.reflect.analyze_logs()
        except Exception as e:  # noqa: BLE001
            res["reflect_error"] = str(e)[:160]
        mid = observe(self.mem.g, "config", "sync",
                      what="project-sync", detail=json.dumps(res, ensure_ascii=False)[:400])
        res["memory_id"] = mid
        return res

    def watch(self, interval: int = 60) -> None:
        last = self.snapshot()
        print(f"[WATCH] monitoring {len(last)} files, interval {interval}s. Ctrl+C to stop.",
              flush=True)
        while True:
            time.sleep(interval)
            cur = self.snapshot()
            changed = self.diff(last, cur)
            if changed:
                print(f"[WATCH] {len(changed)} file(s) changed -> sync...", flush=True)
                r = self.sync(changed)
                print(f"[WATCH] sync done: {json.dumps(r, ensure_ascii=True)[:200]}", flush=True)
                last = cur
# ===AGENT5===


def build_engines(db: str | None = None):
    g = MemoryGraph(db or DB_PATH)
    g.initialize_schema()
    mem = MemoryEngine(g)
    ref = ReflectionEngine(mem)
    learn = LearningEngine(mem)
    ctx = ContextEngine(mem, learn)
    dream = DreamEngine(mem)
    sync = SyncEngine(mem, ref)
    return g, mem, ref, learn, ctx, dream, sync


def detect_changes(mem: MemoryEngine, since_minutes: int = 0) -> dict:
    """CBM-parity detect_changes: file thay đổi (mtime/git) + node liên quan trong graph."""
    import subprocess  # noqa: PLC0415
    sync = SyncEngine(mem, ReflectionEngine(mem))
    snap = sync.snapshot()
    cutoff = time.time() - since_minutes * 60 if since_minutes else None
    changed = [f for f, ts in snap.items() if cutoff is None or ts >= cutoff] if cutoff \
        else []
    git_files: list[str] = []
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            for ln in r.stdout.splitlines():
                p = ln[3:].strip().strip('"')
                if p:
                    git_files.append(p)
    except Exception:
        pass
    affected = mem.g.search_memories({"limit": 200})
    hit = [m for m in affected
           if any(f in str(m.get("content", "")) for f in (changed or git_files))]
    return {"since_minutes": since_minutes, "recent_files": changed[:40],
            "git_changed": git_files[:40],
            "affected_nodes": [m["id"] for m in hit[:40]],
            "counts": {"recent": len(changed), "git": len(git_files), "nodes": len(hit)}}


def main(argv=None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="memory_agent — openbrain engines (port)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync"); sub.add_parser("watch").add_argument("--interval", type=int, default=60)
    sub.add_parser("reflect"); sub.add_parser("dream"); sub.add_parser("stats")
    sub.add_parser("context").add_argument("query", nargs="?", default="")
    sp = sub.add_parser("skill")
    sp.add_argument("--name", required=True); sp.add_argument("--desc", default="")
    sp.add_argument("--steps", default=""); sp.add_argument("--result", choices=["ok", "fail"])
    sp = sub.add_parser("skills")
    sp = sub.add_parser("arch"); sp.add_argument("--hubs", type=int, default=12)
    sp = sub.add_parser("trace"); sp.add_argument("start"); sp.add_argument("end", nargs="?")
    sp.add_argument("--depth", type=int, default=4)
    sp = sub.add_parser("snippet"); sp.add_argument("id")
    sp = sub.add_parser("changes"); sp.add_argument("--minutes", type=int, default=0)
    sp = sub.add_parser("daemon"); sp.add_argument("--interval", type=int, default=60)
    sp.add_argument("--dream-every", type=int, default=10)
    args = ap.parse_args(argv)

    g, mem, ref, learn, ctx, dream, sync = build_engines()

    if args.cmd == "sync":
        print(json.dumps(sync.sync(), ensure_ascii=False, indent=1))
    elif args.cmd == "watch":
        sync.watch(args.interval)
    elif args.cmd == "reflect":
        r = ref.analyze_logs()
        print(json.dumps({"reflection": r["id"], "mistakes": len(r["mistakes"]),
                          "lessons": len(r["lessons"]), "patterns": len(r["patterns"]),
                          "decisions": len(r["decisions"])}, ensure_ascii=False, indent=1))
    elif args.cmd == "dream":
        print(json.dumps(dream.run_once(), indent=1))
    elif args.cmd == "context":
        print(ctx.build_context(args.query))
    elif args.cmd == "skill":
        if args.result:
            ok = learn.record_skill_result(args.name, args.result == "ok")
            print(f"skill '{args.name}' result={args.result} ok={ok}")
        else:
            mid = learn.create_skill(args.name, args.desc,
                                     [s for s in args.steps.split(";") if s])
            print(f"skill stored {mid}")
    elif args.cmd == "skills":
        for s in learn.list_skills():
            print(f"- {s.get('name')}: {str(s.get('description'))[:70]} "
                  f"(used={s.get('usage_count')}, sr={s.get('success_rate')})")
    elif args.cmd == "stats":
        print(json.dumps(g.stats(), ensure_ascii=False, indent=1))
    elif args.cmd == "arch":
        print(json.dumps(g.get_architecture(args.hubs), ensure_ascii=False, indent=1))
    elif args.cmd == "trace":
        for h in g.trace_path(args.start, args.end, max_depth=args.depth):
            pre = f"d{h['depth']} " if "depth" in h else ""
            print(f"{pre}{h['from']} -[{h['rel']}]-> {h['to']}")
    elif args.cmd == "snippet":
        s = g.snippet(args.id)
        if not s:
            print("not found")
        else:
            print(f"# {s['memory']['title']} ({s.get('file')}:{s.get('line')})")
            print(s.get("source") or "(no source linked)")
    elif args.cmd == "changes":
        print(json.dumps(detect_changes(mem, args.minutes), ensure_ascii=False, indent=1))
    elif args.cmd == "daemon":
        last = sync.snapshot()
        n = 0
        print(f"[DAEMON] sync+reflect+maint every {args.interval}s "
              f"({len(last)} files watched). Ctrl+C to stop.", flush=True)
        while True:
            time.sleep(args.interval)
            cur = sync.snapshot()
            changed = sync.diff(last, cur)
            if changed:
                r = sync.sync(changed)
                print(f"[DAEMON] synced {len(changed)} file(s): "
                      f"{json.dumps(r, ensure_ascii=True)[:180]}", flush=True)
                last = cur
            n += 1
            if n % max(args.dream_every, 1) == 0:
                d = dream.run_once()
                print(f"[DAEMON] maintenance: {json.dumps(d)}", flush=True)
                try:
                    ref.reflect(content=f"periodic reflect (cycle {n})",
                                lessons=[], session_id="daemon")
                except Exception as e:  # noqa: BLE001
                    print(f"[DAEMON] reflect warn: {e}", flush=True)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
