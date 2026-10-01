"""Che do TURBO DEMO: bot tu dong mo them vi the tren cac cap con lai
(BTC/ETH/SOL) de test song song tat ca 4 cap — chi dung tren demo!

Chay: python turbo_demo.py [--rounds N]  (mac dinh chay lien tuc 20s/vong)
Logic: giong bot.step() nhung bo qua gioi han MAX_POSITIONS=1,
van giu: sentiment veto (KHONG noi), ATR SL/TP R:R=1:2, quantize qty, check margin.
Log day: song song hoa fetch 4 cap + cache BTC regime + het-vong bao Telegram.
"""
from __future__ import annotations

import concurrent.futures as _fut
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path

from bot import TradingBot
from agents import AgentLayer, review_payload, setup_payload
from config import Settings
from derivatives import derivatives_guard, fetch_liquidations, fetch_oi_funding
from exchange import BinanceFutures
from indicators import (liquidity_sweep, market_regime, mtf_trend, retest_ok,
                        technical_score, vwap)
from journal import log_trade
from live_guard import enforce as live_guard_enforce
from learner import (OnlineLearner, extract_features, news_features,
                     signal_score_100, structure_score)
from strategy import bump as strat_bump, classify_strategy, report as strat_report, gate_check as strat_gate
from notify import fmt_close, fmt_kill, fmt_open, send as tg_send
from managed_state import load as ms_load, load_into as ms_load_into
from managed_state import save as ms_save
from portfolio import Position, can_add_risk, planned_risk_usd
from position_sync import adopt as adopt_positions
from ranking import Candidate, composite_alpha, sentiment_veto
from reconcile import reconcile as reconcile_journal
from risk import atr_levels, load_state as load_risk_state, position_size
from risk import save_state as save_risk_state

SYMBOLS = ("BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT")
FEE_ROUNDTRIP_PCT = 0.001  # 0.05% x 2 chieu x leverage buffer
LEARN_MIN_EDGE = -0.30  # nguong hoc: duoi muc nay thi giam size/khong vao


def active_symbols(cfg) -> tuple:
    """Danh sach cap turbo quet: SYMBOLS mac dinh + EXTRA_SYMBOLS (neu co).

    Gioi han o day KHONG tang risk: moi lenh van 1% risk, tran danh muc
    MAX_TOTAL_RISK_PCT van chan o 3%. Them cap chi tang CO HOI tim setup dat
    alpha (valid) khi slot trong, khong ha nguong mo lenh.
    """
    base = tuple(getattr(cfg, "symbols", None) or SYMBOLS)
    extra = tuple(getattr(cfg, "extra_symbols", None) or ())
    seen: list[str] = []
    for s in list(base) + list(extra):
        if s and s not in seen:
            seen.append(s)
    return tuple(seen) or SYMBOLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("turbo")

_learner = OnlineLearner()
_last_close: dict[str, float] = {}
_pending_feats: dict[str, dict] = {}  # symbol -> {feats, direction} cho lan close hoc
_btc_cache: dict = {"ts": 0.0, "df": None}  # cache BTC 1h 60s de 4 cap dung chung

# P0-watchdog: bot co the TREO (HTTP khong tra ve) ma TIEN TRINH VAN SONG, khi do
# supervisor chi restart theo exit-code se khong bao gio phat hien. Nhip tim ra file
# la kenh duy nhat de run_forever.py biet bot con thuc su chay.
_HEARTBEAT = Path(__file__).resolve().parent / "logs" / "heartbeat.json"


def heartbeat(extra: dict | None = None) -> None:
    """Ghi nhip tim nguyen tu (tmp + os.replace). Loi -> im lang (khong lam chet bot)."""
    try:
        _HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(_HEARTBEAT) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "pid": os.getpid(), **(extra or {})}, f)
        os.replace(tmp, _HEARTBEAT)
    except Exception:
        pass


def atr_of(ex, cfg, sym: str) -> dict:
    """Gia + ATR hien tai — dung de tinh lai SL/TP khi adopt vi the cu (P0-1)."""
    try:
        df = ex.fetch_ohlcv(sym, cfg.timeframe, cfg.ohlcv_limit)
        t = technical_score(df, cfg.atr_period)
        return {"price": float(t["close"]), "atr": float(t["atr"])}
    except Exception as e:  # noqa: BLE001
        log.warning("adopt: khong lay duoc ATR cho %s: %s", sym, e)
        return {}



def _fetch_one(args):
    """Fetch 1 cap: ohlcv + tech + mtf + deriv + liq. Chay song song 4 cap."""
    bot, sym = args
    cfg = bot.cfg
    out: dict = {"sym": sym}
    try:
        out["df"] = bot.exchange.fetch_ohlcv(sym, cfg.timeframe, cfg.ohlcv_limit)
        out["t"] = technical_score(out["df"], cfg.atr_period)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"DATA_FAIL {str(e)[:120]}"
        return out
    try:
        out["mtf_b"] = mtf_trend(bot.exchange, sym, "1h", 60)["bias"]
    except Exception:
        out["mtf_b"] = 0
    try:
        out["deriv"] = fetch_oi_funding(sym)
    except Exception:
        out["deriv"] = {"oi": 0.0, "oi_chg_24h": 0.0, "funding": 0.0, "ls_ratio": 0.0}
    try:
        out["liq"] = fetch_liquidations(sym)
    except Exception:
        out["liq"] = {"long_liq": 0.0, "short_liq": 0.0, "total": 0.0, "dominance": 0.0}
    return out


def tg(bot_cfg, text: str) -> None:
    """Chi gui khi LIVE (DRY_RUN=false) co du token+chat; demo thi im lang."""
    try:
        if str(getattr(bot_cfg, "dry_run", True)).lower() in ("1", "true", "yes"):
            return
        tg_send(getattr(bot_cfg, "tg_token", ""), getattr(bot_cfg, "tg_chat", ""), text)
    except Exception:
        pass


