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


def is_reduce_only_rejected(err) -> bool:
    """Loi `-2022 ReduceOnly Order is rejected` (= vi the da dong TRUOC do)?

    Vi sao can (19/10, tai dien 20/10): khi SL/TP dat TREN SAN khop truoc, vi the ve 0
    ngay tai thoi diem bot gui lenh dong ⇒ san tu choi lenh giam vi the bang `-2022`.
    Day KHONG phai loi he thong ma la "dua nhau ve dich": phai xu ly tuong minh.
    """
    s = str(err or "")
    return "-2022" in s or "ReduceOnly Order is rejected" in s


def _row_side(p) -> str | None:
    """`LONG`/`SHORT` cua 1 dong vi the ccxt (None = khong doc duoc phia)."""
    d = p or {}
    s = str(d.get("side") or "").upper()
    if s not in ("LONG", "SHORT"):
        s = str((d.get("info") or {}).get("positionSide") or "").upper()
    return s if s in ("LONG", "SHORT") else None


def _row_qty(p) -> float | None:
    """So hop dong cua 1 dong vi the (None = du lieu hong)."""
    try:
        return abs(float((p or {}).get("contracts") or 0))
    except (TypeError, ValueError):
        return None


def to_ccxt_symbol(raw: str) -> str:
    """`AEROUSDT` -> `AERO/USDT:USDT` (giu nguyen neu da dung dang ccxt)."""
    s = str(raw or "")
    if "/" in s:
        return s
    if s.endswith("USDT") and len(s) > 4:
        return "%s/USDT:USDT" % s[:-4]
    return s


def to_raw_symbol(sym: str) -> str:
    """`AERO/USDT:USDT` -> `AEROUSDT` (endpoint algo nhan symbol tran)."""
    return str(sym or "").replace("/", "").split(":")[0]


def _tune_session(cli) -> None:
    """Nới connection pool của `requests` (mặc định 10 → 32).

    Vì sao (11/10): quét ~460 cặp với `SCAN_WORKERS=16` làm pool đầy ⇒ log đầy
    `Connection pool is full, discarding connection: fapi.binance.com` ⇒ request bị chậm/bỏ,
    vòng quét kéo dài (đo được > 4 phút cho 1 vòng LIVE).
    """
    try:
        from requests.adapters import HTTPAdapter
        ad = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=2)
        cli.session.mount("https://", ad)
        cli.session.mount("http://", ad)
    except Exception:  # noqa: BLE001
        pass


