from __future__ import annotations
import logging, time
from datetime import datetime, timezone
from .exchange.binance import BinanceFutures
from .news.feeds import fetch_feeds
from .news.scorer import score_news
from .risk.manager import RiskManager
from .storage.db import Journal
from .strategy.scorer import build_trade

log=logging.getLogger("bot")
class TradingEngine:
    def __init__(self,cfg):
        self.cfg=cfg; logging.basicConfig(level=getattr(logging,__import__('os').getenv('LOG_LEVEL','INFO')),format='%(asctime)s %(levelname)s %(message)s')
        self.ex=BinanceFutures(cfg.api_key,cfg.api_secret,cfg.mode,cfg.dry_run); self.ex.refresh_filters(); self.journal=Journal()
        r=cfg.raw["risk"]; self.risk=RiskManager(**r); self.last_trade_ts=0

    def equity(self):
        if self.cfg.dry_run: return 1000.0
        bal=self.ex.balances(); usdt=next((x for x in bal if x["asset"]=="USDT"),None); return float(usdt["balance"]) if usdt else 0
    def current_position(self):
        if self.cfg.dry_run: return None
        for p in self.ex.positions():
            amt=float(p["positionAmt"])
            if abs(amt)>0: return p
        return None
    def run_once(self):
        eq=self.equity()
        if self.risk.halted(eq): log.warning("RISK HALT: equity=%s",eq); return
        news_cfg=self.cfg.raw["news"]
        news_items=fetch_feeds(news_cfg["feeds"],news_cfg["max_items_per_feed"])
        nscore,mhits,nreasons=score_news(news_items,news_cfg["positive"],news_cfg["negative"],news_cfg["macro"])
        if nscore <= self.cfg.raw["strategy"]["risk_off_threshold"]:
            log.warning("NEWS RISK-OFF %.2f; no new trade",nscore); return
        today=datetime.now(timezone.utc).date().isoformat()
        if today in set(self.cfg.raw["strategy"].get("fomc_dates_utc", [])):
            log.warning("MACRO BLACKOUT: scheduled FOMC date %s", today); return
        if self.current_position() is not None:
            log.info("Existing position: no new overlapping trade"); return
        if time.time()-self.last_trade_ts < self.cfg.raw["strategy"]["cooldown_minutes"]*60: return
        candidates=[]
        for sym in self.cfg.symbols:
            dfs={tf:self.ex.klines(sym,tf,500) for tf in self.cfg.raw["timeframes"]}
            s=build_trade(sym,dfs,nscore,self.cfg.raw)
            if s:
                direction,score,entry,stop,target,reason=s; candidates.append((score,sym,direction,entry,stop,target,reason))
        if not candidates: return
        candidates.sort(reverse=True,key=lambda z:z[0]); score,sym,direction,entry,stop,target,reason=candidates[0]
        if score < self.cfg.raw["strategy"]["min_score"] or score < self.cfg.raw["strategy"].get("min_edge", 0): log.info("No score above threshold: %.3f",score); return
        q=self.risk.qty(eq,entry,stop)
        if q*entry < self.cfg.raw["risk"]["min_qty_usdt"]: log.warning("Qty below min notional; skip"); return
        side="BUY" if direction=="LONG" else "SELL"
        self.ex.set_leverage(sym,self.cfg.raw["risk"]["max_leverage"])
        result=self.ex.market_order_with_protection(sym,side,q,stop,target)
        self.journal.log(symbol=sym,direction=direction,entry=entry,stop=stop,target=target,qty=q,score=score,reason=reason+f" news_items={mhits}")
        self.last_trade_ts=time.time(); log.warning("TRADE %s %s qty=%s entry=%.4f SL=%.4f TP=%.4f | %s | result=%s",direction,sym,q,entry,stop,target,reason,result)
    def run_forever(self):
        log.warning("BOT START mode=%s dry_run=%s symbols=%s",self.cfg.mode,self.cfg.dry_run,self.cfg.symbols)
        while True:
            try: self.run_once()
            except Exception as e: log.exception("cycle failed: %s",e)
            time.sleep(self.cfg.raw["loop_seconds"])
