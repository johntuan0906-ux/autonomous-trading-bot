from __future__ import annotations
import hashlib, hmac, time
from decimal import Decimal, ROUND_DOWN
import httpx

class BinanceFutures:
    def __init__(self, api_key, api_secret, mode="testnet", dry_run=True):
        self.key=api_key; self.secret=api_secret; self.dry_run=dry_run
        self.base = "https://testnet.binancefuture.com" if mode=="testnet" else "https://fapi.binance.com"
        self.client=httpx.Client(timeout=15, headers={"X-MBX-APIKEY":api_key} if api_key else {})
        self.filters={}

    def _signed(self, method, path, params=None):
        params=dict(params or {}); params["timestamp"]=int(time.time()*1000); params["recvWindow"]=5000
        q="&".join(f"{k}={params[k]}" for k in sorted(params))
        sig=hmac.new(self.secret.encode(),q.encode(),hashlib.sha256).hexdigest(); params["signature"]=sig
        r=self.client.request(method,self.base+path,params=params); r.raise_for_status(); return r.json()
    def public(self,path,params=None):
        r=self.client.get(self.base+path,params=params or {}); r.raise_for_status(); return r.json()
    def exchange_info(self): return self.public("/fapi/v1/exchangeInfo")
    def klines(self,symbol,interval,limit=500):
        rows=self.public("/fapi/v1/klines",{"symbol":symbol,"interval":interval,"limit":limit})
        import pandas as pd
        cols=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
        df=pd.DataFrame(rows,columns=cols)
        for c in ["open","high","low","close","volume"]: df[c]=df[c].astype(float)
        return df
    def mark_price(self,symbol): return float(self.public("/fapi/v1/premiumIndex",{"symbol":symbol})["markPrice"])
    def ticker(self,symbol): return self.public("/fapi/v1/ticker/bookTicker",{"symbol":symbol})
    def balances(self): return self._signed("GET","/fapi/v3/balance")
    def positions(self): return self._signed("GET","/fapi/v3/positionRisk")
    def set_leverage(self,symbol,leverage):
        if self.dry_run: return {"dry_run":True}
        return self._signed("POST","/fapi/v1/leverage",{"symbol":symbol,"leverage":leverage})
    def _quant(self,symbol,qty,price):
        f=self.filters[symbol];
        step=Decimal(str(f["stepSize"])); tick=Decimal(str(f["tickSize"]))
        q=(Decimal(str(qty))/step).to_integral_value(rounding=ROUND_DOWN)*step
        p=(Decimal(str(price))/tick).to_integral_value(rounding=ROUND_DOWN)*tick
        return f"{q:f}",f"{p:f}"
    def refresh_filters(self):
        for s in self.exchange_info()["symbols"]:
            if s["symbol"] in {"BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"}:
                ff={x["filterType"]:x for x in s["filters"]}
                self.filters[s["symbol"]]={"stepSize":ff["LOT_SIZE"]["stepSize"],"tickSize":ff["PRICE_FILTER"]["tickSize"],"minQty":ff["LOT_SIZE"]["minQty"]}
    def market_order_with_protection(self,symbol,side,qty,stop,target):
        q,sp=self._quant(symbol,qty,stop); _,tp=self._quant(symbol,qty,target)
        if self.dry_run:
            return {"mode":"dry_run","symbol":symbol,"side":side,"qty":q,"stop":sp,"target":tp}
        entry=self._signed("POST","/fapi/v1/order",{"symbol":symbol,"side":side,"type":"MARKET","quantity":q,"newOrderRespType":"RESULT"})
        close_side="SELL" if side=="BUY" else "BUY"
        self._signed("POST","/fapi/v1/algoOrder",{"algoType":"CONDITIONAL","symbol":symbol,"side":close_side,"type":"STOP_MARKET","triggerPrice":sp,"closePosition":"true","workingType":"MARK_PRICE"})
        self._signed("POST","/fapi/v1/algoOrder",{"algoType":"CONDITIONAL","symbol":symbol,"side":close_side,"type":"TAKE_PROFIT_MARKET","triggerPrice":tp,"closePosition":"true","workingType":"MARK_PRICE"})
        return entry
    def close_position(self,symbol,position_amt):
        if not position_amt: return None
        side="SELL" if position_amt>0 else "BUY"
        q,_=self._quant(symbol,abs(position_amt),self.mark_price(symbol))
        if self.dry_run: return {"dry_run":True,"close":symbol,"qty":q}
        return self._signed("POST","/fapi/v1/order",{"symbol":symbol,"side":side,"type":"MARKET","quantity":q,"reduceOnly":"true"})
