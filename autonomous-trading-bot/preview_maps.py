"""Render 2 SVG preview tinh + 2 SVG hub (mo truc tiep trong VSCode).

- preview_graph.svg / preview_map.svg : toan bo nodes (layout xoan oc, 1200 edge dau)
- preview_graph_hubs.svg / preview_map_hubs.svg : top 80 hub theo degree + edge
  noi bo + nhan label -> nhin truc quan, biet ngay nut trung tam.

Run: python preview_maps.py
Xem: mo PREVIEW_MAPS.md roi bam Ctrl+Shift+V (Markdown Preview),
     hoac click truc tiep file .svg trong Explorer.
"""
from __future__ import annotations

import json
import math
import html as _html
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PALETTE = {
    "file": "#789bff", "def": "#7ef1c0", "class": "#f2c14e",
    "concept": "#c792ea", "env": "#ff8a80", "envkey": "#ff8a80",
    "code_file": "#789bff", "code_def": "#7ef1c0", "code_class": "#f2c14e",
    "config": "#f2c14e", "trade": "#7ef1c0", "reflection": "#c792ea",
    "decision": "#ffab91", "bug": "#ff8a80", "concept_hub": "#c792ea",
}
GREY = "#8b9bc7"
MAX_EDGES = 1200
TOP_HUBS = 80

SVG_GRAPH = "preview_graph.svg"
SVG_MAP = "preview_map.svg"
SVG_GRAPH_HUBS = "preview_graph_hubs.svg"
SVG_MAP_HUBS = "preview_map_hubs.svg"
PREVIEW_README = "PREVIEW_README.md"


def _layout(nodes, W=1000, H=750):
    pos = {}
    n = max(len(nodes), 1)
    R = min(W, H) * 0.40
    for i, nd in enumerate(nodes):
        a = i * 2.399963  # golden angle -> trai deu
        rr = R * math.sqrt((i + 1) / n)
        pos[nd["id"]] = (W / 2 + math.cos(a) * rr, H / 2 + math.sin(a) * rr)
    return pos


def _render(data_nodes, data_links, out: Path, title: str, kind_key: str,
            with_labels: bool = False):
    W, H = 1000, 750
    pos = _layout(data_nodes, W, H)
    edges = [(l.get("source"), l.get("target")) for l in data_links
             if l.get("source") in pos and l.get("target") in pos][:MAX_EDGES]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#0f1320"/>',
        f'<text x="16" y="28" fill="#e6e9ff" font-size="16" font-family="sans-serif">{_html.escape(title)}</text>',
        f'<text x="16" y="48" fill="#93a0c4" font-size="12" font-family="sans-serif">nodes={len(data_nodes)} links={len(data_links)} (ve {len(edges)} edge)</text>',
    ]
    for s, t in edges:
        x1, y1 = pos[s]
        x2, y2 = pos[t]
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#2a3350" stroke-width="0.7"/>')
    for nd in data_nodes:
        x, y = pos[nd["id"]]
        kind = str(nd.get(kind_key, nd.get("kind", nd.get("type", ""))))
        c = PALETTE.get(kind, GREY)
        label = str(nd.get("label", nd.get("id")))
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{"9" if with_labels else "6"}" fill="{c}"><title>{_html.escape(label)} [{kind}]</title></circle>')
        if with_labels:
            parts.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" fill="#cfdcff" font-size="10" text-anchor="middle" font-family="sans-serif">{_html.escape(label[:22])}</text>')
    kinds = sorted({str(nd.get(kind_key, nd.get("kind", nd.get("type", "")))) for nd in data_nodes})
    lx = 16
    for k in kinds[:10]:
        c = PALETTE.get(k, GREY)
        parts.append(f'<circle cx="{lx + 6}" cy="{H - 18}" r="5" fill="{c}"/>')
        parts.append(f'<text x="{lx + 15}" y="{H - 14}" fill="#cfdcff" font-size="11" font-family="sans-serif">{_html.escape(k)}</text>')
        lx += len(k) * 7 + 28
    parts.append("</svg>")
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"[OK] {out.name}: {len(data_nodes)} nodes, ve {len(edges)}/{len(data_links)} edges")


def _hub_subset(nodes, links):
    deg = Counter()
    for l in links:
        if l.get("source"):
            deg[l["source"]] += 1
        if l.get("target"):
            deg[l["target"]] += 1
    top = {nid for nid, _ in deg.most_common(TOP_HUBS)}
    sub_n = [n for n in nodes if n["id"] in top]
    sub_l = [l for l in links if l.get("source") in top and l.get("target") in top]
    return sub_n, sub_l, deg


