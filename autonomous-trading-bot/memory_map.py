"""memory_map.py — Bản đồ biểu đồ TƯƠNG TÁC hợp nhất (code + memories), tự cập nhật.

Kết hợp 3 nguồn:
  * graph_memory.json  (memory-mcp/CBM-style cấu trúc code: file/def/class/concept)
  * memory.db          (memory-graph schema + openbrain engines: memories/relationships)
  * (tuỳ chọn) logs    (qua memory_agent reflect -> memory.db)

Sinh ra:
  * memory_map_data.json : dữ liệu hợp nhất {nodes, links, meta}
  * memory_map.html      : viewer canvas, TỰ ĐỘNG fetch lại data mỗi N giây (live),
                           có search, lọc theo type, click node xem nội dung + liên kết.

Chạy:
  python memory_map.py                 # sinh data + html (1 lần)
  python memory_map.py --serve         # + http.server :8790 và mở browser (LIVE)
  python memory_map.py --watch 30      # chạy ngầm: rebuild data mỗi 30s
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from memory_graph import DB_PATH, ROOT, MemoryGraph

GRAPH_JSON = ROOT / "graph_memory.json"
MAP_DATA = ROOT / "memory_map_data.json"
MAP_DATA_JS = ROOT / "memory_map_data.js"  # ban nhung san cho file:// (fetch bi CORS chan)

# code-structure types (từ graph_memory.json)
CODE_TYPES = {"file": "code_file", "def": "code_def", "class": "code_class",
              "concept": "concept", "env": "env", "envkey": "env", "field": "config",
              "state": "state", "error": "bug"}
# CBM edge parity: giữ nguyên nhãn CALLS / SIMILAR_TO / SEMANTICALLY_RELATED /
# defines / import / field / env / emits trong map
# memory types (từ memory.db)
MEM_CODE = {"code_pattern": "code_def", "technology": "code_file"}
MEM_MEMORY = {"trade": "trade", "config": "config", "bug": "bug", "error": "bug",
              "decision": "decision", "reflection": "reflection", "skill": "skill",
              "semantic": "reflection", "episodic": "episodic",
              "procedural": "procedural", "workspace": "file_context",
              "project": "project", "concept": "concept", "problem": "problem",
              "solution": "solution", "fix": "fix", "task": "task",
              "workflow": "workflow", "general": "general",
              "file_context": "file_context", "command": "command"}


def _code_kind(node: dict) -> str:
    return CODE_TYPES.get(str(node.get("type")), "code_def")


def build_map(with_memories: bool = True) -> dict:
    nodes: list[dict] = []
    links: list[dict] = []
    seen: set[str] = set()

    def add(nid: str, label: str, kind: str, **extra) -> bool:
        if nid in seen:
            return False
        seen.add(nid)
        nodes.append({"id": nid, "label": label, "kind": kind, **extra})
        return True

    # ---------- 1) code structure (+ code<->memory bridges) ----------
    code_id: dict[str, str] = {}
    code_by_file: dict[str, str] = {}   # "bot.py" -> node id
    code_by_def: dict[str, list[str]] = {}  # "manage_trade" -> [node ids]
    if GRAPH_JSON.exists():
        try:
            data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {"nodes": [], "links": []}
        for n in data.get("nodes", []):
            nid = f"code:{n['type']}:{n['label']}"
            code_id[n["id"]] = nid
            add(nid, n["label"], _code_kind(n), file=n.get("file"), line=n.get("line"))
            if n.get("type") == "file":
                base = (n.get("file") or n["label"]).replace("\\", "/").split("/")[-1]
                code_by_file[base] = nid
            if n.get("type") in ("def", "class"):
                code_by_def.setdefault(n["label"], []).append(nid)
        for l in data.get("links", []):
            s, t = code_id.get(l["source"]), code_id.get(l["target"])
            if s and t and s != t:
                links.append({"source": s, "target": t, "rel": l.get("label") or "rel"})
        meta_extra = data.get("meta", {})
    else:
        meta_extra = {}

    # ---------- 2) memories + relationships (+ bridges code<->memory) ----------
    n_mem = 0
    n_bridge = 0
    if with_memories and Path(str(DB_PATH)).exists():
        import re as _re
        g = MemoryGraph()
        g.initialize_schema()
        mems = g.search_memories({"limit": 5000})
        for m in mems:
            kind = MEM_MEMORY.get(m["type"]) or MEM_CODE.get(m["type"]) or "general"
            nid = f"mem:{m['id']}"
            if add(nid, m["title"][:60], kind, imp=round(float(m["importance"]), 2),
                   conf=round(float(m["confidence"]), 2), type=m["type"],
                   content=str(m["content"])[:400], tags=m.get("tags") or []):
                n_mem += 1
        # bridge: memory content/context nhắc "file.py" hoặc "def_name"
        # -> link FOUND_IN / APPLIES_TO sang node code (memory-graph FOUND_IN parity)
        for m in mems:
            nid = f"mem:{m['id']}"
            if nid not in seen:
                continue
            blob = f"{m['title']}\n{m['content']}\n{' '.join(m.get('tags') or [])}"
            for fn in set(_re.findall(r"([A-Za-z_][\w\-]*\.py)", blob)):
                base = fn.split("/")[-1]
                tgt = code_by_file.get(base)
                if tgt:
                    links.append({"source": nid, "target": tgt, "rel": "FOUND_IN"})
                    n_bridge += 1
            for tok in set(_re.findall(r"[A-Za-z_]\w{3,}", blob)):
                for tgt in code_by_def.get(tok, [])[:2]:
                    links.append({"source": nid, "target": tgt, "rel": "APPLIES_TO"})
                    n_bridge += 1
                    break
        for r in g.conn.execute(
                "SELECT from_id, to_id, rel_type, strength FROM relationships LIMIT 8000"):
            s, t = f"mem:{r['from_id']}", f"mem:{r['to_id']}"
            if s in seen and t in seen:
                links.append({"source": s, "target": t, "rel": r["rel_type"],
                              "w": float(r["strength"] or 0.5)})

    # runtime overlay riêng (memory-mcp RUNTIME_TRACE_MODEL parity):
    # runtime facts KHÔNG trộn vào links tĩnh — trả ở meta.overlay riêng.
    return {"nodes": nodes, "links": links,
            "meta": {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "nodes": len(nodes), "links": len(links), "from_memory_db": n_mem,
                     "code_memory_bridges": n_bridge, "root": str(ROOT),
                     "excluded_dirs": meta_extra.get("excluded_dirs", []),
                     "excluded_count": meta_extra.get("excluded_count", 0),
                     "ignored_total": meta_extra.get("ignored_total", 0)}}


def write_data(m: dict) -> None:
    MAP_DATA.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    # '<\\/' giu nguyen gia tri JSON, tranh dong the <script> som neu du lieu chua '</script>'
    MAP_DATA_JS.write_text(
        "window.MAP_DATA = " + json.dumps(m, ensure_ascii=False).replace("</", "<\\/") + ";\n",
        encoding="utf-8")


def sync_all() -> dict:
    import graph_memory

    graph = graph_memory.build_graph()
    GRAPH_JSON.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
    graph_memory.write_html(graph, ROOT / "graph_memory.html")

    data = build_map()
    write_data(data)
    write_html()

    import build_dashboard
    import build_glow
    build_dashboard.main()
    build_glow.main()
    return data


HTML_HEAD = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Memory Map — code + memories</title>
<style>
:root{--bg:#0b0f1a;--panel:#141a2b;--line:#26304a;--fg:#e6e9ff;--dim:#93a0c2}
*{box-sizing:border-box}
body{margin:0;height:100vh;display:flex;font-family:system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
#canvas-wrap{flex:1;position:relative;overflow:hidden}
#canvas-wrap canvas{display:block;width:100%;height:100%}
#side{width:380px;max-width:44%;background:var(--panel);border-left:1px solid var(--line);padding:14px;overflow:auto;font-size:13px}
.bar{position:absolute;left:10px;top:10px;z-index:3;background:rgba(20,26,43,.94);border:1px solid var(--line);border-radius:8px;padding:10px;max-width:min(780px,92%)}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input,button,select{background:#1d2438;color:#cfdcff;border:1px solid #38466a;border-radius:5px;padding:4px 8px;font-size:12px}
button{cursor:pointer}button:hover{background:#28334f}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px;max-height:96px;overflow:auto}
.chip{border:1px solid #38466a;border-radius:999px;padding:2px 9px;font-size:11px;cursor:pointer;background:#1b2234;white-space:nowrap}
.chip.on{background:#2f4f8f;border-color:#5b8ae8}
.chip i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
#stat{color:var(--dim);font-size:11px;margin-top:8px}
#title{font-weight:700;font-size:15px;margin-bottom:4px}
#meta{color:var(--dim);font-size:12px;margin-bottom:8px}
.sec{margin:10px 0 4px;font-weight:600;font-size:12px;color:#a9b7db;text-transform:uppercase;letter-spacing:.04em}
.item{border-top:1px solid #1f2942;padding:6px 0;color:var(--dim)}
.item b{color:#dbe4ff;font-weight:600}
pre{margin:6px 0 0;background:#0e1420;border:1px solid #1f2942;border-radius:6px;padding:8px;max-height:240px;overflow:auto;white-space:pre-wrap;font-size:11px;color:#c8d4f0}
</style></head><body>
<div id="canvas-wrap"><canvas id="cv"></canvas>
  <div class="bar">
    <div class="row">
      <input id="q" placeholder="tim node / memory..." style="width:190px">
      <button id="reload">reload</button>
      <button id="pause">pause live</button>
  <button id="fit">fit</button>
      <select id="layout"><option value="force">force</option><option value="circle">circle</option></select>
      <span style="color:#93a0c2;font-size:11px">keo: pan - lan chuot: zoom - click: chi tiet</span>
    </div>
    <div class="chips" id="chips"></div>
    <div id="stat">...</div>
  </div>
</div>
<div id="side">
  <div id="title">Memory Map — code + memories</div>
  <div id="meta">Dang tai...</div>
  <div id="info" class="item">Click mot node de xem noi dung + lien ket.</div>
</div>
<script src="memory_map_data.js"></script>
<script>
"""