class BinanceFutures:
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = True,
                 dry_run: bool = True):
        self.dry_run = dry_run
        self.testnet = testnet
        self._client = None
        self._public = None
        self.last_error: str = ""   # loi cuoi cung khi doc/ghi (de chan doan -2015...)
        self._hedge: bool | None = None   # None = chua do; xem hedge_mode()
        # (20/10) San co the TU CHOI `reduceOnly` cho lenh MARKET (`-2022`; do that tren
        # demo: qty=1 tren vi the 31 hop dong van bi tu choi). Ghi nho trong phien de lan
        # dong sau di thang duong "qty chinh xac" (xem `close_position`/`_close_exact`).
        self._ro_market_rejected: bool = False
        try:
            import ccxt  # type: ignore
            self._public = ccxt.binance({"options": {"defaultType": "future"},
                                         "enableRateLimit": True})
            _tune_session(self._public)
            if not dry_run:
                self._client = ccxt.binance({
                    "apiKey": api_key, "secret": api_secret,
                    "options": {"defaultType": "future"},
                    "enableRateLimit": True,
                })
                _tune_session(self._client)
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
        """OHLCV + cache tang dan (11/10): quet ~460 cap thi KHONG the refetch
        day du moi vong (weight ~916-2300/vong -> rate-limit -> FETCH_TIMEOUT).
        Vong dau lay day du; cac vong sau chi ghep phan duoi (8 nen, weight 1)
        -> ~458 weight/vong, khong can chet IP.

        - Timeframe cao (1h/4h/1d): nen chi xuong 1 cai moi gio -> TTL 900s de
          mtf khong phai fetch moi vong (cat ~1/2 so request moi vong).
        - Fetch loi thi 'cache loi' 120s: khong retry full-fetch lien tuc moi
          vong (retry-storm lam chet IP; symbol se duoc thu lai vong sau).

        Thread-safe-ish (GIL): worst-case 2 luong fetch trung 1 cap — khong sai data.
        """
        src = self._client if self._client is not None else self._public
        if src is None:
            raise RuntimeError("khong co ccxt / mang - dung demo.py offline")
        cache = getattr(self, "_ohlcv_cache", None)
        if cache is None:
            cache = {}
            self._ohlcv_cache = cache
        key = (symbol, timeframe)
        ent = cache.get(key)
        now = time.monotonic()
        m = re.search(r"(\d+)([a-z])$", str(timeframe))
        slow_tf = bool(m) and (m.group(2) in "hdw" or (m.group(2) == "m" and int(m.group(1)) >= 60))
        fresh_sec = 900.0 if slow_tf else 45.0      # 1h+ : nen xuong cham, 15p/vong
        merge_sec = 86400.0 if slow_tf else 3600.0
        if ent is not None:
            if "err" in ent:
                if now - ent["ts"] < 120.0:
                    raise RuntimeError("fetch %s that bai gan day (cooldown): %s"
                                       % (symbol, ent["err"][:80]))
                ent = None                          # het cooldown -> thu lai
        if ent is not None and now - ent["ts"] < fresh_sec:
            # Moi bam gan day: dung lai, khong goi san.
            return ent["df"].copy()
        if ent is not None and now - ent["ts"] < merge_sec:
            # Cap nhat tang dan: lay 8 nen moi nhat, ghep vao, cat bo nen cu.
            try:
                tail_raw = src.fetch_ohlcv(symbol, timeframe, limit=8)
                tdf = pd.DataFrame(tail_raw, columns=["ts", "open", "high", "low", "close", "volume"])
                tdf["ts"] = pd.to_datetime(tdf["ts"], unit="ms")
            except Exception as e:  # noqa: BLE001
                cache[key] = {"err": str(e), "ts": now}
                raise
            df = pd.concat([ent["df"], tdf], ignore_index=True)
            df = (df.drop_duplicates(subset=["ts"], keep="last")
                    .sort_values("ts").tail(limit).reset_index(drop=True))
        else:
            try:
                raw = src.fetch_ohlcv(symbol, timeframe, limit=limit)
            except Exception as e:  # noqa: BLE001
                cache[key] = {"err": str(e), "ts": now}
                raise
            df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
            df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        cache[key] = {"df": df.copy(), "ts": time.monotonic()}
        return df.copy()

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
        """Cat qty theo precision + min/max amount cua san.

        (12/10) Them kep MAX: truoc day chi kep min nen cap co `maxQty` nho
        (vd 1000PEPE/1000BONK...) bi san tra `-4005 Quantity greater than max
        quantity` -> mat co hoi vao lenh + log on. Kep ve max la AN TOAN hon
        (vi the nho hon du dinh = rui ro thap hon, khong bao gio lon hon).
        """
        src = self._client if self._client is not None else self._public
        if src is None:
            return round(qty, 6)
        try:
            markets = src.load_markets()
            m = markets.get(symbol)
            if not m:
                return round(qty, 6)
            q = float(src.amount_to_precision(symbol, qty))
            lim = ((m.get("limits") or {}).get("amount") or {})
            max_amt = lim.get("max")
            if max_amt and q > float(max_amt):
                q = float(src.amount_to_precision(symbol, float(max_amt)))
            min_amt = lim.get("min")
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

    def set_margin_mode(self, symbol: str, mode: str = "ISOLATED") -> bool:
        """Dat margin type cho 1 cap (ISOLATED/CROSS) — goi NGAY TRUOC khi vao lenh.

        (16/10) Vi sao: hoi dong (phieu VETO cua `qwen3.7-plus`) canh bao tai khoan LIVE
        chi ~41 USDT ma dang co vi the **CROSS** do NGUOI DUNG mo (`BTW`) => vi the do
        **chieu margin chung** voi vi the cua bot, trong khi phep tinh rui ro cua bot
        khong biet no ton tai. Isolated tach margin tung vi the => vi the nguoi dung
        khong the keo vi the cua bot vao thanh ly (va nguoc lai).

        LUU Y: Binance CHI cho doi khi cap do KHONG con vi the va KHONG con lenh cho =>
        vi vay phai goi luc cap con phang (ngay truoc lenh vao). `-4046` = dang dung roi.
        KHONG nem loi (fail-open): khong doi duoc thi bot van vao lenh nhu cu.
        """
        mode = str(mode or "").strip().upper()
        if mode not in ("ISOLATED", "CROSS"):
            return False
        if self._client is None or self.dry_run:
            return False
        try:
            self._client.set_margin_mode(mode.lower(), symbol)
            return True
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "-4046" in msg or "No need to change" in msg:
                return True                       # da o dung che do mong muon
            return False

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
        """Dong vi the bang lenh MARKET.

        (20/10) `-2022 ReduceOnly Order is rejected` — DO THAT tren API THAT:

          1. `reduceOnly=True` MARKET bi tu choi **VO DIEU KIEN** (ca khi qty=1 tren vi the
             31 hop dong) ⇒ day la ly do that cua "hang chuc lan -2022/ngay" (20/10:
             **157 lan**, 13 lan `monitor ... failed` ⇒ **kill-switch TRIP oan** "7
             consecutive API errors" luc 09:06, roi `_flatten` dong 16 vi the ma KHONG
             dong duoc vi the nao ⇒ so sach sach trong khi san van giu 16 vi the).
          2. `closePosition=true` cung KHONG dung duoc cho MARKET: `-4136 Target strategy
             invalid for orderType MARKET,closePosition true`.
          3. Cach DUY NHAT dong duoc: lenh MARKET **khong `reduceOnly`** voi qty DUNG BANG
             vi the that (do lai tu san) — da kiem chung: FILLED, vi the 31 -> 0.
          4. Neu vi the da ve 0 (SL/TP tren san khop TRUOC khi bot kip dong) ⇒ `-2022`
             va day **khong phai loi**: tra `already_closed` (coi nhu DA DONG).

        Vi vay: thu `reduceOnly` truoc (an toan nhat, dung duoc o moi truong cho phep);
        gap `-2022` ⇒ chuyen sang `_close_exact()` (qty lay TU SAN, khong reduceOnly, va
        DOC LAI sau khi dong de bat truong hop vi the lat chieu).
        """
        side = "sell" if direction == "LONG" else "buy"
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "side": side, "qty": qty, "dry_run": True}
        ps = self._pos_side(direction)
        params: dict = {"newClientOrderId": cid or _cid("close")}
        if ps:
            params.update(ps)          # HEDGE: positionSide thay cho reduceOnly
        elif not self._ro_market_rejected:
            params["reduceOnly"] = True
        else:
            # Da biet san tu choi `reduceOnly` cho MARKET (memo trong phien) -> di thang
            # duong "qty chinh xac", khong ton 1 request chac chan that bai moi lan dong.
            return self._close_exact(symbol, direction, side, qty, ps, None)
        try:
            return self._client.create_market_order(symbol, side, qty, params=params)
        except Exception as e:  # noqa: BLE001
            if not is_reduce_only_rejected(e):
                raise
            self._ro_market_rejected = True
            return self._close_exact(symbol, direction, side, qty, ps, e)

    def _close_exact(self, symbol: str, direction: str, side: str, qty: float,
                     ps: dict, err) -> dict:
        """Dong vi the khi `reduceOnly` khong dung duoc (hoac vua bi tu choi `-2022`).

        AN TOAN (vi sao khong the "lat chieu"): qty lay **tu san** (`position_qty` theo
        DUNG phia) va `q2 = min(quantize(qty_san), qty_yeu_cau)` — lenh chi co the GIAM
        vi the, khong bao gio lon hon vi the dang co. Sau khi gui, DOC LAI:
        `left_qty` > 0 ⇒ bao con du (so sach lech); phia KIA co vi the ⇒ `flipped`
        (SL dong dung luc gui ⇒ lenh mo nguoc chieu) — vong `adopt` ke tiep se nhan va
        arm bao ve, KHONG tu dong ban tiep (tranh "ping-pong" lenh).
        """
        left = self.position_qty(symbol, direction=direction)
        if left is None:
            raise err if err is not None else RuntimeError(
                "khong doc duoc vi the %s -> khong doan de dong" % symbol)
        if left <= 0:
            return {"symbol": symbol, "side": side, "qty": qty,
                    "already_closed": True, "left_qty": left,
                    "reason": str(err)[:200] if err is not None else ""}
        want = min(float(left), float(qty))
        q2 = self.quantize_qty(symbol, want) or want
        if q2 > want:
            q2 = want                  # khong bao gio gui lon hon y dinh/vi the
        if q2 <= 0:
            raise err if err is not None else RuntimeError("qty dong <= 0 cho %s" % symbol)
        params = {"newClientOrderId": _cid("clr")}
        params.update(ps)
        out = self._client.create_market_order(symbol, side, q2, params=params)
        res = dict(out) if isinstance(out, dict) else {"order": out}
        after = self.position_qty(symbol, direction=direction)
        res.update({"qty": q2, "closed_without_reduce_only": True, "left_qty": after,
                    "reduce_only_error": str(err)[:200] if err is not None else ""})
        if after is None:
            res["verify_failed"] = True
        elif after > 0:
            res["left_over"] = after
        # Vi the LAT CHIEU chi co the xay ra o ONE-WAY (HEDGE: lenh co `positionSide`
        # chi tac dong len DUNG phia, khong the lat). Khi do phia KIA co vi the ⇒ lenh
        # cua ta da mo nguoc chieu (SL khop dung luc gui) ⇒ bao DONG.
        if not self.hedge_mode() and (after is None or after <= 0):
            other = "SHORT" if str(direction).upper() == "LONG" else "LONG"
            opp = self.position_qty(symbol, direction=other)
            if opp:
                res["flipped"] = other
                res["flipped_qty"] = opp
        return res

    # ---- P0-1/P0-5: doc trang thai THAT tren san -------------------------------

    def cancel_symbol_orders(self, symbol: str) -> dict:
        """Huy MOI lenh dang treo cua symbol (best-effort, khong nem loi).

        (12/10) Huy CA lenh dieu kien o Algo Order API. Truoc day chi goi
        `cancel_all_orders` (endpoint lenh THUONG) -> lenh SL/TP nam o algo
        KHONG BAO GIO duoc huy: vi the dong xong van con STOP/TP treo, co the
        kich hoat va dong/mo nham vi the sau nay.
        """
        if self._client is None or self.dry_run:
            return {"symbol": symbol, "cancelled": 0, "dry_run": True}
        n = 0
        err = None
        try:
            res = self._client.cancel_all_orders(symbol)
            n += len(res) if isinstance(res, list) else 1
        except Exception as e:  # noqa: BLE001
            err = str(e)[:200]
        n_algo, aerr = self._cancel_algo(symbol)
        out = {"symbol": symbol, "cancelled": n + n_algo, "cancelled_algo": n_algo}
        if err:
            out["error"] = err
        if aerr:
            out["error_algo"] = aerr
        return out

    def _cancel_algo(self, symbol: str) -> tuple:
        """Huy lenh dieu kien dang treo cua 1 symbol. Tra (so lenh, loi)."""
        fn = getattr(self._client, "fapiPrivateDeleteAlgoOpenOrders", None)
        if fn is None:
            return 0, None
        try:
            res = fn({"symbol": to_raw_symbol(symbol)})
            n = len(res) if isinstance(res, list) else (1 if res else 0)
            return n, None
        except Exception as e:  # noqa: BLE001
            return 0, str(e)[:200]

    def algo_orders(self, symbol: str | None = None) -> list:
        """Lenh cho DIEU KIEN dang treo (Algo Order API `/fapi/v1/algoOrder`).

        Vi sao can (12/10): Binance chuyen lenh dieu kien sang Algo Order API.
        ccxt `fetch_open_orders()` chi tra lenh THUONG -> tra `[]` du tai khoan
        dang co hang tram lenh SL/TP treo. Hau qua THAT (do duoc 12/10):
        LIVE co **200** lenh algo (TESTNET 100) trong khi `fetch_open_orders`
        bao 0 -> bot tuong "chua co bao ve" nen RE-ARM moi 60s
        (`cancel_first=False`) => tich tu trung lap, cham tran stop-order =>
        `-4045` => khong dat duoc bao ve MOI nua.

        Tra dict da chuan hoa: id/symbol(ccxt)/type/stopPrice/clientOrderId/algo/ts.
        """
        out: list = []
        if self._client is None or self.dry_run:
            return out
        fn = getattr(self._client, "fapiPrivateGetOpenAlgoOrders", None)
        if fn is None:
            return out
        try:
            params = {"symbol": to_raw_symbol(symbol)} if symbol else {}
            for o in (fn(params) or []):
                st = str((o or {}).get("algoStatus") or "NEW").upper()
                if st not in ("NEW", "WORKING", "PENDING", ""):
                    continue          # da huy/khop -> khong tinh la dang treo
                out.append({"id": o.get("algoId"),
                            "symbol": to_ccxt_symbol(o.get("symbol")),
                            "type": o.get("orderType") or o.get("algoType") or "",
                            "stopPrice": o.get("triggerPrice"),
                            "clientOrderId": o.get("clientAlgoId"),
                            "algo": True,
                            "ts": o.get("bookTime") or o.get("time") or 0})
        except Exception as e:  # noqa: BLE001
            self.last_error = "algoOrders: %s" % str(e)[:200]
        return out

    def fetch_positions(self, symbols=None) -> list:
        """Vi the dang mo THAT tren san (ccxt). Loi/dry_run -> [] (khong suy dien)."""
        if self._client is None or self.dry_run:
            return []
        try:
            return list(self._client.fetch_positions(symbols) or [])
        except Exception:
            return []

    def position_qty(self, symbol: str, direction: str | None = None) -> float | None:
        """So hop dong dang mo THUC TE. None = khong doc duoc (khac 0.0 = da dong).

        `direction` (20/10): tai khoan HEDGE co **2 dong LONG/SHORT cho CUNG symbol** —
        khong chi dinh phia thi "dong dau tien khop symbol" co the la **phia KIA**.
        Ket luan sai phia ("vi the da dong") => bot xoa vi the khoi so sach trong khi
        san van giu ⇒ **vi the mo coi khong SL/TP**. Vi vay moi cho can ket luan
        "da dong hay chua" PHAI truyen `direction`.

        Tra None khi: khong doc duoc (mang loi / du lieu hong) HOAC khong the ket luan
        phia (ONE-WAY ma dong tra ve LECH phia). Tra 0.0 khi san xac nhan khong con
        vi the phia do.
        """
        if self._client is None or self.dry_run:
            return None
        want = str(direction).upper() if direction else None
        try:
            rows = [p for p in (self._client.fetch_positions([symbol]) or [])
                    if str((p or {}).get("symbol")) == symbol]
        except Exception:  # noqa: BLE001
            return None
        hedge = self.hedge_mode()
        unknown = False
        ambiguous = False
        for p in rows:
            side = _row_side(p)
            if side is None:
                unknown = True
                continue
            if want is None or side == want:
                return _row_qty(p)
            if not hedge:
                # ONE-WAY: chi co 1 vi the cho 1 cap -> dong lech phia la bat thuong.
                ambiguous = True
        if want is None:
            return None if unknown else 0.0
        if ambiguous or unknown:
            return None
        return 0.0

    def fetch_protection(self, symbol: str) -> dict:
        """SL/TP dang TREO tren san -> {'sl': float|None, 'tp': float|None}.

        Dung khi khoi dong lai: biet vi the con duoc bao ve hay khong.

        (12/10) Doc CA lenh dieu kien o Algo Order API. Truoc day chi doc
        `fetch_open_orders` (lenh thuong) -> luon thay "thieu bao ve" du dang co
        lenh SL/TP treo => `_rearm_missing` dat lai moi 60s => tich tu 200 lenh
        trung tren LIVE (do duoc 12/10) => cham tran stop-order (`-4045`).
        """
        out: dict = {"sl": None, "tp": None}
        if self._client is None or self.dry_run:
            return out
        orders: list = []
        try:
            orders.extend(self._client.fetch_open_orders(symbol) or [])
        except Exception:  # noqa: BLE001
            pass
        orders.extend(self.algo_orders(symbol))
        for o in orders:
            t = str((o or {}).get("type") or "")
            px = (o.get("stopPrice") or (o.get("info") or {}).get("stopPrice")
                  or (o.get("info") or {}).get("triggerPrice"))
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
        return out