def tg_round(bot_cfg, text: str) -> None:
    """Gui tom tat het vong — chi khi TELEGRAM_EVERY_ROUND=true (tranh spam)."""
    try:
        import os
        if os.getenv("TELEGRAM_EVERY_ROUND", "false").lower() not in ("1", "true", "yes"):
            return
        tg(bot_cfg, text)
    except Exception:
        pass


# ---- Phase 2: tang multi-AI agent (CHI CO VAN) -------------------------------
# Agent KHONG duoc doi qty/SL/TP/kill-switch: vote() chi tra ve y kien va duoc ghi
# vao journal (event=AGENT) de do luong ("shadow"). Muon cap quyen hanh dong thi
# phai la thay doi co chu dich + co so lieu shadow chung minh (xem README).
# CLI that (copilot) mat ~13s/luot => vote chay o LUONG RIENG, khong lam cham vong
# lap trading (xem _agent_submit).
_AGENTS: dict = {"layer": None, "failed": False, "pool": None, "pending": 0,
                 "dropped": 0}
_AGENT_AUTH: dict = {"ts": 0.0, "res": None}   # Phase 4: cache quyen veto
_AGENT_MAX_PENDING = 4   # hang doi toi da: vuot thi bo (khong de nghen bot)
_AGENT_TIMEOUT_HINT = 90.0


def _agent_submit(job) -> bool:
    """Chay 1 job agent o luong rieng. Tra False neu hang doi day (bo qua job).

    Ly do: provider that (Copilot CLI) mat ~10-20s/luot; neu chay dong bo trong
    turbo_round thi vong quet bi cham => bo lo co hoi vao lenh o cac cap khac.
    """
    layer = _AGENTS.get("layer")
    if layer is None:
        return False
    if _AGENTS["pending"] >= _AGENT_MAX_PENDING:
        _AGENTS["dropped"] += 1
        log.warning("AGENTS: hang doi day (%d) -> bo 1 luot vote (dropped=%d)",
                    _AGENT_MAX_PENDING, _AGENTS["dropped"])
        return False
    pool = _AGENTS.get("pool")
    if pool is None:
        pool = _fut.ThreadPoolExecutor(max_workers=1)
        _AGENTS["pool"] = pool
    _AGENTS["pending"] += 1

    def _run():
        try:
            job()
        except Exception as e:  # noqa: BLE001
            log.warning("AGENTS: job loi (bo qua): %s", e)
        finally:
            _AGENTS["pending"] -= 1

    try:
        pool.submit(_run)
        return True
    except Exception:  # noqa: BLE001
        _AGENTS["pending"] -= 1
        return False


def agent_layer(cfg):
    """Lazy-init AgentLayer. Loi bat ky -> tat agent (khong anh huong trading)."""
    if not getattr(cfg, "agents_enabled", False):
        return None
    if _AGENTS["failed"]:
        return None
    if _AGENTS["layer"] is None:
        try:
            _AGENTS["layer"] = AgentLayer(cfg, log=log)
            _s = _AGENTS["layer"].stats()
            log.info("AGENTS: provider=%s model=%s shadow=%s (Phase 1: chi ghi nhan)",
                     _s["provider"], _s["model"], _s["shadow"])
        except Exception as e:  # noqa: BLE001
            _AGENTS["failed"] = True
            log.warning("AGENTS: khong khoi tao duoc (%s) -> tat", e)
            return None
    return _AGENTS["layer"]


def agent_vote_setup(cfg, sym: str, direction: str, alpha: float, strat: str,
                     tech: dict, senti, regime: str) -> None:
    """Ghi y kien macro+critic cho 1 setup — CHAY NEN, khong doi hanh vi/khong chan."""
    layer = agent_layer(cfg)
    if layer is None:
        return
    try:
        pay = setup_payload(sym, direction, alpha, strat, tech,
                            {"score": getattr(senti, "score", 0.0),
                             "urgent_bearish": getattr(senti, "urgent_bearish", 0)},
                            regime)
    except Exception as e:  # noqa: BLE001
        log.warning("AGENTS: payload loi (bo qua): %s", e)
        return

    def _job():
        for role in ("macro", "critic"):
            d = layer.vote(role, pay)
            layer.log_decision(d, extra={"symbol": sym, "direction": direction,
                                         "status": "SETUP"})
            if d.action == "VETO":
                log.warning("AGENT %s VETO %s %s (conf=%.2f): %s [shadow=%s]",
                            role, direction, sym, d.confidence,
                            "; ".join(d.reasons)[:120], d.shadow)

    _agent_submit(_job)


def agent_authority_cached(cfg, ttl_sec: float = 3600.0) -> dict:
    """Phase 4: cache ket qua cap quyen veto (tinh tu journal, khong ton LLM)."""
    import time as _t
    now = _t.time()
    if _AGENT_AUTH["res"] is not None and (now - _AGENT_AUTH["ts"]) < ttl_sec:
        return _AGENT_AUTH["res"]
    try:
        from agents import agent_authority as _auth
        res = _auth(str(getattr(cfg, "agent_journal_path", "logs/journal.jsonl")),
                    min_n=int(getattr(cfg, "agent_veto_min_n", 10) or 10),
                    min_gap=float(getattr(cfg, "agent_veto_min_gap", 0.15) or 0.15))
    except Exception as e:  # noqa: BLE001
        res = {"granted": False, "reason": f"loi tinh authority: {str(e)[:80]}"}
    _AGENT_AUTH["ts"] = now
    _AGENT_AUTH["res"] = res
    if res.get("granted"):
        log.warning("AGENTS: DA CAP QUYEN VETO (%s)", res.get("reason"))
    return res