HTML_JS_A = r"""const DATA_URL = "memory_map_data.json";
const FILE_MODE = location.protocol === "file:";  // fetch bi chan CORS tren file://
const TYPE_STYLE = {code_file:"#5fb3ff",code_def:"#8fe3a5",code_class:"#ffa366",concept:"#c58cff",
 env:"#ff9a9e",config:"#ffd46b",state:"#f7a561",bug:"#ff6b6b",trade:"#ffb27b",decision:"#ffe08a",
 skill:"#7ef1c0",reflection:"#d98cff",episodic:"#9fb3ff",procedural:"#9ee7ff",file_context:"#a8c6ff",
 project:"#a0f0c0",problem:"#ff8fa3",solution:"#7ef1c0",fix:"#8fe3a5",task:"#b9c7ff",
 workflow:"#d7c4ff",command:"#c9d6ef",general:"#8b9bc7"};
const C=document.getElementById("cv"), ctx=C.getContext("2d");
let DATA={nodes:[],links:[],meta:{}}, N={}, nodes=[], links=[], shown=new Set(),
    live=true, sel=null, hov=null, mode="force";
const S={zoom:1,ox:0,oy:0,down:false,lx:0,ly:0};
function fit(){C.width=C.clientWidth*devicePixelRatio;C.height=C.clientHeight*devicePixelRatio;
  ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);}
addEventListener("resize",()=>{fit();place(false);});
async function load(){
  const st=document.getElementById("stat"); st.textContent="dang tai data...";
  if(FILE_MODE){
    if(!window.MAP_DATA){ st.innerHTML="thieu memory_map_data.js - chay: python memory_map.py"; return; }
    DATA=window.MAP_DATA;
    st.textContent="data nhung san (file://) - chay --serve de LIVE 15s";
    place(true); chips(); meta(); return;
  }
  try{
    const r=await fetch(DATA_URL+"?t="+Date.now(),{cache:"no-store"});
    DATA=await r.json();
  }catch(e){
    if(!window.MAP_DATA){ st.innerHTML="fetch loi (can chay --serve): "+e; return; }
    DATA=window.MAP_DATA;
    st.textContent="fetch loi - dung data nhung san";
  }
  place(true); chips(); meta();
}
function place(reset){
  const W=C.clientWidth,H=C.clientHeight,R=Math.min(W,H)*0.42;
  nodes=DATA.nodes.map((n,i)=>{
    const a=i*2.399963, rr=R*Math.sqrt((i+1)/Math.max(DATA.nodes.length,1));
    return {...n, x:W/2+Math.cos(a)*rr, y:H/2+Math.sin(a)*rr, vx:0, vy:0,
            r:(n.kind==="code_file"||n.kind==="concept")?7:5};
  });
  N=Object.fromEntries(nodes.map(n=>[n.id,n]));
  links=DATA.links.filter(l=>N[l.source]&&N[l.target]);
  if(reset){shown=new Set(nodes.map(n=>n.kind));S.zoom=1;}
  fitView(false); // tu dong can giua khung nhin sau khi tai data (zoom.transform identity)
}
function meta(){
  const m=DATA.meta||{};
  document.getElementById("meta").innerHTML=
    `nodes <b>${m.nodes||0}</b> - links <b>${m.links||0}</b> - from memory.db <b>${m.from_memory_db||0}</b><br>`+
    `<generated ${m.generated||"?"} - <span style="color:#7ef1c0">${FILE_MODE?"STATIC (file://)":"LIVE 15s"}</span>`;
}
function chips(){
  const box=document.getElementById("chips"); box.innerHTML="";
  [...new Set(nodes.map(n=>n.kind))].sort().forEach(k=>{
    const cnt=nodes.filter(n=>n.kind===k).length;
    const d=document.createElement("div");
    d.className="chip"+(shown.has(k)?" on":"");
    d.innerHTML=`<i style="background:${TYPE_STYLE[k]||"#8b9bc7"}"></i>${k} ${cnt}`;
    d.onclick=()=>{shown.has(k)?shown.delete(k):shown.add(k);chips();};
    box.appendChild(d);
  });
  document.getElementById("stat").textContent=
    `hien thi ${nodes.filter(n=>shown.has(n.kind)).length}/${nodes.length} node - ${links.length} lien ket`;
}
function step(){
  if(mode==="circle") return;
  const W=C.clientWidth,H=C.clientHeight;
  for(const n of nodes){
    if(S.dragNode===n) continue;
    n.vx*=0.86; n.vy*=0.86; n.x+=n.vx; n.y+=n.vy;
    n.vx+=(W/2-n.x)*0.0006; n.vy+=(H/2-n.y)*0.0006;
    n.x=Math.max(12,Math.min(W-12,n.x)); n.y=Math.max(12,Math.min(H-12,n.y));
  }
  for(const l of links){
    const a=N[l.source], b=N[l.target]; if(!a||!b) continue;
    let dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||1;
    const f=(d-70)*0.0016; dx/=d; dy/=d;
    a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f;
  }
}
"""


