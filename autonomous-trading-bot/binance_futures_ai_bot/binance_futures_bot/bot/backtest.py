"""
Backtest đơn-cặp trên dữ liệu lịch sử CÔNG KHAI của Binance Futures — KHÔNG
cần API key (dùng endpoint public /fapi/v1/klines).

Cố tình dùng lại NGUYÊN VẸN compute_technical_score() / evaluate_signal() /
RiskManager từ chính package bot thật, để kết quả backtest phản ánh đúng
logic sẽ chạy live — tránh lỗi kinh điển "backtest một kiểu, live một kiểu".

GIỚI HẠN QUAN TRỌNG (đọc trước khi tin số liệu):
  1. news_score luôn = 0 (trung lập) — không có nguồn dữ liệu tin tức lịch
     sử miễn phí đủ tốt để mô phỏng lùi thời gian. Kết quả phản ánh HIỆU
     SUẤT THUẦN PHÂN TÍCH KỸ THUẬT, chưa tính phần tin tức thật.
  2. Không mô phỏng funding rate (phí 8h/lần) — chỉ có phí giao dịch ước
     lượng qua --fee-bps. Với lệnh giữ qua nhiều chu kỳ funding, PF thật
     sẽ thấp hơn số backtest báo ra.
  3. Đơn giản hoá intrabar: nếu cả SL và TP cùng nằm trong biên độ 1 nến,
     giả định SL bị chạm trước (kịch bản an toàn/thận trọng hơn). Nến vừa
     mở lệnh chưa được kiểm tra SL/TP ngay trong chính nến đó.
  4. Hiệu suất quá khứ KHÔNG đảm bảo cho tương lai — đây là công cụ để
     hiểu cơ chế và so sánh tương đối giữa các cấu hình, không phải lời
     hứa hẹn lợi nhuận.

Chạy:
    python -m bot.backtest --symbol BTCUSDT --days 180
    python -m bot.backtest --symbol BTCUSDT --days 180 --sweep
"""
import argparse
import copy
from datetime import datetime, timezone

import requests

from bot.config_loader import load_config
from bot.indicators import compute_technical_score, klines_to_dataframe
from bot.risk_manager import RiskManager
from bot.signal_engine import evaluate_signal

BINANCE_FAPI_KLINES = "https://fapi.binance.com/fapi/v1/klines"
STARTING_EQUITY = 10_000.0


