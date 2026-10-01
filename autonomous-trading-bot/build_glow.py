# -*- coding: utf-8 -*-
"""build_glow.py - sinh glow_map.html: dashboard 3D "star cluster" (offline).

Tai hien giao dien 3D cua memory-mcp/graph-ui (node = instanced sphere to mau
theo "spectral class", edge = LineSegments AdditiveBlending, hau xu ly
UnrealBloom) bang Canvas2D + bloom pass 'lighter', KHONG dung thu vien ngoai
nen mo truc tiep bang file:// duoc (khong CDN, khong CORS, khong node_modules).

Cac thong so duoc copy dung tu graph-ui:
  - spectral palette (lib/colors.ts STELLAR_LEGEND): O 50+ -> M 0-1 connection
  - node glow boost theo channel dominance (lib/density.ts nodeGlowBoost)
  - edge intensity: cung cluster 0.25 / khac cluster 0.06, nhan voi
    1/sqrt(edgeCount) de khong bi "white blob" (lib/density.ts edgeIntensityScale)
  - bloom: luminanceThreshold 0.3 / smoothing 0.7 / intensity 1.45 / radius 0.6
  - highlight: node khong duoc chon bi nhan 0.15 (NodeCloud.nodeColor)
  - idle 60s -> tu xoay (GraphScene.IdleAutoRotate)

Nguon : graph_memory.json, memory_map_data.json
Xuat  : glow_map.html   (data + layout 3D nhung san inline)
Chay  : python build_glow.py

3 kieu "khoi cau" (chi khac toa do node; edge + hieu ung dung chung):
  cluster - force layout (mac dinh, giong graph-ui)      -> pos
  shell   - vo cau rai deu Fibonacci, ban kinh dung 1.0  -> posShell
  ball    - khoi cau dac, mat do deu theo the tich       -> posBall
Ve tinh (mem:*) cung co 3 bo toa do tuong ung: sat.pos / sat.posShell / sat.posBall.

Lop "tin hieu truy xuat AI" (bus __GSL dung chung 2 engine):
  glow_signals.js + glow_signals_lib.js + glow_signals.css duoc nhung NGUYEN VAN
  vao CA HAI ban render (placeholder __GLOW_SIGNALS_LIB__ / /*__GLOW_SIGNALS_CSS__*/)
  -> HUD + logic truy xuat + dong bo giong het nhau. Toggle rieng #fxSignals
  (ngoai 7 hieu ung goc).
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "glow_map_template.html"
WEBGL_TEMPLATE = ROOT / "glow_map_webgl_template.html"
WEBGL_ENGINE = ROOT / "glow_map_webgl_engine.js"
OUT = ROOT / "glow_map.html"
WEBGL_OUT = ROOT / "glow_map_webgl.html"
VENDOR = ROOT / "vendor" / "three"
CROSS_PATH = ROOT / "cross_index.json"
MEM_PATH = ROOT / "memory_map_data.json"

SAT_RADIUS = 2.15        # ban kinh vo ve tinh (galaxy chinh = qua cau ban kinh 1)
SAT_COLOR = "#c084fc"    # node ky uc (mem:*)
CROSS_COLOR = "#fb923c"  # cross edge giua 2 galaxy

DATASETS = [
    ("Graph Memory", ROOT / "graph_memory.json"),
    ("Memory Map", ROOT / "memory_map_data.json"),
]

# ── Palette (copy tu graph-ui/src/lib) ──────────────────────────────────────
NODE_KIND_COLORS = {
    "file": "#3b82f6", "code_file": "#3b82f6",
    "def": "#06b6d4", "code_def": "#06b6d4",
    "class": "#a855f7", "code_class": "#a855f7",
    "env": "#22c55e", "config": "#22c55e",
    "envkey": "#eab308",
    "state": "#f97316",
    "concept": "#64748b",
    "reflection": "#ec4899",
}
NODE_KIND_DEFAULT = "#94a3b8"

EDGE_TYPE_COLORS = {
    "CALLS": "#1DA27E",
    "defines": "#a855f7",
    "import": "#3b82f6",
    "emits": "#eab308",
    "SIMILAR_TO": "#f97316",
    "SEMANTICALLY_RELATED": "#e879f9",
    "RELATED_TO": "#22c55e",
    "APPLIES_TO": "#eab308",
    "FOUND_IN": "#64748b",
    "MEMBER_OF": "#64748b",
    "CROSS_LINK": CROSS_COLOR,
}
EDGE_TYPE_DEFAULT = "#1C8585"

# (degree nguong, mau) - STELLAR_LEGEND, index 0 = O (hub) .. 6 = M (leaf)
STELLAR = [
    (50, "#80a0ff", "O"),
    (26, "#c0d0ff", "B"),
    (13, "#e8e8ff", "A"),
    (7, "#fff0c0", "F"),
    (4, "#ffe080", "G"),
    (2, "#ffa060", "K"),
    (0, "#ff6050", "M"),
]

# Trong so spring cho layout: quan he cau truc hut manh hon quan he ngu nghia
SPRING_WEIGHT = {
    "defines": 1.0, "CALLS": 1.0, "import": 0.9, "emits": 0.8,
    "SIMILAR_TO": 0.45, "SEMANTICALLY_RELATED": 0.4,
    "RELATED_TO": 0.5, "APPLIES_TO": 0.5, "FOUND_IN": 0.7,
}
SPRING_DEFAULT = 0.7


def spectral_index(deg: int) -> int:
    for i, (lo, _c, _k) in enumerate(STELLAR):
        if deg >= lo:
            return i
    return len(STELLAR) - 1


def load_dataset(path: Path):
    """Doc 1 file JSON (graph_memory / memory_map) -> (nodes, links) chuan hoa.

    graph_memory: node {id,label,type,file?}, link {source,target,label}
    memory_map  : node {id,label,kind,file?}, link {source,target,rel,w?}
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes, links = [], []
    for n in data.get("nodes", []):
        kind = n.get("type") or n.get("kind") or "unknown"
        nodes.append({
            "id": str(n.get("id")),
            "label": str(n.get("label") or n.get("id")),
            "kind": str(kind),
            "file": n.get("file"),
        })
    for l in data.get("links") or data.get("edges") or []:
        rel = l.get("label") or l.get("rel") or l.get("type") or "related"
        links.append({
            "source": str(l.get("source")),
            "target": str(l.get("target")),
            "rel": str(rel),
            "w": float(l.get("w") or 1.0),
        })
    return nodes, links
