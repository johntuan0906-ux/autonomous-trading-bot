"""Interactive Graph Memory Map â€” knowledge map for the trading bot codebase.

Scans .py / .env / logs, builds a node/edge graph, exports:
  - graph_memory.json : raw graph
  - graph_memory.html : self-contained vanilla-JS force-directed viewer (no CDN)

Run:  python graph_memory.py            # build files
      python graph_memory.py --serve     # also start http.server and open browser
"""
from __future__ import annotations

import argparse
import json
import re
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_ignore_file(name: str) -> list[str]:
    """Đọc .cbmignore / .gitignore ở root (gitignore-style đơn giản)."""
    f = ROOT / name
    pats: list[str] = []
    if f.exists():
        for ln in f.read_text(errors="ignore").splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                pats.append(ln)
    return pats


def _ignore_match(pat: str, rel: str, is_dir: bool) -> bool:
    """So khớp gitignore-style đơn giản: *, ?, **, tiền tố dir, neo root (/), phủ định (!)."""
    neg = pat.startswith("!")
    if neg:
        pat = pat[1:]
    anchored = pat.startswith("/")
    if anchored:
        pat = pat[1:]
    dir_only = pat.endswith("/")
    if dir_only:
        pat = pat[:-1]
    if dir_only and not is_dir and not rel.startswith(pat + "/"):
        res = False
    elif "/" not in pat.rstrip("*?[]"):
        import fnmatch
        res = fnmatch.fnmatch(rel.split("/")[0], pat) if anchored \
            else any(fnmatch.fnmatch(seg, pat) for seg in rel.split("/"))
    else:
        import fnmatch
        res = fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.rstrip("/") + "/*")
        if pat.startswith("**/"):
            res = res or fnmatch.fnmatch(rel, pat[3:]) or any(
                fnmatch.fnmatch(seg, pat[3:]) for seg in rel.split("/"))
    return (not res) if neg else res


class _IgnoreStack:
    """Discovery layers theo memory-mcp/discover: builtin skip -> .gitignore ->
    nested .gitignore -> .cbmignore -> suffix/size. Phủ định (!) cứu được path."""

    # builtin skip (layer 1) — khớp CBM ALWAYS_SKIP + dự án
    SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", ".env", "node_modules",
                 "logs", "data", "dist", "media", "assets", "vendor", "archive",
                 ".pytest_cache", ".github", "binance", "_archive",
                 "openbrain-master", "memory-mcp", "memory-graph", "binance_futures_ai_bot"}
    # safety core: negation không cứu được (CBM parity)
    SAFETY_CORE = {".git", "node_modules"}
    SKIP_SUFFIX = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                   ".zip", ".7z", ".rar", ".db", ".db-wal", ".db-shm", ".o",
                   ".min.js", ".lock"}
    MAX_FILE_BYTES = 512 * 1024  # 512 KiB cap/file (CBM parity)

    def __init__(self) -> None:
        self.root_git = _load_ignore_file(".gitignore")
        self.cbm = _load_ignore_file(".cbmignore")
        self.nested: dict[str, list[str]] = {}
        for gi in sorted(ROOT.rglob(".gitignore")):
            try:
                rel = str(gi.parent.relative_to(ROOT)).replace("\\", "/")
            except ValueError:
                continue
            if rel == ".":
                continue
            pats = [l.strip() for l in gi.read_text(errors="ignore").splitlines()
                    if l.strip() and not l.strip().startswith("#")]
            if pats:
                self.nested[rel] = pats
        self.excluded_dirs: list[str] = []
        self.ignored_files: list[tuple[str, str]] = []  # (rel, reason)

    def _layer(self, pats: list[str], rel: str, is_dir: bool) -> bool | None:
        """Trả True=skip, False=un-skip(negation), None=không match."""
        decision: bool | None = None
        for pat in pats:
            if _ignore_match(pat, rel, is_dir):
                decision = not pat.startswith("!")
        return decision

    def skip_dir(self, rel: str) -> bool:
        name = rel.split("/")[-1]
        if name in self.SAFETY_CORE:
            return True
        if name in self.SKIP_DIRS:
            # negation trong .cbmignore cứu được (trừ safety core)
            if self._layer(self.cbm, rel, True) is False:
                return False
            self.excluded_dirs.append(rel)
            return True
        d = self._layer(self.root_git, rel, True)
        if d is True:
            self.excluded_dirs.append(rel)
            return True
        for prefix, pats in self.nested.items():
            if rel == prefix or rel.startswith(prefix + "/"):
                sub = rel[len(prefix) + 1:] if rel != prefix else ""
                if self._layer(pats, sub or name, True) is True:
                    self.excluded_dirs.append(rel)
                    return True
        if self._layer(self.cbm, rel, True) is True:
            self.excluded_dirs.append(rel)
            return True
        return False

    def skip_file(self, rel: str, size: int = 0) -> str | None:
        """Trả reason string nếu skip, None nếu index. Negation cứu được."""
        low = rel.lower()
        if any(low.endswith(s) for s in self.SKIP_SUFFIX):
            return "ignored-suffix"
        if size > self.MAX_FILE_BYTES:
            return "size-cap"
        d = self._layer(self.root_git, rel, False)
        if d is True:
            return "gitignore"
        for prefix, pats in self.nested.items():
            if rel.startswith(prefix + "/"):
                if self._layer(pats, rel[len(prefix) + 1:], False) is True:
                    return "gitignore-nested"
        c = self._layer(self.cbm, rel, False)
        if c is True:
            return "cbmignore"
        return None


