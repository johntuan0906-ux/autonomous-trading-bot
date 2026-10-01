/* _js_parity.js — cầu nối test: chạy kernel JS (glow_signals.js) với đúng
 * đầu vào mà Python (glow_retrieval.py) đã dùng, rồi xuất JSON để so sánh.
 * Cách chạy: node tests/_js_parity.js <input.json> <output.json>
 * Đảm bảo 2 bản đồ (canvas2d + webgl, cùng 1 lib nhúng) cho RA CÙNG kết quả
 * truy xuất với phía Python đã sinh ra snapshot nhúng trong 2 file HTML.
 */
'use strict';
var fs = require('fs');
var path = require('path');
var GS = require(path.join(__dirname, '..', 'glow_signals.js'));

var inPath = process.argv[2], outPath = process.argv[3];
var inp = JSON.parse(fs.readFileSync(inPath, 'utf8'));
var out = {};

out.V = GS.V;
out.K1 = GS.K1;
out.defaultAgents = GS.defaultAgents();
out.tokenize = inp.texts.map(function (s) { return GS.tokenize(s); });
out.normQuery = inp.queries.map(function (q) { return GS.normQuery(q); });
out.pct = inp.pcts.map(function (p) { return GS.pct(p.xs, p.p); });

var ix = GS.buildIndex(inp.docs, inp.flatEdges, inp.fileTokens, 'fixture');
out.index = { n: ix.n, terms: ix.terms };
out.search = [];
for (var i = 0; i < inp.search.length; i++) {
  var s = inp.search[i];
  var r = ix.search(s.query, s.k, s.strategy);
  out.search.push({
    scored: r.scored, qtokens: r.qtokens, cost: r.cost,
    hits: r.hits.map(function (h) {
      return { i: h.i, id: h.id, label: h.label, file: h.file,
               deg: h.deg, score: h.score };
    })
  });
}

var cache = GS.makeCache(4);
var cacheSeq = [];
var NOW = 1000;
for (i = 0; i < inp.cacheSeq.length; i++) {
  var c = inp.cacheSeq[i];
  var got = cache.get(c.key, NOW + c.at);
  cacheSeq.push([got === null ? null : got.v, cache.stats()]);
  if (c.put) cache.put(c.key, { v: c.put }, NOW + c.at, c.ttl);
}
out.cacheSeq = cacheSeq;
out.cacheStats = cache.stats();

var tuner = GS.makeTuner(12);
out.tuner = inp.tunerSeq.map(function (t) {
  var ag = { id: t.id, k: t.k, beam: t.beam, ms_budget: t.ms_budget };
  var r2 = tuner.adapt(ag, t.ms, t.hit);
  return [r2[0], r2[1], r2[2]];
});
out.tunerSnapshot = tuner.snapshot();

/* cache RIENG cho phan runAgent (tranh lam han che ca 2 ben nhu nhau) */
var cacheRuns = GS.makeCache(256);
var ix2 = GS.buildIndex(inp.docs, inp.flatEdges, inp.fileTokens, 'fixture');
var ag = inp.agent;
out.runs = inp.runs.map(function (rr) {
  var e = GS.runAgent(ix2, ag, rr.query, cacheRuns, GS.makeTuner(12), 'fixture',
                      rr.round, 1000.0 + rr.at);
  var t = {};
  for (var k in e) if (k !== 'latency_ms') t[k] = e[k];
  return t;
});

out.metrics = GS.metrics(inp.events);

fs.writeFileSync(outPath, JSON.stringify(out));
console.log('[parity-js] ok: ' + out.search.length + ' searches, ' +
            out.runs.length + ' runs');