def agent_veto(cfg, sym: str, direction: str, alpha: float, strat: str, tech: dict,
               senti, regime: str) -> dict:
    """Phase 4 (opt-in): hoi agent DONG BO truoc khi mo lenh -> co the BO QUA lenh.

    An toan:
      * CHI chay khi `AGENTS_VETO_ENABLED=true` VA authority da duoc cap (bang chung
        shadow: nhom VETO te hon ALLOW >= min_gap, n >= min_n);
      * Veto chi duoc PHEP bo qua lenh (giam rui ro) — khong tang size, khong doi
        SL/TP, khong dong lenh;
      * loi/timeout/het ngan sach -> KHONG chan (fail-open).
    Tra {"block": bool, "reason": str, "decision": dict|None}.
    """
    if not getattr(cfg, "agents_veto_enabled", False):
        return {"block": False, "reason": "veto dang TAT (AGENTS_VETO_ENABLED=false)",
                "decision": None}
    layer = agent_layer(cfg)
    if layer is None:
        return {"block": False, "reason": "agent khong khoi tao duoc", "decision": None}
    auth = agent_authority_cached(cfg)
    if not auth.get("granted"):
        return {"block": False, "reason": "chua duoc cap quyen: " + str(auth.get("reason")),
                "decision": None}
    try:
        from agents import Decision, setup_payload, veto_decision
        pay = setup_payload(sym, direction, alpha, strat, tech,
                            {"score": getattr(senti, "score", 0.0),
                             "urgent_bearish": getattr(senti, "urgent_bearish", 0)},
                            regime)
        v = veto_decision(cfg, layer, pay)
        dec = v.get("decision") or {}
        if v.get("block"):
            d = Decision(**{k: dec.get(k) for k in
                            ("role", "agent", "action", "confidence", "reasons",
                             "risk_flags", "provider", "model", "shadow", "cache_hit",
                             "latency_ms", "tokens_in", "tokens_out", "cost_usd",
                             "ts", "note", "raw_text") if k in dec})
            layer.log_decision(d, extra={"symbol": sym, "direction": direction,
                                         "status": "VETO_ENFORCED"})
            reason = "; ".join(d.reasons)[:140]
            log.warning("AGENT VETO CHAN LENH %s %s (conf=%.2f): %s",
                        direction, sym, d.confidence, reason)
            return {"block": True, "reason": reason, "decision": dec}
        return {"block": False, "reason": "agent khong phan doi", "decision": dec}
    except Exception as e:  # noqa: BLE001
        log.warning("AGENTS veto loi (bo qua, khong chan): %s", e)
        return {"block": False, "reason": f"loi: {str(e)[:100]}", "decision": None}


def agent_vote_review(cfg, sym: str, direction: str, r_multiple: float, won: bool,
                      reason: str, strat: str) -> None:
    """Ghi y kien review sau khi dong lenh — CHAY NEN, chi ghi nhan."""
    layer = agent_layer(cfg)
    if layer is None:
        return
    try:
        pay = review_payload(sym, direction, r_multiple, won, reason, strat)
    except Exception as e:  # noqa: BLE001
        log.warning("AGENTS: payload review loi (bo qua): %s", e)
        return

    def _job():
        d = layer.vote("review", pay)
        layer.log_decision(d, extra={"symbol": sym, "direction": direction,
                                     "status": "CLOSED"})

    _agent_submit(_job)


