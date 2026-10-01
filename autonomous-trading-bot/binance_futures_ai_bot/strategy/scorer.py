from __future__ import annotations
import numpy as np
from ..indicators import enrich

def _clip(x): return float(max(-1,min(1,x)))

def technical_score(dfs):
    scores=[]; details=[]
    for tf,df in dfs.items():
        x=enrich(df).iloc[-1]
        bull=0; bear=0
        bull += 1.0 if x.ema20>x.ema50>x.ema200 else 0
        bear += 1.0 if x.ema20<x.ema50<x.ema200 else 0
        bull += _clip((x.rsi-50)/20); bear += _clip((50-x.rsi)/20)
        bull += 1 if x.macd_hist>0 else 0; bear += 1 if x.macd_hist<0 else 0
        bull += 0.5 if x.adx>20 and x.close>x.bb_mid else 0; bear += 0.5 if x.adx>20 and x.close<x.bb_mid else 0
        bull += 0.5 if x.close>x.high20 else 0; bear += 0.5 if x.close<x.low20 else 0
        s=(bull-bear)/4.5; scores.append(s); details.append(f"{tf}:{s:.2f}")
    return float(np.average(scores,weights=[1,1.5,2,2.5])), ", ".join(details)

def build_trade(symbol, dfs, news_score, cfg):
    t,detail=technical_score(dfs)
    total=cfg["strategy"]["technical_weight"]*t + cfg["strategy"]["news_weight"]*news_score
    direction="LONG" if total>0 else "SHORT"
    score=abs(total)
    x=enrich(dfs["15m"]).iloc[-1]
    entry=float(x.close); a=float(x.atr)
    if a<=0: return None
    slm=cfg["strategy"]["atr_sl_mult"]; rr=cfg["strategy"]["risk_reward"]
    if direction=="LONG": stop=entry-slm*a; target=entry+slm*a*rr
    else: stop=entry+slm*a; target=entry-slm*a*rr
    reason=f"tech={t:.2f} news={news_score:.2f} | {detail}"
    return direction,score,entry,stop,target,reason
