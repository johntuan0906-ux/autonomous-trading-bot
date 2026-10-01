"""Python port of MemoryGraph (memory-graph/ts) v0.14.0 — SQLite backend.

Faithfully mirrors ts/src/backends/sqlite.ts schema + ts/src/models.ts enums so the
trading bot STORES/CHERCHER/LINK memories (code units, trades, errors, configs)
and RECALL via the same conceptual surface as the TS CLI (`memorygraph`).

Run:
  python memory_graph.py seed
  python memory_graph.py store --type trade --title "t" --content "r=-1" --tags trade,loss
  python memory_graph.py search --query partial
  python memory_graph.py related <id>
  python memory_graph.py observe --kind trade --sym BTC --r -1.2 --won 0
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "memory.db"
GRAPH_JSON = ROOT / "graph_memory.json"

MEMORY_TYPES = ("task", "code_pattern", "problem", "solution", "project",
                "technology", "error", "fix", "command", "file_context",
                "workflow", "general", "conversation",
                "trade", "config", "concept",
                # openbrain-master types (ported; see memory-graph/openbrain-bridge.md)
                "episodic", "semantic", "procedural", "decision", "bug",
                "workspace", "reflection", "skill")

RELATIONSHIP_TYPES = (
    "CAUSES", "TRIGGERS", "LEADS_TO", "PREVENTS", "BREAKS",
    "SOLVES", "ADDRESSES", "ALTERNATIVE_TO", "IMPROVES", "REPLACES",
    "OCCURS_IN", "APPLIES_TO", "WORKS_WITH", "REQUIRES", "USED_IN",
    "BUILDS_ON", "CONTRADICTS", "CONFIRMS", "GENERALIZES", "SPECIALIZES",
    "SIMILAR_TO", "VARIANT_OF", "RELATED_TO", "ANALOGY_TO", "OPPOSITE_OF",
    "FOLLOWS", "DEPENDS_ON", "ENABLES", "BLOCKS", "PARALLEL_TO",
    "EFFECTIVE_FOR", "INEFFECTIVE_FOR", "PREFERRED_OVER", "DEPRECATED_BY",
    "VALIDATED_BY",
    "INVOLVES", "PART_OF", "EXECUTED_IN", "EXHIBITS", "ATTEMPTED_SOLUTION",
    "IN_SESSION", "MODIFIES", "CREATES", "FOUND_IN")
REL_SET = set(RELATIONSHIP_TYPES)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_type(t: str) -> str:
    return t if t in MEMORY_TYPES else "general"


def _rel(rel: str) -> str:
    return rel.upper() if rel.upper() in REL_SET else "RELATED_TO"


# ===CHUNK_ANCHOR===


class MemoryGraph:
    """SQLite-backed MemoryGraph mirroring ts MemoryDatabase (falkordblite)."""

    def __init__(self, db_path: str | os.PathLike = DB_PATH):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")

    def initialize_schema(self) -> None:
        self.conn.executescript(r"""
        CREATE TABLE IF NOT EXISTS memories(
          id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL,
          content TEXT NOT NULL, summary TEXT, tags TEXT NOT NULL DEFAULT '[]',
          importance REAL NOT NULL DEFAULT 0.5, confidence REAL NOT NULL DEFAULT 0.8,
          effectiveness REAL, usage_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_accessed TEXT,
          version INTEGER NOT NULL DEFAULT 1, updated_by TEXT, context TEXT);
        CREATE TABLE IF NOT EXISTS relationships(
          id TEXT PRIMARY KEY, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
          rel_type TEXT NOT NULL, strength REAL NOT NULL DEFAULT 0.5,
          confidence REAL NOT NULL DEFAULT 0.8, context TEXT,
          evidence_count INTEGER NOT NULL DEFAULT 1, success_rate REAL,
          created_at TEXT NOT NULL, last_validated TEXT NOT NULL,
          validation_count INTEGER NOT NULL DEFAULT 0, counter_evidence_count INTEGER NOT NULL DEFAULT 0,
          valid_from TEXT NOT NULL, valid_until TEXT,
          recorded_at TEXT NOT NULL, invalidated_by TEXT,
          FOREIGN KEY (from_id) REFERENCES memories(id) ON DELETE CASCADE,
          FOREIGN KEY (to_id) REFERENCES memories(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
        CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
        CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(rel_type);
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
          id, title, content, summary, tags, tokenize='porter unicode61');
        CREATE TRIGGER IF NOT EXISTS trg_memories_ai AFTER INSERT ON memories BEGIN
          INSERT INTO memories_fts(rowid,id,title,content,summary,tags)
          VALUES(new.rowid,new.id,new.title,new.content,COALESCE(new.summary,''),new.tags);
        END;
        CREATE TRIGGER IF NOT EXISTS trg_memories_ad AFTER DELETE ON memories BEGIN
          DELETE FROM memories_fts WHERE id=old.id;
        END;
        CREATE TRIGGER IF NOT EXISTS trg_memories_au AFTER UPDATE ON memories
          WHEN old.title IS NOT new.title OR old.content IS NOT new.content
          OR old.summary IS NOT new.summary OR old.tags IS NOT new.tags
        BEGIN
          DELETE FROM memories_fts WHERE id=old.id;
          INSERT INTO memories_fts(rowid,id,title,content,summary,tags)
          VALUES(new.rowid,new.id,new.title,new.content,COALESCE(new.summary,''),new.tags);
        END;
        """)
        self.conn.commit()
# ===CHUNK2===

    def store_memory(self, memory: dict) -> str:
        mid = memory.get("id") or str(uuid.uuid4())
        ntype = _valid_type(memory.get("type") or "general")
        tags = json.dumps([t.lower().strip() for t in (memory.get("tags") or []) if t])
        now = _now()
        self.conn.execute(
            "INSERT OR REPLACE INTO memories(id,type,title,content,summary,tags,"
            "importance,confidence,usage_count,created_at,updated_at,context) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid, ntype, memory["title"], memory["content"], memory.get("summary"),
             tags, float(memory.get("importance", 0.5)),
             float(memory.get("confidence", 0.8)),
             int(memory.get("usage_count", 0)), memory.get("created_at", now),
             memory.get("updated_at", now),
             json.dumps(memory.get("context") or {})))
        self.conn.commit()
        return mid

    def get_memory(self, mid: str, include_rels: bool = True) -> dict | None:
        row = self.conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
        if not row:
            return None
        m = dict(row)
        m["tags"] = json.loads(m["tags"])
        m["usage_count"] = m["usage_count"] + 1
        self.conn.execute("UPDATE memories SET usage_count=?, last_accessed=?, updated_at=? WHERE id=?",
                          (m["usage_count"], _now(), _now(), mid))
        self.conn.commit()
        if include_rels:
            m["relationships"] = self._relview(mid)
        return m

    def update_memory(self, mid: str, patch: dict) -> bool:
        sets, vals = [], []
        for k, v in patch.items():
            if k in ("id", "type") or k is None:
                continue
            if k == "tags":
                v = json.dumps([t.lower().strip() for t in v if t])
            sets.append(f"{k}=?"); vals.append(v)
        if not sets:
            return False
        vals.append(mid); vals.append(_now())
        self.conn.execute(f"UPDATE memories SET {','.join(sets)}, updated_at=? WHERE id=?", vals)
        self.conn.commit()
        return True

    def delete_memory(self, mid: str) -> bool:
        cur = self.conn.execute("DELETE FROM memories WHERE id=?", (mid,))
        self.conn.commit()
        return cur.rowcount > 0
# ===CHUNK3===

    def search_memories(self, query: dict) -> list[dict]:
        q = (query.get("query") or "").strip()
        types = query.get("types") or []
        min_imp = float(query.get("min_importance") or 0)
        limit = int(query.get("limit") or 50)
        conds, params = [], []
        if types:
            ph = ",".join("?" * len(types))
            conds.append(f"memories.type IN ({ph})"); params.extend(types)
        if min_imp:
            conds.append("memories.importance >= ?"); params.append(min_imp)
        if q:
            terms = [t for t in re.split(r"[^\w]+", q, flags=re.UNICODE) if t]
            terms = [t for t in terms if len(t) >= 2][:10]
            if not terms:
                terms = ["bot"]
            conds.append("memories_fts MATCH ?")
            params.insert(0, " OR ".join(terms))
            sql = ("SELECT memories.* FROM memories_fts "
                   "JOIN memories ON memories_fts.id = memories.id "
                   + ("WHERE " + " AND ".join(conds) if conds else "")
                   + " ORDER BY bm25(memories_fts) LIMIT ?")
        else:
            sql = ("SELECT memories.* FROM memories "
                   + ("WHERE " + " AND ".join(conds) if conds else "")
                   + " ORDER BY importance DESC, created_at DESC LIMIT ?")
        params.append(limit)
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["tags"] = json.loads(d.get("tags") or "[]")
            except Exception:
                d["tags"] = []
            out.append(d)
        return out

    def get_related(self, mid: str, rel_types: list[str] | None = None,
                    limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT oid, rel_type, strength FROM ("
            " SELECT to_id AS oid, rel_type, strength FROM relationships WHERE from_id=? "
            " UNION ALL SELECT from_id, rel_type, strength FROM relationships WHERE to_id=?)",
            (mid, mid)).fetchall()
        rels = [dict(r) for r in rows]
        if rel_types:
            want = {t.upper() for t in rel_types}
            rels = [r for r in rels if r["rel_type"].upper() in want]
        rels.sort(key=lambda r: r.get("strength", 0), reverse=True)
        out, seen = [], set()
        for r in rels[:limit]:
            oid = r["oid"]
            if oid in seen:
                continue
            seen.add(oid)
            m = self.get_memory(oid, include_rels=False)
            if m:
                out.append({"memory": m, "rel": r["rel_type"], "strength": r["strength"]})
        return out

    def create_relationship(self, from_id, to_id, rel_type, props: dict | None = None) -> str:
        props = props or {}
        rid = str(uuid.uuid4()); now = _now()
        self.conn.execute(
            "INSERT INTO relationships(id,from_id,to_id,rel_type,strength,confidence,"
            "context,evidence_count,created_at,last_validated,valid_from,recorded_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, from_id, to_id, _rel(rel_type), float(props.get("strength", 0.5)),
             float(props.get("confidence", 0.8)), props.get("context"),
             int(props.get("evidence_count", 1)), props.get("created_at", now),
             props.get("last_validated", now), props.get("valid_from", now),
             props.get("recorded_at", now)))
        self.conn.commit()
        return rid

    def stats(self) -> dict:
        n = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        r = self.conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        cur = self.conn.execute("SELECT type, COUNT(*) AS c FROM memories GROUP BY type").fetchall()
        return {"memories": n, "relationships": r,
                "by_type": {row["type"]: row["c"] for row in cur}, "db": self.db_path}

    def _relview(self, mid: str) -> dict:
        rows = self.conn.execute(
            "SELECT rel_type, to_id AS oid FROM relationships WHERE from_id=? "
            "UNION ALL SELECT rel_type, from_id AS oid FROM relationships WHERE to_id=?",
            (mid, mid)).fetchall()
        return {"out": [dict(r) for r in rows]}

    # ---- CBM-parity intel (codebase-memory-mcp): trace_path / get_architecture ----
    def trace_path(self, start: str, end: str | None = None, max_depth: int = 4,
                   limit: int = 200) -> list[dict]:
        """BFS theo quan hệ (thay cho CBM trace_path/trace_call_path).

        Không có `end` -> trả các hop từ `start` (call-chain quanh node).
        Có `end` -> trả 1 đường đi ngắn nhất start -> end.
        """
        adj: dict[str, list[tuple[str, str]]] = {}
        for r in self.conn.execute("SELECT from_id,to_id,rel_type FROM relationships"):
            adj.setdefault(r["from_id"], []).append((r["to_id"], r["rel_type"]))
            adj.setdefault(r["to_id"], []).append((r["from_id"], r["rel_type"]))
        if end:
            prev: dict[str, tuple[str, str] | None] = {start: None}
            q = [start]
            while q:
                cur = q.pop(0)
                if cur == end:
                    break
                for nxt, rel in adj.get(cur, []):
                    if nxt not in prev:
                        prev[nxt] = (cur, rel)
                        q.append(nxt)
            if end not in prev:
                return []
            path, cur = [], end
            while prev[cur]:
                p, rel = prev[cur]
                path.append({"from": p, "rel": rel, "to": cur})
                cur = p
            path.reverse()
            return path
        out, seen = [], {start}
        frontier = [start]
        for depth in range(1, max_depth + 1):
            nxt_frontier = []
            for node in frontier:
                for nxt, rel in adj.get(node, []):
                    if nxt in seen:
                        continue
                    seen.add(nxt)
                    nxt_frontier.append(nxt)
                    out.append({"depth": depth, "from": node, "rel": rel, "to": nxt})
                    if len(out) >= limit:
                        return out
            frontier = nxt_frontier
            if not frontier:
                break
        return out

    def get_architecture(self, top_hubs: int = 12) -> dict:
        """Tóm tắt kiến trúc (thay cho CBM get_architecture)."""
        by_type = {r["type"]: r["c"] for r in self.conn.execute(
            "SELECT type, COUNT(*) AS c FROM memories GROUP BY type ORDER BY c DESC")}
        rels = {r["rel_type"]: r["c"] for r in self.conn.execute(
            "SELECT rel_type, COUNT(*) AS c FROM relationships GROUP BY rel_type "
            "ORDER BY c DESC")}
        hubs = self.conn.execute(
            "SELECT m.id, m.type, m.title, COUNT(r.id) AS deg FROM memories m "
            "JOIN relationships r ON r.from_id=m.id OR r.to_id=m.id "
            "GROUP BY m.id ORDER BY deg DESC LIMIT ?", (top_hubs,)).fetchall()
        files = [r["id"] for r in self.conn.execute(
            "SELECT id FROM memories WHERE type IN ('technology','file_context') "
            "AND id LIKE '%.py%' ORDER BY id").fetchall()]
        return {"nodes": sum(by_type.values()), "edges": sum(rels.values()),
                "node_types": by_type, "edge_types": rels, "files": len(files),
                "top_hubs": [{"id": h["id"], "type": h["type"], "title": h["title"],
                              "degree": h["deg"]} for h in hubs]}

    def snippet(self, mid: str) -> dict:
        """Lấy 'code snippet' (thay cho CBM get_code_snippet): đọc đúng dòng của node."""
        m = self.get_memory(mid, include_rels=False)
        if not m:
            return {}
        ctx = {}
        try:
            ctx = json.loads(m.get("context") or "{}")
        except Exception:
            pass
        f = (ctx.get("files_involved") or [None])[0]
        if not f:
            return {"memory": m, "source": None}
        p = ROOT / f
        if not p.exists():
            return {"memory": m, "source": None, "error": f"missing {f}"}
        line = 0
        m2 = re.search(r":(\d+)$", m.get("content") or "")
        if m2:
            line = int(m2.group(1))
        lines = p.read_text(errors="ignore").splitlines()
        lo = max(0, line - 12) if line else 0
        hi = min(len(lines), (line + 12) if line else 24)
        return {"memory": m, "file": f, "line": line, "source": "\n".join(lines[lo:hi])}
# ===CHUNK4===


# ---- seed: nap graph_memory.json vao schema MemoryGraph ---------------------
NODE_TYPE_MAP = {"file": "technology", "def": "code_pattern", "class": "code_pattern",
                 "concept": "concept", "env": "config", "envkey": "config",
                 "field": "code_pattern", "state": "code_pattern", "error": "error"}


def seed_from_graph(g: MemoryGraph, clear: bool = True) -> dict:
    """Nạp graph_memory.json vào schema MemoryGraph (dedupe theo id ổn định).

    clear=True: xoá node seed cũ (`seed:1` trong tags) trước khi nạp lại để
    reseed/watcher không phình DB (openbrain DreamEngine parity)."""
    if not GRAPH_JSON.exists():
        return {"error": "graph_memory.json not found (run graph_memory.py first)"}
    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    if clear:
        for r in g.conn.execute(
                "SELECT id FROM memories WHERE tags LIKE '%seed:1%'").fetchall():
            g.conn.execute("DELETE FROM memories WHERE id=?", (r["id"],))
        g.conn.commit()
    id_map = {}
    n_ok = n_skip = 0
    for node in data["nodes"]:
        label = node["label"]
        mtype = NODE_TYPE_MAP.get(node.get("type"), "code_pattern")
        title = label[:200]
        content = f"{node.get('type','node')} {label} @ {node.get('file') or 'n/a'}" \
                  f":{node.get('line') or 0}"
        mid = f"{node['type']}:{label}"
        g.store_memory({"id": mid, "type": mtype, "title": title, "content": content,
                        "summary": f"{node.get('kind') or node.get('type')}"[:500],
                        "tags": [node.get("type"), node.get("file") or "root", "seed:1"],
                        "importance": 0.6, "confidence": 0.9,
                        "context": {"project_path": str(ROOT),
                                    "files_involved": [node.get("file")]}})
        id_map[node["id"]] = mid
        n_ok += 1
    rels = 0
    seen_rel: set[tuple[str, str, str]] = set()
    for l in data["links"]:
        src, dst = id_map.get(l["source"]), id_map.get(l["target"])
        if not src or not dst:
            continue
        key = (src, dst, (l.get("label") or "RELATED_TO").upper())
        if key in seen_rel:
            n_skip += 1
            continue
        seen_rel.add(key)
        try:
            g.create_relationship(src, dst, l.get("label") or "RELATED_TO",
                                  {"strength": 0.7, "confidence": 0.9,
                                   "context": "seeded from graph_memory.json"})
            rels += 1
        except Exception:
            n_skip += 1
    return {"memories": n_ok, "relationships": rels, "skipped": n_skip}


# ---- ingest_traces (memory-mcp RUNTIME_TRACE_MODEL parity) ------------------
# Runtime facts KHÔNG patch CALLS tĩnh, KHÔNG tạo node tĩnh, KHÔNG persist vào
# bảng relationships mặc định. Lưu ở bảng runtime_* riêng + đọc qua overlay
# opt-in (runtime_overlay=True). Đây là hợp đồng kiến trúc của CBM.
RUNTIME_SCHEMA = """
CREATE TABLE IF NOT EXISTS runtime_spans(
  span_id TEXT PRIMARY KEY, caller TEXT NOT NULL, callee TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 1, project TEXT NOT NULL DEFAULT 'bot',
  generation INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runtime_head(project TEXT PRIMARY KEY, generation INTEGER NOT NULL);
"""


def ingest_traces(g: MemoryGraph, project: str = "bot",
                  traces: list[dict] | None = None) -> dict:
    """Validate + count runtime traces; KHÔNG tạo edge tĩnh (CBM parity).

    Idempotent theo span_id: cùng payload retry không đổi generation;
    payload khác dưới cùng span_id -> conflict, không mutate."""
    traces = traces or []
    g.conn.executescript(RUNTIME_SCHEMA)
    row = g.conn.execute("SELECT generation FROM runtime_head WHERE project=?",
                         (project,)).fetchone()
    gen = int(row[0]) if row else 1
    accepted = dup = conflicts = 0
    for t in traces:
        _c = t.get("caller"); _e = t.get("callee")
        sid = str(t.get("span_id") or (str(_c) + "->" + str(_e)))
        caller, callee = str(t.get("caller", "?")), str(t.get("callee", "?"))
        cnt = int(t.get("count", 1) or 1)
        old = g.conn.execute("SELECT caller,callee,count FROM runtime_spans "
                             "WHERE span_id=? AND project=?", (sid, project)).fetchone()
        if old:
            if old["caller"] == caller and old["callee"] == callee:
                dup += 1
            else:
                conflicts += 1
            continue
        g.conn.execute("INSERT INTO runtime_spans(span_id,caller,callee,count,"
                       "project,generation,created_at) VALUES(?,?,?,?,?,?,?)",
                       (sid, caller, callee, cnt, project, gen, _now()))
        accepted += 1
    g.conn.execute("INSERT OR REPLACE INTO runtime_head(project,generation) VALUES(?,?)",
                   (project, gen))
    g.conn.commit()
    return {"status": "accepted", "traces_received": len(traces),
            "accepted": accepted, "duplicates": dup, "conflicts": conflicts,
            "generation": gen,
            "note": "runtime-only overlay; static CALLS unchanged"}


def runtime_overlay(g: MemoryGraph, symbol: str, project: str = "bot",
                    max_depth: int = 2) -> list[dict]:
    """Opt-in RUNTIME_CALL overlay: caller/callee quanh symbol ở generation hiện tại."""
    g.conn.executescript(RUNTIME_SCHEMA)
    out: list[dict] = []
    seen = {symbol}
    frontier = [symbol]
    for depth in range(1, max_depth + 1):
        nxt: list[str] = []
        for node in frontier:
            for r in g.conn.execute(
                    "SELECT caller,callee,count FROM runtime_spans "
                    "WHERE project=? AND (caller=? OR callee=?) LIMIT 100",
                    (project, node, node)):
                other = r["callee"] if r["caller"] == node else r["caller"]
                out.append({"depth": depth, "from": node, "rel": "RUNTIME_CALL",
                            "to": other, "count": r["count"]})
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
        if not frontier:
            break
    return out


# ---- observe: bot ghi memory khi mo/dong lenh / gap loi --------------------
def observe(g: MemoryGraph, kind: str, sym: str, **kw) -> str:
    """Ghi 1 Memory tu runtime bot (trade close / error / config change) + link."""
    if kind == "trade":
        title = f"TRADE {sym} {kw.get('reason', '?')} r={kw.get('r', 0):+.2f}"
        content = (f"symbol={sym} reason={kw.get('reason')} r={kw.get('r')} "
                   f"won={kw.get('won')} pnl={kw.get('pnl')} "
                   f"partial={kw.get('partial')} mfe_r={kw.get('mfe_r')}")
        mtype, tags = "trade", ["trade", sym, kw.get("reason") or "?"]
        imp = 0.9 if not kw.get("won") else 0.7
    elif kind == "error":
        title = f"ERROR {sym or 'bot'} {kw.get('what', '')[:80]}"
        content = kw.get("detail") or str(kw)
        mtype, tags, imp = "error", ["error", sym or "bot"], 0.95
    elif kind == "config":
        title = f"CONFIG {kw.get('what', 'change')}"
        content = json.dumps(kw, default=str)
        mtype, tags, imp = "config", ["config"], 0.8
    else:
        title, content, mtype, tags, imp = f"{kind} {sym}", str(kw), "general", [kind], 0.5
    mid = g.store_memory({"type": mtype, "title": title, "content": content,
                          "tags": [t for t in tags if t], "importance": imp,
                          "context": {"project_path": str(ROOT),
                                      "timestamp": _now(),
                                      "additional_metadata": kw}})
    # gan vao concept anchor phu hop de truy ve nhanh
    anchor = ("PositionManagement" if kind == "trade" else
              "RiskKillSwitch" if kind == "error" else "SweepOptimalConfig")
    try:
        g.create_relationship(mid, f"concept:{anchor}", "APPLIES_TO",
                              {"strength": 0.8, "confidence": 0.9,
                               "context": f"auto-observe {kind}"})
    except Exception:
        pass
    return mid
# ===CHUNK5===


def _print_mem(m: dict) -> None:
    rels = m.pop("relationships", None)
    print(f"[{m['type']}] {m['id']}")
    print(f"  title   : {m['title']}")
    print(f"  content : {m['content'][:160]}")
    print(f"  tags    : {','.join(m['tags'] or [])}")
    print(f"  imp/conf: {m['importance']}/{m['confidence']}  n_used={m['usage_count']}")
    if rels and rels.get("out"):
        for r in rels["out"][:8]:
            print(f"  -> {r['rel_type']} {r['oid']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MemoryGraph (Python port) CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("seed"); sp.add_argument("--out", default="memory.db")
    sp = sub.add_parser("store")
    sp.add_argument("--type", default="general"); sp.add_argument("--title", required=True)
    sp.add_argument("--content", required=True); sp.add_argument("--tags", default="")
    sp.add_argument("--importance", type=float, default=0.5)
    sp.add_argument("--summary", default="")
    sp = sub.add_parser("get"); sp.add_argument("id")
    sp = sub.add_parser("search")
    sp.add_argument("--query", default=""); sp.add_argument("--types", default="")
    sp.add_argument("--min-importance", type=float, default=0.0)
    sp.add_argument("--limit", type=int, default=20)
    sp = sub.add_parser("related"); sp.add_argument("id"); sp.add_argument("--limit", type=int, default=20)
    sp = sub.add_parser("recall"); sp.add_argument("--query", required=True)
    sp.add_argument("--types", default=""); sp.add_argument("--limit", type=int, default=20)
    sp = sub.add_parser("update"); sp.add_argument("id")
    sp.add_argument("--title", default=None); sp.add_argument("--content", default=None)
    sp.add_argument("--tags", default=None); sp.add_argument("--importance", type=float, default=None)
    sp.add_argument("--summary", default=None)
    sp = sub.add_parser("delete"); sp.add_argument("id")
    sp = sub.add_parser("link"); sp.add_argument("from_id"); sp.add_argument("to_id")
    sp.add_argument("rel_type"); sp.add_argument("--strength", type=float, default=0.5)
    sp.add_argument("--context", default="")
    sp = sub.add_parser("observe"); sp.add_argument("--kind", default="trade")
    sp.add_argument("--sym", default=""); sp.add_argument("--r", type=float, default=0.0)
    sp.add_argument("--won", type=int, default=0); sp.add_argument("--pnl", type=float, default=0.0)
    sp.add_argument("--reason", default="?"); sp.add_argument("--partial", type=int, default=0)
    sp.add_argument("--mfe-r", type=float, default=0.0)
    sp = sub.add_parser("ingest"); sp.add_argument("--project", default="bot")
    sp.add_argument("--traces", default="[]",
                    help="JSON list [{caller,callee,count,span_id?}] (CBM ingest_traces parity)")
    sp = sub.add_parser("overlay"); sp.add_argument("symbol")
    sp.add_argument("--project", default="bot"); sp.add_argument("--depth", type=int, default=2)
    sp = sub.add_parser("check"); sp.add_argument("path", nargs="?", default="")
    sp.add_argument("--limit", type=int, default=20)
    sp = sub.add_parser("changes"); sp.add_argument("--minutes", type=int, default=0)
    sp = sub.add_parser("arch"); sp.add_argument("--hubs", type=int, default=12)
    sp = sub.add_parser("snippet"); sp.add_argument("id")
    sub.add_parser("stats")
    args = ap.parse_args(argv)

    g = MemoryGraph(args.out if hasattr(args, "out") else DB_PATH)
    g.initialize_schema()

    if args.cmd == "seed":
        print(json.dumps(seed_from_graph(g), indent=1))
    elif args.cmd == "store":
        mid = g.store_memory({"type": args.type, "title": args.title,
                              "content": args.content, "summary": args.summary,
                              "tags": [t for t in args.tags.split(",") if t],
                              "importance": args.importance})
        print(f"stored {mid}")
    elif args.cmd == "get":
        m = g.get_memory(args.id)
        if not m:
            print("not found"); return 1
        _print_mem(m)
    elif args.cmd == "search":
        types = [t for t in args.types.split(",") if t]
        rows = g.search_memories({"query": args.query, "types": types,
                                  "min_importance": args.min_importance,
                                  "limit": args.limit})
        for m in rows:
            print(f"[{m['type']}] {m['id']}  imp={m['importance']}  {m['title'][:70]}")
        print(f"({len(rows)} ket qua)")
    elif args.cmd == "related":
        for item in g.get_related(args.id, limit=args.limit):
            m = item["memory"]
            print(f"-{item['rel']}-> [{m['type']}] {m['id']}  {m['title'][:70]}")
    elif args.cmd == "recall":
        types = [t for t in args.types.split(",") if t]
        rows = g.search_memories({"query": args.query, "types": types,
                                  "limit": args.limit})
        for m in rows:
            print(f"[{m['type']}] {m['id']}  imp={m['importance']}  {m['title'][:70]}")
        print(f"({len(rows)} ket qua)")
    elif args.cmd == "update":
        patch = {k: v for k, v in
                 {"title": args.title, "content": args.content,
                  "summary": args.summary}.items() if v is not None}
        if args.tags is not None:
            patch["tags"] = json.dumps([t for t in args.tags.split(",") if t])
        if args.importance is not None:
            patch["importance"] = args.importance
        print("updated" if g.update_memory(args.id, patch) else "not found")
    elif args.cmd == "delete":
        print("deleted" if g.delete_memory(args.id) else "not found")
    elif args.cmd == "link":
        rid = g.create_relationship(args.from_id, args.to_id, args.rel_type,
                                    {"strength": args.strength, "context": args.context})
        print(f"linked {rid}")
    elif args.cmd == "observe":
        mid = observe(g, args.kind, args.sym,
                      r=args.r, won=bool(args.won), pnl=args.pnl,
                      reason=args.reason, partial=bool(args.partial), mfe_r=args.mfe_r)
        print(f"observed {mid}")
    elif args.cmd == "ingest":
        try:
            traces = json.loads(args.traces)
        except Exception as e:  # noqa: BLE001
            print(f"bad --traces JSON: {e}"); return 1
        print(json.dumps(ingest_traces(g, args.project, traces), indent=1))
    elif args.cmd == "overlay":
        for h in runtime_overlay(g, args.symbol, args.project, args.depth):
            print(f"d{h['depth']} {h['from']} -[{h['rel']} x{h.get('count',1)}]-> {h['to']}")
    elif args.cmd == "check":
        # CBM check_index_coverage parity: path có trong graph? files liên quan?
        q = (args.path or "").strip()
        cov = g.search_memories({"query": q, "limit": args.limit}) if q else []
        try:
            import graph_memory as _gm
            _g = _gm.build_graph()
            in_graph = any(q in n.get("file", "") or q == n.get("label")
                           for n in _g["nodes"]) if q else True
            print(json.dumps({"path": q, "in_static_graph": in_graph,
                              "related_memories": len(cov),
                              "graph_nodes": _g["meta"]["n"],
                              "graph_edges": _g["meta"]["e"],
                              "excluded": _g["meta"].get("excluded_count", 0)},
                             ensure_ascii=False, indent=1))
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"path": q, "related_memories": len(cov),
                              "graph_error": str(e)[:160]}, indent=1))
    elif args.cmd == "changes":
        import subprocess
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
        print(json.dumps({"git_changed": git_files[:40],
                          "count": len(git_files)}, ensure_ascii=False, indent=1))
    elif args.cmd == "arch":
        print(json.dumps(g.get_architecture(args.hubs), ensure_ascii=False, indent=1))
    elif args.cmd == "snippet":
        s = g.snippet(args.id)
        if not s:
            print("not found")
        else:
            print(f"# {s['memory']['title']} ({s.get('file')}:{s.get('line')})")
            print(s.get("source") or "(no source linked)")
    elif args.cmd == "stats":
        print(json.dumps(g.stats(), indent=1))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