def turbo_round(bot: TradingBot) -> list[dict]:
    """Moi cap chua co vi the -> tu danh gia doc lap -> mo lenh neu dat alpha."""
    cfg = bot.cfg
    syms = active_symbols(cfg)  # SYMBOLS + EXTRA_SYMBOLS (env) — giu nguong mo lenh nguyen
    bot._max_atr_pct = 0.0  # P0-2: ATR% lon nhat trong vong -> cho kill-switch bien dong
    senti = bot.sentiment.get(cfg.cryptopanic_token)
    results: list[dict] = []
    bal_now = bot.exchange.fetch_balance_usdt() if not cfg.dry_run else cfg.balance_usdt
    live_bal = bal_now
    if live_bal is not None and live_bal > 0:
        bot.balance = min(cfg.balance_usdt, live_bal) / 1.0
    # BTC regime 1 lan/vong (cache 60s) — 4 cap dung chung, KHONG fetch lai 4 lan
    regime_b = 0.0
    try:
        if time.time() - _btc_cache.get("ts", 0) > 60 or _btc_cache.get("df") is None:
            _btc_cache["df"] = bot.exchange.fetch_ohlcv("BTC/USDT:USDT", "1h", 60)
            _btc_cache["ts"] = time.time()
        btc_df = _btc_cache["df"]
        regime_b = 1.0 if float(btc_df["close"].iloc[-1]) > float(
            btc_df["close"].rolling(50).mean().iloc[-1]) else -1.0
    except Exception:
        regime_b = 0.0
    # Song song hoa: fetch toan bo cap chua co vi the cung luc
    todo = [s for s in syms if s not in bot.portfolio.positions]
    fetched: dict[str, dict] = {}
    if todo:
        # P0-watchdog: 1 HTTP call treo se chan CA vong lap (pool.map khong timeout).
        # -> gioi han thoi gian cho ca cum fetch; cap nao qua han thi bo qua vong nay.
        pool = _fut.ThreadPoolExecutor(max_workers=len(todo))
        try:
            futs = {pool.submit(_fetch_one, (bot, s)): s for s in todo}
            done, pending = _fut.wait(futs, timeout=float(cfg.round_timeout_sec),
                                      return_when=_fut.ALL_COMPLETED)
            for fut in done:
                try:
                    r = fut.result()
                    fetched[r["sym"]] = r
                except Exception as e:  # noqa: BLE001
                    fetched[futs[fut]] = {"sym": futs[fut],
                                          "error": f"FETCH_FAIL {str(e)[:100]}"}
            for fut in pending:
                fetched[futs[fut]] = {"sym": futs[fut],
                                      "error": "FETCH_TIMEOUT round_timeout_sec"}
                log.warning("fetch %s qua han %ss -> bo qua vong nay",
                            futs[fut], cfg.round_timeout_sec)
        finally:
            pool.shutdown(wait=False)
    for sym in syms:
        if sym in bot.portfolio.positions:
            results.append({"symbol": sym, "status": "SKIP_OPEN"})
            continue
        # Cooldown: tranh vao lai ngay sau khi SL/TP tren cung cap (chong overtrade).
        if sym in _last_close and (time.time() - _last_close[sym]) < cfg.cooldown_sec:
            results.append({"symbol": sym, "status": "COOLDOWN"})
            continue
        fr = fetched.get(sym, {})
        if fr.get("error"):
            results.append({"symbol": sym, "status": "DATA_FAIL", "reason": fr["error"]})
            continue
        try:
            df = fr["df"]
            t = fr["t"]
        except Exception as e:  # noqa: BLE001
            results.append({"symbol": sym, "status": "DATA_FAIL", "reason": str(e)[:120]})
            continue
        bot._max_atr_pct = max(float(getattr(bot, "_max_atr_pct", 0.0)),
                               float(t.get("atr_pct") or 0.0))
        mtf_b = fr.get("mtf_b", 0)
        deriv = fr.get("deriv", {})
        liq = fr.get("liq", {})
        alpha = composite_alpha(t["score"], senti.score, cfg.w_tech, cfg.w_sent)
        direction = "LONG" if alpha > 0 else ("SHORT" if alpha < 0 else "FLAT")
        if abs(alpha) < cfg.min_alpha_score or direction == "FLAT":
            results.append({"symbol": sym, "status": "WAIT",
                            "reason": f"alpha {alpha} < min {cfg.min_alpha_score}"})
            continue
        # Urgent macro veto: chi chan LONG khi QUA NHIEU tin khan cap (>=20)
        # nguong cu 3 lam bot bi block vi 11 tin urgent_bearish -> khong bao gio trade
        urg = getattr(senti, "urgent_bearish", 0)
        if direction == "LONG" and urg >= 20:
            results.append({"symbol": sym, "status": "BLOCKED_URGENT",
                            "reason": f"{urg} tin khan cap vi mo"})
            continue
        if sentiment_veto(direction, senti.score, cfg.block_long_below, cfg.block_short_above):
            results.append({"symbol": sym, "status": "BLOCKED_SENT"})
            continue
        # Deep-learning nhe: trich features + hoi learner (da hoc tu lich su thang/thua)
        # Kien truc tu duy bot (muc 20): NEWS->MACRO->BTC REGIME->ALT->STRUCT->CANDLE
        # ->VOLUME->OI->FUNDING->RISK->ENTRY->SL/TP. BTC la leader regime (muc 21).
        # (regime_b da fetch 1 lan dau vong + cache; mtf/deriv/liq lay tu fetch song song)
        st = structure_score(df)
        reg = market_regime(df)  # regime rieng cua pair (muc 4) + BTC leader ben duoi
        # score100 khung moi (muc 14): them liquidity zone + BTC align
        liq_zone = bool(t.get("eq_high") is not None or t.get("eq_low") is not None
                        or t.get("near_sr") is not None)
        btc_align_now = (regime_b == 0.0) or ((regime_b > 0) == (direction == "LONG"))
        liq_bias = 0.0  # Long bi thanh ly ap dao -> hoi phuc ky thuat; nguoc lai cho Short
        try:
            liq_bias = -float(liq.get("dominance") or 0.0)
        except Exception:
            liq_bias = 0.0
        nf = news_features(getattr(senti, "headlines", []))
        news_risk = min(nf["macro_risk"] + nf["crypto_risk"], 0.0)
        sig100 = signal_score_100(regime_b, mtf_b, st["struct"], t.get("near_sr"),
                                  t.get("pattern_bias", 0.0), t.get("vol_confirm", False),
                                  float(deriv.get("oi_chg_24h") or 0.0),
                                  float(deriv.get("funding") or 0.0),
                                  news_risk, t.get("atr_pct", 0.005),
                                  liq_zone, btc_align_now)
        # NO-TRADE khung moi (muc 14/17): grade NO (<60) + alpha yeu; deriv cuc doan
        guard = derivatives_guard(float(deriv.get("oi") or 0.0),
                                  float(deriv.get("funding") or 0.0),
                                  float(deriv.get("ls_ratio") or 0.0))
        no_trade = None
        if sig100["grade"] == "NO" and abs(alpha) < 0.15:
            no_trade = (f"NO-TRADE score {sig100['total']} grade NO (<60, muc 14: "
                        "setup khong ro)")
        elif guard["halve"] and abs(alpha) < 0.10:
            no_trade = f"NO-TRADE deriv: {guard['warn']}"
        if no_trade:
            results.append({"symbol": sym, "status": "NO_TRADE", "reason": no_trade,
                            "alpha": alpha, "score100": sig100["total"]})
            continue
        size_mult = 0.5 if guard["halve"] else 1.0
        # Muc 15 tai lieu: phan loai setup A/B/C/D de thong ke rieng tung strategy
        _rt = retest_ok(df, direction)
        strat = classify_strategy(direction, regime=str(reg.get("regime", "")),
                                  struct=float(st.get("struct", 0.0)),
                                  bos=str(st.get("bos", "NONE")),
                                  retest=bool(_rt.get("ok", False)),
                                  sweep=bool(t.get("sweep")),
                                  sweep_bias=float(t.get("sweep_bias") or 0.0),
                                  near_sr=t.get("near_sr"),
                                  pattern_bias=float(t.get("pattern_bias") or 0.0),
                                  vol_confirm=bool(t.get("vol_confirm")),
                                  htf=mtf_b, rsi=float(t.get("rsi") or 50.0))
        # Strategy gate: chan setup thuoc strategy dang am du mau (khong ha nguong,
        # khong loai strategy khac). Ghi BLOCKED_STRAT de monitor dem.
        if cfg.strategy_gate:
            try:
                _g = strat_gate(strat, min_n=cfg.strat_min_n, avg_r=cfg.strat_avg_r,
                                path=cfg.strat_stats_path,
                                blocklist=tuple(getattr(cfg, "strategy_block", ()) or ()))
            except Exception:  # noqa: BLE001
                _g = {"blocked": False}
            if _g.get("blocked"):
                results.append({"symbol": sym, "status": "BLOCKED_STRAT",
                                "reason": _g.get("reason", ""), "strategy": strat})
                continue
        feats = extract_features(t["score"], senti.score, t.get("rsi", 50.0),
                                 t.get("ema50", 0.0), t.get("ema200", 1.0),
                                 t.get("macd_hist", 0.0), t.get("atr_pct", 0.005),
                                 t.get("vol_ratio", 1.0), t.get("vol_confirm", False),
                                 t.get("pattern_bias", 0.0), t.get("near_sr"),
                                 t.get("bb_pctb"), regime_b, mtf_b,
                                 st.get("struct", 0.0),
                                 float(deriv.get("oi_chg_24h") or 0.0),
                                 float(deriv.get("funding") or 0.0), liq_bias,
                                 bool(t.get("above_vwap", False)),
                                 float(t.get("sweep_bias") or 0.0),
                                 bool(retest_ok(df, direction).get("ok", False)),
                                 float(liq.get("dominance") or 0.0))
        learn_edge = _learner.edge(feats, direction)
        if learn_edge < LEARN_MIN_EDGE:
            results.append({"symbol": sym, "status": "BLOCKED_LEARN",
                            "reason": f"learner edge {learn_edge:.2f} (da hoc: mo kieu nay hay thua)"})
            continue
        # Phase 4 (opt-in): VETO cua agent — CHI khi da duoc cap quyen bang bang chung
        # shadow (agent_authority) va AGENTS_VETO_ENABLED=true. Chi BO QUA lenh.
        _v = agent_veto(cfg, sym, direction, alpha, strat, t, senti,
                        str(reg.get("regime", "")))
        if _v.get("block"):
            results.append({"symbol": sym, "status": "SKIP_AGENT_VETO",
                            "reason": _v.get("reason", ""), "direction": direction,
                            "alpha": alpha})
            continue
        lv = atr_levels(t["close"], t["atr"], direction, cfg.sl_atr_mult, cfg.tp_atr_mult)
        # Loc 1: TP phai du lon de cover phi round-trip (MIN_TP_PCT).
        # FOMO MODE: chi canh bao, van cho vao lenh (demo von ao, uu tien toc do test).
        tp_pct = lv["tp_dist"] / max(lv["entry"], 1e-9)
        tp_small = tp_pct < cfg.min_tp_pct
        # Loc 2: TP phai gap it nhat 1.5x phi (log canh bao, khong chan).
        fee_thin = lv["tp_dist"] < lv["sl_dist"] * 2.0 + lv["entry"] * FEE_ROUNDTRIP_PCT
        qty = bot.exchange.quantize_qty(
            sym, position_size(bot.balance, cfg.risk_per_trade_pct, lv["entry"], lv["sl"]) * size_mult)
        if qty <= 0:
            results.append({"symbol": sym, "status": "BLOCKED_QTY"})
            continue
        need = qty * lv["entry"] / max(cfg.leverage, 1)
        # Margin con lai = wallet - margin dang dung (neu doc duoc chi tiet).
        # Tranh mo them khi sap het margin -> -2019 lien tuc.
        try:
            bal_full = bot.exchange._client.fetch_balance() if bot.exchange._client else None
            info = (bal_full.get("info") or {}) if bal_full else {}
            wallet = float(info.get("totalWalletBalance") or 0)
            init_margin = float(info.get("totalInitialMargin") or 0)
            free_margin = wallet - init_margin
        except Exception:
            free_margin = bal_now if bal_now is not None else 0.0
        if free_margin is not None and need > max(free_margin * 0.8, 0):
            results.append({"symbol": sym, "status": "SKIP_MARGIN",
                            "need": round(need, 2), "free": round(float(free_margin), 2),
                            "reason": "het margin kha dung, giu vi the hien tai"})
            continue
        # P0-6: tran TONG risk danh muc. 4 cap crypto tuong quan ~1 -> 4 vi the 1%
        # KHONG phai 4 canh bac doc lap ma la mot canh bac 4%, vuot tran lo ngay 2%.
        new_risk = planned_risk_usd(lv["entry"], lv["sl"], qty)
        ok_risk, why_risk = can_add_risk(
            bot.portfolio.positions, bot.equity or bot.balance, cfg.max_total_risk_pct,
            new_risk, {s: m.initial_sl for s, m in bot.managed.items()})
        if not ok_risk:
            results.append({"symbol": sym, "status": "SKIP_RISK", "reason": why_risk,
                            "new_risk_usdt": round(new_risk, 2)})
            continue
        try:
            bot.exchange.set_leverage(sym, cfg.leverage)
            entry_res = bot.exchange.market_entry(sym, direction, qty)
            bot.exchange.stop_tp_orders(sym, direction, qty, lv["sl"], lv["tp"])
            # Bypass MAX_POSITIONS: ghi thang vao portfolio (van cam trung symbol)
            bot.portfolio.positions[sym] = Position(sym, direction, lv["entry"], qty,
                                                    lv["sl"], lv["tp"])
            _pending_feats[sym] = {"feats": feats, "direction": direction,
                                   "strategy": strat}
            # Nhat ky giao dich day du (muc 17): regime/struct/OI/funding/news/score100
            log_trade(event="OPEN", pair=sym, direction=direction, timeframe=cfg.timeframe,
                      entry=lv["entry"], sl=lv["sl"], tp=lv["tp"], qty=qty,
                      leverage=cfg.leverage, risk_pct=cfg.risk_per_trade_pct,
                      rr=lv.get("rr"), alpha=alpha, score100=sig100["total"],
                      market_regime=reg.get("regime"), btc_regime=regime_b,
                      htf_bias=mtf_b,
                      setup_type=st.get("bos", "NONE"), candlestick=t.get("pattern"),
                      volume_ratio=t.get("vol_ratio"),
                      vwap_side="ABOVE" if t.get("above_vwap") else "BELOW",
                      sweep=t.get("sweep"), retest=retest_ok(df, direction).get("ok"),
                      oi_chg=deriv.get("oi_chg_24h"), funding=deriv.get("funding"),
                      ls_ratio=deriv.get("ls_ratio"),
                      long_liq=liq.get("long_liq"), short_liq=liq.get("short_liq"),
                      news_score=senti.score,
                      econ_event=nf.get("econ_event"), sentiment_n=senti.n_articles,
                      strategy=strat, kelly_size_mult=size_mult,
                      feats=feats)
            flag = (" [TP_MONG]" if tp_small else "") + (" [FEE_THIN]" if fee_thin else "")
            log.info("TURBO OPEN %s %s qty=%s SL=%s TP=%s alpha=%s strat=%s%s", direction,
                     sym, qty, lv["sl"], lv["tp"], alpha, strat, flag)
            oid = entry_res.get("id") if isinstance(entry_res, dict) else None
            tg(cfg, fmt_open(sym, direction, qty, lv["entry"], lv["sl"], lv["tp"],
                             alpha, oid, flag))
            results.append({"symbol": sym, "status": "OPENED", "direction": direction,
                            "qty": qty, "alpha": alpha, "orderId": oid})
            # Phase 1: agent CHI CO VAN — ghi y kien macro/critic vao journal.
            agent_vote_setup(cfg, sym, direction, alpha, strat, t, senti,
                             str(reg.get("regime", "")))
        except Exception as e:  # noqa: BLE001
            # P0-4: loi mang co the xay ra SAU khi san da khop -> kiem tra vi the THAT.
            # Neu khong kiem tra, vong sau bot se mo them 1 lenh nua = gap doi risk va
            # vi the "mo ho" khong ai quan ly.
            landed = bot.exchange.position_qty(sym)
            if landed:
                pos = Position(sym, direction, lv["entry"], landed, lv["sl"], lv["tp"])
                bot.exchange.stop_tp_orders(sym, direction, landed, lv["sl"], lv["tp"])
                bot.portfolio.positions[sym] = pos
                bot._managed_for(sym, pos)
                _pending_feats[sym] = {"feats": feats, "direction": direction,
                                       "strategy": strat}
                log.warning("TURBO OPEN %s %s bao loi nhung vi the DA mo qty=%s -> "
                            "ghi nhan (recovered)", direction, sym, landed)
                results.append({"symbol": sym, "status": "OPENED", "direction": direction,
                                "qty": landed, "recovered": True,
                                "reason": str(e)[:200]})
            else:
                results.append({"symbol": sym, "status": "ORDER_FAILED",
                                "reason": str(e)[:200]})
    return results


