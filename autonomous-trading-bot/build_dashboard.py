# -*- coding: utf-8 -*-
"""build_dashboard.py - generate preview_dashboard.html with 4 D3 panels.

Reads graph_memory.json + memory_map_data.json and writes preview_dashboard.html
containing four interactive D3 force-directed panels:
  1) Graph Memory  2) Memory Map  3) Graph Hubs  4) Map Hubs

Run: python build_dashboard.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRAPH_PATH = ROOT / "graph_memory.json"
MAP_PATH = ROOT / "memory_map_data.json"
OUT_HTML = ROOT / "preview_dashboard.html"
D3_PATH = ROOT / "d3.v7.min.js"

MAX_EDGES_PER_PANEL = 1200
HUB_LIMIT = 80
D3_MODE = "local"  # 'local' = doc file d3.v7.min.js ke HTML; 'cdn' = dung d3js.org


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def js(v):
    """Serialize a Python object to a JSON literal safe for inline <script>."""
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")


def cap_edges(links, cap):
    return links[:cap] if len(links) > cap else links


def top_hubs(nodes, links, limit=HUB_LIMIT):
    """Return (hub_id_set, degree_map) for the top-N nodes by degree."""
    deg = {}
    for n in nodes:
        deg[str(n.get("id"))] = 0
    for l in links:
        s = str(l.get("source"))
        t = str(l.get("target"))
        deg[s] = deg.get(s, 0) + 1
        deg[t] = deg.get(t, 0) + 1
    ranked = sorted(deg.items(), key=lambda x: -x[1])
    return {k for k, _ in ranked[:limit]}, deg


def d3_block():
    """Return a <script> block providing D3.

    Prefers a local d3.v7.min.js (works offline and inside the VS Code
    integrated browser, which blocks external CDN scripts); falls back to CDN.
    """
    if D3_PATH.exists():
        try:
            lib = D3_PATH.read_text(encoding="utf-8")
            if "</script" in lib:
                raise ValueError("d3 bundle contains closing script tag")
            return "<script>\n" + lib + "\n</script>\n"
        except Exception as e:
            print(f"WARN d3 local read failed: {e}")
    # Fallback CDN
    return '<script src="https://d3js.org/d3.v7.min.js"></script>\n'

def d3_with_cross():
    d3src = '<script src="https://d3js.org/d3.v7.min.js"></script>\n'
    if D3_MODE == "local":
        try:
            body = (ROOT / "d3.v7.min.js").read_text(encoding="utf-8")
            if "</script" in body:
                raise ValueError("d3 bundle contains closing script tag")
            d3src = "<script>\n" + body + "\n</script>\n"
        except Exception as e:
            print("WARN vendored d3 unavailable, fallback CDN:", e)
    try:
        cross = json.loads((ROOT / "cross_index.json").read_text(encoding="utf-8"))["entities"]
    except Exception as e:
        print("WARN cross index unavailable:", e)
        cross = {}
    return (d3src
            + '<script>\nwindow.__CROSS_INDEX = ' + js(cross) + ';\n</script>\n'
            + '<script src="d3-fallback-note.js" onerror="void 0"></script>\n<script>\n'
            + 'if(typeof d3 === "undefined"){ document.body.insertAdjacentHTML("afterbegin", '
            + '"<div style=\\"margin:8px;padding:10px;border:1px solid #a33;background:#2a1215\\">'
            + 'D3 chua nap duoc (CDN bi chan / offline). Hay mo bang Live Server, hoac chay lai build voi D3_MODE=local.</div>"); }\n'
            + "window.__panels = {};\n"
            + "function crossOf(entry){\n"
            + "  const raw = String((entry && (entry.label || entry.id)) || '');\n"
            + "  const C = window.__CROSS_INDEX || {};\n"
            + "  const parts = raw.split(/[\\/]/);\n"
            + "  const base = parts[parts.length-1].toLowerCase();\n"
            + "  if(base.endsWith('.py') && C['file:'+base]) return C['file:'+base];\n"
            + "  const id = String(entry?.id || '');\n"
            + "  const m = id.match(/^(code:)?(file|def|class):(.+)$/i);\n"
            + "  if(m) {\n"
            + "    const key = m[2].toLowerCase() === 'file' ? 'file:'+base : 'sym:'+m[3].toLowerCase();\n"
            + "    if(C[key]) return C[key];\n"
            + "  }\n"
            + "  const lbl = String(entry?.label || '').toLowerCase();\n"
            + "  if(lbl.endsWith('.py') && C['file:'+lbl]) return C['file:'+lbl];\n"
            + "  const msym = lbl.match(/^(.+)::(.+)$/i);\n"
            + "  const symKey = msym ? 'sym:'+msym[2].toLowerCase() : 'sym:'+lbl;\n"
            + "  return C[symKey] || null;\n"
            + "}\n"
            + "function gotoNode(panelPrefix, nodeId){\n"
            + "  const ctl = window.__panels && window.__panels[panelPrefix];\n"
            + "  if(!ctl || !ctl.node) return;\n"
            + "  const node = ctl.node.filter(d => d.id === nodeId);\n"
            + "  if(!node.size()) return;\n"
            + "  try { ctl.fit(); } catch(e) {}\n"
            + "  node.select('circle').attr('stroke', '#ffd54f').attr('stroke-width', 2.5);\n"
            + "}\n")



def build_html(g_nodes, g_links, m_nodes, m_links, g_hubs, m_hubs, g_deg, m_deg):
    """Return the full preview_dashboard.html document as a string."""
    out = []
    out.append("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />\n<meta http-equiv=\"Content-Security-Policy\" content=\"default-src * data: blob: ws: wss:; script-src * unsafe-inline unsafe-eval; connect-src * data: blob: ws: wss:; style-src * unsafe-inline; img-src * data: blob: ; font-src * data: ; object-src none;\">\n<title>Preview Dashboard</title>\n")
    out.append("<style>\n")
    out.append("* { box-sizing:border-box; margin:0; padding:0; }\n")
    out.append("body { background:#0b1020; color:#e6edf5; font:13px/1.3 ui-sans-serif,system-ui,sans-serif; }\n")
    out.append(".wrap { display:grid; grid-template-columns:1fr 1fr; grid-template-rows:minmax(320px,44vh) minmax(320px,44vh); gap:10px; padding:8px; min-height:calc(100vh - 96px); }\n")
    out.append(".panel { background:#172033; border:1px solid #28334a; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; min-height:320px; }\n")
    out.append(".panel-head { display:flex; align-items:center; padding:8px 10px; border-bottom:1px solid #28334a; }\n")
    out.append(".panel-head h3 { font-size:13px; margin:0; display:flex; align-items:center; font-weight:600; }\n")
    out.append(".panel-head .meta { margin-left:8px; color:#8a9bb5; font-size:11px; }\n")
    out.append(".panel-body { position:relative; flex:1; min-height:0; }\n")
    out.append(".panel-body svg { display:block; width:100%; height:100%; }\n")
    out.append(".hint { padding:8px 10px; color:#7a8aa5; font-size:11px; }\n")
    out.append(".topbar { padding:8px 10px 0; }\n")
    out.append(".btn { background:#24314a; color:#dde6f2; border:1px solid #3a4a66; padding:2px 7px; border-radius:4px; font-size:11px; cursor:pointer; }\n")
    out.append(".btn:hover { background:#2e405e; }\n")
    out.append(".toast { position:fixed; bottom:14px; left:50%; transform:translateX(-50%); background:#3a4a66; color:#fff; padding:5px 12px; border-radius:6px; font-size:12px; opacity:0; transition:opacity .2s; pointer-events:none; }\n")
    out.append(".toast.show { opacity:1; }\n")
    out.append(".modal { position:fixed; inset:0; background:rgba(3,6,16,.6); display:none; align-items:center; justify-content:center; z-index:100; }\n")
    out.append(".modal.open { display:flex; }\n")
    out.append(".modal-card { background:#172033; border:1px solid #36414f; border-radius:10px; padding:16px; max-width:420px; width:90%; }\n")
    out.append(".modal-card h2 { font-size:15px; margin:0 0 8px; color:#f0f6fc; word-break:break-all; }\n")
    out.append(".modal-card dt { color:#8a9bb5; font-size:11px; margin-top:6px; }\n")
    out.append(".modal-card dd { margin:0; color:#dde6f2; word-break:break-all; }\n")
    out.append("</style>\n</head>\n<body>\n")
    out.append('<div class="wrap">\n')
    out.append('<div class="panel" id="panel-g"><div class="panel-head"><h3>Graph Memory<span class="meta" id="g-meta"></span></h3><button class="btn" id="g-fit">Fit</button></div><div class="panel-body"><svg id="g-svg"></svg></div></div>\n')
    out.append('<div class="panel" id="panel-m"><div class="panel-head"><h3>Memory Map<span class="meta" id="m-meta"></span></h3><button class="btn" id="m-fit">Fit</button></div><div class="panel-body"><svg id="m-svg"></svg></div></div>\n')
    out.append('<div class="panel" id="panel-gh"><div class="panel-head"><h3>Graph Hubs<span class="meta" id="gh-meta"></span></h3><button class="btn" id="gh-fit">Fit</button></div><div class="panel-body"><svg id="gh-svg"></svg></div></div>\n')
    out.append('<div class="panel" id="panel-mh"><div class="panel-head"><h3>Map Hubs<span class="meta" id="mh-meta"></span></h3><button class="btn" id="mh-fit">Fit</button></div><div class="panel-body"><svg id="mh-svg"></svg></div></div>\n')
    out.append('</div>\n')
    out.append('<div class="topbar"><input id="search" type="text" placeholder="Filter nodes by label or id across all panels..." autocomplete="off" style="width:100%;padding:8px 12px;border-radius:8px;border:1px solid #2f3742;background:#0d1117;color:#e6edf5;font-size:13px;outline:none;" /></div>\n')
    out.append('<div class="hint">Click a node for details &middot; Esc closes the modal</div>\n')
    out.append('<div id="modal" class="modal"><div class="modal-card" id="modal-card"></div></div>\n')
    out.append('<div id="toast" class="toast"></div>\n')
    out.append(d3_with_cross())
    out.append("<script>\n")
    out.append(f"const G_NODES = {js(g_nodes)};\n")
    out.append(f"const G_LINKS = {js(g_links)};\n")
    out.append(f"const M_NODES = {js(m_nodes)};\n")
    out.append(f"const M_LINKS = {js(m_links)};\n")
    out.append(f"const G_HUBS = new Set({js(sorted(g_hubs))});\n")
    out.append(f"const M_HUBS = new Set({js(sorted(m_hubs))});\n")
    out.append(f"const G_DEG = {js(g_deg)};\n")
    out.append(f"const M_DEG = {js(m_deg)};\n")

    out.append("\nconst $ = (s, root=document) => root.querySelector(s);\n")
    out.append("const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));\n")
    out.append("const toastEl = $('#toast');\n")
    out.append("function toast(msg){ toastEl.textContent = msg; toastEl.classList.add('show'); setTimeout(()=>toastEl.classList.remove('show'), 1100); }\n")
    out.append("function connected(a, b, links){ return links.some(l => (l.source.id===a.id && l.target.id===b.id) || (l.source.id===b.id && l.target.id===a.id)); }\n")
    out.append("function degAll(id){ return (G_DEG[id]||0) + (M_DEG[id]||0); }\n")
    out.append("const panels = {};\n")
    out.append("\n")
    out.append("function initPanel(cfg){\n")
    out.append("  const svg = document.getElementById(cfg.prefix + '-svg');\n")
    out.append("  const body = svg.parentElement;\n")
    out.append("  const W = body.clientWidth || 600;\n")
    out.append("  const H = body.clientHeight || 400;\n")
    out.append("  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);\n")
    out.append("  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');\n")
    out.append("  const dsel = d3.select(svg);\n")
    out.append("  const nodes = cfg.nodes.map(n => Object.assign({}, n, { hub: cfg.hubs.has(n.id) }));\n")
    out.append("  const links = cfg.links.map(l => ({ source: l.source, target: l.target }));\n")
    out.append("  document.getElementById(cfg.prefix + '-meta').textContent = `${nodes.length} nodes · ${links.length} links`;\n")
    out.append("  const root = dsel.append('g');\n")
    out.append("  const linkG = root.append('g').attr('class', 'links');\n")
    out.append("  const nodeG = root.append('g').attr('class', 'nodes');\n")
    out.append("  const labelG = root.append('g').attr('class', 'labels');\n")
    out.append("  const sim = d3.forceSimulation(nodes)\n")
    out.append("    .force('link', d3.forceLink(links).id(d => d.id).distance(60).strength(0.35))\n")
    out.append("    .force('charge', d3.forceManyBody().strength(-70))\n")
    out.append("    .force('center', d3.forceCenter(W/2, H/2))\n")
    out.append("    .force('collision', d3.forceCollide().radius(d => d.hub ? 12 : 6));\n")
    out.append("  const link = linkG.selectAll('line').data(links).join('line')\n")
    out.append("    .attr('stroke', '#5a7a9a').attr('stroke-width', 0.8).attr('stroke-opacity', 0.45);\n")
    out.append("  const node = nodeG.selectAll('g.node').data(nodes).join('g').attr('class', 'node').attr('cursor', 'pointer')\n")
    out.append("    .call(d3.drag()\n")
    out.append("      .on('start', (e, d) => { if(!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })\n")
    out.append("      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })\n")
    out.append("      .on('end', (e, d) => { if(!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));\n")
    out.append("  node.append('circle')\n")
    out.append("    .attr('r', d => d.hub ? 8 : 4)\n")
    out.append("    .attr('fill', d => d.hub ? '#ff89c2' : '#58a6ff')\n")
    out.append("    .attr('stroke', '#0b1020').attr('stroke-width', 1.2);\n")
    out.append("  node.on('click', (e, d) => { e.stopPropagation(); showModal(d, cfg.prefix); });\n")
    out.append("  node.on('mouseenter', function(e, d){\n")
    out.append("    d3.select(this).select('circle').attr('r', d.hub ? 11 : 6);\n")
    out.append("    link.attr('stroke-opacity', l => (l.source.id===d.id || l.target.id===d.id) ? 0.95 : 0.05);\n")
    out.append("    node.attr('opacity', n => (n.id===d.id || connected(n, d, links)) ? 1 : 0.15);\n")
    out.append("    label.attr('opacity', n => (n.hub || n.id===d.id) ? 1 : 0);\n")
    out.append("  });\n")
    out.append("  node.on('mouseleave', function(){\n")
    out.append("    d3.select(this).select('circle').attr('r', d => d.hub ? 8 : 4);\n")
    out.append("    link.attr('stroke-opacity', 0.45);\n")
    out.append("    node.attr('opacity', 1);\n")
    out.append("    label.attr('opacity', n => n.hub ? 1 : 0);\n")
    out.append("  });\n")
    out.append("  const label = labelG.selectAll('text').data(nodes.filter(n => n.hub)).join('text')\n")
    out.append("    .attr('x', d => d.x + 9).attr('y', d => d.y + 3)\n")
    out.append("    .attr('font-size', '10px').attr('fill', '#c9d6e8')\n")
    out.append("    .attr('paint-order', 'stroke').attr('stroke', '#0b1020').attr('stroke-width', '2px')\n")
    out.append("    .text(d => d.label || d.id)\n")
    out.append("    .attr('opacity', d => d.hub ? 1 : 0);\n")
    out.append("  sim.on('tick', () => {\n")
    out.append("    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)\n")
    out.append("        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);\n")
    out.append("    node.attr('transform', d => `translate(${d.x},${d.y})`);\n")
    out.append("    label.attr('x', d => d.x + 9).attr('y', d => d.y + 3);\n")
    out.append("  });\n")
    out.append("  const zoom = d3.zoom().scaleExtent([0.1, 8]).on('zoom', (e) => { root.attr('transform', e.transform); });\n")
    out.append("  dsel.call(zoom);\n")
    out.append("  function fit(){\n")
    out.append("    const xs = nodes.map(d => d.x).filter(Number.isFinite);\n")
    out.append("    const ys = nodes.map(d => d.y).filter(Number.isFinite);\n")
    out.append("    if(!xs.length || !ys.length) return;\n")
    out.append("    const x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);\n")
    out.append("    const y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);\n")
    out.append("    const pad = 30;\n")
    out.append("    const bw = Math.max(x1 - x0, 1), bh = Math.max(y1 - y0, 1);\n")
    out.append("    const k = Math.max(0.1, Math.min(8, Math.min((W - pad*2)/bw, (H - pad*2)/bh)));\n")
    out.append("    const tx = W/2 - ((x0 + x1)/2) * k;\n")
    out.append("    const ty = H/2 - ((y0 + y1)/2) * k;\n")
    out.append("    dsel.transition().duration(300).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(k));\n")
    out.append("  }\n")
    out.append("  const ctl = { prefix: cfg.prefix, svg, node, link, label, sim, fit, zoom, nodes, links };\n")
    out.append("  panels[cfg.prefix] = ctl;\n")
    out.append("  setTimeout(fit, 600);\n")
    out.append("  return ctl;\n")
    out.append("}\n")
    out.append("\n")
    out.append("function showModal(d, prefix){\n")
    out.append("  const ctl = panels[prefix];\n")
    out.append("  const nbrs = [];\n")
    out.append("  if(ctl){ ctl.links.forEach(l => { if(l.source.id===d.id) nbrs.push(l.target.id); if(l.target.id===d.id) nbrs.push(l.source.id); }); }\n")
    out.append("  const uniq = Array.from(new Set(nbrs)).sort();\n")
    out.append("  const kind = d.type || d.kind || '-';\n")
    out.append("  let h = '';\n")
    out.append("  $('#modal-card').innerHTML = h +\n")
    out.append("    '<h2>' + (d.label || d.id) + '</h2>' +\n")
    out.append("    '<dl>' +\n")
    out.append("      '<dt>ID</dt><dd>' + d.id + '</dd>' +\n")
    out.append("      '<dt>Type / Kind</dt><dd>' + kind + '</dd>' +\n")
    out.append("      '<dt>Degree (graph+map)</dt><dd>' + degAll(d.id) + '</dd>' +\n")
    out.append("      '<dt>Neighbors (' + uniq.length + ')</dt><dd>' + (uniq.slice(0, 40).join(', ') || '(none)') + (uniq.length > 40 ? ' …' : '') + '</dd>' +\n")
    out.append("    '</dl>' +\n")
    out.append("    (function(){ const ci = crossOf(d); if(ci){ h += '<dl style=\"margin-top:6px\"><dt>Cross-Map Link</dt>'; h += '<dd>graph: ' + (ci.graph||[]).join(', ') + '</dd>'; h += '<dd>map: ' + (ci.map||[]).join(', ') + '</dd>'; h += '</dl>'; } })();\n")
    out.append("    '<div style=\"margin-top:12px;text-align:right;\"><button class=\"btn\" id=\"modal-close\">Close</button></div>';\n")
    out.append("  $('#modal').classList.add('open');\n")
    out.append("  $('#modal-close').onclick = () => $('#modal').classList.remove('open');\n")
    out.append("}\n")
    out.append("\n")
    out.append("$('#modal').addEventListener('click', e => { if(e.target.id === 'modal') $('#modal').classList.remove('open'); });\n")
    out.append("document.addEventListener('keydown', e => { if(e.key === 'Escape') $('#modal').classList.remove('open'); });\n")
    out.append("\n")
    out.append("function applySearch(q){\n")
    out.append("  q = (q || '').trim().toLowerCase();\n")
    out.append("  Object.values(panels).forEach(ctl => {\n")
    out.append("    ctl.node.attr('opacity', d => {\n")
    out.append("      if(!q) return 1;\n")
    out.append("      const ci = crossOf(d); const ciStr = ci ? ((ci.graph||[]).concat(ci.map||[])).join(' ') : ''; const hay = ((d.label || '') + ' ' + d.id + ' ' + ciStr).toLowerCase();\n")
    out.append("      return hay.includes(q) ? 1 : 0.06;\n")
    out.append("    });\n")
    out.append("    ctl.label.attr('opacity', d => {\n")
    out.append("      if(!q) return d.hub ? 1 : 0;\n")
    out.append("      const ci = crossOf(d); const ciStr = ci ? ((ci.graph||[]).concat(ci.map||[])).join(' ') : ''; const hay = ((d.label || '') + ' ' + d.id + ' ' + ciStr).toLowerCase();\n")
    out.append("      return hay.includes(q) ? 1 : 0;\n")
    out.append("    });\n")
    out.append("  });\n")
    out.append("}\n")
    out.append("\n")
    out.append("function buildHubPanel(src_nodes, src_links, prefix){\n")
    out.append("  const ids = new Set();\n")
    out.append("  src_nodes.forEach(n => ids.add(n.id));\n")
    out.append("  const nl = src_links.filter(l => ids.has(l.source) && ids.has(l.target));\n")
    out.append("  return { prefix, nodes: src_nodes, links: nl, hubs: new Set(src_nodes.map(n => n.id)) };\n")
    out.append("}\n")
    out.append("\n")
    out.append("function initDashboard(){\n")
    out.append("  if(typeof d3 === 'undefined'){ document.body.insertAdjacentHTML('afterbegin', '<div style=\"padding:12px;color:#ffb4b4\">D3 failed to load - cannot render graphs.</div>'); return; }\n")
    out.append("  const gHubs = G_HUBS;\n")
    out.append("  const mHubs = M_HUBS;\n")
    out.append("  initPanel({ prefix: 'g', nodes: G_NODES, links: G_LINKS, hubs: gHubs });\n")
    out.append("  initPanel({ prefix: 'm', nodes: M_NODES, links: M_LINKS, hubs: mHubs });\n")
    out.append("  const gHubNodes = G_NODES.filter(n => gHubs.has(n.id));\n")
    out.append("  const gHubLinks = G_LINKS.filter(l => gHubs.has(l.source) && gHubs.has(l.target));\n")
    out.append("  initPanel({ prefix: 'gh', nodes: gHubNodes, links: gHubLinks, hubs: new Set(gHubNodes.map(n => n.id)) });\n")
    out.append("  const mHubNodes = M_NODES.filter(n => mHubs.has(n.id));\n")
    out.append("  const mHubLinks = M_LINKS.filter(l => mHubs.has(l.source) && mHubs.has(l.target));\n")
    out.append("  initPanel({ prefix: 'mh', nodes: mHubNodes, links: mHubLinks, hubs: new Set(mHubNodes.map(n => n.id)) });\n")
    out.append("  ['g','m','gh','mh'].forEach(p => { const btn = document.getElementById(p + '-fit'); if(btn) btn.onclick = () => { panels[p] && panels[p].fit(); }; });\n")
    out.append("  const input = document.getElementById('search');\n")
    out.append("  if(input) input.addEventListener('input', e => applySearch(e.target.value));\n")
    out.append("}\n")
    out.append("\n")
    out.append("if(document.readyState === 'loading'){ document.addEventListener('DOMContentLoaded', initDashboard); } else { initDashboard(); }\n")
    out.append("\n")
    out.append("window.addEventListener('resize', () => { Object.values(panels).forEach(p => p.fit()); });\n")
    out.append("</script>\n</body>\n</html>\n")
    out.append("\n")
    return "".join(out)


def main():
    g = load_json(GRAPH_PATH)
    m = load_json(MAP_PATH)

    g_nodes = g.get("nodes", [])
    g_links = g.get("links", [])
    m_nodes = m.get("nodes", [])
    m_links = m.get("links", [])

    g_hubs, g_deg = top_hubs(g_nodes, g_links)
    m_hubs, m_deg = top_hubs(m_nodes, m_links)

    g_links_c = cap_edges(g_links, MAX_EDGES_PER_PANEL)
    m_links_c = cap_edges(m_links, MAX_EDGES_PER_PANEL)

    print(f"Graph Memory : {len(g_nodes)} nodes, {len(g_links)} links ({len(g_links_c)} rendered), {len(g_hubs)} hubs")
    print(f"Memory Map   : {len(m_nodes)} nodes, {len(m_links)} links ({len(m_links_c)} rendered), {len(m_hubs)} hubs")

    html = build_html(g_nodes, g_links_c, m_nodes, m_links_c, g_hubs, m_hubs, g_deg, m_deg)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"[OK] wrote {OUT_HTML.name} ({OUT_HTML.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