SKIP_DIRS = _IgnoreStack.SKIP_DIRS  # giữ tương thích import cũ
PY_DEF_RE = re.compile(r"^(def|async def|class)\s+([A-Za-z_][\w\.]*)")
CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\(")
PY_KEYWORDS = {"def", "class", "if", "elif", "else", "for", "while", "return",
               "import", "from", "print", "len", "range", "super", "self",
               "isinstance", "hasattr", "getattr", "setattr", "str", "int",
               "float", "list", "dict", "set", "tuple", "open", "max", "min",
               "sum", "abs", "round", "sorted", "enumerate", "zip", "map",
               "filter", "any", "all", "append", "extend", "join", "split",
               "format", "read", "write", "close", "exit", "main", "time",
               "sleep", "json", "re", "os", "sys"}


def _strip_py_noise(text: str) -> str:
    """Bỏ string literal + comment để CALLS không match nhiễu (CBM AST parity)."""
    text = re.sub(r'"""[\s\S]*?"""', " ", text)
    text = re.sub(r"'''[\s\S]*?'''", " ", text)
    text = re.sub(r'"(?:[^"\\]|\\.)*"', '"s"', text)
    text = re.sub(r"'(?:[^'\\]|\\.)*'", "'s'", text)
    return "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())
ENV_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=")
FIELD_RE = re.compile(r"(\w+)\s*:\s*[\w\[\].,]+?=\s*field\(")
IMP_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))")

