import pandas as pd, numpy as np
from binance_futures_ai_bot.indicators import enrich

def test_enrich_columns():
    n=250; base=np.linspace(100,150,n)+np.sin(np.arange(n))*2
    df=pd.DataFrame({"open":base,"high":base+1,"low":base-1,"close":base,"volume":np.ones(n)*100})
    x=enrich(df)
    for c in ["ema20","ema50","ema200","rsi","atr","macd_hist","adx","bb_up","bb_dn","vol_z"]:
        assert c in x
    assert np.isfinite(x.ema20.iloc[-1])
