/* ════════════════════════════════════════════════════════════════════
 * GLOW WEBGL ENGINE — three.js r128 UMD + UnrealBloomPass (THẬT)
 * + BokehPass (DoF THẬT) + OrbitControls.
 *
 * Chung payload + shell (CSS/DOM/sidebar) với bản Canvas2D, vẫn offline
 * và mở bằng file:// được (classic scripts, không ES module, không fetch).
 * Fallback: không có WebGL -> hiện banner + link sang bản Canvas2D.
 * ════════════════════════════════════════════════════════════════════ */

/* ── 0. Bẫy lỗi sớm ─────────────────────────────────────────────────────── */
const WERR = document.getElementById('err');
function wfail(msg){
  WERR.style.display = 'block';
  WERR.textContent += msg + '\n';
  document.title = 'GLOW_WGL_ERR ' + msg;
}
window.addEventListener('error', e => wfail('JS error: ' + (e.message || e.type)));
window.__glowFail = wfail;
const w$ = id => document.getElementById(id);

/* ── 1. Hằng số (đồng bộ với bản Canvas2D + graph-ui) ───────────────────── */
const W_EDGE_REF = 2500, W_EDGE_MIN = 0.05;
const W_SAME = 0.25, W_CROSS = 0.06;             /* EdgeLines.tsx */
const W_BLOOM = { strength: 1.45, radius: 0.6, threshold: 0.3 }; /* GraphScene */
const W_DOF = { focus: 3.4, aperture: 0.00013, maxblur: 0.009 };
const W_CROSS_COLOR = '#fb923c', W_FLOW_COLOR = '#fdba74';
const W_CAM = { fov: 50, near: 0.05, far: 2000, dist: 3.7, min: 0.5, max: 80 };
const W_IDLE_MS = 60000, W_LABEL_MAX = 70;
/* Kiểu khối cầu 3D (chỉ đổi TOẠ ĐỘ - edge + 7 hiệu ứng giữ nguyên) */
const W_LAYOUTS = [['cluster', 'Cụm sao'], ['shell', 'Vỏ cầu'], ['ball', 'Cầu đặc']];
let wlayout = 'cluster';
function wSatScale(sv, i){
  return 0.009 + 0.036 * Math.cbrt(sv.deg[i] / sv.degMax);
}

function wEdgeScale(n){
  if (n <= W_EDGE_REF) return 1;
  return Math.max(W_EDGE_MIN, Math.sqrt(W_EDGE_REF / n));
}
function wGlowBoost(r, g, b){
  return 1.35 + Math.max(0, b - Math.max(r, g)) * 2.4
             + Math.max(0, r - Math.max(g, b)) * 0.9;
}
function wHex(h){
  const v = parseInt(h.slice(1), 16);
  return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255];
}

/* ── 2. Trạng thái ──────────────────────────────────────────────────────── */
const wview = { zoom: 1, panX: 0, panY: 0, idle: Date.now() };
const wdisplay = { edge: 1, glow: 1, bloom: 1, labels: true, hubOnly: false };
const wfilter = { kinds: null, types: null, cluster: null, needle: '' };
const wfx = { twinkle: true, dof: true, flow: true, ripple: true, sat: true,
              nebula: true, auto: true };
let WDS = null, WP = null, WGL = null;
let wselected = null, whighlight = null, whover = null, whoverSat = -1;
let wripples = [], wtNow = 0, wframes = 0, wneed = true, wfly = null, wdrag = null, wmoved = 0;
const WCLAMP = (v, lo, hi) => (v < lo ? lo : (v > hi ? hi : v));