# Curated concept anchors linking multiple modules (the "memories").
CONCEPT_ANCHORS = {
    "PositionManagement": ["trade_mgmt.py:manage_trade", "trade_mgmt.py:manage",
        "trade_mgmt.py:trade_result", "bot.py:_monitor", ".env:PARTIAL_AT_R",
        ".env:BE_AT_R", ".env:TRAIL_ATR_MULT"],
    "SweepOptimalConfig": [".env:SL_ATR_MULT", ".env:TP_ATR_MULT", ".env:MAX_DAILY_LOSS_PCT",
        "config.py:sl_atr_mult", "config.py:tp_atr_mult", "config.py:partial_at_r",
        "config.py:be_at_r", "config.py:trail_atr_mult", "sweep.py:grid", "backtest.py:verdict"],
    "StrategyABC": ["strategy.py:classify_strategy", "strategy.py:bump", "strategy.py:report",
        "turbo_demo.py:strat_bump", "strategy.py:B_BREAKOUT_RETEST",
        "strategy.py:D_RANGE_REVERSAL"],
    "RiskKillSwitch": ["risk.py:KillSwitch", "risk.py:register_close", "risk.py:check",
        "bot.py:_flatten", ".env:MAX_DAILY_LOSS_PCT"],
    "LearnerFeedback": ["learner.py:OnlineLearner.update", "learner.py:extract_features",
        "journal.py:log_trade", "turbo_demo.py:_learner", "trade_mgmt.py:trade_result",
        "strategy.py:bump"],
    "ScanRankOpen": ["ranking.py:rank_markets", "ranking.py:sentiment_veto", "ranking.py:Candidate",
        "bot.py:_scan_and_maybe_open", "indicators.py:technical_score"],
    "TradeLifecycleStates": ["trade_mgmt.py:HOLD", "trade_mgmt.py:PARTIAL", "trade_mgmt.py:BE",
        "trade_mgmt.py:TRAIL", "trade_mgmt.py:EXIT_SL", "trade_mgmt.py:EXIT_TP",
        "bot.py:last_exits", "turbo_demo.py:last_exits"],
    

    "ExecutionLayer": ["exchange.py:BinanceFutures", "exchange.py:market_entry"
        "exchange.py:close_position", "exchange.py:stop_tp_orders"
        "portfolio.py:Position", "portfolio.py:PortfolioManager"
        "risk.py:position_size", "risk.py:atr_levels"],
}