def main() -> None:
    cfg = Settings()
    ex = BinanceFutures(cfg.api_key, cfg.api_secret, cfg.testnet, cfg.dry_run)
    bot = TradingBot(cfg, exchange=ex)
    # P0-watchdog: chan socket -> 1 HTTP call khong treo ca bot vo han
    socket.setdefaulttimeout(float(cfg.socket_timeout_sec))
    heartbeat({"phase": "boot"})
    # P0-2: nap kill-switch da luu -> restart/supervisor KHONG con reset duoc lenh ngung
    load_risk_state(cfg.risk_state_path, bot.kill)
    # Phase 5: INTERLOCK LIVE — chan cung khi chua du dieu kien sang tien that
    # (LIVE_CONFIRM, n>=50, PF>=1.2, risk<=2%, lev<=10, kill-switch sach).
    # Dat TRUOC reconcile/adopt de khong ton tien API khi cau hinh chua hop le.
    if not cfg.testnet:
        _lg = live_guard_enforce(cfg, log=log)
        if not _lg["ok"]:
            msg = "LIVE interlock chan: " + "; ".join(_lg["blockers"])
            tg(cfg, fmt_kill(msg))
            return
    syms0 = active_symbols(cfg)
    # P0-reconcile: doi chieu journal voi FILL THAT tren san -> ghi bu CLOSE bi thieu
    # (chay CA KHI kill-switch dang ngung: ghi bu chi la so lieu, khong phai giao dich).
    if cfg.reconcile_journal and not cfg.dry_run:
        try:
            _rc = reconcile_journal(cfg, ex, log=log)
            if _rc.get("written"):
                log.warning("RECONCILE: da ghi bu %s lenh dong bi thieu "
                            "(backup=%s)", _rc["written"], _rc.get("backup"))
                tg(cfg, f"[RECONCILE] Journal bi thieu {_rc['written']} lenh dong "
                         f"-> da ghi bu tu fill san (n/PF se dung hon).")
        except Exception as e:  # noqa: BLE001
            log.warning("reconcile journal loi (bo qua, khong anh huong trade): %s", e)
    if bot.kill.tripped:
        log.info("TURBO QUET %d cap: %s (dang ngung boi kill-switch -> khong trade)",
                 len(syms0), list(syms0))
        log.error("KILL-SWITCH dang NGUNG: %s | khong trade. Kiem tra roi chay "
                  "`python risk.py --reset` de xoa %s", bot.kill.reason, cfg.risk_state_path)
        tg(cfg, fmt_kill(f"{bot.kill.reason} - state da luu, bot KHONG trade"))
        return
    # P0-1: ADOPT vi the dang mo THAT tren san (ban cu chi log roi bo qua -> mo trung)
    if cfg.adopt_positions and not cfg.dry_run:
        try:
            # P0-watchdog: ADOPT goi san nhieu lan (fetch positions + ATR + arm SL/TP)
            # -> co the lau hon WATCHDOG_SEC. Nhip tim phai duoc ghi TRUOC/SAU buoc nay,
            # neu khong supervisor se kill bot dang lam viec that (da xay ra 01/10).
            heartbeat({"phase": "adopt"})
            _ms = ms_load(cfg.managed_state_path)
            n_state = ms_load_into(bot, _ms)
            rep = adopt_positions(bot, ex.fetch_positions(list(syms0)),
                                  atr_fn=lambda s: atr_of(ex, cfg, s),
                                  managed=_ms.get("trades"),
                                  alert=lambda t: tg(cfg, t))
            heartbeat({"phase": "adopt_done", "adopted": len(rep["adopted"])})
            log.warning("ADOPT vi the san: adopted=%s armed=%s KHONG-arm-duoc-tren-san=%s "
                        "chua-bao-ve=%s skipped=%s errors=%s (state nap=%s)",
                        rep["adopted"], rep["armed"], rep["unarmed"],
                        rep["unmanaged"], rep["skipped"], rep["errors"], n_state)
            if rep["unarmed"]:
                log.error("ADOPT: %d vi the KHONG dat duoc SL/TP TREN SAN (%s) — dang duoc "
                          "bao ve bang MONITOR phan mem (bot tu dong khi gia cham SL/TP). "
                          "Kiem tra bang: python arm_protection.py",
                          len(rep["unarmed"]), rep["unarmed"])
            if rep["adopted"] or rep["unmanaged"] or n_state:
                tg(cfg, (f"[KHOI DONG LAI] adopt={rep['adopted']} armed={rep['armed']} "
                         f"khong-SL-tren-san={rep['unarmed']} "
                         f"chua-bao-ve={rep['unmanaged']} state-nap={n_state}"))
            _eq = ex.fetch_balance_usdt()
            if _eq and _eq > 0:
                bot.equity = float(_eq)
                bot.balance = min(cfg.balance_usdt, bot.equity)
            bot.kill.note_equity(bot.equity or cfg.balance_usdt)
            ms_save(cfg.managed_state_path, bot)
            save_risk_state(cfg.risk_state_path, bot.kill)
        except Exception as e:  # noqa: BLE001
            log.exception("adopt vi the that bai: %s", e)
            tg(cfg, f"[CANH BAO] Adopt vi the that bai: {str(e)[:200]} - kiem tra tay!")
    rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 0
    i = 0
    log.info("TURBO DEMO start: %s (dry_run=%s)", syms0, cfg.dry_run)
    tg(cfg, f"🤖 Bot DEMO started (dry_run={cfg.dry_run}). Quét {len(syms0)} cặp / {cfg.poll_interval_sec}s. Chat OK.")
    import datetime as _dt
    _last_heartbeat = time.time()
    while True:
        i += 1
        heartbeat({"round": i, "phase": "start"})
        # P0-2: kiem tra kill-switch NGAY trong vong lap that (ban cu khong he goi)
        if bot.kill.tripped:
            log.error("KILL-SWITCH: %s -> flatten + dung", bot.kill.reason)
            tg(cfg, fmt_kill(bot.kill.reason))
            bot._flatten("kill-switch")
            break
        # 0) P0-6: dong bo EQUITY THAT (moc DD) — TACH khoi `balance` (chi la tran size
        # cua demo). Gop 2 thu se lam DD sai: balance 1000 vs equity that 4974 -> trip sai.
        _eq = bot.exchange.fetch_balance_usdt()
        if _eq and _eq > 0:
            bot.equity = float(_eq)
            if bot.kill.note_equity(bot.equity):
                log.info("NGAY MOI (UTC %s): moc DD = %.2f USDT", bot.kill.day,
                         bot.kill.start_equity)
            bot.balance = min(cfg.balance_usdt, bot.equity)
        # 1) monitor: cap nao vua dong -> cooldown + LEARN that/bai
        before = set(bot.portfolio.positions)
        mon = bot._monitor()
        if isinstance(mon, dict) and "_error" in mon:
            # P0-3: ban cu log warning roi VAN vao lenh moi ngay sau khi da flatten
            log.error("monitor loi -> flatten + dung: %s", mon)
            tg(cfg, fmt_kill(str(mon)))
            bot._flatten("monitor error")
            break
        for sym in before - set(bot.portfolio.positions):
            _last_close[sym] = time.time()
            pend = _pending_feats.pop(sym, None)
            reason = (mon or {}).get(sym, "?")
            won = reason == "TP"  # TP (ke ca partial-win/trail) = thang, SL/SENT = thua
            # Luu y: KHONG dat ten bien la `ex` (no che khuat doi tuong exchange cua
            # main() — loi cu: sau lan close dau tien `ex` bien thanh dict).
            exr = bot.last_exits.get(sym) or {}
            r_real = float(exr.get("r") or 0.0)
            # Thong ke rieng tung strategy (muc 15): A/B/C/D — phat hien nhom keo PF xuong
            strat = str((pend or {}).get("strategy") or exr.get("strategy") or "NONE")
            try:
                srep = strat_bump(strat, bool(exr.get("won", won)), r_real)
                log.info("STRAT %s n=%s WR=%.0f%% avgR=%s", strat, srep.get("n"),
                         100.0 * float(srep.get("wins", 0)) / max(int(srep.get("n", 1)), 1),
                         round(float(srep.get("sum_r", 0.0)) / max(int(srep.get("n", 1)), 1), 2))
            except Exception as e:  # noqa: BLE001
                log.warning("strat_bump fail: %s", e)
            # Phase 1: agent CHI CO VAN — ghi "bai hoc" sau khi dong lenh (shadow).
            agent_vote_review(cfg, sym,
                              str((pend or {}).get("direction") or exr.get("direction")
                                  or "?"),
                              r_real, bool(exr.get("won", won)), str(reason), strat)
            if pend:
                try:
                    upd = _learner.update(pend["feats"], pend["direction"], won)
                    log.info("LEARN %s %s (%s) R=%.2f n=%s w=%s", sym,
                             "WIN" if won else "LOSS", reason, r_real, upd["n"], upd["w"])
                except Exception as e:  # noqa: BLE001
                    log.warning("learner update fail: %s", e)
            else:
                log.info("close %s (%s) - khong co feats (vi the cu)", sym, reason)
            tg(cfg, fmt_close(sym, f"{reason} R={r_real:+.2f}"))
            # P0-2: nuoi kill-switch bang ket qua THUC (dem thua lien tiep + peak).
            # Ban cu khong he goi register_close trong turbo -> "5 thua lien tiep"
            # khong bao gio kich hoat.
            if bot.kill.register_close(bool(exr.get("won", won)), bot.equity or bot.balance):
                log.error("KILL-SWITCH (sau khi dong lenh): %s", bot.kill.reason)
                tg(cfg, fmt_kill(bot.kill.reason))
                bot._flatten("kill-switch")
            log.info("cooldown %s %ss (vua dong)", sym, cfg.cooldown_sec)
        if bot.kill.tripped:
            log.error("KILL-SWITCH truoc round -> dung han: %s", bot.kill.reason)
            tg(cfg, fmt_kill(bot.kill.reason))
            break
        try:
            res = turbo_round(bot)
        except Exception as e:  # noqa: BLE001
            log.exception("round %d loi: %s", i, e)
            tg(cfg, f"⚠️ Bot loi round {i}: {str(e)[:200]}")
            res = [{"status": "ERROR", "reason": str(e)[:200]}]
        if i % 20 == 0:
            log.info("learner state n=%s w=%s b=%.3f", _learner.n_updates,
                     {k: round(v, 3) for k, v in _learner.w.items()}, _learner.b)
        log.info("round %d monitor=%s -> %s", i, mon, res)
        # P0-6 + P0-2: kiem tra DD ngay (theo equity THAT) va bien dong ATR that su,
        # roi persist state — restart khong duoc quen trang thai ngung.
        if bot.kill.check(bot.equity or bot.balance,
                          float(getattr(bot, "_max_atr_pct", 0.0) or 0.0)):
            log.error("KILL-SWITCH: %s -> flatten + dung", bot.kill.reason)
            tg(cfg, fmt_kill(bot.kill.reason))
            bot._flatten("kill-switch")
            save_risk_state(cfg.risk_state_path, bot.kill)
            ms_save(cfg.managed_state_path, bot)
            break
        save_risk_state(cfg.risk_state_path, bot.kill)
        ms_save(cfg.managed_state_path, bot)
        heartbeat({"round": i, "phase": "end",
                   "equity": round(float(bot.equity or bot.balance or 0), 2)})
        # Het vong bao Telegram: tom tat quyet dinh + alpha/score tung cap (log day realtime)
        # Mac dinh TAT (TELEGRAM_EVERY_ROUND=false) de tranh spam — chi gui khi co lenh.
        try:
            acted = [r for r in res if str(r.get("status", "")).upper() in
                     ("OPENED", "CLOSE", "CLOSED", "KILL", "KILLED", "ORDER_FAILED", "ERROR")]
            _sum = []
            for r in (acted if acted else res):
                s = r.get("symbol", "?").split("/")[0]
                stt = r.get("status", "?")
                extra = ""
                if r.get("alpha") is not None:
                    extra += f" a={r['alpha']:.3f}"
                if r.get("score100") is not None:
                    extra += f" s={r['score100']}"
                if r.get("reason"):
                    extra += f" ({str(r['reason'])[:60]})"
                _sum.append(f"{s}:{stt}{extra}")
            if acted:
                tg(cfg, f"📋 Round {i} | {' | '.join(_sum)}")
            else:
                tg_round(cfg, f"📋 Round {i} | {' | '.join(_sum)}")
        except Exception:
            pass
        if time.time() - _last_heartbeat >= 1800:
            _last_heartbeat = time.time()
            try:
                _b = bot.exchange.fetch_balance_usdt()
                _pos = ", ".join(f"{s}:{p.direction} {round(p.qty,4)}"
                                 for s, p in bot.portfolio.positions.items()) or "trong"
                tg(cfg, f"💓 Heartbeat {_dt.datetime.now().strftime('%H:%M %d/%m')} | wallet~{_b} | vi the: {_pos} | round {i}")
            except Exception:
                pass
        if rounds and i >= rounds:
            break
        time.sleep(cfg.poll_interval_sec)


if __name__ == "__main__":
    main()