def fib_sphere(n: int, radius: float, rng, jitter: float = 0.06):
    """n diem rai deu tren vo cau ban kinh radius (+ jitter)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / max(n, 1))
    theta = np.pi * (1 + 5 ** 0.5) * i
    p = np.stack([np.cos(theta) * np.sin(phi),
                  np.sin(theta) * np.sin(phi),
                  np.cos(phi)], axis=1)
    return p * radius + rng.normal(0, jitter, p.shape)


def load_mem_galaxy():
    """Galaxy ve tinh = cac node ky uc (mem:*) trong memory_map_data.json.

    Tra ve (nodes_by_id, edges) - chi giu edge noi 2 node mem voi nhau.
    """
    if not MEM_PATH.exists():
        return {}, []
    data = json.loads(MEM_PATH.read_text(encoding="utf-8"))
    nodes = {}
    for nd in data.get("nodes", []):
        nid = str(nd.get("id"))
        if nid.startswith("mem:"):
            nodes[nid] = {"id": nid, "label": str(nd.get("label") or nid),
                          "file": nd.get("file")}
    edges = []
    for l in data.get("links") or data.get("edges") or []:
        s, t = str(l.get("source")), str(l.get("target"))
        if s in nodes and t in nodes:
            edges.append((s, t, str(l.get("label") or l.get("rel") or "RELATED_TO")))
    return nodes, edges


_MEM_CACHE: dict = {}
_CROSS_CACHE: dict = {}


def mem_galaxy():
    """Cache lai galaxy ve tinh (doc 1 lan)."""
    if "v" not in _MEM_CACHE:
        _MEM_CACHE["v"] = load_mem_galaxy()
    return _MEM_CACHE["v"]


def cross_index() -> dict:
    """Cache cross_index.json (map graph id <-> map id)."""
    if "v" not in _CROSS_CACHE:
        try:
            _CROSS_CACHE["v"] = json.loads(CROSS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print("WARN cross_index:", e)
            _CROSS_CACHE["v"] = {}
    return _CROSS_CACHE["v"]


def build_satellites(node_ids, pos_by_id, mem_nodes, mem_edges, cross):
    """Vo ve tinh + cross edge (giong linked_projects + cross_edges cua graph-ui).

    Moi entry cross_index (sym:/file:) noi 1 node cua galaxy chinh voi 1 node
    mem:* -> ve tinh duoc day ra xa theo huong node chinh, hop thanh vo cau thu 2.
    """
    if not cross or not mem_nodes:
        return None
    links = []
    for ent in cross.get("entities", {}).values():
        mains = [g for g in ent.get("graph", []) if g in node_ids]
        mems = [m for m in ent.get("map", []) if m in mem_nodes]
        for g in mains[:2]:
            for m in mems[:2]:
                links.append((g, m))
    if not links:
        return None

    rng = np.random.default_rng(11)
    sat_ids = sorted({m for _g, m in links})
    idx = {sid: i for i, sid in enumerate(sat_ids)}
    pos = np.zeros((len(sat_ids), 3), dtype=np.float64)
    placed = np.zeros(len(sat_ids), dtype=bool)
    for g, m in links:                       # huong = huong node chinh lien ket
        i = idx[m]
        if placed[i]:
            continue
        base = pos_by_id.get(g)
        if base is None:
            continue
        v = np.asarray(base, dtype=np.float64) + rng.normal(0, 0.12, 3)
        norm = float(np.linalg.norm(v)) or 1.0
        pos[i] = v / norm * (SAT_RADIUS + float(rng.normal(0, 0.14)))
        placed[i] = True
    free = int((~placed).sum())
    if free:
        pos[~placed] = fib_sphere(free, SAT_RADIUS, rng, jitter=0.2)

    sat_edges, deg = [], [0] * len(sat_ids)
    for s, t, rel in mem_edges:
        if s in idx and t in idx and s != t:
            si, ti = idx[s], idx[t]
            sat_edges.extend([si, ti, 1, 1])
            deg[si] += 1
            deg[ti] += 1

    cross_flat = []
    for g, m in links:
        gi, si = node_ids.get(g), idx.get(m)
        if gi is None or si is None:
            continue
        cross_flat.extend([gi, si])
        deg[si] += 1

    return {
        "name": "Memory records",
        "color": SAT_COLOR,
        "pos": [round(float(v), 4) for v in pos.reshape(-1)],
        "label": [mem_nodes[sid]["label"] for sid in sat_ids],
        "id": sat_ids,
        "deg": deg,
        "spec": [spectral_index(d) for d in deg],
        "edges": sat_edges,
        "cross": cross_flat,
        "radial": SAT_RADIUS,
    }

def force_layout(n: int, src: np.ndarray, tgt: np.ndarray, w: np.ndarray,
                 iterations: int = 200, seed: int = 7):
    """Layout 3D: khoi cau Fibonacci + Coulomb repulsion + spring theo edge.

    Tra ve float32 (n,3) da chuan hoa ve ban kinh max = 1.0. Layout tinh san o
    Python (numpy, vector hoa) de browser chi viec render -> khong giat khi mo.
    """
    rng = np.random.default_rng(seed)
    # Khoi cau Fibonacci (phan bo deu tren mat cau) = trang thai dau on dinh
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    pos = np.stack([np.cos(theta) * np.sin(phi),
                    np.sin(theta) * np.sin(phi),
                    np.cos(phi)], axis=1).astype(np.float64)
    pos += rng.normal(0, 0.02, pos.shape)
    vel = np.zeros_like(pos)

    repel = 0.011          # day ra (Coulomb)
    spring = 0.32          # hut theo canh
    rest = 0.055           # do dai canh tu nhien
    shell = 0.030          # giu node tren vo cau ban kinh 1 -> hinh "qua cau sao"
    damping = 0.82
    dt = 1.0

    for _ in range(iterations):
        diff = pos[:, None, :] - pos[None, :, :]          # (n,n,3)
        dist2 = np.einsum("ijk,ijk->ij", diff, diff)
        np.fill_diagonal(dist2, np.inf)
        dist = np.sqrt(dist2)
        coeff = repel / (dist2 * dist)                    # |F| = repel/dist^2
        acc = np.einsum("ij,ijk->ik", coeff, diff)

        if len(src):
            sv = pos[src] - pos[tgt]
            sd = np.sqrt(np.einsum("ij,ij->i", sv, sv)) + 1e-9
            mag = (spring * w * (sd - rest) / sd)[:, None]
            f = mag * sv
            np.add.at(acc, src, -f)
            np.add.at(acc, tgt, f)

        rad = np.sqrt(np.einsum("ij,ij->i", pos, pos)) + 1e-9
        acc -= (shell * (rad - 1.0) / rad)[:, None] * pos  # keo ve vo cau r=1

        vel = (vel + acc * dt) * damping
        speed = np.sqrt(np.einsum("ij,ij->i", vel, vel)) + 1e-9
        too_fast = speed > 0.08                            # chan "no so"
        if too_fast.any():
            vel[too_fast] *= (0.08 / speed[too_fast])[:, None]
        pos = pos + vel * dt

    pos -= pos.mean(axis=0)
    rad = np.sqrt(np.einsum("ij,ij->i", pos, pos))
    scale = float(rad.max()) or 1.0
    return (pos / scale).astype(np.float32)


# ── Cac kieu "khoi cau" (deu la 3D that, chi khac cach rai node) ──────────────
LAYOUTS = ["cluster", "shell", "ball"]


def sphere_shell(n: int, radius: float = 1.0) -> np.ndarray:
    """Vo cau: n diem rai deu kieu Fibonacci tren mat cau ban kinh radius.

    Khoang cach giua cac diem gan bang nhau -> khi xoay nhin ro hinh cau
    (khong bi don cuc nhu chia theo vi do).
    """
    n = max(n, 1)
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    p = np.stack([np.cos(theta) * np.sin(phi),
                  np.sin(theta) * np.sin(phi),
                  np.cos(phi)], axis=1)
    return (p * radius).astype(np.float32)


def solid_ball(n: int, radius: float = 1.0, seed: int = 13) -> np.ndarray:
    """Khoi cau dac: huong Fibonacci x ban kinh ~ cbrt(u).

    Ban kinh lay theo phan vi the tich -> mat do node deu trong ca khoi cau
    (khong bi dac o vo nhu force_layout). Chan duoi 0.10*R de khong co node
    nam dung tam (tam bi che hoan toan, khong nhin thay).
    """
    n = max(n, 1)
    rng = np.random.default_rng(seed)
    r = radius * (0.10 + 0.90 * np.cbrt(rng.random(n)))
    return sphere_shell(n, 1.0) * r[:, None]


def radius_stats(pos: np.ndarray) -> tuple[float, float]:
    """(ban kinh min, max) - dung cho log/test."""
    rad = np.sqrt(np.einsum("ij,ij->i", pos, pos))
    return float(rad.min()), float(rad.max())


def cluster_of(node: dict) -> str:
    """Nhom node theo file/don vi (dung cho do sang edge + danh sach ben trai)."""
    if node.get("file"):
        return str(node["file"])
    nid = node["id"]
    if "::" in nid:
        return nid.split("::")[0]
    if ":" in nid:
        return nid.split(":", 1)[1].split("::")[0]
    return nid
def build_payload(name: str, path: Path) -> dict:
    """Tinh degree / spectral / cluster / palette + layout 3D cho 1 dataset."""
    nodes, links = load_dataset(path)
    n = len(nodes)
    index = {nd["id"]: i for i, nd in enumerate(nodes)}

    edges, deg = [], [0] * n
    for l in links:
        si = index.get(l["source"])
        ti = index.get(l["target"])
        if si is None or ti is None or si == ti:
            continue
        deg[si] += 1
        deg[ti] += 1
        edges.append((si, ti, l["rel"], l["w"]))

    kinds, kcount = {}, {}
    clusters, ccount = {}, {}
    for i, nd in enumerate(nodes):
        k = nd["kind"]
        if k not in kinds:
            kinds[k] = len(kinds)
        kcount[k] = kcount.get(k, 0) + 1
        c = cluster_of(nd)
        if c not in clusters:
            clusters[c] = len(clusters)
        ccount[c] = ccount.get(c, 0) + 1

    types, tcount = {}, {}
    for _s, _t, rel, _w in edges:
        if rel not in types:
            types[rel] = len(types)
        tcount[rel] = tcount.get(rel, 0) + 1

    spec = [spectral_index(d) for d in deg]
    spec_count = [0] * len(STELLAR)
    for s in spec:
        spec_count[s] += 1

    src = np.array([e[0] for e in edges], dtype=np.int64)
    tgt = np.array([e[1] for e in edges], dtype=np.int64)
    wgt = np.array([SPRING_WEIGHT.get(e[2], SPRING_DEFAULT) * e[3] for e in edges],
                   dtype=np.float64)
    iterations = 200 if n <= 600 else 130
    pos = force_layout(n, src, tgt, wgt, iterations=iterations)
    # 2 kieu khoi cau khac: vo cau deu (Fibonacci) + khoi cau dac (mat do the tich)
    pos_shell = sphere_shell(n, 1.0)
    pos_ball = solid_ball(n, 1.0)

    # Edge list phang: [srcIdx, tgtIdx, typeIdx, sameCluster]
    cluster_idx = [clusters[cluster_of(nd)] for nd in nodes]
    flat_edges = []
    for si, ti, rel, _w in edges:
        flat_edges.extend([si, ti, types[rel], 1 if cluster_idx[si] == cluster_idx[ti] else 0])

    hubs = sorted(range(n), key=lambda i: -deg[i])[:60]

    # Galaxy ve tinh (node ky uc mem:*) - chi khi galaxy chinh chua co mem:*
    sat = None
    if not any(nid.startswith("mem:") for nid in index):
        mem_nodes, mem_edges = mem_galaxy()
        cross = cross_index()
        variants = {}
        for key, arr in (("cluster", pos), ("shell", pos_shell), ("ball", pos_ball)):
            by_id = {nodes[i]["id"]: arr[i].tolist() for i in range(n)}
            st = build_satellites(index, by_id, mem_nodes, mem_edges, cross)
            if st:
                variants[key] = st
        if variants:
            sat = variants.get("cluster") or next(iter(variants.values()))
            # Ve tinh o vo ban kinh SAT_RADIUS: huong tia theo node chinh cua
            # tung kieu layout -> cross link ngan, khong cat qua khoi cau.
            sat["posShell"] = variants["shell"]["pos"] if "shell" in variants else sat["pos"]
            sat["posBall"] = variants["ball"]["pos"] if "ball" in variants else sat["pos"]

    return {
        "name": name,
        "pos": [round(float(v), 4) for v in pos.reshape(-1)],
        "posShell": [round(float(v), 4) for v in pos_shell.reshape(-1)],
        "posBall": [round(float(v), 4) for v in pos_ball.reshape(-1)],
        "layouts": list(LAYOUTS),
        "id": [nd["id"] for nd in nodes],
        "label": [nd["label"] for nd in nodes],
        "kind": [kinds[nd["kind"]] for nd in nodes],
        "cluster": cluster_idx,
        "deg": deg,
        "spec": spec,
        "edges": flat_edges,
        "kinds": [[k, NODE_KIND_COLORS.get(k, NODE_KIND_DEFAULT), kcount[k]]
                  for k in sorted(kinds, key=lambda k: -kcount[k])],
        "types": [[t, EDGE_TYPE_COLORS.get(t, EDGE_TYPE_DEFAULT), tcount[t]]
                  for t in sorted(types, key=lambda t: -tcount[t])],
        "clusters": [c for c in sorted(clusters, key=lambda k: clusters[k])],
        "clusterCount": [ccount[c] for c in sorted(clusters, key=lambda k: clusters[k])],
        "stellar": [[STELLAR[i][2], STELLAR[i][1], spec_count[i]]
                    for i in range(len(STELLAR))],
        "hubs": [[i, deg[i]] for i in hubs],
        "sat": sat,
        "stats": {"nodes": n, "edges": len(edges), "iterations": iterations,
                  "sat": len(sat["id"]) if sat else 0},
    }


def render_canvas2d(payload: dict) -> None:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    signals = _signals_lib()
    css = SIGNALS_CSS.read_text(encoding="utf-8") if SIGNALS_CSS.exists() else ""
    if "</style" in css:
        raise ValueError("signals css chua the </style>")
    html = (tpl.replace("__GLOW_PAYLOAD__", blob)
               .replace("__GLOW_SIGNALS_LIB__", signals)
               .replace("/*__GLOW_SIGNALS_CSS__*/", css))
    for ph in ("__GLOW_PAYLOAD__", "__GLOW_SIGNALS_LIB__", "/*__GLOW_SIGNALS_CSS__*/"):
        assert ph not in html, f"con placeholder chua thay the (canvas2d): {ph}"
    OUT.write_text(html, encoding="utf-8")
    print(f"[out] {OUT.name}  {OUT.stat().st_size / 1024:,.0f} KB")


VENDOR_FILES = ["three.min.js", "CopyShader.js", "LuminosityHighPassShader.js",
                "BokehShader.js", "MaskPass.js", "EffectComposer.js", "RenderPass.js",
                "ShaderPass.js", "UnrealBloomPass.js", "BokehPass.js", "OrbitControls.js"]
SIGNALS_LIB = ROOT / "glow_signals.js"
SIGNALS_BUS = ROOT / "glow_signals_lib.js"
SIGNALS_CSS = ROOT / "glow_signals.css"


def _signals_lib() -> str:
    """Kernel + bus DUNG CHUNG cho 2 engine (nhung nguyen van -> dong bo)."""
    kernel = SIGNALS_LIB.read_text(encoding="utf-8") if SIGNALS_LIB.exists() else ""
    bus = SIGNALS_BUS.read_text(encoding="utf-8") if SIGNALS_BUS.exists() else ""
    lib = (kernel + "\n" + bus).strip()
    assert lib and "window.__GSL" in lib, "thieu glow_signals_lib.js / GS"
    if "</script" in lib:
        raise ValueError("signals lib chua the </script>")
    return lib


def render_webgl(payload: dict) -> None:
    """Ban WebGL: nhung three.js + UnrealBloomPass + BokehPass (van offline)."""
    if not WEBGL_TEMPLATE.exists():
        print("[skip] webgl: chua co glow_map_webgl_template.html")
        return
    if not WEBGL_ENGINE.exists():
        print("[skip] webgl: chua co glow_map_webgl_engine.js")
        return
    missing = [f for f in VENDOR_FILES if not (VENDOR / f).exists()]
    if missing:
        print("[skip] webgl: thieu vendor/three/" + ", ".join(missing))
        return
    libs = []
    for name in VENDOR_FILES:
        body = (VENDOR / name).read_text(encoding="utf-8")
        if "</script" in body:
            raise ValueError(f"{name} chua the </script>")
        libs.append("<script>\n" + body + "\n</script>\n")
    engine = WEBGL_ENGINE.read_text(encoding="utf-8")
    if "</script" in engine:
        raise ValueError("webgl engine chua the </script>")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    signals = _signals_lib()
    css = SIGNALS_CSS.read_text(encoding="utf-8") if SIGNALS_CSS.exists() else ""
    html = (WEBGL_TEMPLATE.read_text(encoding="utf-8")
            .replace("__GLOW_VENDOR__", "".join(libs))
            .replace("__GLOW_SIGNALS_LIB__", signals)
            .replace("/*__GLOW_SIGNALS_CSS__*/", css)
            .replace("__GLOW_ENGINE__", engine)
            .replace("__GLOW_PAYLOAD__", blob))
    for ph in ("__GLOW_VENDOR__", "__GLOW_ENGINE__", "__GLOW_PAYLOAD__",
               "__GLOW_SIGNALS_LIB__", "/*__GLOW_SIGNALS_CSS__*/"):
        assert ph not in html, f"con placeholder chua thay the (webgl): {ph}"
    WEBGL_OUT.write_text(html, encoding="utf-8")
    print(f"[out] {WEBGL_OUT.name}  {WEBGL_OUT.stat().st_size / 1024:,.0f} KB")


def main() -> None:
    t0 = time.time()
    payload = {"generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "datasets": []}
    for name, path in DATASETS:
        if not path.exists():
            print(f"[skip] {name}: khong thay {path.name}")
            continue
        ds = build_payload(name, path)
        payload["datasets"].append(ds)
        s = ds["stats"]
        rmin, rmax = radius_stats(np.asarray(ds["posShell"], dtype=np.float64).reshape(-1, 3))
        print(f"[ok] {name:14s} {s['nodes']:5d} nodes / {s['edges']:6d} edges "
              f"({s['iterations']} iters)"
              + (f" + ve tinh {s['sat']}" if s["sat"] else "")
              + f" | layouts {','.join(ds['layouts'])} (vo cau r={rmin:.3f}..{rmax:.3f})")

    try:
        import glow_retrieval as _R
        _docs = _R.load_all_docs(ROOT)
        payload["signature"] = _R.fingerprint(
            {n: (d, l) for n, (d, l, _f) in _docs.items()})
        _ev = _R.read_events(ROOT / "retrieval_log.jsonl")
        _info = [{"name": n, "nodes": len(d), "edges": len(l),
                  "tokens": sum(max(_R.MIN_DOC_TOKENS, x["tokens"]) for x in d)}
                 for n, (d, l, _f) in _docs.items()]
        payload["signals"] = _R.snapshot(
            _ev, copy.deepcopy(_R.AGENTS), _info, payload["signature"])
        print(f"[ok] signals: {len(_ev)} events, {len(_R.AGENTS)} agents, "
              f"sig={payload['signature']}")
    except Exception as e:
        print(f"[warn] signals: bo qua ({e})")

    render_canvas2d(payload)
    render_webgl(payload)
    print(f"[done] {time.time() - t0:.1f}s")



if __name__ == "__main__":
    main()

