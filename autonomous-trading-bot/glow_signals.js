/* glow_signals.js - runtime "tin hieu truy xuat AI" dung chung cho CA HAI ban do.
 * build_glow.py nhung NGUYEN VAN vao glow_map.html + glow_map_webgl.html
 * (placeholder GLOW_SIGNALS_LIB o dau script) -> 2 engine luon chay cung 1 logic.
 * Giong het ban Python (glow_retrieval.py): tokenize, BM25-lite, cache LRU/TTL,
 * tuner, metrics. Khong dung thu vien ngoai. Top-level khong cham DOM
 * (de `node --check` va test parity Python<->JS chay duoc).
 */
var GS = (function(){
'use strict';
var K1 = 1.2, B_LEN = 0.3, MIN_TOK = 8, REC_TOK = 140;
var AGENTS0 = [
  {id:'scout',label:'Scout',model:'gpt-4o-mini',provider:'OpenAI',color:'#22d3ee',
   tier:'fast',strategy:'fast',k:8,beam:1,ms_budget:45,token_budget:900,
   cache_ttl_ms:90000,price_in:0.15,price_out:0.60},
  {id:'analyst',label:'Analyst',model:'claude-3.5-sonnet',provider:'Anthropic',color:'#a855f7',
   tier:'deep',strategy:'deep',k:20,beam:2,ms_budget:120,token_budget:2600,
   cache_ttl_ms:180000,price_in:3.0,price_out:15.0},
  {id:'coder',label:'Coder',model:'qwen3-coder',provider:'Alibaba',color:'#fbbf24',
   tier:'code',strategy:'code',k:12,beam:1,ms_budget:70,token_budget:1500,
   cache_ttl_ms:120000,price_in:0.30,price_out:1.20},
  {id:'auditor',label:'Auditor',model:'deepseek-v3',provider:'DeepSeek',color:'#34d399',
   tier:'verify',strategy:'hybrid',k:16,beam:1,ms_budget:100,token_budget:2000,
   cache_ttl_ms:150000,price_in:0.27,price_out:1.10},
  {id:'oracle',label:'Oracle',model:'bge-m3-embed',provider:'local',color:'#e2e8f0',
   tier:'index',strategy:'semantic',k:24,beam:1,ms_budget:60,token_budget:3200,
   cache_ttl_ms:300000,price_in:0.02,price_out:0.02}
];
function estTok(s){ s = String(s); return Math.max(1, Math.ceil(s.length * 0.25)); }
function tokenize(text){
  var out = [], words = String(text).match(/[A-Za-z_][A-Za-z0-9_]*|\d+/g) || [];
  for (var w = 0; w < words.length; w++){
    var raw = words[w], segs = raw.split('_'), bits = [];
    for (var s = 0; s < segs.length; s++){
      if (!segs[s]) continue;
      var parts = segs[s].split(/(?<=[a-z0-9])(?=[A-Z])/);
      for (var p = 0; p < parts.length; p++) bits.push(parts[p]);
    }
    for (var b = 0; b < bits.length; b++){
      var t = bits[b].toLowerCase();
      if (t.length >= 2 || /^\d+$/.test(t)) out.push(t);
    }
    if (bits.length > 1) out.push(raw.toLowerCase());
  }
  return out;
}
function normQuery(q){
  var seen = {}, u = [], arr = tokenize(q), i;
  for (i = 0; i < arr.length; i++) if (!seen[arr[i]]){ seen[arr[i]] = 1; u.push(arr[i]); }
  u.sort();
  return u.join(' ') || String(q).trim().toLowerCase();
}
function pct(xs, p){
  var s = xs.slice().sort(function(a,b){ return a-b; });
  if (!s.length) return 0;
  if (s.length === 1) return s[0];
  var r = (s.length - 1) * (p / 100), lo = Math.floor(r), hi = Math.min(s.length - 1, lo + 1);
  return s[lo] + (s[hi] - s[lo]) * (r - lo);
}
/* Chi muc cho 1 dataset: docs=[{id,label,deg,file,tokens}], edges=[s,t,ti,same..]. */
function buildIndex(docs, edges, fileTokens, name){
  var n = docs.length, df = {}, post = {}, tlen = [], ltoks = [], adj = [];
  var i, e;
  for (i = 0; i < n; i++) adj.push([]);
  for (i = 0; i < n; i++){
    var toks = tokenize(docs[i].id).concat(tokenize(docs[i].label));
    var tf = {}, x;
    for (x = 0; x < toks.length; x++) tf[toks[x]] = (tf[toks[x]] || 0) + 1;
    tlen.push(Math.max(1, toks.length));
    var ls = {}, ll = tokenize(docs[i].label), q;
    for (q = 0; q < ll.length; q++) ls[ll[q]] = 1;
    ltoks.push(ls);
    for (var k in tf){
      if (!tf.hasOwnProperty(k)) continue;
      df[k] = (df[k] || 0) + 1;
      if (!post[k]) post[k] = [];
      post[k].push([i, tf[k]]);
    }
  }
  var avg = 1;
  if (n){ var s0 = 0; for (i = 0; i < n; i++) s0 += tlen[i]; avg = s0 / n; }
  if (edges) for (e = 0; e + 3 < edges.length; e += 4){
    var a = edges[e], b = edges[e + 1];
    if (a >= 0 && a < n && b >= 0 && b < n){ adj[a].push(b); adj[b].push(a); }
  }
  function idf(t){
    var d = df[t] || 0;
    return Math.log(1 + (n - d + 0.5) / (d + 0.5));
  }
  function baseline(i){
    var f = docs[i].file;
    if (f && fileTokens && fileTokens[f]) return fileTokens[f];
    return REC_TOK;
  }
  function expand(t, strategy, cand){
    var out = [], i2, j, tok, lst;
    if ((strategy === 'code' && t.length >= 3) ||
        (strategy === 'semantic' && t.length >= 4)){
      var pre = (strategy === 'code');
      for (i2 = 0; i2 < cand.length; i2++) out.push([cand[i2][0], cand[i2][1], 1.0]);
      for (tok in post){
        if (!post.hasOwnProperty(tok) || tok === t) continue;
        var hit = pre ? (tok.indexOf(t) === 0) : (tok.indexOf(t) >= 0);
        if (hit){
          lst = post[tok];
          for (j = 0; j < lst.length; j++) out.push([lst[j][0], lst[j][1], pre ? 0.6 : 0.5]);
        }
      }
      return out;
    }
    for (i2 = 0; i2 < cand.length; i2++) out.push([cand[i2][0], cand[i2][1], 1.0]);
    return out;
  }
  function costOf(hits){
    var ret = 0, base = 0, seen = {}, nf = 0, i3;
    for (i3 = 0; i3 < hits.length; i3++){
      var h = hits[i3];
      ret += Math.max(MIN_TOK, docs[h.i].tokens || MIN_TOK);
      var key = docs[h.i].file || ('mem:' + docs[h.i].id);
      if (!seen[key]){ seen[key] = 1; nf++; base += baseline(h.i); }
    }
    var saved = Math.max(0, base - ret);
    return {returned: ret, baseline: base, saved: saved,
            pct: base ? Math.round(1000 * saved / base) / 10 : 0, files: nf};
  }
  function search(query, k, strategy){
    var scored = {}, qtoks = tokenize(query), i4, j4;
    for (i4 = 0; i4 < qtoks.length; i4++){
      var t = qtoks[i4], cand = post[t];
      if (!cand) continue;
      var w = idf(t), ex = expand(t, strategy, cand);
      for (j4 = 0; j4 < ex.length; j4++){
        var di = ex[j4][0], tf = ex[j4][1], mul = ex[j4][2], dl = tlen[di];
        var bm = (tf * (K1 + 1)) / (tf + K1 * (1 - B_LEN + B_LEN * dl / avg));
        var sc = w * bm * mul;
        if (ltoks[di][t]) sc *= 1.6;
        sc *= 1 + 0.12 * Math.log(1 + docs[di].deg);
        scored[di] = (scored[di] || 0) + sc;
      }
    }
    var keys = Object.keys(scored), kk;
    if ((strategy === 'hybrid' || strategy === 'deep') && keys.length){
      var base = {};
      for (kk = 0; kk < keys.length; kk++) base[keys[kk]] = scored[keys[kk]];
      var seeds = keys.map(Number)
        .sort(function(x, y){ return base[y] - base[x]; }).slice(0, 8);
      for (var s2 = 0; s2 < seeds.length; s2++){
        var nb = adj[seeds[s2]];
        for (var n2 = 0; n2 < nb.length; n2++)
          if (!(nb[n2] in scored)) scored[nb[n2]] = base[seeds[s2]] * 0.35;
      }
      if (strategy === 'deep'){
        var k2 = Object.keys(scored).map(Number)
          .sort(function(x, y){ return scored[y] - scored[x]; }).slice(0, 12);
        for (var s3 = 0; s3 < k2.length; s3++){
          var nb2 = adj[k2[s3]];
          for (var n3 = 0; n3 < nb2.length; n3++)
            if (!(nb2[n3] in scored)) scored[nb2[n3]] = scored[k2[s3]] * 0.15;
        }
      }
    }
    var order = Object.keys(scored).map(Number).sort(function(a, b){
      if (scored[b] !== scored[a]) return scored[b] - scored[a];
      if (docs[b].deg !== docs[a].deg) return docs[b].deg - docs[a].deg;
      return docs[a].id < docs[b].id ? -1 : 1;
    });
    var lim = Math.max(1, k), hits = [];
    for (var h2 = 0; h2 < order.length && h2 < lim; h2++){
      var di2 = order[h2];
      hits.push({i: di2, id: docs[di2].id, label: docs[di2].label,
                 file: docs[di2].file || '', deg: docs[di2].deg,
                 score: Math.round(scored[di2] * 10000) / 10000});
    }
    return {hits: hits, scored: order.length, qtokens: qtoks.length, cost: costOf(hits)};
  }
  return {name: name, n: n, docs: docs, adj: adj, search: search, costOf: costOf,
          baseline: baseline, terms: Object.keys(post).length};
}
/* Cache LRU + TTL + Tuner + runAgent + metrics (giong ban Python). */
function makeCache(maxsize){
  var store = {}, order = [], hits = 0, misses = 0, maxn = maxsize || 256;
  function drop(k){ delete store[k]; var i = order.indexOf(k); if (i >= 0) order.splice(i, 1); }
  return {
    get: function(key, nowMs){
      var e = store[key];
      if (!e){ misses++; return null; }
      if (e.exp < nowMs){ drop(key); misses++; return null; }
      var i = order.indexOf(key);
      if (i >= 0){ order.splice(i, 1); order.push(key); }
      hits++;
      return e.val;
    },
    put: function(key, val, nowMs, ttlMs){
      if (!store[key]) order.push(key); else { var i = order.indexOf(key); order.splice(i, 1); order.push(key); }
      store[key] = {val: val, exp: nowMs + ttlMs};
      while (order.length > maxn) drop(order[0]);
    },
    stats: function(){
      var t = hits + misses;
      return {hits: hits, misses: misses, size: order.length,
              hit_pct: t ? Math.round(1000 * hits / t) / 10 : 0};
    },
    clear: function(){ store = {}; order = []; hits = misses = 0; }
  };
}
function makeTuner(window){
  var W = window || 12, state = {};
  function init(a){
    var s = state[a.id];
    if (!s){ s = {k: a.k, beam: a.beam, hist: [], tuned: 0}; state[a.id] = s; }
    return s;
  }
  return {
    init: init,
    adapt: function(a, ms, cacheHit){
      var s = init(a);
      s.hist.push(ms); if (s.hist.length > W) s.hist = s.hist.slice(-W);
      if (s.hist.length < 4) return [s.k, s.beam, false];
      var p95 = pct(s.hist, 95), top = a.ms_budget || 60, kk = s.k, bb = s.beam;
      if (p95 > top && kk > 4){ kk = Math.max(4, kk - 2); bb = Math.max(1, bb - 1); }
      else if (p95 < 0.5 * top && cacheHit && kk < a.k){ kk = Math.min(a.k, kk + 1); }
      var done = (kk !== s.k) || (bb !== s.beam);
      if (done){ s.k = kk; s.beam = bb; s.tuned++; }
      return [kk, bb, done];
    },
    snapshot: function(){
      var o = {}, k;
      for (k in state){
        if (!state.hasOwnProperty(k)) continue;
        var s = state[k];
        o[k] = {k: s.k, beam: s.beam, tuned: s.tuned,
                p95_ms: s.hist.length ? Math.round(pct(s.hist, 95) * 100) / 100 : 0};
      }
      return o;
    }
  };
}
function defaultAgents(){
  return AGENTS0.map(function(a){
    var c = {};
    for (var k in a) if (a.hasOwnProperty(k)) c[k] = a[k];
    c.note = ''; c.on = true;
    return c;
  });
}
function runAgent(ix, agent, query, cache, tuner, dataset, rund, nowSec){
  var now = (nowSec == null) ? (Date.now() / 1000) : nowSec;
  var t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  var st = tuner.init(agent);
  var key = agent.id + '|' + dataset + '|' + normQuery(query) + '|' + st.k;
  var hit = cache.get(key, now * 1000), res, cached;
  if (hit !== null){ res = hit; cached = true; }
  else { res = ix.search(query, st.k, agent.strategy || 'fast'); cached = false;
         cache.put(key, res, now * 1000, agent.cache_ttl_ms || 120000); }
  var kept = [], used = 0, i, bud = agent.token_budget || 1e9;
  for (i = 0; i < res.hits.length; i++){
    var c = Math.max(MIN_TOK, ix.docs[res.hits[i].i].tokens || MIN_TOK);
    if (used + c > bud) break;
    kept.push(res.hits[i]); used += c;
  }
  var cost = ix.costOf(kept);
  var t1 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  var ms = t1 - t0;
  var ad = tuner.adapt(agent, ms, cached);
  var tokIn = cost.returned;
  var usd = tokIn / 1e6 * ((agent.price_in || 0) + (agent.price_out || 0)) / 2;
  var hh = [];
  for (i = 0; i < kept.length; i++)
    hh.push({i: kept[i].i, id: kept[i].id, file: kept[i].file, score: kept[i].score});
  return {t: Math.round(now * 1000) / 1000, agent: agent.id, model: agent.model,
    query: query, dataset: dataset, round: rund || 0,
    k: st.k, beam: st.beam, strategy: agent.strategy || 'fast',
    hits: hh, n_hits: hh.length, scored: res.scored,
    latency_ms: Math.round(ms * 100) / 100, cache: cached,
    tokens_returned: cost.returned, tokens_baseline: cost.baseline,
    tokens_saved: cost.saved, saved_pct: cost.pct, files_touched: cost.files,
    cost_usd: Math.round(usd * 1e6) / 1e6, truncated: kept.length < res.hits.length,
    tuned: ad[2], k_after: ad[0], beam_after: ad[1], ok: true};
}
function metrics(events){
  var by = {}, i;
  for (i = 0; i < events.length; i++){
    var e = events[i];
    if (e.ok === false) continue;
    var a = by[e.agent];
    if (!a){ a = {ms: [], ret: 0, base: 0, saved: 0, cache: 0, runs: 0, cost: 0,
                   tuned: 0, trunc: 0, hits: 0, model: e.model || ''}; by[e.agent] = a; }
    a.ms.push(+e.latency_ms || 0); a.ret += e.tokens_returned || 0;
    a.base += e.tokens_baseline || 0; a.saved += e.tokens_saved || 0;
    if (e.cache) a.cache++; a.runs++; a.cost += e.cost_usd || 0;
    if (e.tuned) a.tuned++; if (e.truncated) a.trunc++; a.hits += e.n_hits || 0;
  }
  var out = {}, aid;
  for (aid in by){
    if (!by.hasOwnProperty(aid)) continue;
    var x = by[aid], ms = x.ms.length ? x.ms : [0];
    var bud = 60;
    for (var g = 0; g < AGENTS0.length; g++) if (AGENTS0[g].id === aid) bud = AGENTS0[g].ms_budget;
    var p95 = pct(ms, 95);
    out[aid] = {model: x.model, runs: x.runs,
      p50_ms: Math.round(pct(ms, 50) * 100) / 100, p95_ms: Math.round(p95 * 100) / 100,
      ms_budget: bud, speed: Math.min(200, Math.round(100 * bud / Math.max(p95, 0.05))),
      tokens_returned: x.ret, tokens_baseline: x.base, tokens_saved: x.saved,
      saved_pct: x.base ? Math.round(1000 * x.saved / x.base) / 10 : 0,
      cache_hit_pct: x.runs ? Math.round(1000 * x.cache / x.runs) / 10 : 0,
      cost_usd: Math.round(x.cost * 1e6) / 1e6, tuned: x.tuned,
      truncated: x.trunc, hits: x.hits};
  }
  var tot = {runs: 0, ret: 0, base: 0, saved: 0, cost: 0, cache: 0};
  for (aid in by){
    if (!by.hasOwnProperty(aid)) continue;
    var y = by[aid];
    tot.runs += y.runs; tot.ret += y.ret; tot.base += y.base;
    tot.saved += y.saved; tot.cost += y.cost; tot.cache += y.cache;
  }
  tot.cost = Math.round(tot.cost * 1e6) / 1e6;
  tot.saved_pct = tot.base ? Math.round(1000 * tot.saved / tot.base) / 10 : 0;
  tot.cache_hit_pct = tot.runs ? Math.round(1000 * tot.cache / tot.runs) / 10 : 0;
  return {byAgent: out, totals: tot};
}
return {V: '1.0', K1: K1, estTok: estTok, tokenize: tokenize, normQuery: normQuery,
  pct: pct, buildIndex: buildIndex, makeCache: makeCache, makeTuner: makeTuner,
  defaultAgents: defaultAgents, runAgent: runAgent, metrics: metrics,
  REC_TOK: REC_TOK, MIN_TOK: MIN_TOK};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = GS;
