'use strict';
/* bench_core.js — loi do toc do tim kiem/truy xuat DUNG CHUNG node + browser.
 * Doc DUNG pipeline cua ban do: DATA payload -> docsFromDs -> GS.buildIndex
 * -> GS.search / GS.runAgent (kernel nhung trong glow_map.html).
 * Khong thu vien ngoai; hoat dong ca trong node (module.exports) va <script>.
 */
var GB = (function (GS) {
  if (!GS) throw new Error('GS chua duoc nap (glow_signals.js truoc bench_core.js)');
  function nowMs() {
    if (typeof performance !== 'undefined' && performance.now) return performance.now();
    return Date.now();
  }
  function pct(xs, p) {
    if (!xs.length) return 0;
    var s = xs.slice().sort(function (a, b) { return a - b; });
    if (s.length === 1) return s[0];
    var r = (s.length - 1) * (p / 100), lo = Math.floor(r),
        hi = Math.min(s.length - 1, lo + 1);
    return s[lo] + (s[hi] - s[lo]) * (r - lo);
  }
  function stats(xs) {
    var sum = 0, i;
    for (i = 0; i < xs.length; i++) sum += xs[i];
    var mean = xs.length ? sum / xs.length : 0;
    return { n: xs.length, p50: pct(xs, 50), p95: pct(xs, 95),
             max: xs.length ? Math.max.apply(null, xs) : 0,
             mean: mean, qps: mean > 0 ? 1000 / mean : 0 };
  }
  function r2(x) { return Math.round(x * 100) / 100; }
  function pack(st) {
    return { n: st.n, p50: r2(st.p50), p95: r2(st.p95), max: r2(st.max),
             mean: r2(st.mean), qps: Math.round(st.qps) };
  }
  function docsFromPayload(ds) {
    /* copy doc ban glow_signals_lib.js docsFromDs (id/label/deg/file/kind/tokens). */
    var ids = ds.id || [], labels = ds.label || [], degs = ds.deg || [];
    var kinds = ds.kinds || [], kind = ds.kind || [];
    var clusters = ds.clusters || [], cluster = ds.cluster || [];
    var out = new Array(ids.length), seenF = {}, i;
    for (i = 0; i < ids.length; i++) {
      var id = String(ids[i]);
      var label = String(labels[i] == null ? id : labels[i]);
      var f = '', kk = '';
      try {
        var ci = cluster[i];
        if (ci != null && clusters[ci] != null) f = String(clusters[ci]);
      } catch (e) {}
      try {
        var ki = kind[i];
        if (ki != null && kinds[ki] && kinds[ki][0] != null) kk = String(kinds[ki][0]);
      } catch (e) {}
      out[i] = { id: id, label: label, deg: +degs[i] || 0, file: f, kind: kk,
                 tokens: Math.max(GS.MIN_TOK, GS.estTok(id + ' ' + label)) };
      if (f) seenF[f] = 1;
    }
    return { docs: out, files: Object.keys(seenF) };
  }
  function linksFromPayload(ds) {
    /* edges phang stride 4: (a, b, ti, same) — giong buildIndex doc. */
    var e = ds.edges || [], out = [], n = (ds.id || []).length, i;
    for (i = 0; i + 3 < e.length; i += 4) {
      var a = e[i], b = e[i + 1];
      if (a >= 0 && a < n && b >= 0 && b < n) out.push([a, b]);
    }
    return out;
  }
  function sidebarScan(docs, q) {
    /* giong o Search cua sidebar: toLowerCase + includes, dung khi du 500 hit. */
    var hit = [], i;
    for (i = 0; i < docs.length && hit.length < 500; i++) {
      if (docs[i].label.toLowerCase().indexOf(q) >= 0 ||
          docs[i].id.toLowerCase().indexOf(q) >= 0) hit.push(i);
    }
    return hit.length;
  }
  /* ── Phan chinh: nhan {payloadText, queries, strategies, iters, fileTokens} ── */
  function run(input) {
    var t0 = nowMs();
    var payload = JSON.parse(input.payloadText);
    var res = { engine: 'js', ver: GS.V, payloadMs: r2(nowMs() - t0), datasets: [] };
    var ft = input.fileTokens || {};
    var iters = input.iters || 200;
    var queries = input.queries || ['x'];
    var strategies = input.strategies || ['fast'];
    var dsList = payload.datasets || [];
    var di, si, i;
    for (di = 0; di < dsList.length; di++) {
      var ds = dsList[di];
      var tD = nowMs();
      var dd = docsFromPayload(ds);
      var docsMs = r2(nowMs() - tD);
      var links = linksFromPayload(ds);
      var tL = nowMs();
      var ixLive = GS.buildIndex(dd.docs, ds.edges || [], ft, ds.name);
      var idxLiveMs = r2(nowMs() - tL);
      var tO = nowMs();
      var ixOff = GS.buildIndex(dd.docs, ds.edges || [], {}, ds.name);
      var idxOffMs = r2(nowMs() - tO);
      var dOut = { name: ds.name, nodes: dd.docs.length, edges: links.length,
                   docsMs: docsMs, idxLiveMs: idxLiveMs, idxOffMs: idxOffMs,
                   search: {} };
      /* tim kiem: iters luot / chien luoc, xoay query; do theo LO (batch 10)
       * de khong bi nhiet do phan giai timer (Chrome co the tra ve 0ms). */
      var B = 10;
      for (si = 0; si < strategies.length; si++) {
        var st = strategies[si], lat = [], hits = 0;
        for (i = 0; i < iters; i++) {
          var q = queries[i % queries.length];
          var a = nowMs(), r;
          for (var b = 0; b < B; b++) r = ixLive.search(q, 12, st);
          lat.push((nowMs() - a) / B);
          hits += r.hits.length;
        }
        var sLive = ixLive.search(queries[0], 12, st).cost;
        var sOff = ixOff.search(queries[0], 12, st).cost;
        dOut.search[st] = pack(stats(lat));
        dOut.search[st].hitsAvg = r2(hits / iters);
        dOut.search[st].savedLivePct = sLive.pct;
        dOut.search[st].savedOffPct = sOff.pct;
      }
      /* cache: 2000 lan miss + 2000 lan hit -> us/op */
      var c = GS.makeCache(64);
      var tM = nowMs();
      for (i = 0; i < 2000; i++) c.get('absent|' + (i & 31), 1000);
      var missUs = (nowMs() - tM) * 1000 / 2000;
      c.put('ck', { v: 1 }, 1000, 1e9);
      var tH = nowMs();
      for (i = 0; i < 2000; i++) c.get('ck', 1000);
      var hitUs = (nowMs() - tH) * 1000 / 2000;
      dOut.cache = { missUs: r2(missUs), hitUs: r2(hitUs) };
      /* vong agent: lan luot (cache) + lan 2 (chay lai) */
      var agents = GS.defaultAgents();
      dOut.round = roundBench(ixLive, agents, queries, ds.name);
      /* sidebar search (o Search) */
      var sLat = [];
      for (i = 0; i < Math.min(iters, 300); i++) {
        var qy = queries[i % queries.length].split(' ')[0].toLowerCase();
        if (qy.length < 2) qy = 'mem';
        var b = nowMs();
        sidebarScan(dd.docs, qy);
        sLat.push(nowMs() - b);
      }
      dOut.sidebar = pack(stats(sLat));
      res.datasets.push(dOut);
    }
    return res;
  }
  function roundBench(ix, agents, queries, dsName) {
    var cache = GS.makeCache(256), tuner = GS.makeTuner(12);
    var perAgent = [], i, j;
    var t0 = nowMs();
    for (i = 0; i < agents.length; i++) {
      var a0 = nowMs();
      for (j = 0; j < queries.length; j++)
        GS.runAgent(ix, agents[i], queries[j], cache, tuner, dsName, 1);
      perAgent.push({ id: agents[i].id, coldMs: r2(nowMs() - a0) });
    }
    var coldMs = r2(nowMs() - t0);
    var warmEvs = [], t1 = nowMs();
    for (i = 0; i < agents.length; i++)
      for (j = 0; j < queries.length; j++)
        warmEvs.push(GS.runAgent(ix, agents[i], queries[j], cache, tuner, dsName, 2));
    var warmMs = r2(nowMs() - t1);
    /* metrics tren vong WARM -> cache_hit% / tiet kiem that su */
    var m = GS.metrics(warmEvs);
    return { agents: agents.length, queries: queries.length,
             coldMs: coldMs, warmMs: warmMs, perAgent: perAgent,
             totals: m.totals };
  }
  return { run: run, stats: stats, pack: pack, docsFromPayload: docsFromPayload,
           sidebarScan: sidebarScan, nowMs: nowMs };
})(typeof GS !== 'undefined' ? GS :
    (typeof require === 'function' && typeof module !== 'undefined' &&
     module.exports) ? require('./glow_signals.js') : null);
if (typeof module !== 'undefined' && module.exports) module.exports = GB;