HTML_JS_B = r"""const q=document.getElementById("q");
function match(n){const s=q.value.trim().toLowerCase();
  return !s || n.label.toLowerCase().includes(s) || (n.content||"").toLowerCase().includes(s);}
function draw(){
  step();
  const W=C.clientWidth,H=C.clientHeight;
  ctx.clearRect(0,0,W,H);
  ctx.save(); ctx.translate(S.ox,S.oy); ctx.scale(S.zoom,S.zoom);
  for(const l of links){
    const a=N[l.source],b=N[l.target]; if(!a||!b) continue;
    if(!shown.has(a.kind)||!shown.has(b.kind)) continue;
    const hot = sel && (l.source===sel||l.target===sel);
    ctx.strokeStyle = hot? "#7fa8ff" : "#232c47";
    ctx.lineWidth = hot?1.6:0.7;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  for(const n of nodes){
    if(!shown.has(n.kind)) continue;
    const on=match(n), isSel=(sel===n.id), isHov=(hov===n.id);
    ctx.globalAlpha=on?1:0.16;
    ctx.fillStyle=TYPE_STYLE[n.kind]||"#8b9bc7";
    ctx.beginPath(); ctx.arc(n.x,n.y,n.r+(isHov?2:0)+(isSel?2:0),0,Math.PI*2); ctx.fill();
    if(isSel){ctx.strokeStyle="#fff";ctx.lineWidth=2;ctx.stroke();}
    if(shown.size<=8||isSel||isHov){
      ctx.globalAlpha=on?0.95:0.12;
      ctx.fillStyle="#cfdcff"; ctx.font="10px system-ui"; ctx.textAlign="center";
      ctx.fillText(n.label.slice(0,20), n.x, n.y-n.r-4);
    }
  }
  ctx.globalAlpha=1; ctx.restore();
  requestAnimationFrame(draw);
}
function pick(mx,my){
  const x=(mx-S.ox)/S.zoom, y=(my-S.oy)/S.zoom;
  let best=null, bd=18;
  for(const n of nodes){ if(!shown.has(n.kind)) continue;
    const d=Math.hypot(n.x-x,n.y-y); if(d<bd){bd=d;best=n;} }
  return best;
}
C.addEventListener("mousedown",e=>{const r=C.getBoundingClientRect();
  const n=pick(e.clientX-r.left,e.clientY-r.top);
  if(n){S.dragNode=n; sel=n.id; detail(n);}
  else {S.down=true; S.lx=e.clientX; S.ly=e.clientY;}
});
C.addEventListener("mousemove",e=>{const r=C.getBoundingClientRect();
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  if(S.dragNode){S.dragNode.x=(mx-S.ox)/S.zoom; S.dragNode.y=(my-S.oy)/S.zoom; return;}
  if(S.down){S.ox+=e.clientX-S.lx; S.oy+=e.clientY-S.ly; S.lx=e.clientX; S.ly=e.clientY; return;}
  const n=pick(mx,my); hov=n?n.id:null;
});
addEventListener("mouseup",()=>{S.down=false; S.dragNode=null;});
C.addEventListener("wheel",e=>{e.preventDefault();
  const r=C.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
  const k=e.deltaY<0?1.12:0.89, nz=Math.max(0.2,Math.min(4,S.zoom*k)), f=nz/S.zoom;
  S.ox=mx-(mx-S.ox)*f; S.oy=my-(my-S.oy)*f; S.zoom=nz;},{passive:false});
function detail(n){
  const rels=links.filter(l=>l.source===n.id||l.target===n.id);
  let h=`<div id="title">${n.label}</div><div id="meta">kind <b>${n.kind}</b>`+
        (n.type?` - type <b>${n.type}</b>`:"")+
        (n.file?` - file <b>${n.file}${n.line?":"+n.line:""}</b>`:"")+"</div>";
  if(n.imp!==undefined) h+=`<div class="item">importance ${n.imp} - confidence ${n.conf}</div>`;
  if(n.tags&&n.tags.length) h+=`<div class="item">tags: ${n.tags.join(", ")}</div>`;
  if(n.content) h+=`<div class="sec">noi dung</div><pre>${String(n.content).replace(/</g,"&lt;")}</pre>`;
  h+=`<div class="sec">lien ket (${rels.length})</div>`;
  rels.slice(0,30).forEach(l=>{
    const o=N[l.source===n.id?l.target:l.source]; if(!o) return;
    h+=`<div class="item">${l.source===n.id?"-&gt;":"&lt;-"} <b>${o.label}</b> [${l.rel}] (${o.kind})</div>`;
  });
  document.getElementById("info").innerHTML=h;
}
function fitView(resetZoom){
  // Tuong duong d3: svg.call(zoom.transform, d3.zoomIdentity) + can giua bbox
  const W=C.clientWidth,H=C.clientHeight;
  const vis=nodes.filter(n=>shown.size===0||shown.has(n.kind));
  if(!vis.length){S.ox=0;S.oy=0;S.zoom=1;return;}
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  for(const n of vis){if(n.x<x0)x0=n.x;if(n.y<y0)y0=n.y;if(n.x>x1)x1=n.x;if(n.y>y1)y1=n.y;}
  const bw=Math.max(x1-x0,50), bh=Math.max(y1-y0,50);
  if(resetZoom!==false) S.zoom=Math.max(0.2,Math.min(1.5,Math.min(W/bw,H/bh)*0.9));
  S.ox=W/2-(x0+x1)/2*S.zoom; S.oy=H/2-(y0+y1)/2*S.zoom; // dua tam bbox ve tam man hinh
}
document.getElementById("reload").onclick=()=>{load().then(()=>fitView(true));};
document.getElementById("pause").onclick=e=>{live=!live;
  e.target.textContent=live?"pause live":"resume live";};
document.getElementById("layout").onchange=e=>{mode=e.target.value; place(false);};
document.getElementById("fit").onclick=()=>fitView(true);
fit(); place(true); load(); draw();
setInterval(()=>{ if(live && !FILE_MODE) load(); }, 15000);
</script></body></html>
"""


