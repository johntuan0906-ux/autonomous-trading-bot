"use strict";

(() => {
  const POLL_MS = 10000;
  const SVG_NS = "http://www.w3.org/2000/svg";

  const state = {
    env: "testnet",       // "testnet" | "live" | "both"
    tab: "overview",      // overview | positions | performance | council | harness | architecture
    pollEnabled: true,
    pollTimer: null,
    perfDays: 30,
    botOnly: true,
    chartMode: "equity",  // equity | cum_r | drawdown
    tradePage: 0,
    tradeLimit: 40,
    tradeSymbol: "",
    tradeStrategy: "",
    tradeOutcome: "all",
    docId: "state",
    docFilter: "",
    etagCache: new Map(), // url -> { etag, data }
    docsList: null,
    activeDoc: null,
  };

  // =========================================================================
  // Safe DOM helpers (createElement + textContent only; no raw HTML parsing)
  // =========================================================================
  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined || v === false) continue;
        if (k === "className") node.className = String(v);
        else if (k === "text") node.textContent = String(v);
        else if (k.startsWith("on") && typeof v === "function") {
          node.addEventListener(k.slice(2).toLowerCase(), v);
        } else if (k === "style" && typeof v === "object") {
          for (const [sk, sv] of Object.entries(v)) node.style[sk] = String(sv);
        } else {
          node.setAttribute(k, String(v));
        }
      }
    }
    for (const child of children) {
      if (child === null || child === undefined || child === false) continue;
      if (Array.isArray(child)) {
        for (const sub of child) {
          if (sub !== null && sub !== undefined && sub !== false) {
            node.appendChild(typeof sub === "string" || typeof sub === "number" ? document.createTextNode(String(sub)) : sub);
          }
        }
      } else {
        node.appendChild(typeof child === "string" || typeof child === "number" ? document.createTextNode(String(child)) : child);
      }
    }
    return node;
  }

  function svgEl(tag, attrs, ...children) {
    const node = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined) continue;
        if (k === "text") node.textContent = String(v);
        else node.setAttribute(k, String(v));
      }
    }
    for (const child of children) {
      if (child) node.appendChild(child);
    }
    return node;
  }

  function badge(text, tone = "neutral") {
    return el("span", { className: `badge badge-${tone}`, text });
  }

  // =========================================================================
  // Formatting helpers (honest unknowns, never fake 0)
  // =========================================================================
  function fmtNum(v, digits = 2, suffix = "") {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
    const n = Number(v);
    return `${n.toFixed(digits)}${suffix}`;
  }

  function fmtSigned(v, digits = 2, suffix = "") {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
    const n = Number(v);
    return `${n > 0 ? "+" : ""}${n.toFixed(digits)}${suffix}`;
  }

  function fmtPrice(v) {
    if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
    const n = Number(v);
    const abs = Math.abs(n);
    if (abs === 0) return "0";
    if (abs < 0.01) return n.toFixed(6);
    if (abs < 1) return n.toFixed(4);
    if (abs < 100) return n.toFixed(3);
    return n.toFixed(2);
  }

  function toneBySign(v) {
    if (v === null || v === undefined) return "";
    const n = Number(v);
    if (n > 0) return "val-pos";
    if (n < 0) return "val-neg";
    return "";
  }

  function activeInstance() {
    return state.env === "live" ? "live" : "testnet";
  }

  // =========================================================================
  // ETag-aware GET fetcher
  // =========================================================================
  async function apiGet(url, force = false) {
    const cached = state.etagCache.get(url);
    const headers = {};
    if (!force && cached && cached.etag) {
      headers["If-None-Match"] = cached.etag;
    }
    const resp = await fetch(url, { method: "GET", headers, cache: "no-store" });
    if (resp.status === 304 && cached) {
      return cached.data;
    }
    if (!resp.ok) {
      let msg = `HTTP ${resp.status}`;
      try {
        const err = await resp.json();
        if (err && err.error) msg = err.error;
      } catch (_) {}
      throw new Error(msg);
    }
    const data = await resp.json();
    const etag = resp.headers.get("ETag");
    state.etagCache.set(url, { etag, data });
    return data;
  }

  // =========================================================================
  // Top 5-second vital strip + alert banner
  // =========================================================================
  function setVital(id, valueText, tone = "") {
    const box = document.getElementById(id);
    if (!box) return;
    box.className = `vital-pill${tone ? ` tone-${tone}` : ""}`;
    const vNode = box.querySelector(".vp-v");
    if (vNode) vNode.textContent = valueText;
  }

  function updateVitalStrip(overviewResp) {
    const asOfEl = document.getElementById("header-as-of");
    const banner = document.getElementById("alert-banner");
    clear(banner);

    const deadman = overviewResp.deadman || {};
    if (!deadman.known) {
      setVital("vp-deadman", "UNKNOWN", "warn");
    } else if (deadman.ok) {
      setVital("vp-deadman", deadman.muted ? "OK (MUTED)" : "OK", "ok");
    } else {
      setVital("vp-deadman", `CẢNH BÁO`, "danger");
    }

    if (overviewResp.target === "both") {
      const t = overviewResp.testnet;
      const l = overviewResp.live;
      asOfEl.textContent = `as_of: ${overviewResp.server_ts_human || "--"}`;
      setVital("vp-env", "TESTNET ↔ LIVE", "info");
      const botOk = t.bot.status === "ALIVE" && l.bot.status === "ALIVE";
      setVital("vp-bot", `T:${t.bot.status} | L:${l.bot.status}`, botOk ? "ok" : "danger");
      const ksBad = t.kill_switch.tripped || l.kill_switch.tripped;
      setVital("vp-ks", `T:${t.kill_switch.status} | L:${l.kill_switch.status}`, ksBad ? "danger" : "ok");
      setVital("vp-daily", `T:${fmtSigned(t.equity.daily_pnl_pct, 2, "%")} | L:${fmtSigned(l.equity.daily_pnl_pct, 2, "%")}`, "");
      setVital("vp-pos", `T:${t.positions.open ?? "?"}/${t.positions.max ?? "?"} | L:${l.positions.open ?? "?"}/${l.positions.max ?? "?"}`, "");
      const protBad = t.protection.status === "ALERT" || l.protection.status === "ALERT";
      setVital("vp-prot", `T:${t.protection.status} | L:${l.protection.status}`, protBad ? "danger" : "ok");
      const banAny = t.api_ban.active || l.api_ban.active;
      setVital("vp-ban", banAny ? "ĐANG BAN IP" : "KHÔNG BAN", banAny ? "danger" : "ok");

      const allAlerts = [
        ...(l.alerts || []).map((a) => ({ ...a, prefix: "[LIVE]" })),
        ...(t.alerts || []).map((a) => ({ ...a, prefix: "[TESTNET]" })),
      ];
      renderAlerts(banner, allAlerts);
      return;
    }

    const d = overviewResp.data;
    const isLive = d.instance === "live";
    asOfEl.textContent = `as_of: ${d.as_of_human || "UNKNOWN"}${d.stale ? " (STALE)" : ""}`;
    setVital("vp-env", isLive ? "LIVE · TIỀN THẬT" : "TESTNET · DEMO", isLive ? "danger" : "info");

    const hbText = d.bot.status === "ALIVE"
      ? `ALIVE · ${fmtNum(d.bot.heartbeat_age_s, 0, "s")} (R#${d.bot.round ?? "?"})`
      : `${d.bot.status} (${d.bot.heartbeat_age_s !== null ? fmtNum(d.bot.heartbeat_age_s, 0, "s") : "?"})`;
    setVital("vp-bot", hbText, d.bot.status === "ALIVE" ? "ok" : "danger");

    setVital(
      "vp-ks",
      d.kill_switch.status === "OK" ? "OK (SẠCH)" : d.kill_switch.status,
      d.kill_switch.status === "OK" ? "ok" : (d.kill_switch.status === "TRIPPED" ? "danger" : "warn")
    );

    const dpct = d.equity.daily_pnl_pct;
    const cap = d.equity.max_daily_loss_pct;
    const dailyTone = dpct === null ? "warn" : (cap && dpct <= -cap * 0.7 ? "danger" : (dpct < 0 ? "warn" : "ok"));
    setVital("vp-daily", `${fmtSigned(dpct, 2, "%")} / -${fmtNum(cap, 1, "%")}`, dailyTone);

    const pOpen = d.positions.open;
    const pMax = d.positions.max;
    const posTone = pOpen === null ? "warn" : (pMax && pOpen > pMax ? "warn" : "info");
    setVital("vp-pos", `${pOpen ?? "?"} / ${pMax ?? "?"}`, posTone);

    const pr = d.protection;
    const protText = pr.status === "UNKNOWN"
      ? "UNKNOWN"
      : `${pr.protect_orders ?? "?"}/${pr.expected_orders ?? "?"}${pr.naked && pr.naked.length ? ` (${pr.naked.length} TRẦN!)` : ""}`;
    setVital("vp-prot", protText, pr.status === "OK" ? "ok" : (pr.status === "ALERT" ? "danger" : "warn"));

    const banText = d.api_ban.active
      ? `BAN còn ${fmtNum(d.api_ban.remaining_s / 60, 1, "p")}`
      : "KHÔNG BAN";
    setVital("vp-ban", banText, d.api_ban.active ? "danger" : "ok");

    renderAlerts(banner, (d.alerts || []).map((a) => ({ ...a, prefix: `[${d.instance.toUpperCase()}]` })));
  }

  function renderAlerts(banner, alerts) {
    if (!alerts.length) {
      banner.classList.add("hidden");
      return;
    }
    banner.classList.remove("hidden");
    for (const a of alerts) {
      banner.appendChild(
        el("div", { className: `alert-item ${a.level || "info"}` },
          badge(`${a.prefix} ${a.code}`, a.level === "danger" ? "danger" : (a.level === "warn" ? "warn" : "info")),
          el("span", { text: a.msg })
        )
      );
    }
  }

  // =========================================================================
  // Reusable UI widgets
  // =========================================================================
  function kpi(label, value, meta = "", valClass = "") {
    return el("div", { className: "kpi-card" },
      el("div", { className: "kpi-label", text: label }),
      el("div", { className: `kpi-value ${valClass}`.trim(), text: value }),
      meta ? el("div", { className: "kpi-meta", text: meta }) : null
    );
  }

  function kvRow(k, v, valClass = "") {
    return el("div", { className: "kv-row" },
      el("span", { className: "kv-k", text: k }),
      el("span", { className: `kv-v ${valClass}`.trim(), text: v })
    );
  }

  function makeTable(headers, rows, emptyText = "Không có dữ liệu.") {
    if (!rows.length) {
      return el("div", { className: "empty-box", text: emptyText });
    }
    const thead = el("thead", null,
      el("tr", null, headers.map((h) => el("th", { className: h.num ? "num" : "", text: h.label })))
    );
    const tbody = el("tbody", null,
      rows.map((cells) => el("tr", null, cells.map((c, idx) => {
        const isNum = headers[idx] && headers[idx].num;
        if (c && typeof c === "object" && c instanceof Node) {
          return el("td", { className: isNum ? "num" : "" }, c);
        }
        if (c && typeof c === "object" && "text" in c) {
          return el("td", { className: `${isNum ? "num " : ""}${c.cls || ""}`.trim(), text: c.text });
        }
        return el("td", { className: isNum ? "num" : "", text: c === null || c === undefined ? "N/A" : String(c) });
      })))
    );
    return el("div", { className: "table-wrap" }, el("table", { className: "data-table" }, thead, tbody));
  }

  // =========================================================================
  // TAB 1: OVERVIEW (single instance OR side-by-side comparison)
  // =========================================================================
  function renderInstanceColumn(d) {
    const isLive = d.instance === "live";
    const card = el("section", { className: `card ${isLive ? "card-live" : "card-testnet"}` });

    card.appendChild(el("div", { className: "card-head" },
      el("div", null,
        el("h2", { className: "card-title", text: isLive ? "LIVE — Tiền thật (atb-live, chỉ đọc)" : "TESTNET — Demo & Học (autonomous-trading-bot)" }),
        el("div", { className: "card-sub", text: `commit ${d.git_head || "?"} · as_of ${d.as_of_human || "UNKNOWN"}${d.stale ? " · STALE" : ""}` })
      ),
      el("div", { className: "filter-bar" },
        badge(d.bot.status, d.bot.status === "ALIVE" ? "ok" : "danger"),
        badge(d.kill_switch.status === "OK" ? "KS: SẠCH" : `KS: ${d.kill_switch.status}`, d.kill_switch.status === "OK" ? "ok" : "danger"),
        d.api_ban.active ? badge(`IP BAN ${fmtNum(d.api_ban.remaining_s / 60, 1, "p")}`, "danger") : badge("IP OK", "ok")
      )
    ));

    const eqCur = d.equity.current;
    const dailyPct = d.equity.daily_pnl_pct;
    const cap = d.equity.max_daily_loss_pct || 2.0;
    const lossUsedPct = dailyPct !== null && dailyPct < 0 ? Math.min(100, (Math.abs(dailyPct) / cap) * 100) : 0;

    card.appendChild(el("div", { className: "grid-3" },
      kpi("Equity hiện tại", eqCur !== null ? `${fmtNum(eqCur, 2)} USDT` : "UNKNOWN", `Đầu ngày: ${fmtNum(d.equity.start_day, 2)} · Đỉnh: ${fmtNum(d.equity.peak, 2)}`),
      kpi("PnL trong ngày", dailyPct !== null ? `${fmtSigned(d.equity.daily_pnl_usdt, 2, " $")} (${fmtSigned(dailyPct, 2, "%")})` : "UNKNOWN", `Trần lỗ ngày: -${fmtNum(cap, 1, "%")}`, toneBySign(dailyPct)),
      kpi("Vị thế / Bảo vệ", `${d.positions.open ?? "?"} / ${d.positions.max ?? "?"}`, `Lệnh SL/TP: ${d.protection.protect_orders ?? "?"} (kỳ vọng ${d.protection.expected_orders ?? "?"})`)
    ));

    // Daily loss progress bar
    const barTone = lossUsedPct >= 75 ? "danger" : (lossUsedPct >= 40 ? "warn" : "ok");
    card.appendChild(el("div", null,
      el("div", { className: "kv-row" },
        el("span", { className: "kv-k", text: "Mức sử dụng trần lỗ ngày (Kill-Switch)" }),
        el("span", { className: "kv-v", text: `${fmtNum(lossUsedPct, 1, "%")} (${d.kill_switch.consec_losses ?? "?"}/${d.kill_switch.max_consec_losses ?? "?"} thua liên tiếp · ${d.kill_switch.errors ?? "?"}/${d.kill_switch.max_errors ?? "?"} lỗi API)` })
      ),
      el("div", { className: "bar-track" },
        el("div", { className: `bar-fill ${barTone}`, style: { width: `${lossUsedPct}%` } })
      )
    ));

    // Config & runtime kv
    card.appendChild(el("div", { className: "kv-grid" },
      kvRow("PID / Round / Phase", `${d.bot.pid ?? "?"} · #${d.bot.round ?? "?"} · ${d.bot.phase}`),
      kvRow("Tuổi nhịp tim", d.bot.heartbeat_age_s !== null ? `${fmtNum(d.bot.heartbeat_age_s, 1, "s")} / ${d.bot.watchdog_sec}s` : "UNKNOWN", d.bot.status === "ALIVE" ? "val-pos" : "val-neg"),
      kvRow("Risk / lệnh · Trần tổng", `${fmtNum(d.config.risk_pct, 2, "%")} · ${fmtNum(d.config.max_total_risk_pct, 2, "%")}`),
      kvRow("Leverage · Tier ví", `${d.config.leverage ?? "?"}x · ${d.config.tier_label || "N/A"}`),
      kvRow("Live Ready Gate", d.gates.live_ready_verdict, d.gates.live_ready_ok ? "val-pos" : "val-warn"),
      kvRow("Live Guard Interlock", d.gates.live_guard_ok === true ? "PASS" : (d.gates.live_guard_ok === false ? "BLOCKED" : "UNKNOWN"), d.gates.live_guard_ok ? "val-pos" : "val-neg"),
      kvRow("Hội đồng AI hôm nay", `${d.council_summary.agent_calls_today ?? "?"} gọi · $${fmtNum(d.council_summary.agent_cost_today, 4)}`),
      kvRow("Câu hỏi vận hành chờ", String(d.pending_ops), d.pending_ops > 0 ? "val-warn" : "")
    ));

    // Gate blockers if any
    const blockers = [...(d.gates.live_ready_blockers || []), ...(d.gates.live_guard_blockers || [])];
    if (blockers.length) {
      card.appendChild(el("div", { className: "note-box" },
        el("strong", { text: "Cổng đang chặn: " }),
        el("span", { text: blockers.join(" · ") })
      ));
    }

    // Rolling windows from snapshot (clearly labeled)
    const winRows = [];
    for (const k of ["7", "14", "30"]) {
      const w = (d.snapshot_stats && d.snapshot_stats.windows && d.snapshot_stats.windows[k]) || null;
      if (!w) continue;
      winRows.push([
        `${k} ngày`,
        w.n ?? "N/A",
        fmtNum(w.wr, 1, "%"),
        { text: fmtNum(w.pf_r, 3), cls: (w.pf_r || 0) >= 1.2 ? "val-pos" : "val-neg" },
        { text: fmtNum(w.pf_pnl, 3), cls: (w.pf_pnl || 0) >= 1.1 ? "val-pos" : "val-neg" },
        { text: fmtSigned(w.e_r, 3, "R"), cls: toneBySign(w.e_r) },
        { text: fmtSigned(w.pnl, 2, "$"), cls: toneBySign(w.pnl) },
      ]);
    }
    const allSt = d.snapshot_stats && d.snapshot_stats.all;
    if (allSt && allSt.n !== null) {
      winRows.push([
        "Toàn bộ (gộp)",
        allSt.n,
        fmtNum(allSt.wr, 1, "%"),
        fmtNum(allSt.pf_r, 3),
        fmtNum(allSt.pf_pnl, 3),
        { text: fmtSigned(allSt.e_r, 3, "R"), cls: toneBySign(allSt.e_r) },
        { text: fmtSigned(allSt.pnl, 2, "$"), cls: toneBySign(allSt.pnl) },
      ]);
    }
    card.appendChild(makeTable(
      [
        { label: "Cửa sổ (snapshot)" },
        { label: "n", num: true },
        { label: "WR%", num: true },
        { label: "PF(R)", num: true },
        { label: "PF($)", num: true },
        { label: "E(R)", num: true },
        { label: "PnL $", num: true },
      ],
      winRows,
      "Chưa có state_snapshot.json."
    ));

    if (!isLive) {
      card.appendChild(el("div", { className: "note-box info", text: "Lưu ý: TESTNET là số liệu demo (có thể gồm lệnh tay ở bảng snapshot gộp). Xem tab Hiệu suất với bộ lọc 'Chỉ lệnh BOT' để đối chiếu chuẩn." }));
    }

    return card;
  }

  function renderDeadmanCard(deadman) {
    const card = el("section", { className: "card" });
    card.appendChild(el("div", { className: "card-head" },
      el("div", null,
        el("h3", { className: "card-title", text: "Giám sát Deadman & Supervisor (đã ẩn URL ping)" }),
        el("div", { className: "card-sub", text: `Cập nhật: ${deadman.ts_human || "UNKNOWN"} · Trạng thái: ${deadman.reason || "UNKNOWN"}` })
      ),
      badge(deadman.ok === true ? "DEADMAN OK" : (deadman.ok === false ? "DEADMAN FAIL" : "UNKNOWN"), deadman.ok === true ? "ok" : "danger")
    ));

    const rows = (deadman.instances || []).map((inst) => [
      badge(inst.name, inst.name === "LIVE" ? "danger" : "info"),
      inst.supervisor_pid ?? "N/A",
      inst.round ?? "N/A",
      fmtNum(inst.hb_age_s, 1, "s"),
      badge(inst.kill_tripped ? "TRIPPED" : "OK", inst.kill_tripped ? "danger" : "ok"),
      Object.keys(inst.errors_win || {}).length ? JSON.stringify(inst.errors_win) : "0 lỗi",
    ]);
    card.appendChild(makeTable(
      [
        { label: "Instance" },
        { label: "Supervisor PID", num: true },
        { label: "Round", num: true },
        { label: "HB Age", num: true },
        { label: "Kill-Switch" },
        { label: "Lỗi trong cửa sổ" },
      ],
      rows,
      "Không có dữ liệu deadman.json."
    ));

    if (deadman.pings && deadman.pings.length) {
      const pWrap = el("div", { className: "filter-bar" },
        el("span", { className: "card-sub", text: "Healthchecks pings (URL bị lược bỏ phía server):" }),
        ...deadman.pings.map((p) => badge(`${p.instance}: ${p.ok ? "HTTP " + p.status : "FAIL"}`, p.ok ? "ok" : "danger"))
      );
      card.appendChild(pWrap);
    }
    return card;
  }

  async function renderOverviewTab(container, overviewResp) {
    if (overviewResp.target === "both") {
      container.appendChild(el("div", { className: "grid-2" },
        renderInstanceColumn(overviewResp.testnet),
        renderInstanceColumn(overviewResp.live)
      ));
      container.appendChild(renderDeadmanCard(overviewResp.deadman || {}));
      return;
    }

    container.appendChild(renderInstanceColumn(overviewResp.data));
    container.appendChild(renderDeadmanCard(overviewResp.deadman || {}));
  }

  // =========================================================================
  // TAB 2: POSITIONS & PROTECTION
  // =========================================================================
  async function renderPositionsTab(container, force = false) {
    const inst = activeInstance();
    const data = await apiGet(`/api/positions?t=${inst}`, force);

    const card = el("section", { className: "card" });
    card.appendChild(el("div", { className: "card-head" },
      el("div", null,
        el("h2", { className: "card-title", text: `Vị thế đang quản lý — ${inst.toUpperCase()} (${data.positions.length})` }),
        el("div", { className: "card-sub", text: `managed_state.json lưu lúc: ${data.saved_ts_human || "UNKNOWN"} · as_of: ${data.as_of_human || "UNKNOWN"}` })
      ),
      badge(data.managed_known ? "ĐÃ NẠP" : "THIẾU FILE", data.managed_known ? "ok" : "warn")
    ));

    const posRows = data.positions.map((p) => [
      el("span", { className: "mono", text: p.symbol }),
      badge(p.direction, p.direction === "LONG" ? "ok" : "danger"),
      fmtNum(p.qty, 2),
      fmtPrice(p.entry),
      `${fmtPrice(p.sl)} (${fmtNum(p.sl_pct, 2, "%")})`,
      `${fmtPrice(p.tp)} (${fmtNum(p.tp_pct, 2, "%")})`,
      p.rr !== null ? `${fmtNum(p.rr, 2)}R` : "N/A",
      fmtNum(p.notional_est, 2, "$"),
      { text: `${fmtNum(p.mfe_r, 3)}R`, cls: p.mfe_r >= 1 ? "val-pos" : "" },
      el("div", { className: "filter-bar" },
        badge(p.partial_done ? "PARTIAL" : "FULL", p.partial_done ? "info" : "neutral"),
        badge(p.be_done ? "BE" : "INIT SL", p.be_done ? "ok" : "neutral"),
        p.is_naked ? badge("KHÔNG SL/TP!", "danger") : null,
        p.has_dupes ? badge("TRÙNG LỆNH", "warn") : null
      ),
      p.exchange_orders !== null ? `${p.exchange_orders} lệnh` : "N/A",
    ]);

    card.appendChild(makeTable(
      [
        { label: "Cặp" },
        { label: "Hướng" },
        { label: "Qty", num: true },
        { label: "Entry", num: true },
        { label: "SL (%)", num: true },
        { label: "TP (%)", num: true },
        { label: "R:R", num: true },
        { label: "Notional", num: true },
        { label: "MFE", num: true },
        { label: "Trạng thái" },
        { label: "Algo trên sàn", num: true },
      ],
      posRows,
      "Không có vị thế đang mở trong managed_state.json."
    ));
    container.appendChild(card);

    // Protection Audit + Dust / Banned / Reconcile
    const oa = data.orders_audit || {};
    const auditCard = el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h3", { className: "card-title", text: "Kiểm kê lệnh bảo vệ Algo API (orders_snapshot.json)" }),
          el("div", { className: "card-sub", text: `Snapshot: ${oa.as_of_human || "UNKNOWN"} (0 gọi API sàn trực tiếp)` })
        ),
        badge(oa.known ? ((oa.naked || []).length ? "CÓ VỊ THẾ TRẦN" : "ĐỒNG BỘ") : "UNKNOWN", oa.known ? ((oa.naked || []).length ? "danger" : "ok") : "warn")
      ),
      el("div", { className: "grid-4" },
        kpi("Lệnh bảo vệ", String(oa.protect_orders ?? "N/A"), `Tổng lệnh: ${oa.orders ?? "N/A"}`),
        kpi("Vị thế trên sàn", String(oa.positions ?? "N/A"), `Vị thế bụi: ${(oa.dust || []).length}`),
        kpi("Vị thế trần (naked)", String((oa.naked || []).length), (oa.naked || []).join(", ") || "Không có", (oa.naked || []).length ? "val-neg" : "val-pos"),
        kpi("Lệnh mồ côi / trùng", `${oa.orphans ?? "N/A"} / ${Object.keys(oa.dupes || {}).length}`, (oa.orphan_symbols || []).join(", ") || "Sạch")
      ),
      el("div", { className: "kv-grid" },
        kvRow("Reconcile gần nhất", data.reconcile.last_run_human || "UNKNOWN"),
        kvRow("Reconcile episodes / written", `${data.reconcile.episodes ?? "?"} / ${data.reconcile.written ?? "?"}`)
      )
    );

    const sideGrid = el("div", { className: "grid-2" },
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: `Danh sách Dust Skip (${data.dust_skip.length})` }),
        makeTable(
          [{ label: "Cặp" }, { label: "Lý do bỏ qua (B-024)" }],
          data.dust_skip.map((x) => [el("span", { className: "mono", text: x.symbol }), x.why || "-"]),
          "Không có vị thế bụi trong dust_skip.json."
        )
      ),
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: `Cặp bị cấm vĩnh viễn (${data.banned_pairs.length})` }),
        makeTable(
          [{ label: "Cặp" }, { label: "n", num: true }, { label: "avgR", num: true }, { label: "PF(R)", num: true }, { label: "Lý do" }],
          data.banned_pairs.map((x) => [
            el("span", { className: "mono", text: x.symbol }),
            x.n,
            { text: fmtSigned(x.avg_r, 3), cls: toneBySign(x.avg_r) },
            fmtNum(x.pf_r, 2),
            x.reason || x.banned_at,
          ]),
          "Không có cặp nào trong banned_pairs.json."
        )
      )
    );

    container.appendChild(auditCard);
    container.appendChild(sideGrid);
  }

  // =========================================================================
  // Pure-SVG Interactive Line/Area Chart (Equity / Cumulative R / Drawdown)
  // =========================================================================
  function buildSeriesChart(curve, mode) {
    const wrap = el("div", { className: "chart-wrap" });
    if (!curve || curve.length < 2) {
      wrap.appendChild(el("div", { className: "empty-box", text: "Chưa đủ ngày dữ liệu (>= 2 ngày) để vẽ biểu đồ." }));
      return wrap;
    }

    const W = 980;
    const H = 260;
    const padL = 64;
    const padR = 20;
    const padT = 18;
    const padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;

    const values = curve.map((pt) => {
      if (mode === "cum_r") return pt.cum_r;
      if (mode === "drawdown") return -pt.dd_pct;
      return pt.equity;
    });

    let minV = Math.min(...values);
    let maxV = Math.max(...values);
    if (minV === maxV) {
      minV -= 1;
      maxV += 1;
    }
    const span = maxV - minV;
    minV -= span * 0.06;
    maxV += span * 0.06;

    const xAt = (i) => padL + (i / (curve.length - 1)) * innerW;
    const yAt = (v) => padT + ((maxV - v) / (maxV - minV)) * innerH;

    const strokeColor = mode === "drawdown" ? "#f43f5e" : (mode === "cum_r" ? "#38bdf8" : "#10b981");
    const fillColor = mode === "drawdown" ? "rgba(244,63,94,0.16)" : (mode === "cum_r" ? "rgba(56,189,248,0.15)" : "rgba(16,185,129,0.15)");

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg" });

    // Horizontal grid lines + labels
    const ticks = 4;
    for (let i = 0; i <= ticks; i++) {
      const frac = i / ticks;
      const val = maxV - frac * (maxV - minV);
      const y = padT + frac * innerH;
      svg.appendChild(svgEl("line", { x1: padL, y1: y, x2: W - padR, y2: y, stroke: "#1f2e47", "stroke-width": 1, "stroke-dasharray": "3 3" }));
      const lbl = mode === "drawdown" ? `${val.toFixed(1)}%` : (mode === "cum_r" ? `${val.toFixed(1)}R` : `${val.toFixed(0)}$`);
      svg.appendChild(svgEl("text", { x: padL - 8, y: y + 4, fill: "#64748b", "font-size": 10.5, "text-anchor": "end", "font-family": "monospace", text: lbl }));
    }

    // Zero baseline if visible
    if (minV < 0 && maxV > 0) {
      const y0 = yAt(0);
      svg.appendChild(svgEl("line", { x1: padL, y1: y0, x2: W - padR, y2: y0, stroke: "#475569", "stroke-width": 1 }));
    }

    // Path & area
    const pts = values.map((v, i) => `${xAt(i).toFixed(1)},${yAt(v).toFixed(1)}`);
    const lineD = `M ${pts.join(" L ")}`;
    const baseY = mode === "drawdown" ? yAt(0) : (H - padB);
    const areaD = `${lineD} L ${xAt(curve.length - 1).toFixed(1)},${baseY.toFixed(1)} L ${xAt(0).toFixed(1)},${baseY.toFixed(1)} Z`;

    svg.appendChild(svgEl("path", { d: areaD, fill: fillColor }));
    svg.appendChild(svgEl("path", { d: lineD, fill: "none", stroke: strokeColor, "stroke-width": 2.2 }));

    // X-axis date labels (5 points)
    const xSteps = Math.min(5, curve.length - 1);
    for (let s = 0; s <= xSteps; s++) {
      const idx = Math.round((s / xSteps) * (curve.length - 1));
      svg.appendChild(svgEl("text", {
        x: xAt(idx),
        y: H - 8,
        fill: "#64748b",
        "font-size": 10.5,
        "text-anchor": s === 0 ? "start" : (s === xSteps ? "end" : "middle"),
        "font-family": "monospace",
        text: curve[idx].day,
      }));
    }

    // Crosshair + interactive hit overlay
    const crossLine = svgEl("line", { x1: 0, y1: padT, x2: 0, y2: H - padB, stroke: "#94a3b8", "stroke-width": 1, "stroke-dasharray": "2 2", opacity: 0 });
    const dot = svgEl("circle", { cx: 0, cy: 0, r: 4.5, fill: strokeColor, stroke: "#080c14", "stroke-width": 2, opacity: 0 });
    svg.appendChild(crossLine);
    svg.appendChild(dot);

    const tooltip = el("div", { className: "chart-tooltip hidden" });

    const overlay = svgEl("rect", { x: padL, y: padT, width: innerW, height: innerH, fill: "transparent" });
    overlay.addEventListener("mousemove", (evt) => {
      const rect = svg.getBoundingClientRect();
      const relX = ((evt.clientX - rect.left) / rect.width) * W;
      const clamped = Math.max(padL, Math.min(W - padR, relX));
      const idx = Math.round(((clamped - padL) / innerW) * (curve.length - 1));
      const pt = curve[idx];
      const v = values[idx];
      const cx = xAt(idx);
      const cy = yAt(v);
      crossLine.setAttribute("x1", cx);
      crossLine.setAttribute("x2", cx);
      crossLine.setAttribute("opacity", 1);
      dot.setAttribute("cx", cx);
      dot.setAttribute("cy", cy);
      dot.setAttribute("opacity", 1);

      tooltip.classList.remove("hidden");
      tooltip.textContent =
        `${pt.day} (${pt.n} lệnh)\n` +
        `Equity: ${fmtNum(pt.equity, 2)} $ (${fmtSigned(pt.daily_pnl, 2)} $)\n` +
        `Cum R: ${fmtSigned(pt.cum_r, 3)} R (${fmtSigned(pt.daily_r, 3)} R)\n` +
        `Drawdown: -${fmtNum(pt.dd_pct, 2)}%`;
      const leftPx = Math.min(wrap.clientWidth - 210, Math.max(12, evt.clientX - rect.left + 14));
      tooltip.style.left = `${leftPx}px`;
      tooltip.style.top = "14px";
    });
    overlay.addEventListener("mouseleave", () => {
      crossLine.setAttribute("opacity", 0);
      dot.setAttribute("opacity", 0);
      tooltip.classList.add("hidden");
    });
    svg.appendChild(overlay);

    wrap.appendChild(svg);
    wrap.appendChild(tooltip);
    return wrap;
  }

  // =========================================================================
  // TAB 3: PERFORMANCE & TRADES
  // =========================================================================
  async function renderPerformanceTab(container, force = false) {
    const inst = activeInstance();
    const qsPerf = `/api/performance?t=${inst}&days=${state.perfDays}&bot_only=${state.botOnly ? 1 : 0}`;
    const qsTrades = `/api/trades?t=${inst}&limit=${state.tradeLimit}&offset=${state.tradePage * state.tradeLimit}&bot_only=${state.botOnly ? 1 : 0}&outcome=${encodeURIComponent(state.tradeOutcome)}&symbol=${encodeURIComponent(state.tradeSymbol)}&strategy=${encodeURIComponent(state.tradeStrategy)}`;

    const [perf, trades] = await Promise.all([apiGet(qsPerf, force), apiGet(qsTrades, force)]);

    // Controls bar
    const controls = el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h2", { className: "card-title", text: `Hiệu suất lượng hóa — ${inst.toUpperCase()}` }),
          el("div", { className: "card-sub", text: `Tái dùng monitor_report (lọc R rác B-031 [${(perf.r_band || [-1.6, 5]).join(", ")}]) + perf_report (8 chỉ số chuẩn)` })
        ),
        el("div", { className: "filter-bar" },
          ...[7, 14, 30, 90, 0].map((d) =>
            el("button", {
              type: "button",
              className: `pill-btn${state.perfDays === d ? " active" : ""}`,
              text: d === 0 ? "Tất cả" : `${d} ngày`,
              onClick: () => { state.perfDays = d; renderActiveTab(true); },
            })
          ),
          el("button", {
            type: "button",
            className: `pill-btn${state.botOnly ? " active" : ""}`,
            text: state.botOnly ? "Chỉ lệnh BOT: BẬT" : "Gộp cả lệnh tay",
            onClick: () => { state.botOnly = !state.botOnly; state.tradePage = 0; renderActiveTab(true); },
          })
        )
      )
    );

    if (!perf.known) {
      controls.appendChild(el("div", { className: "empty-box", text: perf.note || "Không có dữ liệu journal." }));
      container.appendChild(controls);
      return;
    }

    const m = perf.metrics;
    const c = perf.counts;

    // Transparency banners (B-031, small sample, mismatch, insolvent)
    const warnings = [];
    if (c.n_dropped_b031 > 0) warnings.push(`B-031: đã loại ${c.n_dropped_b031}/${c.window_raw} bản ghi có R ngoài dải hợp lệ [${perf.r_band.join(", ")}] hoặc r_valid=False.`);
    if (c.small_sample) warnings.push(`Cỡ mẫu nhỏ (n=${c.window_valid} < 30) — số liệu chưa đủ ý nghĩa thống kê.`);
    if (m.r_pnl_mismatch) warnings.push("CẢNH BÁO: Kỳ vọng R và tổng PnL ($) NGƯỢC DẤU (lệch size hoặc lẫn lệnh tay, xem B-050).");
    if (m.insolvent) warnings.push("CẢNH BÁO: Đường equity từng về <= 0 trong cửa sổ này — CAGR/Calmar không có ý nghĩa.");
    for (const note of m.notes || []) warnings.push(note);

    if (warnings.length) {
      controls.appendChild(el("div", { className: "note-box" },
        warnings.map((w, i) => el("div", { text: `${i > 0 ? "• " : ""}${w}` }))
      ));
    }

    // 8 Quant KPI cards + core stats
    controls.appendChild(el("div", { className: "grid-6" },
      kpi("Tổng lệnh hợp lệ (n)", `${c.window_valid}`, `BOT: ${c.bot_closed} · Tay: ${c.manual_closed} · Loại B-031: ${c.n_dropped_b031}`),
      kpi("Winrate", fmtNum(m.winrate, 1, "%"), `${m.wins} thắng / ${c.window_valid} lệnh`),
      kpi("Profit Factor (R)", fmtNum(m.pf_r, 3), `PF($): ${fmtNum(m.pf_pnl, 3)}`, (m.pf_r || 0) >= 1.2 ? "val-pos" : "val-neg"),
      kpi("Kỳ vọng E(R)", fmtSigned(m.exp_r, 4, "R"), `E($): ${fmtSigned(m.exp_pnl, 3, "$")}`, toneBySign(m.exp_r)),
      kpi("PnL cửa sổ", fmtSigned(m.pnl, 2, " $"), `Return: ${fmtSigned(m.return_pct, 2, "%")} (${m.days_active} ngày)`, toneBySign(m.pnl)),
      kpi("Max Drawdown", `${fmtNum(m.max_dd_pct, 2, "%")}`, `Ulcer: ${fmtNum(m.ulcer_pct, 2, "%")}`, m.max_dd_pct > 15 ? "val-neg" : "val-warn"),
      kpi("Sharpe", fmtNum(m.sharpe, 3), `Sortino: ${fmtNum(m.sortino, 3)}`, toneBySign(m.sharpe)),
      kpi("CAGR (quy đổi năm)", fmtSigned(m.cagr_pct, 1, "%"), `Calmar: ${fmtNum(m.calmar, 3)}`, toneBySign(m.cagr_pct)),
      kpi("Thời gian giữ TB", m.avg_hold_min !== null ? `${fmtNum(m.avg_hold_min, 1)} phút` : "N/A", `Mở chưa đóng: ${c.still_open_in_journal}`),
      kpi("Chế độ lọc", state.botOnly ? "CHỈ LỆNH BOT" : "GỘP LỆNH TAY", inst === "testnet" ? "TESTNET (demo)" : "LIVE (tiền thật)", inst === "live" ? "val-warn" : "val-cyan"),
      kpi("Cửa sổ 7 ngày", `PF(R) ${fmtNum(perf.rolling["7"].pf_r, 2)}`, `n=${perf.rolling["7"].n} · PnL ${fmtSigned(perf.rolling["7"].pnl, 2, "$")}`),
      kpi("Cửa sổ 30 ngày", `PF(R) ${fmtNum(perf.rolling["30"].pf_r, 2)}`, `n=${perf.rolling["30"].n} · PnL ${fmtSigned(perf.rolling["30"].pnl, 2, "$")}`)
    ));

    // Chart mode toggle + SVG chart
    controls.appendChild(el("div", { className: "card-head" },
      el("h3", { className: "card-title", text: "Đường hiệu suất theo ngày (UTC)" }),
      el("div", { className: "filter-bar" },
        ...[
          ["equity", "Equity ($)"],
          ["cum_r", "R tích lũy"],
          ["drawdown", "Drawdown (%)"],
        ].map(([k, lbl]) => el("button", {
          type: "button",
          className: `pill-btn${state.chartMode === k ? " active" : ""}`,
          text: lbl,
          onClick: () => { state.chartMode = k; renderActiveTab(false); },
        }))
      )
    ));
    controls.appendChild(buildSeriesChart(perf.curve, state.chartMode));
    container.appendChild(controls);

    // Breakdowns: Strategy + Setup + Regime + Direction
    function breakdownCard(title, rows) {
      return el("section", { className: "card" },
        el("h3", { className: "card-title", text: title }),
        makeTable(
          [
            { label: "Nhóm" },
            { label: "n", num: true },
            { label: "WR%", num: true },
            { label: "PF(R)", num: true },
            { label: "PF($)", num: true },
            { label: "E(R)", num: true },
            { label: "PnL $", num: true },
          ],
          (rows || []).map((r) => [
            el("span", { className: "mono", text: r.name }),
            r.n,
            fmtNum(r.wr, 1, "%"),
            r.pf_r === null ? "∞" : fmtNum(r.pf_r, 2),
            r.pf_pnl === null ? "∞" : fmtNum(r.pf_pnl, 2),
            { text: fmtSigned(r.exp_r, 3, "R"), cls: toneBySign(r.exp_r) },
            { text: fmtSigned(r.pnl, 2, "$"), cls: toneBySign(r.pnl) },
          ])
        )
      );
    }

    container.appendChild(el("div", { className: "grid-2" },
      breakdownCard("Phân rã theo Chiến lược (strategy)", perf.breakdowns.strategy),
      breakdownCard("Phân rã theo Market Regime", perf.breakdowns.market_regime)
    ));
    container.appendChild(el("div", { className: "grid-2" },
      breakdownCard("Phân rã theo Setup Type", perf.breakdowns.setup_type),
      breakdownCard("Phân rã theo Hướng (LONG / SHORT)", perf.breakdowns.direction)
    ));

    // Paginated Trades Journal Table
    const symInput = el("input", { className: "input-box", type: "text", placeholder: "Lọc cặp (vd ADA, SOL)...", value: state.tradeSymbol });
    const stratInput = el("input", { className: "input-box", type: "text", placeholder: "Chiến lược...", value: state.tradeStrategy });
    const outSelect = el("select", { className: "select-box" },
      el("option", { value: "all", text: "Mọi kết quả" }),
      el("option", { value: "win", text: "Chỉ thắng (WIN)" }),
      el("option", { value: "loss", text: "Chỉ thua (LOSS)" })
    );
    outSelect.value = state.tradeOutcome;

    const applyTradeFilters = () => {
      state.tradeSymbol = symInput.value.trim();
      state.tradeStrategy = stratInput.value.trim();
      state.tradeOutcome = outSelect.value;
      state.tradePage = 0;
      renderActiveTab(true);
    };

    const tradesCard = el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h3", { className: "card-title", text: `Nhật ký lệnh đóng (${trades.total} khớp lọc)` }),
          el("div", { className: "card-sub", text: `Trang ${state.tradePage + 1} · Hiển thị ${trades.items.length}/${trades.total} · Mới nhất lên đầu` })
        ),
        el("div", { className: "filter-bar" },
          symInput,
          stratInput,
          outSelect,
          el("button", { type: "button", className: "ctrl-btn ctrl-btn-accent", text: "Lọc", onClick: applyTradeFilters })
        )
      ),
      makeTable(
        [
          { label: "Thời gian" },
          { label: "Cặp" },
          { label: "Hướng" },
          { label: "Nguồn" },
          { label: "Chiến lược / Regime" },
          { label: "Entry → Exit", num: true },
          { label: "R", num: true },
          { label: "PnL $", num: true },
          { label: "Giữ (p)", num: true },
          { label: "Lý do" },
        ],
        trades.items.map((t) => [
          el("span", { className: "mono", text: t.time || "?" }),
          el("span", { className: "mono", text: t.symbol }),
          badge(t.direction || "?", t.direction === "LONG" ? "ok" : "danger"),
          badge(t.source, t.source === "BOT" ? "info" : "purple"),
          `${t.strategy} / ${t.market_regime}`,
          `${fmtPrice(t.entry)} → ${fmtPrice(t.exit)}`,
          { text: `${fmtSigned(t.r, 2, "R")}${t.r_valid ? "" : " [B-031]"}`, cls: t.r_valid ? toneBySign(t.r) : "val-warn" },
          { text: fmtSigned(t.pnl, 3, "$"), cls: toneBySign(t.pnl) },
          t.hold_min !== null ? fmtNum(t.hold_min, 0) : "-",
          t.reason || "-",
        ]),
        "Không có lệnh đóng nào khớp bộ lọc."
      ),
      el("div", { className: "pager" },
        el("button", {
          type: "button",
          className: "ctrl-btn",
          text: "← Trang trước",
          disabled: state.tradePage <= 0,
          onClick: () => { if (state.tradePage > 0) { state.tradePage--; renderActiveTab(true); } },
        }),
        el("span", { className: "card-sub", text: `Trang ${state.tradePage + 1} / ${Math.max(1, Math.ceil(trades.total / state.tradeLimit))}` }),
        el("button", {
          type: "button",
          className: "ctrl-btn",
          text: "Trang sau →",
          disabled: (state.tradePage + 1) * state.tradeLimit >= trades.total,
          onClick: () => { state.tradePage++; renderActiveTab(true); },
        })
      )
    );
    container.appendChild(tradesCard);
  }

  // =========================================================================
  // TAB 4: COUNCIL & LEARNER
  // =========================================================================
  function buildSpendBarChart(series) {
    const wrap = el("div", { className: "chart-wrap" });
    if (!series || !series.length) {
      wrap.appendChild(el("div", { className: "empty-box", text: "Chưa có dữ liệu council_daemon.json." }));
      return wrap;
    }
    const W = 720;
    const H = 180;
    const padL = 48;
    const padR = 14;
    const padT = 16;
    const padB = 28;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const maxSpend = Math.max(0.001, ...series.map((s) => s.spend_usd || 0));

    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg" });
    const barW = Math.max(4, innerW / series.length - 4);
    const step = innerW / series.length;

    svg.appendChild(svgEl("line", { x1: padL, y1: H - padB, x2: W - padR, y2: H - padB, stroke: "#2d4266", "stroke-width": 1 }));
    svg.appendChild(svgEl("text", { x: padL - 6, y: padT + 6, fill: "#64748b", "font-size": 10, "text-anchor": "end", "font-family": "monospace", text: `$${maxSpend.toFixed(3)}` }));
    svg.appendChild(svgEl("text", { x: padL - 6, y: H - padB, fill: "#64748b", "font-size": 10, "text-anchor": "end", "font-family": "monospace", text: "$0" }));

    series.forEach((pt, idx) => {
      const h = ((pt.spend_usd || 0) / maxSpend) * innerH;
      const x = padL + idx * step + (step - barW) / 2;
      const y = H - padB - h;
      const rect = svgEl("rect", {
        x: x.toFixed(1),
        y: y.toFixed(1),
        width: barW.toFixed(1),
        height: Math.max(1, h).toFixed(1),
        rx: 2,
        fill: pt.spend_usd > 0 ? "#a78bfa" : "#1f2e47",
      });
      rect.appendChild(svgEl("title", { text: `${pt.day}: $${pt.spend_usd.toFixed(5)} (${pt.votes} phiếu)` }));
      svg.appendChild(rect);

      if (idx === 0 || idx === series.length - 1 || idx === Math.floor(series.length / 2)) {
        svg.appendChild(svgEl("text", {
          x: (x + barW / 2).toFixed(1),
          y: H - 8,
          fill: "#64748b",
          "font-size": 10,
          "text-anchor": "middle",
          "font-family": "monospace",
          text: pt.day.slice(5),
        }));
      }
    });
    wrap.appendChild(svg);
    return wrap;
  }

  async function renderCouncilTab(container, force = false) {
    const inst = activeInstance();
    const data = await apiGet(`/api/council?t=${inst}`, force);
    const ag = data.agent_state || {};
    const chb = data.council_heartbeat || {};
    const ccfg = data.council_config || {};

    const topCard = el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h2", { className: "card-title", text: `Hội đồng AI (LLM Advisory) — ${inst.toUpperCase()}` }),
          el("div", { className: "card-sub", text: `as_of: ${data.as_of_human || "UNKNOWN"} · Hội đồng chỉ cố vấn (shadow), không tự sửa size/SL/TP` })
        ),
        badge(chb.ok ? `DAEMON ${String(chb.mode || "").toUpperCase()}` : "DAEMON UNKNOWN", chb.ok ? "ok" : "warn")
      ),
      el("div", { className: "grid-4" },
        kpi("Gọi Agent hôm nay", `${ag.calls ?? "N/A"}`, `Chi phí: $${fmtNum(ag.cost_usd, 4)} · Ngày: ${ag.day || "?"}`),
        kpi("Cầu dao provider", ag.disabled ? `TẮT: ${ag.disabled}` : "HOẠT ĐỘNG", `Lỗi: ${JSON.stringify(ag.errors_by || {})}`, ag.disabled ? "val-neg" : "val-pos"),
        kpi("Ngân sách daemon", `$${fmtNum(chb.spend_today, 4)} / $${fmtNum(ccfg.max_usd_day, 2)}`, `Chu kỳ: ${chb.cycles_today ?? "?"}/${ccfg.max_cycles_day ?? "?"}`),
        kpi("Learner Online", `${data.learner.meta.n_updates ?? "N/A"} lần học`, `Bias b = ${fmtNum(data.learner.meta.bias, 4)}`)
      )
    );
    container.appendChild(topCard);

    // Spend chart + Gaps
    const gapsItems = (data.gaps && data.gaps.items) || [];
    const midGrid = el("div", { className: "grid-2" },
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: "Chi phí hội đồng 30 ngày (council_daemon.json)" }),
        buildSpendBarChart(data.daily_series)
      ),
      el("section", { className: "card" },
        el("div", { className: "card-head" },
          el("h3", { className: "card-title", text: `Lỗ hổng hội đồng (${gapsItems.length})` }),
          el("span", { className: "card-sub", text: data.gaps.as_of_human || "" })
        ),
        makeTable(
          [{ label: "ID" }, { label: "Mức" }, { label: "Chỉ số" }, { label: "Hành động" }],
          gapsItems.map((g) => [
            el("span", { className: "mono", text: g.id }),
            badge(g.severity || "info", g.severity === "high" ? "danger" : (g.severity === "medium" ? "warn" : "info")),
            `${g.metric}: ${g.value} (mục tiêu ${g.target})`,
            g.action || "-",
          ]),
          "Không ghi nhận lỗ hổng trong council_gaps.json."
        )
      )
    );
    container.appendChild(midGrid);

    // Learner 20-feature weights + Lessons buckets
    const weights = data.learner.weights || [];
    const maxW = Math.max(0.05, ...weights.map((x) => Math.abs(x.weight || 0)));
    const weightList = el("div", { className: "weight-list" },
      weights.map((w) => {
        const pct = Math.min(50, (Math.abs(w.weight) / maxW) * 50);
        const isPos = w.weight >= 0;
        const barStyle = isPos
          ? { left: "50%", width: `${pct}%` }
          : { left: `${50 - pct}%`, width: `${pct}%` };
        return el("div", { className: "weight-row" },
          el("span", { className: "mono", text: w.feature }),
          el("div", { className: "weight-track" },
            el("div", { className: "weight-mid" }),
            el("div", { className: `weight-bar ${isPos ? "pos" : "neg"}`, style: barStyle })
          ),
          el("span", { className: `num ${isPos ? "val-pos" : "val-neg"}`, text: fmtSigned(w.weight, 4) })
        );
      })
    );

    const lrGrid = el("div", { className: "grid-2" },
      el("section", { className: "card" },
        el("div", { className: "card-head" },
          el("h3", { className: "card-title", text: "Trọng số Online Learner (20 features tuyến tính)" }),
          el("span", { className: "card-sub", text: data.learner.meta.ts_human || "" })
        ),
        weights.length ? weightList : el("div", { className: "empty-box", text: "Không có learner.json." })
      ),
      el("section", { className: "card" },
        el("div", { className: "card-head" },
          el("h3", { className: "card-title", text: `Bài học theo Bucket (${(data.lessons.buckets || []).length} nhóm lớn nhất)` }),
          el("span", { className: "card-sub", text: `ghép: ${data.lessons.meta.trades ?? "?"} · lẻ: ${data.lessons.meta.unpaired ?? "?"}` })
        ),
        makeTable(
          [{ label: "Bucket" }, { label: "n", num: true }, { label: "WR%", num: true }, { label: "avgR", num: true }, { label: "PnL $", num: true }],
          (data.lessons.buckets || []).slice(0, 16).map((b) => [
            el("span", { className: "mono", text: b.bucket }),
            b.n,
            fmtNum(b.wr, 1, "%"),
            { text: fmtSigned(b.avg_r, 3, "R"), cls: toneBySign(b.avg_r) },
            { text: fmtSigned(b.pnl, 2, "$"), cls: toneBySign(b.pnl) },
          ]),
          "Chưa có lessons.json."
        )
      )
    );
    container.appendChild(lrGrid);

    // Recent Journal AGENT votes (100% textContent safe)
    const votesCard = el("section", { className: "card" },
      el("h3", { className: "card-title", text: `Phiếu hội đồng gần nhất trong journal (${data.recent_votes.length})` }),
      makeTable(
        [{ label: "Model / Agent" }, { label: "Cặp" }, { label: "Phiếu" }, { label: "Conf", num: true }, { label: "Lý do / Ghi chú (untrusted text)" }],
        data.recent_votes.slice(0, 30).map((v) => {
          const actTone = v.action === "ALLOW" ? "ok" : (v.action === "VETO" ? "danger" : "neutral");
          const reasonBox = el("div", null,
            v.note ? el("div", { className: "card-sub", text: `Note: ${v.note}` }) : null,
            (v.reasons || []).length ? el("ul", { className: "reason-list" }, v.reasons.map((r) => el("li", { text: r }))) : null
          );
          return [
            el("span", { className: "mono", text: v.model || v.agent || "?" }),
            el("span", { className: "mono", text: `${v.symbol} ${v.direction}`.trim() || "-" }),
            badge(v.action || "?", actTone),
            v.confidence !== null ? fmtNum(v.confidence, 2) : "-",
            reasonBox,
          ];
        }),
        "Chưa có bản ghi AGENT trong journal."
      )
    );
    container.appendChild(votesCard);

    // Council Outbox
    const outboxCard = el("section", { className: "card" },
      el("h3", { className: "card-title", text: `Hộp thư quyết định hội đồng (${data.outbox.length} mục gần nhất)` }),
      makeTable(
        [{ label: "Thời gian" }, { label: "Loại" }, { label: "Phán quyết" }, { label: "Phiếu (A/V/Ab)", num: true }, { label: "Câu hỏi" }],
        data.outbox.slice(0, 20).map((o) => [
          el("span", { className: "mono", text: o.time || "?" }),
          badge(o.kind || o.mode || "-", "purple"),
          badge(o.verdict || "-", o.verdict === "ALLOW" ? "ok" : (o.verdict === "VETO" ? "danger" : "neutral")),
          `${o.n_allow}/${o.n_veto}/${o.n_abstain}`,
          o.question,
        ]),
        "Chưa có bản ghi trong council_outbox.json."
      )
    );
    container.appendChild(outboxCard);
  }

  // =========================================================================
  // TAB 5: HARNESS & SECURITY
  // =========================================================================
  async function renderHarnessTab(container, force = false) {
    const inst = activeInstance();
    const data = await apiGet(`/api/harness?t=${inst}`, force);
    const sec = data.security || {};
    const bug = data.bug_manifest || {};

    // Top summary row
    container.appendChild(el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("h2", { className: "card-title", text: `Vận hành (Harness) & Bảo mật — ${inst.toUpperCase()}` }),
        el("span", { className: "card-sub", text: `as_of: ${data.as_of_human || "UNKNOWN"}` })
      ),
      el("div", { className: "grid-4" },
        kpi("Bug Catalog chốt", bug.known ? `${bug.n_classes} lớp / ${bug.n_tests} test` : "UNKNOWN", bug.known ? `digest ${bug.digest_short}… (${bug.n_files} file)` : ""),
        kpi("Audit bảo mật", sec.known ? `${(sec.findings || []).length} phát hiện` : "UNKNOWN", sec.known ? `Kiểm toán: ${sec.audited_at} · ${(sec.controls || []).length} control` : ""),
        kpi("Câu hỏi vận hành", String(data.ops_questions.length), `Lịch sử ops_queue: ${data.ops_history.length} mục`),
        kpi("Telegram Bridge", data.telegram_bridge.known ? `${data.telegram_bridge.sent_count ?? 0} thông báo` : "UNKNOWN", `as_of: ${data.telegram_bridge.as_of_human || "?"}`)
      )
    ));

    // Ops questions + Drift & Regress
    container.appendChild(el("div", { className: "grid-2" },
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: `Câu hỏi chờ duyệt (ops_questions.json: ${data.ops_questions.length})` }),
        makeTable(
          [{ label: "ID" }, { label: "Mức" }, { label: "Trạng thái" }, { label: "Nội dung & Lý do" }],
          data.ops_questions.map((q) => [
            `#${q.id ?? "?"}`,
            badge(q.priority, q.priority === "high" ? "danger" : "info"),
            badge(q.status, q.status === "ANSWERED" ? "ok" : "warn"),
            el("div", null,
              el("strong", { text: q.question }),
              q.why ? el("div", { className: "card-sub", text: q.why }) : null,
              q.options && q.options.length ? el("div", { className: "card-sub", text: `Lựa chọn: ${q.options.join(" | ")}` }) : null
            ),
          ]),
          "Không có câu hỏi chờ duyệt."
        )
      ),
      el("section", { className: "card" },
        el("div", { className: "card-head" },
          el("h3", { className: "card-title", text: "Cảnh báo tái phát (Regress Watch) & Lệch phân phối (Drift PSI)" }),
          el("span", { className: "card-sub", text: `Drift run: ${data.drift_probe.last_run || "UNKNOWN"}` })
        ),
        makeTable(
          [{ label: "Loại" }, { label: "Thời điểm" }, { label: "Chi tiết" }],
          [
            ...(data.drift_probe.items || []).map((x) => [badge(`DRIFT ${x.key}`, "warn"), x.time || "?", x.why]),
            ...(data.regress_watch.notified || []).slice(0, 12).map((x) => [badge(x.key, "danger"), x.time || "?", x.text || `n=${x.n}`]),
          ],
          "Không có cảnh báo tái phát hoặc drift."
        )
      )
    ));

    // Security Audit 6-phase Findings + Controls
    if (sec.known) {
      container.appendChild(el("section", { className: "card" },
        el("div", { className: "card-head" },
          el("div", null,
            el("h3", { className: "card-title", text: `Audit Bảo Mật (6 pha · ${sec.audited_at})` }),
            el("div", { className: "card-sub", text: sec.scope })
          ),
          badge(`${(sec.findings || []).filter((f) => f.status === "fixed").length}/${(sec.findings || []).length} FIXED`, "ok")
        ),
        makeTable(
          [{ label: "ID" }, { label: "Mức" }, { label: "Trạng thái" }, { label: "Bug" }, { label: "Mô tả & Chốt bảo vệ" }],
          (sec.findings || []).map((f) => [
            el("span", { className: "mono", text: f.id }),
            badge(f.severity, f.severity === "high" || f.severity === "critical" ? "danger" : (f.severity === "medium" ? "warn" : "info")),
            badge(f.status, f.status === "fixed" ? "ok" : "neutral"),
            f.bug || "-",
            el("div", null,
              el("strong", { text: f.title }),
              el("div", { className: "card-sub", text: f.guard })
            ),
          ])
        ),
        el("div", { className: "filter-bar" },
          ...(sec.controls || []).map((c) => badge(`${c.id}: ${c.what.slice(0, 65)}`, "ok"))
        )
      ));
    }

    // Harness Ledger + Autonomy
    container.appendChild(el("div", { className: "grid-2" },
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: `Sổ thay đổi Harness Ledger (${data.ledger.length} gần nhất)` }),
        makeTable(
          [{ label: "ID" }, { label: "Loại" }, { label: "Quyết định" }, { label: "Thay đổi & Bằng chứng" }],
          data.ledger.slice(0, 18).map((r) => [
            el("span", { className: "mono", text: r.id || "?" }),
            badge(r.kind || "-", "purple"),
            badge(r.decision || "-", r.decision === "adopted" ? "ok" : (r.decision === "rejected" ? "danger" : "warn")),
            el("div", null,
              el("strong", { text: r.change || "" }),
              r.evidence ? el("div", { className: "card-sub", text: r.evidence }) : null
            ),
          ]),
          "Chưa có bản ghi harness_ledger.jsonl."
        )
      ),
      el("section", { className: "card" },
        el("h3", { className: "card-title", text: `Nhật ký Tự vận hành (autonomy.jsonl: ${data.autonomy.length})` }),
        makeTable(
          [{ label: "Instance" }, { label: "Action / Mã" }, { label: "Chi tiết" }],
          data.autonomy.slice(0, 18).map((a) => [
            badge(String(a.instance || "?").toUpperCase(), a.instance === "live" ? "danger" : "info"),
            el("span", { className: "mono", text: `${a.action || "?"} (${a.reason_code || "-"})` }),
            a.why || "-",
          ]),
          "Chưa có bản ghi autonomy.jsonl."
        )
      )
    ));
  }

  // =========================================================================
  // TAB 6: ARCHITECTURE & WHITELISTED DOCS
  // =========================================================================
  function buildArchitectureDiagram() {
    const W = 1040;
    const H = 310;
    const svg = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart-svg" });

    const defs = svgEl("defs", null,
      svgEl("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" },
        svgEl("path", { d: "M 0 1 L 10 5 L 0 9 z", fill: "#38bdf8" })
      ),
      svgEl("marker", { id: "arrow-warn", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" },
        svgEl("path", { d: "M 0 1 L 10 5 L 0 9 z", fill: "#f59e0b" })
      )
    );
    svg.appendChild(defs);

    function box(x, y, w, h, title, sub, stroke = "#38bdf8", fill = "#131c2e") {
      const g = svgEl("g");
      g.appendChild(svgEl("rect", { x, y, width: w, height: h, rx: 10, fill, stroke, "stroke-width": 1.6 }));
      g.appendChild(svgEl("text", { x: x + 12, y: y + 23, fill: "#e6edf7", "font-size": 12.5, "font-weight": 700, text: title }));
      sub.forEach((line, idx) => {
        g.appendChild(svgEl("text", { x: x + 12, y: y + 41 + idx * 15, fill: "#94a3b8", "font-size": 10.5, "font-family": "monospace", text: line }));
      });
      svg.appendChild(g);
    }

    function link(x1, y1, x2, y2, dashed = false, warn = false) {
      svg.appendChild(svgEl("line", {
        x1, y1, x2, y2,
        stroke: warn ? "#f59e0b" : "#38bdf8",
        "stroke-width": 1.7,
        "stroke-dasharray": dashed ? "5 4" : null,
        "marker-end": warn ? "url(#arrow-warn)" : "url(#arrow)",
      }));
    }

    // Main trading pipeline (top row)
    box(16, 22, 185, 86, "1. Scanner & Cache", ["scan_plan (B-068)", "Batch 12/20 + Warmup", "Weight & IP Ban Guard"], "#38bdf8");
    box(224, 22, 195, 86, "2. Tín hiệu & Cổng", ["Strategy + Freshness TTL", "Online Learner (20 feat)", "Lessons + Chase + Fee"], "#38bdf8");
    box(442, 22, 190, 86, "3. Chốt An Toàn Cứng", ["risk.py + Kill-Switch", "live_guard + live_ready", "Tất định 100% (No LLM)"], "#10b981");
    box(655, 22, 180, 86, "4. Khớp Lệnh & Algo", ["Binance Futures API", "HEDGE / ISOLATED", "SL/TP Algo (B-065/069)"], "#f43f5e");
    box(856, 22, 168, 86, "5. Monitor & Journal", ["Partial / BE / Dust", "reconcile + orders_audit", "logs/journal.jsonl"], "#10b981");

    link(201, 65, 224, 65);
    link(419, 65, 442, 65);
    link(632, 65, 655, 65);
    link(835, 65, 856, 65);

    // Advisory & Observability row (bottom row)
    box(16, 175, 235, 102, "Hội Đồng AI (Shadow)", ["agents.py · 5 models", "ALLOW / VETO / NO_OPINION", "KHÔNG import risk/bot", "prompt_guard + calib cap"], "#a78bfa");
    box(276, 175, 245, 102, "Harness & Tự kiểm chứng", ["bug_catalog (68 lớp / 267 test)", "golden_set (45 ca) · drift_docs", "security_audit (6 pha)", "watch_regress · review_due"], "#f59e0b");
    box(546, 175, 230, 102, "2 Instance Độc Lập", ["TESTNET: autonomous-trading-bot/", "LIVE: ../atb-live/ (chỉ đọc)", "logs/, .env, kill-switch riêng", "state_sync → STATE.md"], "#38bdf8");
    box(800, 175, 224, 102, "ATB Console (Trang này)", ["dashboard_server.py :8780", "127.0.0.1 · Read-Only · 0 API", "Server Redaction + CSP", "Glow Map: serve_glow :8770"], "#10b981");

    link(320, 108, 170, 175, true, true);
    link(170, 175, 340, 108, true, true);
    link(940, 108, 912, 175, true, false);
    link(660, 175, 800, 226, true, false);
    link(521, 226, 546, 226, true, true);

    return el("div", { className: "chart-wrap" }, svg);
  }

  async function renderArchitectureTab(container, force = false) {
    container.appendChild(el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h2", { className: "card-title", text: "Kiến trúc & Đường đi dữ liệu Autonomous Trading Bot" }),
          el("div", { className: "card-sub", text: "Phân tách ranh giới an toàn: Hội đồng AI chỉ cố vấn; mọi quyền đặt lệnh & dừng lỗ nằm ở code tất định." })
        ),
        badge("Glow Map riêng: python serve_glow.py (:8770)", "purple")
      ),
      buildArchitectureDiagram()
    ));

    // Whitelisted Docs Reader
    if (!state.docsList || force) {
      state.docsList = await apiGet("/api/docs", force);
    }
    const docData = await apiGet(`/api/docs/${encodeURIComponent(state.docId)}`, force);
    state.activeDoc = docData;

    const searchInput = el("input", {
      className: "input-box",
      type: "text",
      placeholder: "Tìm dòng trong tài liệu hiện tại...",
      value: state.docFilter,
    });

    const viewer = el("pre", { className: "doc-viewer" });
    const updateDocText = () => {
      const raw = docData.content || "";
      const q = state.docFilter.trim().toLowerCase();
      if (!q) {
        viewer.textContent = raw || "(Tài liệu trống hoặc không tồn tại)";
        return;
      }
      const matched = raw.split("\n").filter((ln) => ln.toLowerCase().includes(q));
      viewer.textContent = matched.length
        ? `[Tìm thấy ${matched.length} dòng khớp "${state.docFilter}"]\n\n${matched.join("\n")}`
        : `Không có dòng nào khớp "${state.docFilter}".`;
    };
    searchInput.addEventListener("input", () => {
      state.docFilter = searchInput.value;
      updateDocText();
    });
    updateDocText();

    const nav = el("div", { className: "doc-nav" },
      (state.docsList.docs || []).map((d) =>
        el("button", {
          type: "button",
          className: `doc-nav-btn${state.docId === d.id ? " active" : ""}`,
          onClick: () => { state.docId = d.id; renderActiveTab(false); },
        },
          el("strong", { text: d.label }),
          el("span", { className: "card-sub", text: d.exists ? `${Math.round(d.size_bytes / 1024)} KB · ${d.as_of_human || ""}` : "Không tồn tại" })
        )
      )
    );

    const docPanel = el("section", { className: "card" },
      el("div", { className: "card-head" },
        el("div", null,
          el("h3", { className: "card-title", text: `Tài liệu dự án (Whitelist chỉ đọc): ${docData.label || state.docId}` }),
          el("div", { className: "card-sub", text: `${docData.as_of_human || "UNKNOWN"}${docData.truncated ? " · Đã cắt giới hạn hiển thị 120KB" : ""}` })
        ),
        searchInput
      ),
      el("div", { className: "docs-layout" }, nav, viewer)
    );
    container.appendChild(docPanel);
  }

  // =========================================================================
  // Master render & polling lifecycle
  // =========================================================================
  let inFlight = false;

  async function renderActiveTab(force = false) {
    if (inFlight) return;
    inFlight = true;
    const footer = document.getElementById("footer-status");
    const main = document.getElementById("main-content");
    footer.textContent = "Đang đồng bộ...";

    try {
      const overviewResp = await apiGet(`/api/overview?t=${state.env}`, force);
      updateVitalStrip(overviewResp);

      const frag = document.createDocumentFragment();
      const wrap = el("div", { className: "tab-container" });
      wrap.style.display = "flex";
      wrap.style.flexDirection = "column";
      wrap.style.gap = "16px";

      if (state.tab === "overview") {
        await renderOverviewTab(wrap, overviewResp);
      } else {
        if (state.env === "both" && state.tab !== "architecture") {
          wrap.appendChild(el("div", {
            className: "note-box info",
            text: "Chế độ SO SÁNH hiển thị song song 2 instance ở Tab 1 (Tổng quan) và không gộp số. Tab chi tiết này đang hiển thị TESTNET — bấm nút LIVE ở thanh trên để xem chi tiết tiền thật.",
          }));
        }
        if (state.tab === "positions") {
          await renderPositionsTab(wrap, force);
        } else if (state.tab === "performance") {
          await renderPerformanceTab(wrap, force);
        } else if (state.tab === "council") {
          await renderCouncilTab(wrap, force);
        } else if (state.tab === "harness") {
          await renderHarnessTab(wrap, force);
        } else if (state.tab === "architecture") {
          await renderArchitectureTab(wrap, force);
        }
      }

      frag.appendChild(wrap);
      clear(main);
      main.appendChild(frag);
      footer.textContent = `Đồng bộ thành công lúc ${new Date().toLocaleTimeString("vi-VN")}`;
    } catch (err) {
      clear(main);
      main.appendChild(el("div", { className: "note-box", text: `Lỗi tải dữ liệu cục bộ: ${err.message || err}` }));
      footer.textContent = "Lỗi kết nối server cục bộ";
    } finally {
      inFlight = false;
    }
  }

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(() => {
      if (state.pollEnabled && !document.hidden) {
        renderActiveTab(false);
      }
    }, POLL_MS);
  }

  function wireEvents() {
    document.querySelectorAll(".env-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.env = btn.getAttribute("data-env") || "testnet";
        state.tradePage = 0;
        document.querySelectorAll(".env-btn").forEach((b) => b.classList.toggle("active", b === btn));
        renderActiveTab(true);
      });
    });

    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.tab = btn.getAttribute("data-tab") || "overview";
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
        renderActiveTab(false);
      });
    });

    const btnPoll = document.getElementById("btn-toggle-poll");
    btnPoll.addEventListener("click", () => {
      state.pollEnabled = !state.pollEnabled;
      btnPoll.textContent = state.pollEnabled ? "Auto 10s: BẬT" : "Auto 10s: TẠM DỪNG";
    });

    document.getElementById("btn-refresh").addEventListener("click", () => {
      renderActiveTab(true);
    });

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && state.pollEnabled) renderActiveTab(false);
    });
  }

  wireEvents();
  startPolling();
  renderActiveTab(true);
})();
