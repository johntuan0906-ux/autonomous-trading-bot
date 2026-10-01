"""ccxt Binance USDT-M Futures wrapper (testnet aware, DRY_RUN safe).

- Du lieu public (OHLCV/ticker) luon doc duoc KHONG can API key.
- Chi khi dat lenh that (DRY_RUN=false) moi can key/secret.
"""
from __future__ import annotations

import secrets
import time

import pandas as pd


def _cid(tag: str) -> str:
    """clientOrderId <= 36 ky tu (gioi han Binance), duy nhat cho tung lenh.

    P0-4: co idempotency -> timeout mang KHONG lam bot mo trung vi the.
    """
    t = "".join(ch for ch in str(tag) if ch.isalnum())[:8] or "x"
    return ("glow" + t + str(int(time.time() * 1000)) + secrets.token_hex(3))[:36]


class BinanceFutures:
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True,
                 dry_run: bool = True):
        self.dry_run = dry_run
        self.testnet = testnet
        self._client = None
        self._public = None
        try:
            import ccxt  # type: ignore
            self._public = ccxt.binance({"options": {"defaultType": "future"},
                                         "enableRateLimit": True})
            if not dry_run:
                self._client = ccxt.binance({
                    "apiKey": api_key, "secret": api_secret,
                    "options": {"defaultType": "future"},
                    "enableRateLimit": True,
                })
                if testnet:
                    # Binance da khai tu Futures testnet (testnet.binancefuture.com).
                    # Che do paper-trading moi: Demo Trading (demo.binance.com)
                    # + key tao tu demo.binance.com + enable_demo_trading(True).
                    try:
                        self._client.enable_demo_trading(True)
                    except Exception:
                        self._client.set_sandbox_mode(True)  # fallback cu

        except ImportError:
            self._public = None  # che do offline/demo, dung candles_provider

    def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> pd.DataFrame:
        src = self._client if self._client is not None else self._public
        if src is None:
            raise RuntimeError("khong co ccxt / mang - dung demo.py offline")
        raw = src.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df

    def last_price(self, symbol: str) -> float:
        src = self._client if self._client is not None else self._public
        ticker = src.fetch_ticker(symbol)
        return float(ticker["last"])

    def fetch_balance_usdt(self) -> float | None:
        """So du USDT futures thuc te. Tra None neu khong doc duoc."""
        src = self._client if self._client is not None else self._public
        if src is None:
            return None
        try:
            bal = src.fetch_balance()
            info = bal.get("info") or {}
            for key in ("totalMarginBalance", "totalWalletBalance"):
                try:
                    v = float(info.get(key, "nan"))
                    if v == v:  # not NaN
                        return v
                except (TypeError, ValueError):
                    continue
            usdt = bal.get("USDT") or {}
            for key in ("total", "free"):
                try:
                    v = float(usdt.get(key, "nan"))
                    if v == v:
                        return v
                except (TypeError, ValueError):
                    continue
        except Exception:
            return None
        return None

    def quantize_qty(self, symbol: str, qty: float) -> float:
        """Cat qty theo precision + min amount cua san."""
        src = self._client if self._client is not None else self._public
        if src is None:
            return round(qty, 6)
        try:
            markets = src.load_markets()
            m = markets.get(symbol)
            if not m:
                return round(qty, 6)
            q = float(src.amount_to_precision(symbol, qty))
            min_amt = (m.get("limits") or {}).get("amount", {}).get("min")
            if min_amt and q < float(min_amt):
                return 0.0
            return q
        except Exception:
            return round(qty, 6)

    def set_leverage(self, symbol: str, leverage: int) -> None:
        if self._client is None or self.dry_run:
            return
        try:
            self._client.set_leverage(leverage, symbol)
        except Exception:
            pass

    def market_entry(self, symbol: str, direction: str, qty: float,
                     cid: str | None = None) -> dict:
        side = "buy" if direction == "LONG" else "sell"
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "side": side, "qty": qty, "dry_run": True}
        params = {"newClientOrderId": cid or _cid("entry")}
        return self._client.create_market_order(symbol, side, qty, params=params)

    def stop_tp_orders(self, symbol: str, direction: str, qty: float, sl: float,
                       tp: float, cid_prefix: str = "sg",
                       cancel_first: bool = True) -> dict:
        """Arm SL/TP.

        P0-5: `cancel_first=True` HUY het lenh treo cu truoc khi arm -> khong con
        tinh trang 2-4 lenh STOP/TP chong nhau (partial/BE/trail cu goi lai nhieu
        lan, va lenh cu co the kich hoat dong nham vi the MOI mo sau do).
        P0-4: moi lenh co clientOrderId rieng.
        """
        if self._client is None or self.dry_run:
            return {"sl": sl, "tp": tp, "dry_run": True}
        close_side = "sell" if direction == "LONG" else "buy"
        out: dict = {"cancelled": self.cancel_symbol_orders(symbol) if cancel_first else None}
        for tag, otype, price in (("sl", "STOP_MARKET", sl), ("tp", "TAKE_PROFIT_MARKET", tp)):
            try:
                out[tag + "_order"] = self._client.create_order(
                    symbol, otype, close_side, qty,
                    params={"stopPrice": price, "reduceOnly": True,
                            "workingType": "CONTRACT_PRICE",
                            "newClientOrderId": _cid(cid_prefix + tag)})
            except Exception:
                # fallback: closePosition=True (khong truyen quantity -> tranh -1106)
                out[tag + "_order"] = self._client.create_order(
                    symbol, otype, close_side, None,
                    params={"stopPrice": price, "closePosition": True,
                            "workingType": "CONTRACT_PRICE",
                            "newClientOrderId": _cid(cid_prefix + tag)})
        return out

    def close_position(self, symbol: str, direction: str, qty: float,
                       cid: str | None = None) -> dict:
        side = "sell" if direction == "LONG" else "buy"
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "side": side, "qty": qty, "dry_run": True}
        return self._client.create_market_order(
            symbol, side, qty, params={"reduceOnly": True,
                                       "newClientOrderId": cid or _cid("close")})

    # ---- P0-1/P0-5: doc trang thai THAT tren san -------------------------------

    def cancel_symbol_orders(self, symbol: str) -> dict:
        """Huy MOI lenh dang treo cua symbol (best-effort, khong nem loi)."""
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "cancelled": 0, "dry_run": True}
        try:
            res = self._client.cancel_all_orders(symbol)
            return {"symbol": symbol,
                    "cancelled": len(res) if isinstance(res, list) else 1}
        except Exception as e:  # noqa: BLE001
            return {"symbol": symbol, "cancelled": 0, "error": str(e)[:200]}

    def fetch_positions(self, symbols=None) -> list:
        """Vi the dang mo THAT tren san (ccxt). Loi/dry_run -> [] (khong suy dien)."""
        if self._client is None or self.dry_run:
            return []
        try:
            return list(self._client.fetch_positions(symbols) or [])
        except Exception:
            return []

    def position_qty(self, symbol: str) -> float | None:
        """So hop dong dang mo THUC TE. None = khong doc duoc (khac 0.0 = da dong)."""
        if self._client is None or self.dry_run:
            return None
        try:
            for p in self._client.fetch_positions([symbol]):
                if str(p.get("symbol")) == symbol:
                    return abs(float(p.get("contracts") or 0))
        except Exception:
            return None
        return 0.0

    def fetch_protection(self, symbol: str) -> dict:
        """SL/TP dang TREO tren san -> {'sl': float|None, 'tp': float|None}.

        Dung khi khoi dong lai: biet vi the con duoc bao ve hay khong.
        """
        out: dict = {"sl": None, "tp": None}
        if self._client is None or self.dry_run:
            return out
        try:
            for o in self._client.fetch_open_orders(symbol):
                t = str(o.get("type") or "")
                px = o.get("stopPrice") or (o.get("info") or {}).get("stopPrice")
                try:
                    px = float(px or 0) or None
                except (TypeError, ValueError):
                    px = None
                if not px:
                    continue
                if t == "STOP_MARKET":
                    out["sl"] = px
                elif t == "TAKE_PROFIT_MARKET":
                    out["tp"] = px
        except Exception:
            pass
        return out