def write_html() -> Path:
    out = ROOT / "memory_map.html"
    out.write_text(HTML_HEAD + HTML_JS_A + HTML_JS_B, encoding="utf-8")
    return out


def main(argv=None) -> int:
    import argparse
    import functools
    import http.server as hs
    import webbrowser
    ap = argparse.ArgumentParser(description="Unified interactive map (code + memories)")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--watch", type=int, default=0, help="rebuild data moi N giay")
    args = ap.parse_args(argv)

    if args.watch:
        print(f"[MAP] watch: rebuild every {args.watch}s (Ctrl+C to stop)", flush=True)
        while True:
            m = sync_all()
            print(f"[MAP] {m['meta']['nodes']} nodes, {m['meta']['links']} links "
              f"({m['meta']['from_memory_db']} from memory.db)", flush=True)
            time.sleep(args.watch)

    m = sync_all()
    html = ROOT / "memory_map.html"
    print(f"[OK] {MAP_DATA.name}: {m['meta']['nodes']} nodes, {m['meta']['links']} links "
          f"({m['meta']['from_memory_db']} from memory.db)")

    if args.serve:
        url = f"http://127.0.0.1:{args.port}/{html.name}"
        print(f"[SERVE] {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        handler = functools.partial(hs.SimpleHTTPRequestHandler, directory=str(ROOT))
        with hs.HTTPServer(("127.0.0.1", args.port), handler) as httpd:
            httpd.serve_forever()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