def readme(graph, mapdata, deg_g, deg_m, edge_g, edge_m, edge_gh, edge_mh):
    gn, _, _ = _hub_subset(graph["nodes"], graph["links"])
    mn, _, _ = _hub_subset(mapdata["nodes"], mapdata["links"])
    gtop = [(nid, deg_g[nid]) for nid, _ in deg_g.most_common(6)]
    mtop = [(nid, deg_m[nid]) for nid, _ in deg_m.most_common(6)]
    title_g = f"graph_memory — code structure ({len(graph['nodes'])} nodes)"
    title_m = f"memory_map — code + memories ({len(mapdata['nodes'])} nodes)"
    md = f"""# Bảng điều khiển biểu đồ tương tác (Live + Preview)

Mở file SVG trực tiếp trong Explorer (click vào) và xem trước, hoặc mở `{PREVIEW_README}` rồi bấm `Ctrl+Shift+V` để xem trước markdown. Nếu cần zoom/pan live, mở HTML thực tế: `graph_memory.html`, `memory_map.html`.

## 1. Graph Memory (code structure)

- File: `{SVG_GRAPH}` — {len(graph['nodes'])} nodes, {len(graph['links'])} edges.
  - Hiển thị {edge_g} edge trong SVG preview (giới hạn {MAX_EDGES}).
- Hubs: `{SVG_GRAPH_HUBS}` — {len(gn)} hub trung tâm, có nhãn.
  - Hiển thị {edge_gh} edge trong SVG preview (giới hạn {MAX_EDGES}).

Điểm mạnh (top hub): {gtop}

## 2. Memory Map (code + memories)

- File: `{SVG_MAP}` — {len(mapdata['nodes'])} nodes, {len(mapdata['links'])} edges.
  - Hiển thị {edge_m} edge trong SVG preview (giới hạn {MAX_EDGES}).
- Hubs: `{SVG_MAP_HUBS}` — {len(mn)} hub, có nhãn.
  - Hiển thị {edge_mh} edge trong SVG preview (giới hạn {MAX_EDGES}).

Điểm mạnh (top hub): {mtop}

## Xem nhanh trong VSCode

- Mở tab markdown: `Ctrl+Shift+V` trên `{PREVIEW_README}` -> click vào link SVG trong file.
- Mở file `.svg` trong Explorer -> click chuột phải -> `Open With` -> `SVG Preview` (hoặc extension SVG Preview).
- Mở HTML thực tế nếu cần zoom/pan live: `graph_memory.html`, `memory_map.html`.

## Lưu ý

- SVG preview chỉ hiển thị một phần edge (tối đa {MAX_EDGES}) để không quá nặng; nếu cần toàn bộ, dùng file `.html` có zoom/pan.
- Hubs SVG chỉ hiển thị {TOP_HUBS} nút trung tâm + nhãn (để biết nhanh qui tụ).
"""
    (ROOT / PREVIEW_README).write_text(md, encoding="utf-8")
    print("[OK] PREVIEW_README.md written")
    return md



def main():
    g = json.loads((ROOT / "graph_memory.json").read_text(encoding="utf-8"))
    m = json.loads((ROOT / "memory_map_data.json").read_text(encoding="utf-8"))
    edge_g = _render(g["nodes"], g["links"], ROOT / SVG_GRAPH,
                     f"graph_memory — code structure ({len(g['nodes'])} nodes)", "type")
    edge_m = _render(m["nodes"], m["links"], ROOT / SVG_MAP,
                     f"memory_map — code + memories ({len(m['nodes'])} nodes)", "kind")
    gn, gl, gdeg = _hub_subset(g["nodes"], g["links"])
    mn, ml, mdeg = _hub_subset(m["nodes"], m["links"])
    edge_gh = _render(gn, gl, ROOT / SVG_GRAPH_HUBS,
                      f"graph_memory HUBS — top {len(gn)} nut (tong {len(g['nodes'])} nodes)", "type", with_labels=True)
    edge_mh = _render(mn, ml, ROOT / SVG_MAP_HUBS,
                      f"memory_map HUBS — top {len(mn)} nut (tong {len(m['nodes'])} nodes)", "kind", with_labels=True)
    md = readme(g, m, gdeg, mdeg, edge_g, edge_m, edge_gh, edge_mh)
    (ROOT / PREVIEW_README).write_text(md, encoding="utf-8")
    print("[OK] PREVIEW_README.md written")
    print("SVG files:")
    for p in [SVG_GRAPH, SVG_MAP, SVG_GRAPH_HUBS, SVG_MAP_HUBS]:
        fp = ROOT / p
        print(" -", fp.name, fp.stat().st_size, "bytes")
    print("DONE 4 SVG + PREVIEW_README.md")
if __name__ == "__main__":
    main()

