from __future__ import annotations
import numpy as np
import pandas as pd

def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(s, n=14):
    d=s.diff(); up=d.clip(lower=0); down=-d.clip(upper=0)
    rs=up.ewm(alpha=1/n, adjust=False).mean() / down.ewm(alpha=1/n, adjust=False).mean().replace(0,np.nan)
    return 100-(100/(1+rs))
def atr(df, n=14):
    pc=df.close.shift(1)
    tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()
def macd(s):
    m=ema(s,12)-ema(s,26); sig=ema(m,9); return m,sig,m-sig
def adx(df,n=14):
    up=df.high.diff(); dn=-df.low.diff()
    plus=np.where((up>dn)&(up>0),up,0.0); minus=np.where((dn>up)&(dn>0),dn,0.0)
    a=atr(df,n)
    pdi=100*pd.Series(plus,index=df.index).ewm(alpha=1/n,adjust=False).mean()/a
    mdi=100*pd.Series(minus,index=df.index).ewm(alpha=1/n,adjust=False).mean()/a
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean()
def enrich(df):
    x=df.copy()
    x["ema20"]=ema(x.close,20); x["ema50"]=ema(x.close,50); x["ema200"]=ema(x.close,200)
    x["rsi"]=rsi(x.close); x["atr"]=atr(x); x["adx"]=adx(x)
    x["macd"],x["macd_sig"],x["macd_hist"]=macd(x.close)
    mid=x.close.rolling(20).mean(); sd=x.close.rolling(20).std()
    x["bb_mid"]=mid; x["bb_up"]=mid+2*sd; x["bb_dn"]=mid-2*sd
    x["vol_z"]=(x.volume-x.volume.rolling(50).mean())/x.volume.rolling(50).std()
    x["high20"]=x.high.shift(1).rolling(20).max(); x["low20"]=x.low.shift(1).rolling(20).min()
    return x