/* Texture glow dùng cho flow particles + nebula sprite (kiểu point sprite) */
let wGlowTex = null;
function wGetGlowTex(){
  if (wGlowTex) return wGlowTex;
  const s = 64, c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d'), r = s / 2;
  const gr = g.createRadialGradient(r, r, 0, r, r, r);
  gr.addColorStop(0, 'rgba(255,255,255,1)');
  gr.addColorStop(0.4, 'rgba(255,255,255,0.5)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, s, s);
  wGlowTex = new THREE.CanvasTexture(c);
  return wGlowTex;
}

/* ── 3. Chuẩn bị dữ liệu (nằm trong RAM GPU: buffer positions/colors) ─────── */
function wPrepare(ds){
  const n = ds.id.length, m = ds.edges.length / 4;
  const specColors = ds.stellar.map(s => s[1]);
  const degMax = ds.deg.reduce((a, b) => Math.max(a, b), 1);
  const p = {
    n, m, ds, E: Int32Array.from(ds.edges),
    posSrc: {
      cluster: Float32Array.from(ds.pos),
      shell: Float32Array.from(ds.posShell || ds.pos),
      ball: Float32Array.from(ds.posBall || ds.pos)
    },
    pos: null,
    deg: Int32Array.from(ds.deg),
    kind: Int32Array.from(ds.kind),
    cluster: Int32Array.from(ds.cluster),
    spec: Int32Array.from(ds.spec),
    boost: new Float32Array(n), sizeW: new Float32Array(n),
    colBase: new Float32Array(n * 3), colNow: new Float32Array(n * 3),
    phase: new Float32Array(n),
    adj: new Array(n), visible: new Uint8Array(n).fill(1),
    scale: edgeIntensityScaleX(m)
  };
  p.pos = p.posSrc[wlayout] || p.posSrc.cluster;
  function edgeIntensityScaleX(c){
    if (c <= W_EDGE_REF) return 1;
    return Math.max(W_EDGE_MIN, Math.sqrt(W_EDGE_REF / c));
  }
  for (let i = 0; i < n; i++){
    p.adj[i] = [];
    const c = wHex(specColors[p.spec[i]] || '#94a3b8');
    p.boost[i] = wGlowBoost(c[0], c[1], c[2]);
    p.sizeW[i] = 0.008 + 0.038 * Math.cbrt(p.deg[i] / degMax);
    p.colBase[i * 3] = c[0]; p.colBase[i * 3 + 1] = c[1]; p.colBase[i * 3 + 2] = c[2];
    p.phase[i] = ((i * 2654435761) % 1024) / 1024 * 6.2832;
  }
  for (let e = 0; e < m; e++){
    const s = p.E[e * 4], t = p.E[e * 4 + 1];
    p.adj[s].push(t); p.adj[t].push(s);
  }
  const key = e => p.E[e * 4 + 2] * 2 + p.E[e * 4 + 3];
  const order = Array.from({ length: m }, (_, e) => e).sort((a, b) => key(a) - key(b));
  const tcol = ds.types.map(t => wHex(t[1] || '#1C8585'));
  let i = 0;
  p.buckets = [];
  while (i < m){
    const k0 = key(order[i]);
    let j = i;
    while (j < m && key(order[j]) === k0) j++;
    const ti = Math.floor(k0 / 2), same = k0 % 2;
    p.buckets.push({ idx: Int32Array.from(order.slice(i, j)),
                     rgb: tcol[ti] || [0.11, 0.52, 0.52], type: ti,
                     base: same ? W_SAME : W_CROSS });
    i = j;
  }
  const ranking = Array.from({ length: n }, (_, k) => k).sort((a, b) => p.deg[b] - p.deg[a]);
  p.radial = ranking.slice(0, 60);
  p.labelIdx = ranking.slice(0, W_LABEL_MAX);
  p.sat = ds.sat ? wPrepareSat(ds.sat) : null;
  return p;
}

function wPrepareSat(s){
  const n = s.id.length;
  const c = wHex(s.color);
  const g = {
    name: s.name, label: s.label, n, color: s.color, rgb: c,
    posSrc: {
      cluster: Float32Array.from(s.pos),
      shell: Float32Array.from(s.posShell || s.pos),
      ball: Float32Array.from(s.posBall || s.pos)
    },
    pos: null,
    deg: Int32Array.from(s.deg),
    edges: Int32Array.from(s.edges),
    cross: Int32Array.from(s.cross),
    mainOf: new Int32Array(n).fill(-1),
    boost: new Float32Array(n),
    colBase: new Float32Array(n * 3),
    phase: new Float32Array(n),
    visible: new Uint8Array(n).fill(1)
  };
  for (let e = 0; e < g.cross.length; e += 2) g.mainOf[g.cross[e + 1]] = g.cross[e];
  const degMax = s.deg.reduce((a, b) => Math.max(a, b), 1);
  const b0 = wGlowBoost(c[0], c[1], c[2]);
  for (let i = 0; i < n; i++){
    g.boost[i] = b0;
    g.phase[i] = ((i * 40503) % 997) / 997 * 6.2832;
    g.deg[i] = s.deg[i];
    g.colBase[i * 3] = c[0]; g.colBase[i * 3 + 1] = c[1]; g.colBase[i * 3 + 2] = c[2];
  }
  g.degMax = degMax;
  g.pos = g.posSrc[wlayout] || g.posSrc.cluster;
  return g;
}

/* Lọc theo sidebar */
function wApplyFilters(){
  const p = WP;
  for (let i = 0; i < p.n; i++){
    let ok = true;
    if (whighlight) ok = whighlight.has(i);
    if (ok && wdisplay.hubOnly && p.deg[i] < 7) ok = false;
    if (ok && wfilter.kinds && !wfilter.kinds.has(p.kind[i])) ok = false;
    if (ok && wfilter.cluster !== null && p.cluster[i] !== wfilter.cluster) ok = false;
    p.visible[i] = ok ? 1 : 0;
  }
  if (p.sat){
    const on = (wfx.sat && wfilter.cluster === null) ? 1 : 0;
    for (let i = 0; i < p.sat.n; i++) p.sat.visible[i] = on;
  }
}

/* ── 4. Dựng scene (renderer + camera + passes + galaxies) ────────────────── */
function wMakeNebulaTexture(r1, g1, b1){
  const s = 256, c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d'), r = s / 2;
  const gr = g.createRadialGradient(r, r, 0, r, r, r);
  gr.addColorStop(0, 'rgba(' + r1 + ',' + g1 + ',' + b1 + ',0.85)');
  gr.addColorStop(0.5, 'rgba(' + r1 + ',' + g1 + ',' + b1 + ',0.28)');
  gr.addColorStop(1, 'rgba(' + r1 + ',' + g1 + ',' + b1 + ',0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, s, s);
  return new THREE.CanvasTexture(c);
}

function wMakeStarfield(scene){
  /* Bụi sao xa: 800 điểm lặng thinh, toneMapped false, KHÔNG additive
   * để không cộng sáng vào bloom + không sáng hơn node thật. */
  const N = 800, pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
  for (let i = 0; i < N; i++){
    const t = Math.random() * 6.2832, ph = Math.acos(2 * Math.random() - 1);
    const R = 40 + Math.random() * 30;
    pos[i * 3] = R * Math.sin(ph) * Math.cos(t);
    pos[i * 3 + 1] = R * Math.sin(ph) * Math.sin(t);
    pos[i * 3 + 2] = R * Math.cos(ph);
    const b = 0.10 + Math.random() * 0.5;
    const warm = Math.random() < 0.3;
    col[i * 3] = b * (warm ? 1 : 0.75);
    col[i * 3 + 1] = b * 0.9;
    col[i * 3 + 2] = b;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const mat = new THREE.PointsMaterial({ size: 0.075, vertexColors: true,
    transparent: true, opacity: 0.4, depthWrite: false,
    blending: THREE.NormalBlending, fog: false, sizeAttenuation: true,
    toneMapped: false });
  const pts = new THREE.Points(geo, mat);
  pts.frustumCulled = false;
  scene.add(pts);
  return pts;
}

/* ── 4. Helpers galaxy (dùng cho lần dựng đầu và khi đổi dataset) ─────────── */

/* Edge: 1 draw call / bucket (type × cùng/khác cluster), additive. */
function wBuildLineMesh(bucket, nodes, alpha){
  if (!bucket.idx.length || alpha <= 0.004) return null;
  const idx = bucket.idx;
  const pos = new Float32Array(idx.length * 6);
  const col = new Float32Array(idx.length * 6);
  let v = 0;
  for (let q = 0; q < idx.length; q++){
    const e = idx[q], s = WP.E[e * 4], t = WP.E[e * 4 + 1];
    if (!WP.visible[s] || !WP.visible[t]) continue;
    pos[v] = nodes.pos[s * 3]; pos[v + 1] = nodes.pos[s * 3 + 1]; pos[v + 2] = nodes.pos[s * 3 + 2];
    pos[v + 3] = nodes.pos[t * 3]; pos[v + 4] = nodes.pos[t * 3 + 1]; pos[v + 5] = nodes.pos[t * 3 + 2];
    col[v] = bucket.rgb[0] * alpha; col[v + 1] = bucket.rgb[1] * alpha; col[v + 2] = bucket.rgb[2] * alpha;
    col[v + 3] = bucket.rgb[0] * alpha; col[v + 4] = bucket.rgb[1] * alpha; col[v + 5] = bucket.rgb[2] * alpha;
    v += 6;
  }
  if (!v) return null;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos.subarray(0, v), 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col.subarray(0, v), 3));
  const mat = new THREE.LineBasicMaterial({
    vertexColors: true, transparent: true, opacity: 1,
    blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
  const lines = new THREE.LineSegments(geo, mat);
  lines.frustumCulled = false;
  lines.userData.bucket = bucket;
  return lines;
}

/* Xem lại: rebuild tính theo màu vượt sáng (bloom ăn phần dư) */
function wRebuildEdges(g){
  for (const old of g.lineGroup.children.slice()){
    g.lineGroup.remove(old);
    if (old.geometry) old.geometry.dispose();
    if (old.material) old.material.dispose();
  }
  const dens = WP.scale * wdisplay.edge;
  for (const b of WP.buckets){
    if (wfilter.types && !wfilter.types.has(b.type)) continue;
    const a = Math.min(1, (whighlight ? 0.5 : b.base) * dens);
    const obj = wBuildLineMesh(b, { pos: WP.pos }, a);
    if (obj) g.lineGroup.add(obj);
  }
}

/* Cross edge: cầu sáng giữa 2 galaxy (opacity 0.85 như graph-ui) */
function wRebuildCross(g){
  if (g.crossObj){
    g.scene.remove(g.crossObj);
    if (g.crossObj.geometry) g.crossObj.geometry.dispose();
    if (g.crossObj.material) g.crossObj.material.dispose();
    g.crossObj = null;
  }
  if (g.flow){ g.scene.remove(g.flow); g.flow = null; }
  const sv = WP.sat;
  if (!sv || !wfx.sat || wfilter.cluster !== null) return;
  const cr = wHex(W_CROSS_COLOR);
  const dens = WP.scale * wdisplay.edge;
  const pos = new Float32Array(sv.cross.length * 3);
  const col = new Float32Array(sv.cross.length * 3);
  let v = 0;
  const a = Math.min(1, 0.85 * dens);
  for (let c = 0; c < sv.cross.length; c += 2){
    const mi = sv.cross[c], si = sv.cross[c + 1];
    if (mi >= WP.n || !sv.visible[si] || !WP.visible[mi]) continue;
    pos[v] = WP.pos[mi * 3]; pos[v + 1] = WP.pos[mi * 3 + 1]; pos[v + 2] = WP.pos[mi * 3 + 2];
    pos[v + 3] = sv.pos[si * 3]; pos[v + 4] = sv.pos[si * 3 + 1]; pos[v + 5] = sv.pos[si * 3 + 2];
    for (let k = 0; k < 2; k++){ col[v + 3 * k] = cr[0] * a; col[v + 3 * k + 1] = cr[1] * a; col[v + 3 * k + 2] = cr[2] * a; }
    v += 6;
  }
  if (!v) return;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos.subarray(0, v), 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col.subarray(0, v), 3));
  const cl = wHex(W_CROSS_COLOR);
  const mat = new THREE.LineBasicMaterial({
    color: new THREE.Color(cl[0], cl[1], cl[2]).multiplyScalar(a),
    transparent: true, opacity: a,
    blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
  const crossObj = new THREE.LineSegments(geo, mat);
  crossObj.frustumCulled = false;
  g.scene.add(crossObj);
  g.crossObj = crossObj;

  /* Dòng chảy: 1 hạt / cross edge, chạy main -> vệ tinh */
  if (wfx.flow){
    const nf = v / 6;
    const fpos = new Float32Array(nf * 3);
    const fgeo = new THREE.BufferGeometry();
    fgeo.setAttribute('position', new THREE.BufferAttribute(fpos, 3));
    const fw = wHex(W_FLOW_COLOR);
    const fmat = new THREE.PointsMaterial({
      map: wGetGlowTex(), color: new THREE.Color(fw[0], fw[1], fw[2]),
      size: 0.055, transparent: true, opacity: 0.9, depthWrite: false,
      blending: THREE.AdditiveBlending, sizeAttenuation: true });
    const flow = new THREE.Points(fgeo, fmat);
    flow.frustumCulled = false;
    g.scene.add(flow);
    g.flow = flow;
    g.flowPairs = new Int32Array(sv.cross);
  }
}

/* ── 5c. Tín hiệu truy xuất AI (bus dùng chung __GSL, KHÔNG đụng 7 hiệu ứng) ─ */
let wSigFrame = null, wSigApi = null;
function wSigEnsureBoot(){
  /* Boot 1 lần: sau khi map đã có DATA + đã loadDataset (WDS/WP sẵn sàng đổi). */
  if (wSigApi || typeof window.__GSL === 'undefined' || !window.__GSL.boot) return;
  try {
    wSigApi = window.__GSL.boot({ focus: i => { wSelectNode(i); wFlyTo(i); } });
  } catch (e){ wSigApi = null; }
}
function wSignalColor(hex){
  const v = parseInt(String(hex || '#22d3ee').slice(1), 16);
  return new THREE.Color(((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255);
}
function wDrawSignals(){
  /* Heat points + đường nối theo màu agent tại node TRÚNG truy xuất. */
  wSigEnsureBoot();
  const g = WGL;
  if (!WP || !g || !wSigApi) return false;
  try {
    if (!g.sigGroup){
      g.sigGroup = new THREE.Group();
      g.sigGroup.userData.keepBg = true;
      g.scene.add(g.sigGroup);
    }
    const f = wSigApi.frame(WDS.name);
    wSigFrame = f;
    while (g.sigGroup.children.length) {
      const o = g.sigGroup.children.pop();
      g.sigGroup.remove(o);
      if (o.geometry) o.geometry.dispose();
      if (o.material) o.material.dispose();
    }
    const S = (window.__GSL && window.__GSL.S) || {};
    if (S.on === false || !f.rings.length) return false;
    /* heat: điểm sáng tại node trúng (màu agent, mờ dần theo age). */
    const hp = [], hc = [];
    const seen = {};
    for (let r = 0; r < f.rings.length; r++){
      const s = f.rings[r];
      if (s.i < 0 || s.i >= WP.n || seen[s.i]) continue;
      seen[s.i] = 1;
      const fade = Math.max(0, 1 - s.age / 14);
      if (fade <= 0) continue;
      const c = wSignalColor(s.color);
      hp.push(WP.pos[s.i * 3], WP.pos[s.i * 3 + 1], WP.pos[s.i * 3 + 2]);
      hc.push(c.r * fade, c.g * fade, c.b * fade);
    }
    if (hp.length){
      const hg = new THREE.BufferGeometry();
      hg.setAttribute('position', new THREE.Float32BufferAttribute(hp, 3));
      hg.setAttribute('color', new THREE.Float32BufferAttribute(hc, 3));
      const hm = new THREE.PointsMaterial({ map: wGetGlowTex(), size: 0.11,
        vertexColors: true, transparent: true, opacity: 0.95, depthWrite: false,
        blending: THREE.AdditiveBlending, sizeAttenuation: true, toneMapped: false });
      const pts = new THREE.Points(hg, hm);
      pts.frustumCulled = false;
      g.sigGroup.add(pts);
    }
    /* đường nối 8 hit đầu về hit đầu tiên của cùng event (thấy "luồng đọc"). */
    const byQ = {};
    for (let r = 0; r < f.rings.length && r < 64; r++){
      const s = f.rings[r], k = s.agent + '|' + s.q;
      if (!byQ[k]) byQ[k] = [];
      if (byQ[k].length < 9 && s.i >= 0 && s.i < WP.n) byQ[k].push(s);
    }
    for (const k in byQ){
      const arr = byQ[k];
      if (arr.length < 2) continue;
      const lp = [], o = arr[0];
      for (let j = 1; j < arr.length; j++){
        lp.push(WP.pos[o.i * 3], WP.pos[o.i * 3 + 1], WP.pos[o.i * 3 + 2]);
        lp.push(WP.pos[arr[j].i * 3], WP.pos[arr[j].i * 3 + 1], WP.pos[arr[j].i * 3 + 2]);
      }
      const lg = new THREE.BufferGeometry();
      lg.setAttribute('position', new THREE.Float32BufferAttribute(lp, 3));
      const c0 = wSignalColor(arr[0].color);
      const lm = new THREE.LineBasicMaterial({ color: c0, transparent: true, opacity: 0.4,
        blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
      const ln = new THREE.LineSegments(lg, lm);
      ln.frustumCulled = false;
      g.sigGroup.add(ln);
    }
    return hp.length > 0;
  } catch (e){ return false; /* tín hiệu lỗi không được làm chết render */ }
}

/* ── 5c. Lưới kinh/vĩ tuyến: chỉ hiện ở kiểu "Vỏ cầu" để nhìn rõ khối cầu ─── */
function wMakeGlobe(){
  const seg = 96, R = 1.0, verts = [];
  const ring = fn => {
    for (let q = 0; q < seg; q++){
      const a0 = q / seg * 6.2832, a1 = (q + 1) / seg * 6.2832;
      const v0 = fn(a0), v1 = fn(a1);
      verts.push(v0[0], v0[1], v0[2], v1[0], v1[1], v1[2]);
    }
  };
  [-60, -30, 0, 30, 60].forEach(lat => {           /* vĩ tuyến */
    const y = Math.sin(lat * Math.PI / 180), r = Math.cos(lat * Math.PI / 180);
    ring(a => [r * Math.cos(a) * R, y * R, r * Math.sin(a) * R]);
  });
  for (let m = 0; m < 6; m++){                     /* kinh tuyến */
    const lon = m * Math.PI / 6, cl = Math.cos(lon), sl = Math.sin(lon);
    ring(a => [Math.cos(a) * cl * R, Math.sin(a) * R, Math.cos(a) * sl * R]);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  const mat = new THREE.LineBasicMaterial({ color: 0x7ec8e3, transparent: true,
    opacity: 0.085, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
  const globe = new THREE.LineSegments(geo, mat);
  globe.frustumCulled = false;
  globe.userData.keepBg = true;               /* giữ khi đổi dataset */
  globe.visible = (wlayout === 'shell');
  WGL.globe = globe;
  return globe;
}

/* ── 5b. CSS vignette (lớp phủ, giữ nền chính thật tối như UI gốc) ─────────── */
(function wInjectVignette(){
  const st = document.createElement('style');
  st.textContent = '#stage::after{content:"";position:absolute;inset:0;pointer-events:none;z-index:2;'
    + 'background:radial-gradient(ellipse at 50% 46%, rgba(0,0,0,0) 30%, rgba(0,0,0,0.38) 68%, rgba(0,0,0,0.72) 100%)}';
  document.head.appendChild(st);
})();

/* ── 5. Vòng render: passes (bloom + bokeh) + twinkle + flow + ripple + labels */
function wInitPasses(g){
  const w = g.canvas.clientWidth || 1, h = g.canvas.clientHeight || 1;
  g.composer = new THREE.EffectComposer(g.renderer);
  g.renderPass = new THREE.RenderPass(g.scene, g.camera);
  g.composer.addPass(g.renderPass);
  g.bloomPass = new THREE.UnrealBloomPass(new THREE.Vector2(w, h),
    W_BLOOM.strength, W_BLOOM.radius, W_BLOOM.threshold);
  g.composer.addPass(g.bloomPass);
  g.bokehPass = new THREE.BokehPass(g.scene, g.camera, {
    focus: W_DOF.focus, aperture: W_DOF.aperture, maxblur: W_DOF.maxblur,
    width: w, height: h });
  g.composer.addPass(g.bokehPass);
}

function wTwinkle(t){
  if (!wfx.twinkle) return;
  const mesh = WGL ? WGL.mesh : null;
  if (!mesh || !mesh.instanceColor) return;
  const c = new THREE.Color();
  const n = WP.n;
  for (let i = 0; i < n; i++){
    if (WP.sizeW[i] > 0.02) continue;    /* chi "sao nho" */
    const b = (1 + (WP.boost[i] - 1) * wdisplay.glow)
      * (1 + 0.18 * Math.sin(t * 1.9 + WP.phase[i]));
    c.setRGB(WP.colBase[i * 3] * b, WP.colBase[i * 3 + 1] * b, WP.colBase[i * 3 + 2] * b);
    mesh.setColorAt(i, c);
  }
  mesh.instanceColor.needsUpdate = true;
}

function wFlowParticles(t){
  const g = WGL;
  if (!g || !g.flow || !wfx.flow) return;
  const attr = g.flow.geometry.getAttribute('position');
  const pairs = g.flowPairs;
  for (let e = 0, f = 0; e + 1 < pairs.length && f < attr.count; e += 2, f++){
    const mi = pairs[e], si = pairs[e + 1];
    if (mi >= WP.n || !WP.visible[mi]) continue;
    const sv = WP.sat;
    if (!sv || !sv.visible[si]) continue;
    const u = (t * 0.35 + e / (pairs.length)) % 1;
    attr.setXYZ(f,
      WP.pos[mi * 3] + (sv.pos[si * 3] - WP.pos[mi * 3]) * u,
      WP.pos[mi * 3 + 1] + (sv.pos[si * 3 + 1] - WP.pos[mi * 3 + 1]) * u,
      WP.pos[mi * 3 + 2] + (sv.pos[si * 3 + 2] - WP.pos[mi * 3 + 2]) * u);
  }
  attr.needsUpdate = true;
}

/* Ripple click: vòng tròn dựng đứng, bung ra trong mặt phẳng nhìn */
function wSpawnRipple(pt){
  if (!wfx.ripple) return;
  const ring = wMakeRingOnce();
  ring.position.copy(pt);
  ring.visible = true;
  wripples.push({ ring, t: wtNow });
  if (wripples.length > 8){
    const old = wripples.shift();
    old.ring.visible = false;
    if (old.ring.material) old.ring.material.opacity = 0.5;
  }
}
let wRingPool = [];
function wMakeRingOnce(){
  for (const r of wRingPool) if (!r.visible) return r;
  const geo = new THREE.RingGeometry(0.96, 1.0, 64);
  const mat = new THREE.MeshBasicMaterial({ color: 0x1da27e, transparent: true,
    opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false,
    side: THREE.DoubleSide, toneMapped: false });
  const m = new THREE.Mesh(geo, mat);
  m.visible = false;
  WGL.scene.add(m);
  wRingPool.push(m);
  return m;
}
function wUpdateRipples(){
  for (let i = wripples.length - 1; i >= 0; i--){
    const rp = wripples[i], age = wtNow - rp.t;
    if (age > 1.1){ rp.ring.visible = false; wripples.splice(i, 1); continue; }
    const k = 1 - age / 1.1;
    const s = 0.05 + age * 0.85;
    rp.ring.scale.set(s, s, s);
    rp.ring.lookAt(WGL.camera.position);
    rp.ring.material.opacity = 0.5 * k;
  }
}

/* Node đang chọn: vòng tròn "thở" nhìn về camera + fly-to */
function wMakePulse(){
  const geo = new THREE.RingGeometry(0.94, 1.0, 64);
  const mat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true,
    opacity: 0.2, blending: THREE.AdditiveBlending, depthWrite: false,
    side: THREE.DoubleSide, toneMapped: false });
  const prac = new THREE.Mesh(geo, mat);
  prac.visible = false;
  WGL.scene.add(prac);
  return prac;
}
function wUpdatePulse(){
  const pl = WGL.pulse;
  if (wselected === null || !WP.visible[wselected]){ pl.visible = false; return; }
  pl.visible = true;
  pl.position.set(WP.pos[wselected * 3], WP.pos[wselected * 3 + 1], WP.pos[wselected * 3 + 2]);
  const breath = 0.5 + 0.5 * Math.sin(wtNow * 3.0);
  const s = Math.max(0.06, WP.sizeW[wselected] * (3.0 + 0.9 * breath));
  pl.scale.set(s, s, s);
  pl.lookAt(WGL.camera.position);
  pl.material.opacity = 0.10 + 0.16 * breath;
}
function wFlyTo(i){
  const g = WGL;
  const tgt = new THREE.Vector3(WP.pos[i * 3], WP.pos[i * 3 + 1], WP.pos[i * 3 + 2]);
  const dir = g.camera.position.clone().sub(g.controls.target);
  const len = Math.max(0.9, dir.length() * 0.45);
  dir.normalize();
  wfly = { t: 0, fromT: g.controls.target.clone(),
           toT: tgt.clone(),
           fromD: g.camera.position.clone(),
           toD: tgt.clone().add(dir.multiplyScalar(len)) };
}

/* ── 6. Tương tác + sidebar (mirror bản Canvas2D) ─────────────────────────── */
const wray = { raycaster: null, mouse: null };
function wRaySetup(){
  wray.raycaster = new THREE.Raycaster();
  wray.mouse = new THREE.Vector2();
}
function wHitMesh(clientX, clientY){
  const r = WGL.canvas.getBoundingClientRect();
  wray.mouse.set(((clientX - r.left) / r.width) * 2 - 1,
                 -((clientY - r.top) / r.height) * 2 + 1);
  wray.raycaster.setFromCamera(wray.mouse, WGL.camera);
  const hits = wray.raycaster.intersectObject(WGL.mesh);
  if (hits.length && hits[0].instanceId !== undefined){
    const id = hits[0].instanceId;
    if (WP.visible[id]) return { id, point: hits[0].point };
  }
  return null;
}
function wHitSat(clientX, clientY){
  const sv = WP.sat;
  if (!sv || !wfx.sat) return -1;
  const g = WGL, v = new THREE.Vector3(), svv = new THREE.Vector3();
  const rect = g.canvas.getBoundingClientRect();
  let best = -1, bestA = 1e9;
  for (let i = 0; i < sv.n; i++){
    if (!sv.visible[i]) continue;
    svv.set(sv.pos[i * 3], sv.pos[i * 3 + 1], sv.pos[i * 3 + 2]);
    const dist = g.camera.position.distanceTo(svv);
    v.copy(svv).project(g.camera);
    if (v.z > 1) continue;
    const x = rect.left + (v.x * 0.5 + 0.5) * rect.width;
    const y = rect.top + (-v.y * 0.5 + 0.5) * rect.height;
    const r = Math.max(10, 480 / Math.max(0.5, dist * 10));
    const dx = x - clientX, dy = y - clientY, d2 = dx * dx + dy * dy;
    if (d2 <= r * r && d2 / (r * r) < bestA){ best = i; bestA = d2 / (r * r); }
  }
  return best;
}

const WTIP = w$('tip');
function wPlaceTip(mx, my){
  const w = WTIP.offsetWidth, h = WTIP.offsetHeight;
  WTIP.style.left = Math.max(4, Math.min(mx + 14, WGL.canvas.clientWidth - w - 6)) + 'px';
  WTIP.style.top = Math.max(4, Math.min(my + 14, WGL.canvas.clientHeight - h - 6)) + 'px';
  WTIP.style.display = 'block';
}
function wShowTip(i, mx, my){
  const spec = WDS.stellar[WP.spec[i]];
  WTIP.textContent = '';
  const b = document.createElement('b');
  b.textContent = WDS.label[i];
  const sub = document.createElement('span');
  sub.className = 'sub';
  sub.textContent = WDS.id[i];
  const line = document.createElement('span');
  line.textContent = WDS.kinds[WP.kind[i]][0] + ' · ' + WP.deg[i].toLocaleString()
    + ' liên kết · lớp ' + spec[0] + ' · ' + WDS.clusters[WP.cluster[i]];
  const tag = document.createElement('span');
  tag.className = 'tag';
  tag.textContent = 'click = chọn + xem hàng xóm';
  WTIP.appendChild(b); WTIP.appendChild(sub); WTIP.appendChild(line); WTIP.appendChild(tag);
  wPlaceTip(mx, my);
}
function wShowSatTip(i, mx, my){
  const sv = WP.sat;
  WTIP.textContent = '';
  const b = document.createElement('b');
  b.textContent = sv.label[i];
  const sub = document.createElement('span');
  sub.className = 'sub';
  sub.textContent = sv.name + ' · ' + sv.deg[i].toLocaleString() + ' liên kết nội bộ';
  WTIP.appendChild(b); WTIP.appendChild(sub);
  if (sv.mainOf[i] >= 0){
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = 'cross link ↔ ' + WDS.label[sv.mainOf[i]];
    WTIP.appendChild(tag);
  }
  wPlaceTip(mx, my);
}
function wHideTip(){ if (WTIP.style.display !== 'none') WTIP.style.display = 'none'; }

/* Chi tiết node + labels overlay (fade theo khoảng cách) */
function wHideDetail(){ w$('detail').style.display = 'none'; }
function wSelectNode(i){
  wselected = i;
  whighlight = new Set([i].concat(WP.adj[i]));
  wShowDetail(i);
  wApplyFilters();
  wRebuildScene(true);
  wFlyTo(i);
  wneed = true;
}
function wClearSelection(){
  wselected = null;
  whighlight = null;
  wHideDetail();
  wApplyFilters();
  wRebuildScene(true);
  wneed = true;
}
function wShowDetail(i){
  const d = w$('detail');
  d.textContent = '';
  const close = document.createElement('button');
  close.className = 'close';
  close.textContent = '×';
  close.onclick = wClearSelection;
  const h = document.createElement('h3');
  h.textContent = WDS.label[i];
  const sub = document.createElement('div');
  sub.className = 'sub';
  sub.textContent = WDS.id[i];
  d.appendChild(close); d.appendChild(h); d.appendChild(sub);
  const spec = WDS.stellar[WP.spec[i]];
  const rows = [['Kind', WDS.kinds[WP.kind[i]][0]],
                ['Degree', WP.deg[i].toLocaleString()],
                ['Spectral', spec[0] + ' · ' + spec[2].toLocaleString() + ' node'],
                ['File / cluster', WDS.clusters[WP.cluster[i]]]];
  rows.forEach(r => {
    const row = document.createElement('div');
    row.className = 'row';
    const k = document.createElement('span');
    k.textContent = r[0];
    const v = document.createElement('b');
    v.textContent = r[1];
    row.appendChild(k); row.appendChild(v);
    d.appendChild(row);
  });
  const t = document.createElement('p');
  t.className = 'glabel';
  t.style.marginTop = '10px';
  t.textContent = 'Hàng xóm (' + WP.adj[i].length + ')';
  d.appendChild(t);
  WP.adj[i].slice().sort((a, b) => WP.deg[b] - WP.deg[a]).slice(0, 12).forEach(j => {
    const b = document.createElement('button');
    b.className = 'nb';
    b.textContent = WDS.label[j] + '  ·' + WP.deg[j];
    b.onclick = () => wSelectNode(j);
    d.appendChild(b);
  });
  d.style.display = 'block';
}
function wRenderLabels(){
  const lab = WGL.labelLayer;
  lab.textContent = '';
  if (!wdisplay.labels) return;
  const rect = WGL.canvas.getBoundingClientRect();
  const v = new THREE.Vector3();
  const focus = wselected !== null ? wselected : whover;
  let shown = 0;
  for (let q = 0; q < WP.labelIdx.length && shown < W_LABEL_MAX; q++){
    const i = WP.labelIdx[q];
    if (!WP.visible[i]) continue;
    v.set(WP.pos[i * 3], WP.pos[i * 3 + 1], WP.pos[i * 3 + 2]);
    const dist = v.distanceTo(WGL.camera.position);
    let a = WCLAMP((3.6 - dist) / 2.2, 0, 1);
    if (i === focus) a = 1;
    if (a < 0.25 && i !== focus) continue;
    v.project(WGL.camera);
    if (v.z > 1) continue;
    const el = document.createElement('div');
    el.className = 'wlabel';
    el.textContent = WDS.label[i];
    el.style.left = ((v.x * 0.5 + 0.5) * rect.width + 8) + 'px';
    el.style.top = ((-v.y * 0.5 + 0.5) * rect.height - 6) + 'px';
    el.style.opacity = (0.72 * a).toFixed(2);
    lab.appendChild(el);
    shown++;
  }
}

/* CSS thêm cho labels WebGL overlay */
(function wInjectCss(){
  const st = document.createElement('style');
  st.textContent = '#wlabels{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:3}'
    + '.wlabel{position:absolute;font:9px "JetBrains Mono",ui-monospace,monospace;'
    + 'color:rgba(224,237,237,0.72);white-space:nowrap;text-shadow:0 1px 4px #000}';
  document.head.appendChild(st);
})();

/* ── 7. Sidebar (dùng lại DOM của canvas2d) + rebuild scene ──────────────── */
function wToggleSet(set, i){ if (set.has(i)) set.delete(i); else set.add(i); }
function wChipEl(label, color, count, on, onClick){
  const b = document.createElement('button');
  b.className = 'chip' + (on ? '' : ' off');
  const dot = document.createElement('span');
  dot.className = 'cdot';
  dot.style.background = on ? color : '#444';
  const tx = document.createElement('span');
  tx.textContent = label;
  tx.style.color = on ? color : '#555';
  const cn = document.createElement('span');
  cn.className = 'cnt';
  cn.textContent = count.toLocaleString();
  b.appendChild(dot); b.appendChild(tx); b.appendChild(cn);
  b.onclick = onClick;
  return b;
}
function wBuildTabs(){
  const nav = w$('tabs');
  nav.textContent = '';
  DATA.datasets.forEach((ds, i) => {
    const b = document.createElement('button');
    b.textContent = ds.name + ' · ' + ds.stats.nodes;
    b.setAttribute('data-i', i);
    b.onclick = () => wLoadDataset(i);
    nav.appendChild(b);
  });
}
function wBuildSidebar(){
  const ds = WDS;
  if (!wfilter.kinds) wfilter.kinds = new Set(ds.kinds.map((_, i) => i));
  if (!wfilter.types) wfilter.types = new Set(ds.types.map((_, i) => i));
  const nc = w$('nodeChips');
  nc.textContent = '';
  ds.kinds.forEach((k, i) => nc.appendChild(wChipEl(k[0], k[1], k[2], wfilter.kinds.has(i), () => {
    wToggleSet(wfilter.kinds, i); wBuildSidebar(); wApplyFilters(); wRebuildScene(true);
  })));
  const ec = w$('edgeChips');
  ec.textContent = '';
  ds.types.forEach((t, i) => ec.appendChild(wChipEl(t[0], t[1], t[2], wfilter.types.has(i), () => {
    wToggleSet(wfilter.types, i); wBuildSidebar(); wApplyFilters(); wRebuildScene(true);
  })));
  const sl = w$('stellar');
  sl.textContent = '';
  ds.stellar.forEach(st => {
    const wrap = document.createElement('span');
    const dot = document.createElement('i');
    dot.style.background = st[1];
    const tx = document.createElement('span');
    tx.textContent = st[0] + ' ' + st[2].toLocaleString();
    wrap.appendChild(dot); wrap.appendChild(tx); sl.appendChild(wrap);
  });
  const items = w$('items');
  items.textContent = '';
  items.appendChild(wItemEl(null, 'Tất cả file (' + ds.clusters.length + ')',
                            WP ? WP.n : ds.stats.nodes));
  const q = wfilter.needle.toLowerCase();
  ds.clusters.map((_, i) => i)
    .sort((a, b) => ds.clusterCount[b] - ds.clusterCount[a])
    .filter(ci => !q || ds.clusters[ci].toLowerCase().includes(q))
    .slice(0, 300)
    .forEach(ci => items.appendChild(wItemEl(ci, ds.clusters[ci], ds.clusterCount[ci])));
}
function wItemEl(ci, name, count){
  const b = document.createElement('button');
  b.className = 'item' + (ci === wfilter.cluster ? ' on' : '');
  const nm = document.createElement('span');
  nm.className = 'nm';
  nm.textContent = name;
  const cn = document.createElement('span');
  cn.className = 'cnt';
  cn.textContent = count.toLocaleString();
  b.appendChild(nm); b.appendChild(cn);
  b.onclick = () => {
    wfilter.cluster = (ci === null || wfilter.cluster === ci) ? null : ci;
    wBuildSidebar(); wApplyFilters(); wRebuildScene(true); wneed = true;
  };
  return b;
}

/* Rebuild toàn cảnh khi đổi dataset (galaxies cũ bị dispose) */
function wDispose(g){
  g.scene.traverse(o => {
    if (o.geometry) o.geometry.dispose();
  });
  for (const old of g.lineGroup.children.slice()) g.lineGroup.remove(old);
}
function wRebuildScene(edgesOnly){
  const g = WGL;
  if (!edgesOnly){
    /* Node instances đứng yên theo layout đã tính sẵn */
    wPlaceNodes();
    wRefreshColors();
  }
  wRebuildEdges(g);
  wRebuildCross(g);
  g.mesh.visible = true;
  if (g.satMesh) g.satMesh.visible = wfx.sat && wfilter.cluster === null;
  wneed = true;
}
function wRefreshColors(){
  const c = new THREE.Color();
  for (let i = 0; i < WP.n; i++){
    const on = WP.visible[i];
    const b = on ? 1 + (WP.boost[i] - 1) * wdisplay.glow
                 : 0.15;
    c.setRGB(WP.colBase[i * 3] * b, WP.colBase[i * 3 + 1] * b, WP.colBase[i * 3 + 2] * b);
    WGL.mesh.setColorAt(i, c);
    WP.colNow[i * 3] = c.r; WP.colNow[i * 3 + 1] = c.g; WP.colNow[i * 3 + 2] = c.b;
  }
  WGL.mesh.instanceColor.needsUpdate = true;
}

/* Vòng render chính */
function wLoop(){
  requestAnimationFrame(wLoop);
  const g = WGL;
  if (!g) return;
  wtNow = performance.now() / 1000;
  const idle = Date.now() - wview.idle > W_IDLE_MS;
  g.controls.autoRotate = wfx.auto && idle && !wfly;
  g.controls.update();
  /* fly-to */
  if (wfly){
    wfly.t = Math.min(1, wfly.t + 0.02);
    const e = 1 - Math.pow(1 - wfly.t, 3);
    g.controls.target.lerpVectors(wfly.fromT, wfly.toT, e);
    g.camera.position.lerpVectors(wfly.fromD, wfly.toD, e);
    if (wfly.t >= 1) wfly = null;
  }
  wTwinkle(wtNow);
  wFlowParticles(wtNow);
  wUpdateRipples();
  wUpdatePulse();
  wDrawSignals();
  g.composer.render();
  wRenderLabels();
  wUpdateStats();
  wframes++;
  if (wframes === 1) wSelfTest();
}
function wSelfTest(){
  try{
    const gl = WGL.renderer.getContext();
    /* Đo pixel thật trong framebuffer -> phát hiện màn hình trắng/đen */
    const w = Math.min(600, gl.drawingBufferWidth), h = Math.min(360, gl.drawingBufferHeight);
    const x = Math.max(0, Math.floor((gl.drawingBufferWidth - w) / 2));
    const y = Math.max(0, Math.floor((gl.drawingBufferHeight - h) / 2));
    const px = new Uint8Array(w * h * 4);
    gl.readPixels(x, y, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
    let lit = 0, bright = 0;
    for (let i = 0; i < px.length; i += 4){
      const v = (px[i] + px[i + 1] + px[i + 2]) / 3;
      if (v > 8) lit++;
      if (v > 90) bright++;
    }
    const pct = lit / (w * h) * 100;
    if (pct < 2){ wfail('canvas gần như trống (lit=' + pct.toFixed(1) + '%)'); return; }
    document.title = 'GLOW_WGL_OK ' + WP.n + 'n/' + WP.m + 'e lit='
      + pct.toFixed(1) + '% bright=' + bright + ' gl=' + (gl.getParameter(gl.VERSION) || '?');
  } catch (e){ wfail('wSelfTest: ' + e.message); }
}

/* Pointer: hover tooltip + click chọn + idle reset */
function wBindEvents(){
  const cv = WGL.canvas;
  cv.addEventListener('pointerdown', e => {
    wdrag = { x0: e.clientX, y0: e.clientY, moved: 0 };
    WGL.controls.autoRotate = false;
    wview.idle = Date.now();
    try { cv.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
  });
  cv.addEventListener('pointermove', e => {
    if (!wdrag){
      const hit = wHitMesh(e.clientX, e.clientY);
      const s = (!hit && WP.sat && wfx.sat) ? wHitSat(e.clientX, e.clientY) : -1;
      const nid = hit ? hit.id : -1;
      if (nid !== whover || s !== whoverSat){ whover = nid; whoverSat = s; wRefreshColors(); }
      if (nid >= 0) wShowTip(nid, e.clientX - cv.getBoundingClientRect().left, e.clientY - cv.getBoundingClientRect().top);
      else if (s >= 0) wShowSatTip(s, e.clientX - cv.getBoundingClientRect().left, e.clientY - cv.getBoundingClientRect().top);
      else wHideTip();
      return;
    }
    wdrag.moved = Math.max(wdrag.moved,
      Math.abs(e.clientX - wdrag.x0) + Math.abs(e.clientY - wdrag.y0));
    wview.idle = Date.now();
    wHideTip();
  });
  cv.addEventListener('pointerup', e => {
    const d = wdrag;
    wdrag = null;
    if (!d || d.moved > 4) return;
    const hit = wHitMesh(e.clientX, e.clientY);
    if (hit){
      const r = cv.getBoundingClientRect();
      wSpawnRipple(hit.point);
      wSelectNode(hit.id);
    } else {
      wClearSelection();
    }
  });
  cv.addEventListener('pointerleave', () => { whover = null; whoverSat = -1; wHideTip(); wRefreshColors(); });
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('wheel', () => { wview.idle = Date.now(); }, { passive: true });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape'){ wClearSelection(); return; }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const i = ['1', '2', '3'].indexOf(e.key);
    if (i >= 0) wApplyLayout(W_LAYOUTS[i][0]);
  });
}

/* Sliders + checkbox hiệu ứng + nút */
function wBindControls(){
  function slider(id, valId, key){
    const s = w$(id);
    s.addEventListener('input', () => {
      wdisplay[key] = Number(s.value) / 100;
      w$(valId).textContent = wdisplay[key].toFixed(1);
      if (key === 'glow') wRefreshColors();
      if (key === 'edge') wRebuildScene(true);
      if (key === 'bloom' && WGL && WGL.bloomPass) WGL.bloomPass.strength = 1.45 * wdisplay.bloom;
    });
  }
  slider('sEdge', 'vEdge', 'edge');
  slider('sGlow', 'vGlow', 'glow');
  slider('sBloom', 'vBloom', 'bloom');
  w$('showLabels').addEventListener('change', e => { wdisplay.labels = e.target.checked; });
  w$('hubOnly').addEventListener('change', e => {
    wdisplay.hubOnly = e.target.checked; wApplyFilters(); wRebuildScene(true);
  });
  function fx(id, key){
    const el = w$(id);
    el.addEventListener('change', () => {
      wfx[key] = el.checked;
      if (key === 'sat' || key === 'ripple') wApplyFilters();
      if (key === 'dof' && WGL && WGL.bokehPass) WGL.bokehPass.enabled = el.checked;
      wRebuildScene(true);
    });
  }
  fx('fxTwinkle', 'twinkle'); fx('fxDof', 'dof'); fx('fxFlow', 'flow');
  fx('fxRipple', 'ripple'); fx('fxSat', 'sat'); fx('fxNebula', 'nebula'); fx('fxAuto', 'auto');
  w$('search').addEventListener('input', e => {
    wfilter.needle = e.target.value.trim();
    wBuildSidebar();
    const q = wfilter.needle.toLowerCase();
    if (q.length >= 2){
      const hit = [];
      for (let i = 0; i < WP.n && hit.length < 500; i++){
        if (WDS.label[i].toLowerCase().includes(q) || WDS.id[i].toLowerCase().includes(q)) hit.push(i);
      }
      whighlight = hit.length ? new Set(hit) : null;
      if (hit.length === 1){ wselected = hit[0]; wShowDetail(hit[0]); wFlyTo(hit[0]); }
      else { wselected = null; wHideDetail(); }
    } else if (!wfilter.needle){
      wselected = null; whighlight = null; wHideDetail();
    }
    wApplyFilters(); wRebuildScene(true);
  });
  function setAll(on){
    wfilter.kinds = on ? new Set(WDS.kinds.map((_, i) => i)) : new Set();
    wfilter.types = on ? new Set(WDS.types.map((_, i) => i)) : new Set();
    wBuildSidebar(); wApplyFilters(); wRebuildScene(true);
  }
  w$('allBtn').onclick = () => setAll(true);
  w$('noneBtn').onclick = () => setAll(false);
  w$('refresh').onclick = () => {
    wClearSelection();
    wfilter.cluster = null; wfilter.needle = '';
    w$('search').value = '';
    w$('hubOnly').checked = false;
    wdisplay.hubOnly = false;
    setAll(true);
  };
}

function wResetMeshes(g){
  /* Galaxy chính: sphere instanced + màu vượt 1.0 để bloom "ăn" */
  const detail = WP.n <= 8000 ? 18 : 12;
  const geo = new THREE.SphereGeometry(1, detail, Math.max(8, detail - 4));
  const mat = new THREE.MeshBasicMaterial({ toneMapped: false });
  const mesh = new THREE.InstancedMesh(geo, mat, WP.n);
  mesh.frustumCulled = false;
  const m4 = new THREE.Matrix4(), cTmp = new THREE.Color();
  for (let i = 0; i < WP.n; i++){
    m4.makeScale(WP.sizeW[i], WP.sizeW[i], WP.sizeW[i]);
    m4.setPosition(WP.pos[i * 3], WP.pos[i * 3 + 1], WP.pos[i * 3 + 2]);
    mesh.setMatrixAt(i, m4);
    const b = 1 + (WP.boost[i] - 1) * wdisplay.glow;
    cTmp.setRGB(WP.colBase[i * 3] * b, WP.colBase[i * 3 + 1] * b, WP.colBase[i * 3 + 2] * b);
    mesh.setColorAt(i, cTmp);
  }
  mesh.instanceMatrix.needsUpdate = true;
  mesh.instanceColor.needsUpdate = true;
  g.scene.add(mesh);
  g.mesh = mesh;
  const sv = WP.sat;
  g.satMesh = null;
  if (sv){
    const smat = new THREE.MeshBasicMaterial({ toneMapped: false, transparent: true, opacity: 0.55 });
    const satMesh = new THREE.InstancedMesh(geo, smat, sv.n);
    satMesh.frustumCulled = false;
    for (let i = 0; i < sv.n; i++){
      const s = wSatScale(sv, i);
      m4.makeScale(s, s, s);
      m4.setPosition(sv.pos[i * 3], sv.pos[i * 3 + 1], sv.pos[i * 3 + 2]);
      satMesh.setMatrixAt(i, m4);
      const b = 1 + (sv.boost[i] - 1) * wdisplay.glow;
      cTmp.setRGB(sv.colBase[i * 3] * b, sv.colBase[i * 3 + 1] * b, sv.colBase[i * 3 + 2] * b);
      satMesh.setColorAt(i, cTmp);
    }
    satMesh.instanceMatrix.needsUpdate = true;
    satMesh.instanceColor.needsUpdate = true;
    g.scene.add(satMesh);
    g.satMesh = satMesh;
  }
}

/* ── Đổi kiểu khối cầu: chỉ đổi TOẠ ĐỘ, edge + 7 hiệu ứng giữ nguyên ──────── */
/* Đặt lại ma trận instance của 2 galaxy theo WP.pos hiện hành */
function wPlaceNodes(){
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < WP.n; i++){
    const s = WP.sizeW[i];
    m4.makeScale(s, s, s);
    m4.setPosition(WP.pos[i * 3], WP.pos[i * 3 + 1], WP.pos[i * 3 + 2]);
    WGL.mesh.setMatrixAt(i, m4);
  }
  WGL.mesh.instanceMatrix.needsUpdate = true;
  const sv = WP.sat;
  if (sv && WGL.satMesh){
    for (let i = 0; i < sv.n; i++){
      const s = wSatScale(sv, i);
      m4.makeScale(s, s, s);
      m4.setPosition(sv.pos[i * 3], sv.pos[i * 3 + 1], sv.pos[i * 3 + 2]);
      WGL.satMesh.setMatrixAt(i, m4);
    }
    WGL.satMesh.instanceMatrix.needsUpdate = true;
  }
}
function wLayoutName(){
  const l = W_LAYOUTS.filter(x => x[0] === wlayout)[0];
  return l ? l[1] : wlayout;
}
function wMeanR(p){
  if (!p) return 0;
  let s = 0;
  for (let i = 0; i < p.n; i++){
    const x = p.pos[i * 3], y = p.pos[i * 3 + 1], z = p.pos[i * 3 + 2];
    s += Math.sqrt(x * x + y * y + z * z);
  }
  return s / p.n;
}
function wBuildLayoutChips(){
  const host = w$('layChips');
  if (!host) return;
  host.innerHTML = '';
  W_LAYOUTS.forEach(l => {
    const b = document.createElement('button');
    b.className = 'chip' + (l[0] === wlayout ? ' sel' : ' off');
    b.textContent = l[1];
    b.setAttribute('data-lay', l[0]);
    b.onclick = () => wApplyLayout(l[0]);
    host.appendChild(b);
  });
}
function wUpdateName(){
  if (!WDS) return;
  w$('graphName').textContent = WDS.name + ' · ' + WDS.stats.nodes.toLocaleString()
    + ' nodes / ' + WDS.stats.edges.toLocaleString()
    + ' edges · WebGL 3D (UnrealBloom + Bokeh) · kiểu: ' + wLayoutName()
    + (WDS.sat ? ' · ' + WDS.sat.id.length + ' memory records' : '');
}
/* Dòng thống kê góc dưới trái (giống bản Canvas2D) - chỉ ghi DOM khi đổi */
let wStatTxt = '';
function wUpdateStats(){
  const sat = (WP.sat && wfx.sat) ? WP.sat : null;
  const txt = WP.n + ' nodes / ' + WP.m + ' edges'
    + (sat ? '   +   ' + sat.n + ' ' + sat.name.toLowerCase() : '')
    + (wselected !== null ? '   ·   ' + WDS.label[wselected] : '')
    + '   ·   ' + wLayoutName();
  if (txt !== wStatTxt){ wStatTxt = txt; w$('stats').textContent = txt; }
}
function wApplyLayout(key){
  if (!W_LAYOUTS.some(l => l[0] === key)) return;
  wlayout = key;
  if (WP){
    WP.pos = WP.posSrc[key] || WP.posSrc.cluster;
    if (WP.sat) WP.sat.pos = WP.sat.posSrc[key] || WP.sat.posSrc.cluster;
    wPlaceNodes();
    wRebuildEdges(WGL);
    wRebuildCross(WGL);
  }
  if (WGL.globe) WGL.globe.visible = (wlayout === 'shell');
  wBuildLayoutChips();
  wUpdateName();
  wfly = null;                     /* toạ độ đổi -> bỏ fly-to của layout cũ */
  wneed = true;
}

/* Nạp dataset + boot + resize + hook test */
function wLoadDataset(i){
  WDS = DATA.datasets[i];
  WP = wPrepare(WDS);
  wfilter.kinds = null; wfilter.types = null; wfilter.cluster = null; wfilter.needle = '';
  whighlight = null; wselected = null; whover = null; whoverSat = -1;
  wripples = []; wfly = null; wdrag = null;
  wHideDetail();
  wHideTip();
  wdisplay.hubOnly = false;
  w$('hubOnly').checked = false;
  w$('search').value = '';
  wfx.sat = !!WDS.sat;
  w$('fxSat').checked = wfx.sat;
  /* Xoá meshes/edges cũ, giữ nebula + starfield */
  const keep = new Set();
  WGL.scene.children.slice().forEach(o => {
    if (o === WGL.nebGroup || o.userData.keepBg){ keep.add(o); return; }
    WGL.scene.remove(o);
    if (o.geometry) o.geometry.dispose();
  });
  WGL.mesh = null; WGL.satMesh = null; WGL.crossObj = null;
  WGL.flow = null; WGL.flowPairs = null;
  WGL.lineGroup = new THREE.Group();
  WGL.scene.add(WGL.lineGroup);
  wResetMeshes(WGL);
  document.querySelectorAll('#tabs button').forEach(b => {
    b.className = Number(b.getAttribute('data-i')) === i ? 'on' : '';
  });
  wUpdateName();
  wBuildLayoutChips();
  if (WGL.globe) WGL.globe.visible = (wlayout === 'shell');
  wBuildSidebar();
  wApplyFilters();
  wRebuildScene(false);
  wResize();
  wframes = 0;
  wneed = true;
}
function wResize(){
  const g = WGL;
  const w = g.canvas.clientWidth || 1, h = g.canvas.clientHeight || 1;
  const px = Math.min(window.devicePixelRatio || 1, 1.5);
  g.renderer.setPixelRatio(px);
  g.renderer.setSize(w, h, false);
  g.camera.aspect = w / h;
  g.camera.updateProjectionMatrix();
  g.composer.setSize(w, h);
}

window.__glow = {
  data: () => DATA,
  stats: () => ({
    nodes: WP ? WP.n : 0, edges: WP ? WP.m : 0, title: document.title,
    frames: wframes,
    sat: (WP && WP.sat) ? WP.sat.n : 0,
    cross: (WP && WP.sat) ? WP.sat.cross.length / 2 : 0,
    ripples: wripples.length,
    layout: wlayout,
    globe: !!(WGL && WGL.globe && WGL.globe.visible),
    meanR: wMeanR(WP),
    satMeanR: wMeanR(WP && WP.sat),
    effects: Object.assign({}, wfx),
    webgl: true
  }),
  top: () => {
    if (!WP) return null;
    const i = WP.radial[0];
    const v = new THREE.Vector3(WP.pos[i * 3], WP.pos[i * 3 + 1], WP.pos[i * 3 + 2]).project(WGL.camera);
    const rect = WGL.canvas.getBoundingClientRect();
    const x = (v.x * 0.5 + 0.5) * rect.width, y = (-v.y * 0.5 + 0.5) * rect.height;
    return { i, label: WDS.label[i], deg: WP.deg[i], x, y,
             cx: rect.left + x, cy: rect.top + y };
  },
  hoverAt: (x, y) => {
    const r = WGL.canvas.getBoundingClientRect();
    wray.mouse.set((x / r.width) * 2 - 1, -(y / r.height) * 2 + 1);
    wray.raycaster.setFromCamera(wray.mouse, WGL.camera);
    const hits = wray.raycaster.intersectObject(WGL.mesh);
    const id = (hits.length && hits[0].instanceId !== undefined) ? hits[0].instanceId : -1;
    if (id >= 0) wShowTip(id, x, y);
    return id;
  },
  fx: (k, v) => {
    wfx[k] = v;
    if (k === 'sat') wApplyFilters();
    if (k === 'dof' && WGL.bokehPass) WGL.bokehPass.enabled = v;
    wRebuildScene(true);
  },
  layouts: () => W_LAYOUTS.map(l => l[0]),
  layout: k => { wApplyLayout(k); return wlayout; },
  select: i => wSelectNode(i),
  signals: () => wSigApi,
  view: () => ({ zoom: WGL.camera.position.distanceTo(WGL.controls.target) })
};

try {
  if (!DATA || !DATA.datasets || !DATA.datasets.length){
    wfail('Payload rỗng: chưa có dataset nào (chạy: python build_glow.py)');
  } else if (typeof THREE === 'undefined' || !THREE.WebGLRenderer){
    wfail('three.js chưa nạp được (kiểm tra vendor/three). Mở bản Canvas2D: glow_map.html');
  } else {
    let hasGL = false;
    try {
      const probe = document.createElement('canvas');
      const gl = probe.getContext('webgl') || probe.getContext('experimental-webgl');
      hasGL = !!gl;
    } catch (e){ hasGL = false; }
    if (!hasGL){
      wfail('Thiết bị này không có WebGL. Mở bản Canvas2D: glow_map.html');
    } else {
      wHideDetail();
      const canvas = w$('cv');
      WGL = { canvas, scene: null, camera: null, renderer: null, controls: null,
              composer: null, bloomPass: null, bokehPass: null,
              mesh: null, satMesh: null, lineGroup: null,
              crossObj: null, flow: null, flowPairs: null, pulse: null,
              nebGroup: null, labelLayer: null, globe: null };
      WGL.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
      WGL.renderer.setClearColor(0x070f13, 1);
      WGL.scene = new THREE.Scene();
      WGL.scene.fog = new THREE.FogExp2(0x070f13, 0.052);
      WGL.camera = new THREE.PerspectiveCamera(W_CAM.fov, 1, W_CAM.near, W_CAM.far);
      WGL.camera.position.set(0.6, 0.5, W_CAM.dist);
      WGL.controls = new THREE.OrbitControls(WGL.camera, canvas);
      WGL.controls.enableDamping = true;
      WGL.controls.dampingFactor = 0.08;
      WGL.controls.rotateSpeed = 0.5;
      WGL.controls.zoomSpeed = 1.5;
      WGL.controls.minDistance = W_CAM.min;
      WGL.controls.maxDistance = W_CAM.max;
      WGL.controls.autoRotate = false;
      WGL.controls.autoRotateSpeed = 0.4;
      WGL.nebGroup = new THREE.Group();
      WGL.scene.add(WGL.nebGroup);
      [['rgb(8,24,32)', 2.6, -3.4, -9], ['rgb(26,13,38)', 3.4, 2.6, -10],
       ['rgb(8,34,31)', -3.2, 2.8, -9]].forEach(d => {
        const nums = d[0].match(/\d+/g).map(Number);
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({
          map: wMakeNebulaTexture(nums[0], nums[1], nums[2]),
          blending: THREE.NormalBlending, depthWrite: false, fog: false, opacity: 0.16,
          toneMapped: false }));
        sp.position.set(d[1], d[2], d[3]);
        sp.scale.set(11, 11, 1);
        WGL.nebGroup.add(sp);
      });
      wMakeStarfield(WGL.scene).userData.keepBg = true;
      WGL.scene.add(wMakeGlobe());
      WGL.lineGroup = new THREE.Group();
      WGL.scene.add(WGL.lineGroup);
      const lab = document.createElement('div');
      lab.id = 'wlabels';
      w$('stage').appendChild(lab);
      WGL.labelLayer = lab;
      WGL.pulse = wMakePulse();
      wRaySetup();
      wInitPasses(WGL);
      wBuildTabs();
      wLoadDataset(0);
      wBindEvents();
      wBindControls();
      window.addEventListener('resize', wResize);
      requestAnimationFrame(wLoop);
    }
  }
} catch (e){
  wfail('boot: ' + e.message);
}
