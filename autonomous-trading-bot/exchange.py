"""ccxt Binance USDT-M Futures wrapper (testnet aware, DRY_RUN safe).

- Du lieu public (OHLCV/ticker) luon doc duoc KHONG can API key.
- Chi khi dat lenh that (DRY_RUN=false) moi can key/secret.
"""
from __future__ import annotations

import re
import secrets
import time

import pandas as pd


def request_ip_from_error(msg: str) -> str:
    """IP mà Binance THẤY khi trả lỗi -2015 (rỗng nếu Binance không nêu).

    Vì sao cần: máy có nhiều đường ra Internet (2 WAN/CGNAT) ⇒ IP mà Binance thấy
    có thể KHÁC IP `api.ipify.org` báo. Khi đó bật 'Restrict access to trusted IPs'
    là bẫy: key "đúng" vẫn lỗi -2015 ngẫu nhiên, bot LIVE có thể không đặt được SL.
    """
    m = re.search(r"request ip:\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})", str(msg or ""))
    return m.group(1) if m else ""


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
        self.last_error: str = ""   # loi cuoi cung khi doc/ghi (de chan doan -2015...)
        self._hedge: bool | None = None   # None = chua do; xem hedge_mode()
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

    # ---- HEDGE / ONE-WAY: tai khoan LIVE co the o che do 2 chieu ----------------

    def hedge_mode(self) -> bool:
        """Tai khoan dang o HEDGE (dual position side) hay ONE-WAY?

        Vi sao can (loi that 09/10 16:45): lenh KHONG co `positionSide` bi tu choi
        `-4061 Order's position side does not match user's setting` khi tai khoan o HEDGE.
        Tai khoan DEMO la one-way nen bot chay duoc, sang LIVE (hedge) thi moi lenh hong.
        Tu do 1 lan roi nho; loi mang -> coi nhu one-way (giu hanh vi cu).
        """
        if self._hedge is None:
            self._hedge = False
            try:
                if self._client is not None:
                    r = self._client.fapiPrivateGetPositionSideDual()
                    self._hedge = bool((r or {}).get("dualSidePosition"))
            except Exception:  # noqa: BLE001
                pass
        return bool(self._hedge)

    def _pos_side(self, direction: str) -> dict:
        """`{"positionSide": ...}` khi tai khoan HEDGE; rong khi ONE-WAY.

        HEDGE: moi lenh phai khai bao phia vi the; va KHONG duoc gui `reduceOnly`.
        """
        if not self.hedge_mode():
            return {}
        return {"positionSide": "LONG" if str(direction).upper() == "LONG" else "SHORT"}

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
        except Exception as e:  # noqa: BLE001
            # Ghi lai loi THAT (khong nuot) — thieu dong nay thi log chi co
            # "khong doc duoc" va khong biet -2015 (key/IP/quyen) hay -1021 (le gio).
            self.last_error = "%s: %s" % (type(e).__name__, str(e)[:220])
            return None
        self.last_error = "response khong co truong so du USDT"
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
        params.update(self._pos_side(direction))
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
        ps = self._pos_side(direction)   # HEDGE: bat buoc co positionSide (khong dung reduceOnly)
        out: dict = {"cancelled": self.cancel_symbol_orders(symbol) if cancel_first else None}
        for tag, otype, price in (("sl", "STOP_MARKET", sl), ("tp", "TAKE_PROFIT_MARKET", tp)):
            base = {"stopPrice": price, "workingType": "CONTRACT_PRICE",
                    "newClientOrderId": _cid(cid_prefix + tag)}
            base.update(ps)
            p_qty = dict(base)
            p_close = dict(base)
            if ps:
                # HEDGE: `reduceOnly` KHONG duoc phep -> dong bang closePosition/positionSide.
                p_close["closePosition"] = True
                try:
                    out[tag + "_order"] = self._client.create_order(
                        symbol, otype, close_side, None, params=p_close)
                except Exception:
                    out[tag + "_order"] = self._client.create_order(
                        symbol, otype, close_side, qty, params=p_qty)
            else:
                p_qty["reduceOnly"] = True
                try:
                    out[tag + "_order"] = self._client.create_order(
                        symbol, otype, close_side, qty, params=p_qty)
                except Exception:
                    # fallback: closePosition=True (khong truyen quantity -> tranh -1106)
                    p_close["closePosition"] = True
                    out[tag + "_order"] = self._client.create_order(
                        symbol, otype, close_side, None, params=p_close)
        return out

    def close_position(self, symbol: str, direction: str, qty: float,
                       cid: str | None = None) -> dict:
        side = "sell" if direction == "LONG" else "buy"
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "side": side, "qty": qty, "dry_run": True}
        params: dict = {"newClientOrderId": cid or _cid("close")}
        ps = self._pos_side(direction)
        if ps:
            params.update(ps)          # HEDGE: positionSide thay cho reduceOnly
        else:
            params["reduceOnly"] = True
        return self._client.create_market_order(symbol, side, qty, params=params)

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

