"""Autonomous loop: scan -> score -> rank -> risk-size -> execute -> monitor."""
from __future__ import annotations

import logging
import time

from config import Settings
from exchange import BinanceFutures
from indicators import technical_score
from journal import log_trade
from portfolio import PortfolioManager, Position
from ranking import Candidate, rank_markets, sentiment_veto
from risk import KillSwitch, atr_levels, position_size
from sentiment import SentimentCache
from trade_mgmt import ManagedTrade, new_trade, manage_trade, trade_result

log = logging.getLogger("bot")
SENT_REVERSAL = 0.7


class TradingBot:
    def __init__(self, settings=None, exchange=None):
        self.cfg = settings or Settings()
        self.exchange = exchange or BinanceFutures(
            self.cfg.api_key, self.cfg.api_secret, self.cfg.testnet, self.cfg.dry_run)
        self.portfolio = PortfolioManager(self.cfg.max_positions, self.cfg.allow_hedge_opposite)
        self.kill = KillSwitch(self.cfg.max_daily_loss_pct, self.cfg.max_atr_pct,
                               self.cfg.max_consecutive_errors, self.cfg.balance_usdt)
        self.sentiment = SentimentCache(self.cfg.sentiment_cache_sec)
        self.balance = self.cfg.balance_usdt
        # P0-6: `balance` = tran size (BALANCE_USDT), `equity` = tai san THAT tren san.
        # DD/kill-switch PHAI dung `equity`, neu dung `balance` thi tran lo sai hoan toan.
        self.equity = self.cfg.balance_usdt
        self.managed: dict[str, ManagedTrade] = {}  # sym -> trang thai partial/BE/trail
        self.last_exits: dict[str, dict] = {}  # sym -> {reason, r, won, pnl} cho journal/learner

    def step(self, candles_provider=None) -> dict:
        if self.kill.tripped:
            return {"status": "KILLED", "reason": self.kill.reason}
        if self.kill.check(self.balance):
            self._flatten("kill-switch")
            return {"status": "KILLED", "reason": self.kill.reason}
        exit_res = self._monitor(candles_provider)
        if isinstance(exit_res, dict) and "_error" in exit_res:
            return {"status": "KILLED", "reason": exit_res["_error"]}
        return self._scan_and_maybe_open(candles_provider)

    def _monitor(self, candles_provider=None):
        """Tra dict {symbol: 'TP'|'SL'|'SENT'|'BE'|'PARTIAL'} cho cac lenh vua dong.

        Quan ly lenh dong (muc 12/16/18): chot 50% tai +1R, doi SL ve hoa von,
        trailing theo ATR — giup tang win-rate ma khong doi chien luoc vao lenh.
        """
        closed: dict[str, str] = {}
        for sym, pos in list(self.portfolio.positions.items()):
            try:
                price = self._price(sym, candles_provider)
                mt = self._managed_for(sym, pos)
                # Vi the 'bui' ton dong (notional < MIN_NOTIONAL_USDT): san tu choi
                # dong lenh nua -> coi nhu DA DONG (ghi journal + bo state). Khong lam
                # thi 'xac' vi the nam mai trong portfolio (SKIP_OPEN vinh vien) va `n`
                # trong journal ket -> khong bao gio dat moc 50 lenh cho LIVE.
                if self._is_dust(mt.qty, price):
                    log.warning("DUST %s qty=%g notional=%.2f < %.2f -> chot so + ghi CLOSE",
                                sym, mt.qty, mt.qty * price, self.cfg.min_notional_usdt)
                    self._dust_close(sym, pos, mt, price)
                    closed[sym] = "DUST"
                    continue
                atr_est = abs(mt.entry - mt.initial_sl) / max(self.cfg.sl_atr_mult, 1e-9)
                mg = manage_trade(mt, price, atr_est)
                act = mg["action"]

                if act == "PARTIAL" and mg["close_qty"] > 0:
                    q = self.exchange.quantize_qty(sym, mg["close_qty"])
                    if q > 0:
                        self.exchange.close_position(sym, pos.direction, q)
                    pos.qty = mt.qty
                    pos.sl = float(mg["new_sl"] or pos.sl)
                    # P0-5: qty da doi -> phai arm lai SL/TP theo qty CON LAI
                    # (stop cu van giu qty goc va co the dang ton 2-3 lenh chong nhau).
                    try:
                        self.exchange.stop_tp_orders(sym, pos.direction, pos.qty,
                                                     pos.sl, pos.tp, cid_prefix="part")
                    except Exception as e:  # noqa: BLE001
                        log.warning("re-arm SL/TP sau PARTIAL %s that bai: %s", sym, e)
                    log.info("PARTIAL %s qty=%s SL->%s (%s)", sym, q, pos.sl, mg["reason"])
                    # Sau partial, qty con lai co the roi xuong duoi minNotional ->
                    # chot so luon (neu khong: 'xac' lenh + journal thieu CLOSE).
                    if self._is_dust(mt.qty, price):
                        log.warning("DUST sau PARTIAL %s qty=%g -> chot so + ghi CLOSE",
                                    sym, mt.qty)
                        self._dust_close(sym, pos, mt, price)
                        closed[sym] = "DUST"
                    continue

                if act in ("BE", "TRAIL") and mg["new_sl"]:
                    pos.sl = float(mg["new_sl"])
                    try:
                        self.exchange.stop_tp_orders(sym, pos.direction, pos.qty,
                                                     pos.sl, pos.tp)
                    except Exception as e:  # noqa: BLE001
                        log.warning("re-arm SL %s failed: %s", sym, e)
                    log.info("%s %s SL->%s (%s)", act, sym, pos.sl, mg["reason"])
                    continue

                if act in ("EXIT_SL", "EXIT_TP"):
                    reason = "TP" if act == "EXIT_TP" else "SL"
                    res = trade_result(mt, reason, price)
                    # Ghi lai ket qua (R thuc) cho journal + thong ke strategy + kill-switch
                    self.last_exits[sym] = {"reason": reason, "r": res["r"],
                                            "won": res["won"], "pnl": res["pnl"],
                                            "partial": res.get("partial_done"),
                                            "mfe_r": res.get("mfe_r")}
                    if self.kill.register_close(bool(res["won"]), self.balance):
                        self._flatten("kill-switch: thua lien tiep")
                        return {"_error": self.kill.reason}
                    self._close(sym, f"{reason} @ {price} pnl={res['pnl']} R={res['r']}")
                    # Journal CLOSE (muc 17): ghi R/won/pnl -> monitor_report tinh WR/PF
                    log_trade(event="CLOSE", pair=sym, direction=mt.direction,
                              timeframe=self.cfg.timeframe, entry=mt.entry,
                              qty=mt.init_qty, exit_price=price, r=res["r"],
                              won=bool(res["won"]), pnl=res["pnl"], reason=reason,
                              partial=res.get("partial_done"), mfe_r=res.get("mfe_r"))
                    closed[sym] = "TP" if res["won"] else reason
                    continue

                s = self.sentiment.get(self.cfg.cryptopanic_token).score
                if (pos.direction == "LONG" and s <= -SENT_REVERSAL) or \
                   (pos.direction == "SHORT" and s >= SENT_REVERSAL):
                    self.last_exits[sym] = {"reason": "SENT", "r": 0.0, "won": False,
                                            "pnl": 0.0}
                    self._close(sym, f"sentiment reversal {s}")
                    log_trade(event="CLOSE", pair=sym, direction=pos.direction,
                              timeframe=self.cfg.timeframe, entry=pos.entry,
                              qty=pos.qty, exit_price=price, r=0.0, won=False,
                              pnl=0.0, reason="SENT")
                    closed[sym] = "SENT"
            except Exception as e:  # noqa: BLE001
                log.warning("monitor %s failed: %s", sym, e)
                if self.kill.register_error():
                    self._flatten("api errors")
                    return {"_error": "api errors"}
        return closed

    def _managed_for(self, sym: str, pos: Position) -> ManagedTrade:
        """Lay (hoac tao) trang thai quan ly lenh cho 1 vi the dang mo.

        P0-fix (2026-10-01): ban cu so sanh `abs(mt.entry - pos.entry) > 1e-12` —
        chi can entry lech float nhon (hoac san lam tron khac chut) la TAO TRADE MOI,
        mat sach `initial_sl`/`partial_done`/`booked_pnl`. Hau qua that: partial chay
        lai lan 2 -> dong het vi the (XRP/SOL/AVAX dong oan 19:53) va journal thieu
        dong CLOSE (`n` ket o 46/50 -> khong bao gio qua duoc cong LIVE).
        Moc 1R + trang thai chot loi CHI co trong state => phai uu tien state.
        """
        mt = self.managed.get(sym)
        if mt is None or str(mt.direction).upper() != str(pos.direction).upper():
            mt = new_trade(sym, pos.direction, pos.entry, pos.qty, pos.sl, pos.tp)
            self.managed[sym] = mt
        return mt

    def _is_dust(self, qty: float, price: float) -> bool:
        """True neu notional qua nho de san cho phep dat/dong lenh."""
        try:
            return 0.0 < float(qty) * float(price) < float(self.cfg.min_notional_usdt)
        except (TypeError, ValueError):
            return False

    def _dust_close(self, sym: str, pos, mt: ManagedTrade, price: float) -> None:
        """Chot mot vi the 'bui' (qty con lai < minNotional) nhu mot lan CLOSE that.

        Vi sao: sau partial/BE, qty con lai co the nho den muc san TU CHOI dong lenh
        -> 'xac' vi the 0.01 lot nam mai trong portfolio (SKIP_OPEN vinh vien) va
        journal KHONG bao gio co dong CLOSE cho lenh do (WR/PF sai + `n` ket).
        """
        res = trade_result(mt, "PARTIAL", price)
        self.last_exits[sym] = {"reason": "DUST", "r": res["r"], "won": res["won"],
                                "pnl": res["pnl"], "partial": res.get("partial_done"),
                                "mfe_r": res.get("mfe_r")}
        log_trade(event="CLOSE", pair=sym, direction=mt.direction,
                  timeframe=self.cfg.timeframe, entry=mt.entry, qty=mt.init_qty,
                  exit_price=price, r=res["r"], won=bool(res["won"]), pnl=res["pnl"],
                  reason="DUST", partial=res.get("partial_done"),
                  mfe_r=res.get("mfe_r"))
        self._close(sym, f"DUST qty={mt.qty:g} < minNotional @ {price}")

    def _scan_and_maybe_open(self, candles_provider=None) -> dict:
        cfg = self.cfg
        senti = self.sentiment.get(cfg.cryptopanic_token)
        cands: list[Candidate] = []
        for sym in cfg.symbols:
            try:
                if candles_provider:
                    df = candles_provider(sym)
                else:
                    df = self.exchange.fetch_ohlcv(sym, cfg.timeframe, cfg.ohlcv_limit)
                t = technical_score(df, cfg.atr_period)
                if self.kill.check(self.balance, t["atr_pct"]):
                    self._flatten("volatility kill-switch")
                    return {"status": "KILLED", "reason": self.kill.reason}
                cands.append(Candidate(sym, t["score"], senti.score, t["atr"], t["close"]))
            except Exception as e:  # noqa: BLE001
                log.warning("scan %s failed: %s", sym, e)
                if self.kill.register_error():
                    self._flatten("api errors")
                    return {"status": "KILLED", "reason": self.kill.reason}
        self.kill.reset_errors()
        if not cands:
            return {"status": "WAIT", "reason": "no data"}
        decision = rank_markets(cands, cfg.w_tech, cfg.w_sent,
                                cfg.min_alpha_score, cfg.min_edge)
        if decision["action"] == "WAIT":
            out = {"status": "WAIT"}
            out.update({k: v for k, v in decision.items() if k != "ranked"})
            return out
        direction, symbol = decision["action"], decision["symbol"]
        best: Candidate = decision["candidate"]
        veto = sentiment_veto(direction, senti.score, cfg.block_long_below, cfg.block_short_above)
        if veto:
            return {"status": "BLOCKED", "reason": veto, "symbol": symbol}
        ok, reason = self.portfolio.can_open(symbol, direction)
        if not ok:
            return {"status": "BLOCKED", "reason": reason, "symbol": symbol}
        # Dong bo balance that tu san (neu doc duoc) truoc khi size lenh.
        # Neu san = 0 ma cfg.balance > 0 -> bao loi ro rang thay vi -2019 kho hieu.
        live_bal = self.exchange.fetch_balance_usdt() if not cfg.dry_run else None
        if live_bal is not None:
            self.balance = live_bal
            self.equity = live_bal
            if live_bal <= 0:
                return {"status": "BLOCKED", "symbol": symbol, "direction": direction,
                        "reason": "vi demo futures = 0 USDT (nap faucet demo.binance.com -> Wallet/Faucet). "
                                  "Bot size theo BALANCE_USDT nhung san can margin that de khop."}
        lv = atr_levels(best.close, best.atr, direction, cfg.sl_atr_mult, cfg.tp_atr_mult)
        assert lv["rr"] >= 2.0 - 1e-9, "R:R violated"
        qty = position_size(self.balance, cfg.risk_per_trade_pct, lv["entry"], lv["sl"])
        qty = self.exchange.quantize_qty(symbol, qty)
        if qty <= 0:
            return {"status": "BLOCKED", "symbol": symbol,
                    "reason": "qty sau khi chuan hoa < min amount cua san (tang BALANCE/RISK hoac doi cap thanh khoan cao)"}
        # Margin uoc tinh = notional / leverage; chan truoc neu vuot balance.
        need_margin = (qty * lv["entry"]) / max(cfg.leverage, 1)
        if not cfg.dry_run and live_bal is not None and need_margin > live_bal:
            return {"status": "BLOCKED", "symbol": symbol, "direction": direction,
                    "qty": qty, "need_margin": round(need_margin, 2),
                    "reason": f"margin uoc tinh {need_margin:.2f} USDT > so du {live_bal:.2f} "
                              f"(giam LEVERAGE/RISK hoac nap them faucet)"}
        self.exchange.set_leverage(symbol, cfg.leverage)
        try:
            entry_res = self.exchange.market_entry(symbol, direction, qty)
            self.exchange.stop_tp_orders(symbol, direction, qty, lv["sl"], lv["tp"])
        except Exception as e:  # noqa: BLE001  (vd: -2019 margin, -4003 qty...)
            log.warning("order %s %s failed: %s", direction, symbol, e)
            # P0-4: loi mang co the xay ra SAU khi san da khop -> kiem tra vi the that
            # truoc khi ket luan that bai (neu khong vong sau se mo trung = gap doi risk).
            landed = self.exchange.position_qty(symbol)
            if landed:
                self.exchange.stop_tp_orders(symbol, direction, landed, lv["sl"], lv["tp"])
                self.portfolio.open(Position(symbol, direction, lv["entry"], landed,
                                            lv["sl"], lv["tp"]))
                log.warning("entry %s bao loi nhung vi the DA mo qty=%s -> ghi nhan",
                            symbol, landed)
                out = {"status": "OPENED", "symbol": symbol, "direction": direction,
                       "qty": landed, "recovered": True, "reason": str(e)[:200]}
                out.update(lv)
                return out
            return {"status": "ORDER_FAILED", "symbol": symbol, "direction": direction,
                    "qty": qty, "reason": str(e)[:300]}
        self.portfolio.open(Position(symbol, direction, lv["entry"], qty, lv["sl"], lv["tp"]))
        log.info("OPEN %s %s qty=%s SL=%s TP=%s alpha=%s", direction, symbol,
                 qty, lv["sl"], lv["tp"], best.alpha)
        out = {"status": "OPENED", "symbol": symbol, "direction": direction, "qty": qty}
        out.update(lv)
        out.update({"alpha": best.alpha, "entry_res": entry_res})
        return out

    def _price(self, symbol: str, candles_provider=None) -> float:
        if candles_provider:
            return float(candles_provider(symbol)["close"].iloc[-1])
        return self.exchange.last_price(symbol)

    def _close(self, symbol: str, reason: str) -> None:
        pos = self.portfolio.close(symbol)
        self.managed.pop(symbol, None)  # ket thuc chu ky quan ly partial/BE/trail
        if pos:
            try:
                self.exchange.close_position(symbol, pos.direction, pos.qty)
            except Exception as e:  # noqa: BLE001
                log.warning("close %s failed: %s", symbol, e)
            # P0-5: don sach lenh treo con lai — neu khong, STOP/TP cu se kich hoat
            # va dong nham vi the MOI mo sau do tren cung cap.
            try:
                self.exchange.cancel_symbol_orders(symbol)
            except Exception as e:  # noqa: BLE001
                log.warning("cancel orders %s failed: %s", symbol, e)
            log.info("CLOSE %s %s", symbol, reason)

    def _flatten(self, reason: str) -> None:
        for sym in list(self.portfolio.positions):
            self._close(sym, reason)

    def run_forever(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        log.info("Bot start dry_run=%s symbols=%s", self.cfg.dry_run, self.cfg.symbols)
        while not self.kill.tripped:
            try:
                log.info("step -> %s", self.step())
            except Exception as e:  # noqa: BLE001
                log.exception("loop error: %s", e)
                if self.kill.register_error():
                    self._flatten("fatal errors")
                    break
            time.sleep(self.cfg.poll_interval_sec)
        log.warning("STOPPED: %s", self.kill.reason)