def _short(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


_IGN: _IgnoreStack | None = None


def _ign() -> _IgnoreStack:
    global _IGN
    if _IGN is None:
        _IGN = _IgnoreStack()
    return _IGN


def _code_files() -> list[Path]:
    """Walk có prune theo ignore-stack (CBM discover parity): skip dir +
    báo excluded dirs + ignored files thay vì duyệt mù toàn cây."""
    ig = _ign()
    out: list[Path] = []
    for p in sorted(ROOT.rglob("*.py")):
        try:
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            continue
        parts = rel.split("/")[:-1]
        pruned = False
        for i in range(len(parts)):
            if ig.skip_dir("/".join(parts[:i + 1])):
                pruned = True
                break
        if pruned:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        reason = ig.skip_file(rel, size)
        if reason:
            ig.ignored_files.append((rel, reason))
            continue
        out.append(p)
    return out


def _is_code(p: Path) -> bool:
    try:
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return False
    if p.suffix != ".py":
        return False
    parts = rel.split("/")[:-1]
    ig = _ign()
    return not any(ig.skip_dir("/".join(parts[:i + 1])) for i in range(len(parts))) \
        and ig.skip_file(rel, 0) is None


def _defs(p: Path):
    out = []
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return out
    for i, line in enumerate(text.splitlines(), 1):
        m = PY_DEF_RE.match(line.lstrip())
        if m:
            out.append((m.group(1), m.group(2), i))
    return out


def _config_fields():
    f = ROOT / "config.py"
    fields, cur_cls = [], None
    for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
        m = re.match(r"^class\s+(\w+)", line)
        if m:
            cur_cls = m.group(1)
        mf = FIELD_RE.search(line)
        if mf and cur_cls == "Settings":
            fields.append((cur_cls, mf.group(1), i))
    return fields


def _env_keys():
    f = ROOT / ".env"
    keys = []
    if f.exists():
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            m = ENV_RE.match(line.strip())
            if m:
                keys.append((m.group(1), i))
    return keys


def _state_refs():
    """TÃ¬m cÃ¡c xÃ¢u tráº¡ng thÃ¡i/lydo quáº£n lÃ½ lá»‡nh trong code -> node liÃªn káº¿t."""
    refs = []
    for fn in ("trade_mgmt.py",):
        f = ROOT / fn
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for m in re.finditer(r"\"(HOLD|PARTIAL|BE|TRAIL|EXIT_SL|EXIT_TP)\"", line):
                refs.append((fn, m.group(1), i))
    # collapse duplicate (file,kind,line not needed)
    return [(f"{fn}", k, ln) for fn, k, ln in refs]


def build_graph() -> dict:
    nodes, links = [], []
    N = {}
    ig = _ign()

    def add(key, label, ntype, **extra):
        nodes.append({"id": key, "label": label, "type": ntype, **extra})

    def link(a, b, lbl=""):
        links.append({"source": a, "target": b, "label": lbl})

    # CBM ĐÚNG: nested .cbmignore KHÔNG đọc (chỉ root). Nested .gitignore đọc
    # relative theo dir của nó. Discovery prune dir trước khi duyệt file.
    def _walk_py() -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        stack: list[str] = [""]
        while stack:
            rel_dir = stack.pop()
            abs_dir = ROOT if not rel_dir else ROOT / rel_dir
            try:
                entries = sorted(abs_dir.iterdir(), key=lambda x: x.name)
            except OSError:
                continue
            for e in entries:
                rel = (rel_dir + "/" + e.name).lstrip("/") if rel_dir else e.name
                if e.is_dir():
                    if ig.skip_dir(rel):
                        continue
                    stack.append(rel)
                elif e.suffix == ".py":
                    try:
                        size = e.stat().st_size
                    except OSError:
                        continue
                    reason = ig.skip_file(rel, size)
                    if reason:
                        ig.ignored_files.append((rel, reason))
                        continue
                    out.append((rel, size))
        return sorted(out)

    for rel, _size in _walk_py():
        p = ROOT / rel
        short = _short(p)
        add(short, short, "file", path=str(p))

    env = ROOT / ".env"
    if env.exists():
        add(".env", ".env", "env", path=str(env))

    # def/class -> file  (+ CALLS giữa def trong cùng dự án — CBM pass_calls parity)
    _def_names: dict[str, list[str]] = {}  # name -> [kid]
    _def_body: dict[str, str] = {}
    _py_files: list[Path] = [ROOT / rel for rel, _s in _walk_py()]
    for p in _py_files:
        short = _short(p)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for kind, name, ln in _defs(p):
            kid = f"{short}::{name}"
            if kind == "class":
                add(kid, name, "class", file=short, line=ln, kind=kind)
            else:
                add(kid, name, "def", file=short, line=ln, kind=kind)
            link(short, kid, "defines")
            _def_names.setdefault(name, []).append(kid)
            _def_body[kid] = text
    for kid, body in _def_body.items():
        seen_calls: set[str] = set()
        for m in CALL_RE.finditer(_strip_py_noise(body)):
            callee = m.group(1)
            if callee in PY_KEYWORDS or callee not in _def_names:
                continue
            if callee in seen_calls:
                continue
            seen_calls.add(callee)
            for tgt in _def_names[callee]:
                if tgt != kid:
                    link(kid, tgt, "CALLS")

    # imports: file -> module.py
    for p in _py_files:
        short = _short(p)
        for line in p.read_text(errors="ignore").splitlines():
            m = IMP_RE.match(line)
            if not m:
                continue
            mod = (m.group(1) or m.group(2) or "").split(".")[0]
            tgt = f"{mod}.py"
            if (ROOT / tgt).exists():
                link(short, tgt, "import")

    # config fields
    for cls, fname, ln in _config_fields():
        kid = f"config.py::{fname}"
        add(kid, fname, "field", file="config.py", line=ln)
        link("config.py", kid, "field")
        link(kid, f"ENV:{fname.upper()}", "env")

    # env keys
    for key, ln in _env_keys():
        add(f"ENV:{key}", key, "envkey", file=".env", line=ln)

    # lifecycle state refs (HOLD/PARTIAL/BE/TRAIL/EXIT_*)
    for fn, st, ln in _state_refs():
        kid = f"trade_mgmt.py::{st}"
        if kid not in N:
            add(kid, st, "state", file="trade_mgmt.py", line=ln)
            N[kid] = True
        link("trade_mgmt.py::manage", kid, "emits")

    # curated concept anchors
    for concept, edgelist in CONCEPT_ANCHORS.items():
        add(concept, concept, "concept")
        for ref in edgelist:
            where, what = ref.split(":", 1)
            if where == ".env":
                tgt = f"ENV:{what}"
            else:
                tgt = f"{where}::{what}"
            link(concept, tgt, where)

    # dedupe
    seen, uniq = set(), []
    for l in links:
        k = (l["source"], l["target"], l["label"])
        if k not in seen:
            seen.add(k)
            uniq.append(l)
    links = uniq

    # --- semantic edges (CBM parity): SIMILAR_TO (MinHash-LSH tên hàm) +
    #     SEMANTICALLY_RELATED (chia sẻ từ vựng domain, khác tên) ---
    try:
        _add_semantic_edges(nodes, links)
    except Exception:
        pass

    ig = _ign()
    return {"nodes": nodes, "links": links,
            "meta": {"root": str(ROOT), "n": len(nodes), "e": len(links),
                     "excluded_dirs": sorted(set(ig.excluded_dirs))[:25],
                     "excluded_count": len(set(ig.excluded_dirs)),
                     "ignored_files": [{"path": p, "reason": r}
                                       for p, r in ig.ignored_files[:200]],
                     "ignored_total": len(ig.ignored_files)}}


def _tok(s: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", re.sub(r"(?=[A-Z])", " ", s).lower()))


def _minhash(tokens: set[str], k: int = 32) -> list[int]:
    import hashlib
    return sorted(int(hashlib.md5(f"{k}:{t}".encode()).hexdigest(), 16)
                  % (2 ** 31 - 1) for t in tokens)[:k]


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / max(len(a | b), 1)


def _add_semantic_edges(nodes: list[dict], links: list[dict]) -> None:
    """MinHash-LSH gần đúng trên token tên def/class (~CBM SIMILAR_TO) +
    chia sẻ từ vựng domain quản lý lệnh/rủi ro (~CBM SEMANTICALLY_RELATED)."""
    DOMAIN = {"trade", "position", "partial", "risk", "stop", "trail", "entry",
              "exit", "signal", "scan", "rank", "strategy", "backtest", "sweep",
              "monitor", "manage", "kill", "switch", "atr", "sync", "reflect"}
    defs = [n for n in nodes if n.get("type") in ("def", "class")]
    toks = {n["id"]: _tok(n.get("label", "")) | _tok(n.get("file", "")) for n in defs}
    have = {(l["source"], l["target"]) for l in links}
    for i in range(len(defs)):
        for j in range(i + 1, len(defs)):
            a, b = defs[i]["id"], defs[j]["id"]
            if (a, b) in have or (b, a) in have:
                continue
            ta, tb = toks[a], toks[b]
            if not ta or not tb:
                continue
            ha, hb = set(_minhash(ta)), set(_minhash(tb))
            sim = len(ha & hb) / max(len(ha | hb), 1)
            jac = _jaccard(ta, tb)
            if sim >= 0.30 or jac >= 0.55:
                links.append({"source": a, "target": b, "label": "SIMILAR_TO"})
            elif (ta & DOMAIN) and (tb & DOMAIN) and (ta & tb & DOMAIN):
                links.append({"source": a, "target": b,
                              "label": "SEMANTICALLY_RELATED"})


HTML_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Graph Memory</title>
<style>body{margin:0;font-family:sans-serif;background:#0f1320;color:#e6e9ff}
#app{display:flex;height:100vh}
#graph{flex:1;position:relative;min-width:0}
#graph canvas{display:block;width:100%;height:100%}
#side{width:360px;max-width:42%;background:#151a2b;border-left:1px solid #2a3142;padding:14px;box-sizing:border-box;overflow:auto;font-size:13px}
.bar{position:absolute;left:8px;top:8px;z-index:2;background:#151a2b;padding:8px;border:1px solid #2a3142;border-radius:6px}
.bar input,.bar button,.bar select{background:#1f2739;color:#cfdcff;border:1px solid #3a4a6b;border-radius:4px;font-size:12px}
.bar input{width:150px}.bar button{cursor:pointer}
.bar button:hover{background:#2d3a5a}
.tags{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
.tag{background:#24304c;border:1px solid #3b4f7a;border-radius:10px;padding:2px 8px;font-size:11px;cursor:pointer;white-space:nowrap}
.tag.sel{background:#3b6fd1}
.node-title{font-weight:700;margin-bottom:6px;font-size:14px}
.node-meta{color:#98a1c0;margin:3px 0}
.node-edges{margin-top:8px}.node-edges div{color:#7f9bb6;margin:2px 0}
</style></head>
<body>
<div id="app"><div id="graph"></div>
<div id="side"><div class="bar">
  <input id="search" placeholder="tim node..."><button id="reset">dat lai</button>
  <div class="tags" id="types"></div>
</div>
<div id="info"><div class="node-title">Graph Memory</div>
<div class="node-meta">Click node, keo de di chuyen.</div></div></div></div>
<script>
const G = __GRAPH__;
const cv = document.createElement('canvas');
cv.style.cssText='display:block;width:100%;height:100%';
document.getElementById('graph').appendChild(cv);
const c = cv.getContext('2d');
function resize(){cv.width=cv.clientWidth;cv.height=cv.clientHeight;}
window.addEventListener('resize',resize); resize();
const byId = Object.fromEntries(G.nodes.map(n=>[n.id,n]));
const R=8; let nodes, links, N={};
const typeColor={file:'#5fb3ff',def:'#9cffb3',class:'#ffa366',concept:'#d96cff',env:'#ff9a9e',
  envkey:'#ff9a9e',field:'#ffd46b',error:'#ff6b6b',state:'#f7a561',node:'#789bff'};
let showTypes=new Set(G.nodes.map(n=>n.type));
let drag=null,selected=null;
function fit(){cv.width=cv.clientWidth*devicePixelRatio;cv.height=cv.clientHeight*devicePixelRatio;c.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);}
addEventListener('resize',()=>{fit();});
function setup(){
  fit();
  const W=cv.clientWidth,H=cv.clientHeight;
  nodes=G.nodes.map(n=>({id:n.id,label:n.label,type:n.type,fx:-1,fy:-1,
    x:Math.random()*(W-120)+60,y:Math.random()*(H-120)+60,vx:0,vy:0}));
  links=G.links; for(const n of nodes)N[n.id]=n;
  G.deg={}; for(const l of links){G.deg[l.source]=(G.deg[l.source]||0)+1;G.deg[l.target]=(G.deg[l.target]||0)+1;}
  // Can giua khoi do thi: dua centroid ve tam man hinh (forceCenter W/2,H/2)
  let sx=0,sy=0; for(const n of nodes){sx+=n.x;sy+=n.y;}
  if(nodes.length){sx/=nodes.length;sy/=nodes.length;
    for(const n of nodes){n.x+=W/2-sx;n.y+=H/2-sy;}}
}
setup();
function step(){
  // Force-directed layout (tuong duong D3 forceSimulation):
  // link (distance 80) + charge day am (-300) + center (W/2,H/2) + collision (r 25)
  const W=cv.clientWidth,H=cv.clientHeight,cx=W/2,cy=H/2;
  for(const n of nodes){ if(n.fx>=0){n.x=n.fx;n.y=n.fy;continue;}
    n.vx*=(1-0.12);n.vy*=(1-0.12);
    n.vx+=(cx-n.x)*0.012; n.vy+=(cy-n.y)*0.012; // forceCenter
    const deg=G.deg[n.id]||1, k=Math.min(deg,12);
    n.vx+=(Math.random()-0.5)*0.25*Math.sqrt(k); n.vy+=(Math.random()-0.5)*0.25*Math.sqrt(k);
    if(n.x<10||n.x>W-10)n.vx*=-0.6; if(n.y<10||n.y>H-10)n.vy*=-0.6; n.x+=n.vx;n.y+=n.vy;}
  for(let pass=0;pass<2;pass++){
    for(let i=0;i<nodes.length;i++){const a=nodes[i]; if(a.fx>=0)continue;
      for(let j=i+1;j<nodes.length;j++){const b=nodes[j]; if(b.fx>=0)continue;
        let dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;
        if(d2>160*160||d2<0.01)continue;
        const d=Math.sqrt(d2), f=300/(d2+40)*0.5; // forceManyBody strength -300
        dx/=d;dy/=d;
        a.vx-=dx*f;a.vy-=dy*f;b.vx+=dx*f;b.vy+=dy*f;}}
    for(const l of links){const a=N[l.source],b=N[l.target];if(!a||!b)continue;
      if(a.fx>=0&&b.fx>=0)continue;
      let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy)||1; // forceLink distance 80
      const f=(d-80)*0.02;dx/=d;dy/=d;
      if(a.fx<0){a.vx+=dx*f;a.vy+=dy*f;} if(b.fx<0){b.vx-=dx*f;b.vy-=dy*f;}}
    for(const n of nodes){if(n.fx>=0)continue;n.x+=n.vx*0.5;n.y+=n.vy*0.5;}
    for(let i=0;i<nodes.length;i++){const a=nodes[i];
      for(let j=i+1;j<nodes.length;j++){const b=nodes[j];
        let dx=b.x-a.x,dy=b.y-a.y,d=Math.hypot(dx,dy);
        const min=25; // forceCollide radius 25
        if(d>0.01&&d<min){const push=(min-d)/d*0.35;dx*=push;dy*=push;
          if(a.fx<0){a.x-=dx;a.y-=dy;} if(b.fx<0){b.x+=dx;b.y+=dy;}}}}
  }
  for(const n of nodes){if(n.fx>=0)continue;
    n.x=Math.max(10,Math.min(W-10,n.x));n.y=Math.max(10,Math.min(H-10,n.y));}
}
function draw(){
  step(); const W=cv.clientWidth,H=cv.clientHeight; c.clearRect(0,0,W,H);
  c.strokeStyle='#2a3350';c.lineWidth=0.8;
  for(const l of links){const a=N[l.source],b=N[l.target];if(a&&b){c.beginPath();c.moveTo(a.x,a.y);c.lineTo(b.x,b.y);c.stroke();}}
  for(const n of nodes){if(!showTypes.has(n.type))continue;
    c.fillStyle='#cfdcff';c.font=`${11}px sans-serif`;c.textAlign='center';
    c.fillText(n.label.slice(0,18),n.x,n.y-12);
    c.fillStyle=typeColor[n.type]||'#789bff';c.beginPath();
    if(n.type==='envkey')c.rect(n.x-6,n.y-6,12,12);else c.arc(n.x,n.y,R,0,Math.PI*2);
    c.fill();
    if(n.id===selected){c.strokeStyle='#fff';c.lineWidth=2;c.beginPath();c.arc(n.x,n.y,R+3,0,2*Math.PI);c.stroke();}}
  requestAnimationFrame(draw);
}
cv.addEventListener('mousedown',e=>{
  const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
  let hit=null,bd=R;
  for(const n of nodes){if(!showTypes.has(n.type))continue;const d=Math.hypot(n.x-x,n.y-y);if(d<bd){bd=d;hit=n;}}
  if(hit){selected=hit.id;showInfo(hit);}
});
function showInfo(n){
  let h='<div class="node-title">'+n.label+'</div>'
  h+='<div class="node-meta">loai: '+n.type+'</div>';
  if(n.file)h+='<div class="node-meta">file: '+n.file+(n.line?' :'+n.line:'')+'</div>';
  if(n.kind)h+='<div class="node-meta">kind: '+n.kind+'</div>';
  const inl=G.links.filter(l=>l.source===n.id).map(l=>byId[l.target]);
  const outl=G.links.filter(l=>l.target===n.id).map(l=>byId[l.source]);
  h+='<div class="node-meta">lien ket: '+(inl.length+outl.length)+'</div><div class="node-edges">';
  [...inl,...outl].slice(0,12).forEach(t=>{if(t)h+='<div>- '+t.label+'</div>';});
  h+='</div>'; document.getElementById('info').innerHTML=h;
}
const td=document.getElementById('types');
[...new Set(G.nodes.map(n=>n.type))].forEach(t=>{const b=document.createElement('div');b.className='tag';b.textContent=t;b.onclick=()=>{showTypes.has(t)?showTypes.delete(t):showTypes.add(t);b.classList.toggle('sel',showTypes.has(t));};td.appendChild(b);});
document.getElementById('reset').onclick=()=>{for(const n of nodes){n.fx=-1;n.fy=-1;}setup();};
function recenter(){ // dua centroid ve tam man hinh (giong d3.forceCenter)
  const W=cv.clientWidth,H=cv.clientHeight;
  let sx=0,sy=0,cnt=0;
  for(const n of nodes){if(!showTypes.has(n.type))continue;sx+=n.x;sy+=n.y;cnt++;}
  if(!cnt)return; sx/=cnt; sy/=cnt;
  for(const n of nodes){n.x+=W/2-sx;n.y+=H/2-sy;n.vx=0;n.vy=0;}
}
const rc=document.createElement('button');rc.textContent='center';rc.id='center';
rc.style.cssText='flex:1;background:#1c2438;color:#e6e9ff;border:1px solid #31405f;border-radius:6px;padding:6px;cursor:pointer';
document.querySelector('#side>div:last-child').appendChild(rc);
rc.onclick=recenter; setTimeout(recenter,600);
draw();
</script></body></html>
"""


def write_html(graph: dict, out: Path):
    # Escape '</' -> '<\\/' : JSON inline chua chuoi '</script>' se dong the <script> som
    # trong browser -> JS bi cat giua chung -> canvas khong ve (man hinh trang).
    payload = json.dumps(graph).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__GRAPH__", payload)
    out.write_text(html, encoding="utf-8")
    print(f"[OK] wrote {out}  (nodes={graph['meta']['n']}, edges={graph['meta']['e']})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build interactive graph memory map")
    ap.add_argument("--serve", action="store_true", help="also serve html on local http")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args(argv)

    graph = build_graph()
    Path(ROOT, "graph_memory.json").write_text(
        json.dumps(graph, indent=1, ensure_ascii=False), encoding="utf-8")
    write_html(graph, Path(ROOT, "graph_memory.html"))
    print(f"[OK] graph_memory.json  n={graph['meta']['n']}  e={graph['meta']['e']}")

    if args.serve:
        url = f"http://127.0.0.1:{args.port}/graph_memory.html"
        print(f"[SERVE] {url}")
        webbrowser.open(url)
        import http.server as hs
        import functools
        handler = functools.partial(hs.SimpleHTTPRequestHandler, directory=str(ROOT))
        with hs.HTTPServer(("127.0.0.1", args.port), handler) as httpd:
            httpd.serve_forever()


if __name__ == "__main__":
    main()

