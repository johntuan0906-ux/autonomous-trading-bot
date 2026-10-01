/* glow_signals_lib.js — BUS "tín hiệu truy xuất AI" DÙNG CHUNG cho cả 2 engine.
 * build_glow.py nhúng NGUYÊN VĂN vào glow_map.html + glow_map_webgl.html
 * (placeholder GLOW_SIGNALS_LIB ở đầu script) nên 2 bản đồ luôn chạy cùng 1 logic.
 * Phụ thuộc: GS (glow_signals.js, kernel thuần) + DATA.signals (snapshot nhúng).
 * Không dùng fetch khi ở file:// (chỉ live qua serve_glow.py + http).
 * Mọi DOM đều lấy lazy + try/catch: thiếu node nào map vẫn chạy bình thường.
 */
(function(){
'use strict';
if (typeof GS === 'undefined') return;   /* kernel thiếu -> câm lặng, map vẫn chạy */
var $ = function(id){ try { return document.getElementById(id); } catch (e){ return null; } };
var LS_KEY = 'glow_sig_cache_v1';
var FRAME_MAX_AGE = 14, EV_CAP = 200, DRAW_CAP = 400;
function esc(s){
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
var S = {
  snap: null, agents: [], byId: {}, events: [], evKeys: {},
  cache: GS.makeCache(256), tuner: GS.makeTuner(12),
  ix: {}, idmap: {}, ftok: {}, queries: [],
  on: true, auto: false, qrot: 0, round: 0, lastQ: '',
  solo: null, live: 'snapshot', sig: '', generated: '',
  pollT: null, es: null, cfg: null, puts: 0
};
function evKey(e){ return e.t + '|' + e.agent + '|' + e.query + '|' + e.n_hits; }
function fmtTok(n){
  n = Math.round(n || 0);
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k';
  return '' + n;
}
function fmtMs(x){ x = +x || 0; return x >= 100 ? Math.round(x) + '' : x.toFixed(1); }
function fmtUsd(x){ x = +x || 0; return x < 0.01 ? '$' + x.toFixed(6) : '$' + x.toFixed(4); }
function docsFromDs(ds){
  /* Dựng docs truy xuất từ payload dataset; idmap cần cho frame() sau này. */
  var ids = ds.id || [], labels = ds.label || [], degs = ds.deg || [];
  var kinds = ds.kinds || [], clusters = ds.clusters || [];
  var kind = ds.kind || [], cluster = ds.cluster || [];
  var out = new Array(ids.length), map = {}, ft = {}, seenF = {};
  var i, f;
  for (i = 0; i < ids.length; i++){
    var id = String(ids[i]), label = String(labels[i] == null ? id : labels[i]);
    f = '';
    try {
      var ci = cluster[i];
      if (ci != null && clusters[ci] != null) f = String(clusters[ci]);
    } catch (e){}
    var kk = '';
    try {
      var ki = kind[i];
      if (ki != null && kinds[ki] && kinds[ki][0] != null) kk = String(kinds[ki][0]);
    } catch (e){}
    out[i] = {id: id, label: label, deg: +degs[i] || 0, file: f, kind: kk,
              tokens: Math.max(GS.MIN_TOK, GS.estTok(id + ' ' + label))};
    map[id] = i;
    if (f && !seenF[f]){ seenF[f] = 1; ft[f] = 0; }
  }
  return {docs: out, map: map, files: Object.keys(seenF)};
}
function fetchFileTokens(files, done){
  /* Lấy token từng file qua serve_glow.py (/api/files); file:// thì bỏ qua. */
  var out = {};
  if (!files.length || location.protocol !== 'http:'){ done(out); return; }
  var xhr;
  try { xhr = new XMLHttpRequest(); } catch (e){ done(out); return; }
  try {
    xhr.open('GET', 'api/files?n=' + files.length, true);
    xhr.timeout = 8000;
    xhr.onreadystatechange = function(){
      if (xhr.readyState !== 4) return;
      if (xhr.status === 200){
        try {
          var j = JSON.parse(xhr.responseText), t = (j && j.tokens) || {};
          for (var f in t) if (t.hasOwnProperty(f)) out[f] = +t[f] || 0;
        } catch (e){}
      }
      done(out);
    };
    xhr.onerror = function(){ done(out); };
    xhr.ontimeout = function(){ done(out); };
    xhr.send();
  } catch (e){ done({}); }
}
function buildAllIx(datasets, done){
  /* Dựng index cho mọi dataset; fileTokens có thì dùng, không thì REC_TOK. */
  var names = [], i;
  for (i = 0; i < datasets.length; i++) names.push(datasets[i].name || ('ds' + i));
  var acc = {};
  function next(k){
    if (k >= datasets.length){
      for (var n = 0; n < datasets.length; n++){
        var nm = names[n], d = acc[nm];
        S.ix[nm] = GS.buildIndex(d.docs, datasets[n].edges || [], d.ft, nm);
      }
      done();
      return;
    }
    var dd = docsFromDs(datasets[k]);
    S.idmap[names[k]] = dd.map;
    fetchFileTokens(dd.files, function(ft){
      var m = {};
      for (var f in ft) if (ft.hasOwnProperty(f)) m[f] = ft[f];
      acc[names[k]] = {docs: dd.docs, ft: m};
      next(k + 1);
    });
  }
  next(0);
}
function loadPersistedCache(){
  /* Giữ hit-rate qua lần mở trang (ghi chú "truy xuất nhanh chóng"). */
  try {
    if (location.protocol !== 'http:' || typeof localStorage === 'undefined') return;
    var raw = localStorage.getItem(LS_KEY);
    if (!raw) return;
    var j = JSON.parse(raw);
    if (!j || !j.items) return;
    var now = Date.now(), n = 0;
    for (var k in j.items){
      if (!j.items.hasOwnProperty(k)) continue;
      var e = j.items[k];
      if (e && e.exp > now && e.val){ S.cache.put(k, e.val, now, e.exp - now); n++; }
    }
    if (n) S.puts = 0;
  } catch (e){}
}
function persistCacheSoon(){
  try {
    if (location.protocol !== 'http:' || typeof localStorage === 'undefined') return;
    if (S.puts % 8) return;
    var items = {}, st = S.cache;
    if (st._dump) items = st._dump() || {};
    localStorage.setItem(LS_KEY, JSON.stringify({v: 1, items: items}));
  } catch (e){}
}
function pushEvent(e, silent){
  /* Ghi event (bỏ trùng), cắt 200, vẽ HUD. Mọi agent/model/tool đều qua đây. */
  if (!e) return;
  var k = evKey(e);
  if (S.evKeys[k]) { paintHud(); return; }
  S.evKeys[k] = 1;
  S.events.push(e);
  if (S.events.length > EV_CAP){
    var old = S.events.splice(0, S.events.length - EV_CAP);
    for (var i = 0; i < old.length; i++) delete S.evKeys[evKey(old[i])];
  }
  if (!silent) paintHud();
  return e;
}
function runRound(opts){
  /* 1 vòng: mỗi agent bật chạy 1 query (xoay vòng theo qrot) trên dataset hiện tại. */
  opts = opts || {};
  var ags = [], i;
  for (i = 0; i < S.agents.length; i++) if (S.agents[i].on) ags.push(S.agents[i]);
  if (!ags.length || !S.queries.length) return [];
  var ds = opts.dataset || curDatasetName() || S.queries && agentDataset();
  var out = [];
  S.round++;
  for (i = 0; i < ags.length; i++){
    var ix = S.ix[ds];
    if (!ix) continue;
    var q = S.queries[(S.qrot + i) % S.queries.length];
    out.push(pushEvent(GS.runAgent(ix, ags[i], q, S.cache, S.tuner, ds, S.round), true));
  }
  S.qrot = (S.qrot + 1) % S.queries.length;
  S.lastQ = opts.dataset ? '' : S.lastQ;
  paintHud();
  return out;
}
function runQuery(agentId, q, dsName){
  var ix = S.ix[dsName || curDatasetName()];
  if (!ix) return null;
  var ag = S.byId[agentId || 'scout'] || S.agents[0];
  if (!ag) return null;
  return pushEvent(GS.runAgent(ix, ag, q, S.cache, S.tuner, ix.name, S.round));
}
function curDatasetName(){
  try {
    if (typeof WDS !== 'undefined' && WDS && WDS.name) return WDS.name;
  } catch (e){}
  try {
    if (typeof DS !== 'undefined' && DS && DS.name) return DS.name;
  } catch (e){}
  return null;
}
function agentDataset(){
  for (var k in S.ix) if (S.ix.hasOwnProperty(k)) return k;
  return null;
}
function frame(dsName){
  /* Khung tín hiệu cho engine vẽ: hit mới nhất của mỗi agent + heat map decay.
   * Tra ve {rings:[{i,x,y?,color,age,ms,agent,model,q,hits}], heat:{idx:0..1}}. */
  var rings = [], heat = {}, i, e;
  var now = Date.now() / 1000;
  var per = {}, order = [];
  for (i = S.events.length - 1; i >= 0; i--){
    e = S.events[i];
    if (e.dataset !== dsName) continue;
    if (S.solo && e.agent !== S.solo) continue;
    if (!per[e.agent]){ per[e.agent] = e; order.push(e); }
    if (order.length >= 12) break;
  }
  for (i = 0; i < order.length; i++){
    e = order[i];
    var ag = S.byId[e.agent];
    var col = (ag && ag.color) || '#22d3ee';
    for (var h = 0; h < e.hits.length && h < 24; h++){
      var idx = toIdx(dsName, e.hits[h]);
      if (idx < 0) continue;
      var age = Math.max(0, now - (+e.t || now));
      heat[idx] = Math.max(heat[idx] || 0, Math.max(0, 1 - age / FRAME_MAX_AGE));
      rings.push({i: idx, color: col, age: age, ms: e.latency_ms, agent: e.agent,
                  model: e.model || '', q: e.query, id: e.hits[h].id});
      if (rings.length >= DRAW_CAP) break;
    }
    if (rings.length >= DRAW_CAP) break;
  }
  /* heat cho các hit cũ hơn (vẫn trong 14s nhưng không phải mới nhất/agent). */
  for (i = S.events.length - 1; i >= 0; i--){
    e = S.events[i];
    if (e.dataset !== dsName) continue;
    var a2 = Math.max(0, now - (+e.t || now));
    if (a2 > FRAME_MAX_AGE) break;
    for (var h2 = 0; h2 < e.hits.length && h2 < 8; h2++){
      var ix2 = toIdx(dsName, e.hits[h2]);
      if (ix2 >= 0) heat[ix2] = Math.max(heat[ix2] || 0, 1 - a2 / FRAME_MAX_AGE);
    }
  }
  return {rings: rings, heat: heat, n: S.events.length};
}
function toIdx(dsName, h){
  if (!h) return -1;
  if (h.i != null && +h.i >= 0){
    var n = ixSize(dsName);
    if (+h.i < n) return +h.i;
  }
  var m = S.idmap[dsName];
  if (m && h.id != null && m[h.id] != null) return m[h.id];
  return -1;
}
function ixSize(dsName){
  var ix = S.ix[dsName];
  return ix ? ix.n : 0;
}
function statsForHud(){
  /* Tổng hợp cho HUD: cùng số với Python metrics(). */
  var m = GS.metrics(S.events), tot = m.totals || {}, by = m.byAgent || {};
  var cs = S.cache.stats(), tun = S.tuner.snapshot();
  var spd = [], aid;
  for (aid in by){
    if (!by.hasOwnProperty(aid)) continue;
    var ag = S.byId[aid] || {};
    spd.push({id: aid, label: ag.label || aid, model: by[aid].model || ag.model || '',
              color: ag.color || '#22d3ee', on: ag.on !== false,
              speed: by[aid].speed, p50: by[aid].p50_ms, p95: by[aid].p95_ms,
              bud: by[aid].ms_budget, runs: by[aid].runs,
              saved: by[aid].tokens_saved, spct: by[aid].saved_pct,
              hit: by[aid].cache_hit_pct, cost: by[aid].cost_usd,
              tuned: (tun[aid] && tun[aid].tuned) || 0,
              k: (tun[aid] && tun[aid].k) || (ag.k || 0)});
  }
  spd.sort(function(a, b){ return b.speed - a.speed; });
  return {agents: spd, runs: tot.runs || 0, saved: tot.saved || 0,
          spct: tot.saved_pct || 0, ret: tot.ret || 0, base: tot.base || 0,
          cost: tot.cost || 0, hitpct: tot.cache_hit_pct || 0,
          chits: cs.hits || 0, cmiss: cs.misses || 0, live: S.live,
          sig: S.sig, gen: S.generated, n: S.events.length,
          solo: S.solo, on: S.on, auto: S.auto};
}
function esc2(s){ return esc(s); }
function paintHud(){
  /* Vẽ HUD (lazy, thiếu node nào vẫn không lỗi). */
  var st = $('sigStats'), ag = $('sigAgents'), ev = $('sigEvents');
  var d = statsForHud(), i, h;
  if (st){
    h = '<div class="sg-top"><span class="sg-badge ' + (d.live === 'live' ? 'on' : '') + '">' +
        (d.live === 'live' ? '● LIVE' : '○ SNAPSHOT') + '</span>' +
        '<span class="sg-sig" title="signature dữ liệu (2 map đồng bộ)">sig ' + esc(d.sig || '—') + '</span></div>' +
        '<div class="sg-nums"><div><b>' + fmtTok(d.saved) + '</b><span>token tiết kiệm (' +
        d.spct + '%)</span></div>' +
        '<div><b>' + d.runs + '</b><span>lượt truy xuất</span></div>' +
        '<div><b>' + d.hitpct + '%</b><span>cache hit</span></div>' +
        '<div><b>' + fmtUsd(d.cost) + '</b><span>chi phí</span></div></div>';
    if (S.solo) h += '<div class="sg-solo">đang lọc: <b>' + esc(S.solo) + '</b> ' +
      '<button data-sg="unsolo">× bỏ lọc</button></div>';
    st.innerHTML = h;
  }
  if (ag){
    h = '';
    for (i = 0; i < d.agents.length; i++){
      var a = d.agents[i];
      h += '<button class="sg-ag' + (a.on ? '' : ' off') + '" data-sg="agent" data-id="' + esc(a.id) + '"' +
           ' title="' + esc(a.model) + ' · p50 ' + fmtMs(a.p50) + 'ms · p95 ' + fmtMs(a.p95) +
           'ms / budget ' + a.bud + 'ms">' +
           '<i style="background:' + esc(a.color) + '"></i><span class="sg-an">' + esc(a.label) + '</span>' +
           '<span class="sg-am">' + esc(a.model) + '</span>' +
           '<span class="sg-as">' + a.speed + '</span></button>';
    }
    h += '<div class="sg-ctl"><button data-sg="round">▶ chạy 1 vòng</button>' +
         '<button data-sg="auto">' + (d.auto ? '⏸ auto' : '▶ auto') + '</button>' +
         '<button data-sg="poll">⟳ đồng bộ</button></div>';
    ag.innerHTML = h;
  }
  if (ev){
    h = '';
    for (i = d ? 0 : 0, i = S.events.length - 1; i >= 0 && h.length < 6000; i--){
      var e = S.events[i];
      if (S.solo && e.agent !== S.solo) continue;
      var c2 = (S.byId[e.agent] && S.byId[e.agent].color) || '#22d3ee';
      h += '<button class="sg-ev" data-sg="ev" data-t="' + e.t + '" data-a="' + esc(e.agent) + '">' +
           '<i style="background:' + esc(c2) + '"></i>' +
           '<span class="sg-eq">' + esc2(e.query) + '</span>' +
           '<span class="sg-em">' + esc(e.agent) + ' · ' + fmtMs(e.latency_ms) + 'ms · −' +
           fmtTok(e.tokens_saved) + (e.cache ? ' · cache' : '') + (e.tuned ? ' · tuned' : '') + '</span></button>';
      if (S.events.length - 1 - i > 24) break;
    }
    ev.innerHTML = h || '<div class="sg-empty">chưa có tín hiệu — bấm “chạy 1 vòng”.</div>';
  }
  bindHudClicks();
}
function bindHudClicks(){
  var host = $('sigPanel');
  if (!host || host._sgBound) return;
  host._sgBound = 1;
  host.addEventListener('click', function(ev){
    var t = ev.target;
    while (t && t !== host && !t.getAttribute('data-sg')) t = t.parentNode;
    if (!t || t === host) return;
    var act = t.getAttribute('data-sg');
    if (act === 'round'){ runRound({}); needsRenderSoon(); }
    else if (act === 'auto'){ S.auto = !S.auto; setupPoll(); paintHud(); needsRenderSoon(); }
    else if (act === 'poll'){ pollSnapshot(true); }
    else if (act === 'unsolo'){ S.solo = null; paintHud(); needsRenderSoon(); }
    else if (act === 'agent'){
      var id = t.getAttribute('data-id');
      if (S.byId[id]){ S.byId[id].on = !(S.byId[id].on !== false); }
      if (S.solo === id) S.solo = null; else S.solo = id;
      paintHud(); needsRenderSoon();
    }
    else if (act === 'ev'){
      soloEvent(t.getAttribute('data-a'), parseFloat(t.getAttribute('data-t')));
    }
  });
}
function soloEvent(agent, tt){
  S.solo = (S.solo === agent) ? null : agent;
  for (var i = S.events.length - 1; i >= 0; i--){
    var e = S.events[i];
    if (e.agent === agent && Math.abs((+e.t || 0) - tt) < 0.001){
      try { focusHit(e); } catch (err){}
      break;
    }
  }
  paintHud(); needsRenderSoon();
}
function focusHit(e){
  /* Engine đăng ký hook này: Canvas2D selectNode+flyTo, WebGL wSelectNode+wFlyTo. */
  if (S.cfg && S.cfg.focus && e && e.hits && e.hits.length){
    var ds = e.dataset || curDatasetName(), idx = toIdx(ds, e.hits[0]);
    if (idx >= 0) S.cfg.focus(idx);
  }
}
function needsRenderSoon(){
  try {
    if (typeof needsRender !== 'undefined') needsRender = true;
  } catch (e){}
  try {
    if (typeof wneed !== 'undefined') wneed = true;
  } catch (e){}
}
function applySnapshot(j, why){
  /* Nhận snapshot (nhúng / poll / SSE): chỉ merge event MỚI + refresh số liệu. */
  if (!j) return false;
  S.snap = j;
  if (j.signature) S.sig = j.signature;
  if (j.generated) S.generated = j.generated;
  if (j.agents && j.agents.length){
    S.agents = j.agents.map(function(a){
      var c = {};
      for (var k in a) if (a.hasOwnProperty(k)) c[k] = a[k];
      if (c.on == null) c.on = (S.byId[c.id] ? S.byId[c.id].on !== false : true);
      return c;
    });
    S.byId = {};
    for (var i = 0; i < S.agents.length; i++) S.byId[S.agents[i].id] = S.agents[i];
  }
  if (j.queries && j.queries.length) S.queries = j.queries.slice();
  var added = 0;
  if (j.events && j.events.length){
    for (var e = 0; e < j.events.length; e++){
      var k = evKey(j.events[e]);
      if (!S.evKeys[k]){
        S.evKeys[k] = 1; S.events.push(j.events[e]); added++;
      }
    }
    S.events.sort(function(a, b){ return (+a.t || 0) - (+b.t || 0); });
    if (S.events.length > EV_CAP){
      var old = S.events.splice(0, S.events.length - EV_CAP);
      for (var o = 0; o < old.length; o++) delete S.evKeys[evKey(old[o])];
    }
  }
  paintHud();
  return added > 0 || why === 'init';
}
function pollSnapshot(force){
  if (location.protocol !== 'http:'){ if (force) paintHud(); return; }
  var xhr;
  try { xhr = new XMLHttpRequest(); } catch (e){ return; }
  try {
    xhr.open('GET', 'api/snapshot?t=' + Date.now(), true);
    xhr.timeout = 8000;
    xhr.onreadystatechange = function(){
      if (xhr.readyState !== 4) return;
      if (xhr.status === 200){
        try {
          var j = JSON.parse(xhr.responseText);
          S.live = 'live';
          var had = applySnapshot(j);
          if (j.signature && j.signature !== S.sig0 && S.sig0) offerReload();
          if (had) needsRenderSoon();
        } catch (e){}
      }
      paintHud();
    };
    xhr.onerror = function(){ S.live = 'snapshot'; paintHud(); };
    xhr.ontimeout = function(){ S.live = 'snapshot'; paintHud(); };
    xhr.send();
  } catch (e){}
}
function setupSSE(){
  try {
    if (location.protocol !== 'http:' || typeof EventSource === 'undefined') return;
    if (S.es) return;
    var es = new EventSource('api/stream');
    S.es = es;
    es.addEventListener('event', function(ev){
      try {
        var e = JSON.parse(ev.data);
        S.live = 'live';
        pushEvent(e);
        needsRenderSoon();
      } catch (err){}
    });
    es.addEventListener('snapshot', function(ev){
      try {
        var j = JSON.parse(ev.data);
        S.live = 'live';
        if (applySnapshot(j)) needsRenderSoon();
      } catch (err){}
    });
    es.addEventListener('reload', function(){
      try {
        var j = JSON.parse((arguments[0] || {}).data || '{}');
        if (j.signature && j.signature !== currentSig()) offerReload();
      } catch (err){ offerReload(); }
    });
    es.onerror = function(){ S.live = 'snapshot'; paintHud(); };
  } catch (e){}
}
function setupPoll(){
  try { if (S.pollT){ clearInterval(S.pollT); S.pollT = null; } } catch (e){}
  try {
    S.pollT = setInterval(function(){ pollSnapshot(false); }, S.auto ? 4000 : 15000);
  } catch (e){}
}
/*__MORE7__*/
function currentSig(){
  try {
    if (typeof DATA !== 'undefined' && DATA && DATA.signature) return DATA.signature;
  } catch (e){}
  return S.sig0 || '';
}
function offerReload(){
  /* Dữ liệu build mới trên server -> toast, bấm để reload (liên tục, không mất trang). */
  try {
    var host = $('sigReload');
    if (host){ host.style.display = 'block'; bindReload(host); return; }
    var st = $('stage') || document.body;
    var d = document.createElement('div');
    d.id = 'sigReload';
    d.innerHTML = 'Dữ liệu bản đồ đã cập nhật — <button data-sg="doreload">tải lại</button>';
    st.appendChild(d);
    bindReload(d);
  } catch (e){}
}
function bindReload(host){
  if (!host || host._sgR) return;
  host._sgR = 1;
  host.addEventListener('click', function(ev){
    var t = ev.target;
    if (t && (t.getAttribute('data-sg') === 'doreload' || t.tagName === 'BUTTON')){
      try { location.reload(); } catch (e){}
    }
  });
}
function applySignalFx(key, on){
  /* Checkbox "Tín hiệu truy xuất" ở sidebar (ngoài 7 hiệu ứng gốc). */
  S.on = (on !== false);
  try {
    var el = $('fxSignals');
    if (el && el.checked !== S.on) el.checked = S.on;
  } catch (e){}
  paintHud(); needsRenderSoon();
}
function boot(cfg){
  /* cfg = {focus(i)}. Gọi 1 lần sau khi map boot xong. */
  S.cfg = cfg || {};
  var sig0 = '';
  try {
    if (typeof DATA !== 'undefined' && DATA){
      if (DATA.signature) sig0 = DATA.signature;
      if (DATA.signals) applySnapshot(DATA.signals, 'init');
    }
  } catch (e){}
  S.sig0 = sig0 || S.sig;
  if (!S.agents.length){
    S.agents = GS.defaultAgents();
    S.byId = {};
    for (var i = 0; i < S.agents.length; i++) S.byId[S.agents[i].id] = S.agents[i];
  }
  if (!S.queries.length){
    S.queries = ['risk stop loss', 'layout 3d', 'memory agent', 'backtest pnl'];
  }
  loadPersistedCache();
  bindHudClicks();
  buildAllIx((typeof DATA !== 'undefined' && DATA && DATA.datasets) || [], function(){
    paintHud();
    needsRenderSoon();
  });
  paintHud();
  setupSSE();
  setupPoll();
  try {
    var el = $('fxSignals');
    if (el) el.addEventListener('change', function(){ applySignalFx(el.checked); });
  } catch (e){}
  /* Phím tắt Q = chạy 1 vòng, Shift+A = auto (ngoài 1/2/3 của layout). */
  try {
    document.addEventListener('keydown', function(ev){
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      var tag = (ev.target && ev.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (ev.key === 'q' || ev.key === 'Q'){ runRound({}); needsRenderSoon(); }
      else if (ev.key === 'A'){ S.auto = !S.auto; setupPoll(); paintHud(); }
    });
  } catch (e){}
  return api();
}
function api(){
  return {
    S: S, stats: statsForHud, frame: frame,
    run: runQuery, round: runRound, boot: boot,
    fx: applySignalFx, poll: pollSnapshot,
    on: function(id){ var a = S.byId[id]; if (a){ a.on = true; paintHud(); } },
    off: function(id){ var a = S.byId[id]; if (a){ a.on = false; paintHud(); } },
    solo: function(id){ S.solo = (S.solo === id) ? null : id; paintHud(); }
  };
}
window.__GSL = { S: S, V: '1.0', api: api, boot: boot };

})();