def fetch_historical_klines(symbol: str, interval: str, days: int) -> list:
    """Lấy nến lịch sử từ endpoint CÔNG KHAI của Binance Futures (không cần
    API key) — tự động phân trang vì mỗi lần gọi tối đa 1500 nến."""
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = end_time - days * 24 * 60 * 60 * 1000
    all_klines = []
    cursor = start_time
    while cursor < end_time:
        resp = requests.get(
            BINANCE_FAPI_KLINES,
            params={"symbol": symbol, "interval": interval, "startTime": cursor, "limit": 1500},
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_klines.extend(batch)
        cursor = batch[-1][0] + 1  # tiếp sau open_time của nến cuối cùng vừa lấy
        if len(batch) < 1500:
            break
    return all_klines


def run_backtest(symbol: str, cfg: dict, klines: list, fee_bps: float = 5.0) -> dict:
    """Chạy backtest đơn-cặp. Trả về dict thống kê từ summarize()."""
    lookback = cfg["lookback_candles"]
    risk = RiskManager(cfg["risk"])
    equity = STARTING_EQUITY
    equity_curve = [equity]
    trades = []
    position = None  # dict: side, entry, sl, tp, qty

    if len(klines) < lookback + 2:
        return summarize([], equity_curve, symbol)

    for i in range(lookback - 1, len(klines) - 1):
        window = klines[i - lookback + 1: i + 1]  # đúng `lookback` nến, giống live get_klines(limit=lookback)
        df = klines_to_dataframe(window)
        tech = compute_technical_score(df, cfg["indicators"])
        signal = evaluate_signal(symbol, tech, 0.0, cfg["signal"])  # news_score=0, xem giới hạn ở đầu file

        next_candle = klines[i + 1]
        next_open = float(next_candle[1])
        next_high = float(next_candle[2])
        next_low = float(next_candle[3])

        if position is not None:
            side, entry, sl, tp, qty = (
                position["side"], position["entry"], position["sl"], position["tp"], position["qty"],
            )
            exit_price, reason = None, None
            hit_sl = (next_low <= sl) if side == "LONG" else (next_high >= sl)
            hit_tp = (next_high >= tp) if side == "LONG" else (next_low <= tp)

            if hit_sl:  # ưu tiên SL nếu cả 2 cùng nằm trong 1 nến -> giả định thận trọng
                exit_price, reason = sl, "SL"
            elif hit_tp:
                exit_price, reason = tp, "TP"
            elif (side == "LONG" and signal.action == "SHORT") or (side == "SHORT" and signal.action == "LONG"):
                exit_price, reason = next_open, "REVERSAL"

            if exit_price is not None:
                pnl = (exit_price - entry) * qty if side == "LONG" else (entry - exit_price) * qty
                fee = (abs(entry * qty) + abs(exit_price * qty)) * (fee_bps / 10_000.0)
                pnl -= fee
                equity += pnl
                trades.append({"side": side, "entry": entry, "exit": exit_price, "pnl": pnl, "reason": reason})
                equity_curve.append(equity)
                position = None
            continue  # đã có vị thế trong nến này -> không mở thêm lệnh mới cùng lúc

        if signal.action in ("LONG", "SHORT"):
            sl, tp = risk.calc_sl_tp(signal.action, next_open, tech["atr"])
            qty = risk.calc_position_size(equity, next_open, sl)
            if qty > 0:
                position = {"side": signal.action, "entry": next_open, "sl": sl, "tp": tp, "qty": qty}

    return summarize(trades, equity_curve, symbol)


def summarize(trades: list, equity_curve: list, symbol: str = "") -> dict:
    if not trades:
        return {
            "symbol": symbol, "n_trades": 0, "win_rate_pct": 0.0, "profit_factor": 0.0,
            "total_return_pct": 0.0, "max_drawdown_pct": 0.0, "n_long": 0, "n_short": 0,
            "n_sl": 0, "n_tp": 0, "n_reversal": 0,
        }

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    win_rate = len(wins) / len(trades)
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        if peak > 0:
            max_dd = max(max_dd, (peak - e) / peak * 100)

    return {
        "symbol": symbol,
        "n_trades": len(trades),
        "win_rate_pct": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else float("inf"),
        "total_return_pct": round((equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_win": round(gross_profit / len(wins), 2) if wins else 0.0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0.0,
        "n_long": sum(1 for t in trades if t["side"] == "LONG"),
        "n_short": sum(1 for t in trades if t["side"] == "SHORT"),
        "n_sl": sum(1 for t in trades if t["reason"] == "SL"),
        "n_tp": sum(1 for t in trades if t["reason"] == "TP"),
        "n_reversal": sum(1 for t in trades if t["reason"] == "REVERSAL"),
    }


def sweep(symbol: str, base_cfg: dict, klines: list, fee_bps: float) -> list:
    """Quét lưới (threshold, sl_atr_multiplier, tp_atr_multiplier) và chạy
    backtest cho từng bộ, để tìm cấu hình đạt tiêu chí mong muốn."""
    thresholds = [0.25, 0.35, 0.45]
    sl_tp_pairs = [(1.0, 1.5), (1.5, 2.25), (1.5, 3.0), (1.5, 3.75), (2.0, 4.0)]

    results = []
    for threshold in thresholds:
        for sl_mult, tp_mult in sl_tp_pairs:
            cfg = copy.deepcopy(base_cfg)
            cfg["signal"]["long_threshold"] = threshold
            cfg["signal"]["short_threshold"] = -threshold
            cfg["risk"]["sl_atr_multiplier"] = sl_mult
            cfg["risk"]["tp_atr_multiplier"] = tp_mult

            r = run_backtest(symbol, cfg, klines, fee_bps=fee_bps)
            r.update({"threshold": threshold, "rr": round(tp_mult / sl_mult, 2)})
            results.append(r)
    return results


def _print_result(r: dict):
    print(f"\n=== KẾT QUẢ BACKTEST {r['symbol']} ===")
    print(f"Số lệnh: {r['n_trades']}  (LONG {r.get('n_long', 0)} / SHORT {r.get('n_short', 0)})")
    print(f"Thoát lệnh: SL={r.get('n_sl', 0)}  TP={r.get('n_tp', 0)}  Đảo tín hiệu={r.get('n_reversal', 0)}")
    print(f"Win-rate: {r['win_rate_pct']}%")
    print(f"Profit Factor: {r['profit_factor']}")
    print(f"Tổng lợi nhuận: {r['total_return_pct']}%")
    print(f"Max drawdown: {r['max_drawdown_pct']}%")
    if r["n_trades"] > 0:
        print(f"Lãi TB/lệnh thắng: {r['avg_win']} | Lỗ TB/lệnh thua: {r['avg_loss']}")


def main():
    parser = argparse.ArgumentParser(description="Backtest đơn-cặp cho bot Binance Futures")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--fee-bps", type=float, default=5.0, help="Phí round-trip ước tính (bps, mặc định 5 = 0.05%%)")
    parser.add_argument("--sweep", action="store_true", help="Quét lưới threshold/R:R thay vì chạy 1 cấu hình")
    parser.add_argument("--min-trades", type=int, default=30, help="Số lệnh tối thiểu để coi kết quả sweep đáng tin")
    args = parser.parse_args()

    cfg = load_config()
    print(f"Đang tải dữ liệu lịch sử {args.symbol} ({args.days} ngày, khung {cfg['timeframe']})...")
    klines = fetch_historical_klines(args.symbol, cfg["timeframe"], args.days)
    print(f"Đã tải {len(klines)} nến.")

    if not args.sweep:
        result = run_backtest(args.symbol, cfg, klines, fee_bps=args.fee_bps)
        _print_result(result)
        return

    print("Đang quét lưới cấu hình (threshold x SL/TP multiplier)...")
    results = sweep(args.symbol, cfg, klines, fee_bps=args.fee_bps)

    print(f"\n{'threshold':>9} {'R:R':>5} {'trades':>7} {'win%':>7} {'PF':>7} {'return%':>9} {'maxDD%':>8}  đạt tiêu chí?")
    print("-" * 90)
    for r in sorted(results, key=lambda x: x["profit_factor"] if x["profit_factor"] != float("inf") else -1, reverse=True):
        meets = (
            r["n_trades"] >= args.min_trades
            and r["win_rate_pct"] >= 35.0
            and r["profit_factor"] >= 1.0
        )
        flag = "✅" if meets else ("⚠️ ít mẫu" if r["n_trades"] < args.min_trades else "❌")
        pf_str = "inf" if r["profit_factor"] == float("inf") else f"{r['profit_factor']:.2f}"
        print(
            f"{r['threshold']:>9} {r['rr']:>5} {r['n_trades']:>7} {r['win_rate_pct']:>7.1f} "
            f"{pf_str:>7} {r['total_return_pct']:>9.1f} {r['max_drawdown_pct']:>8.1f}  {flag}"
        )
    print(f"\n(⚠️ ít mẫu = dưới {args.min_trades} lệnh, số liệu chưa đủ tin cậy thống kê)")


if __name__ == "__main__":
    main()
