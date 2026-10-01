"""Unit test cho bot/backtest.py — kiểm chứng công thức win-rate/PF/drawdown
bằng dữ liệu tự tính tay (không cần mạng). Chạy: python -m pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.backtest import summarize  # noqa: E402


def _equity_curve(start, trades):
    curve = [start]
    e = start
    for t in trades:
        e += t["pnl"]
        curve.append(e)
    return curve


def test_summarize_matches_hand_calculated_pf_and_winrate():
    # 7 thắng (+200), 13 thua (-100) -> win-rate=35%, R:R=2:1
    # PF lý thuyết = (0.35*2)/(0.65*1) = 1400/1300 ≈ 1.0769
    trades = (
        [{"side": "LONG", "entry": 0, "exit": 0, "pnl": -100, "reason": "SL"} for _ in range(13)]
        + [{"side": "LONG", "entry": 0, "exit": 0, "pnl": 200, "reason": "TP"} for _ in range(7)]
    )
    equity = _equity_curve(10_000.0, trades)
    r = summarize(trades, equity, "TEST")

    assert r["n_trades"] == 20
    assert abs(r["win_rate_pct"] - 35.0) < 1e-9
    assert abs(r["profit_factor"] - round(1400 / 1300, 3)) < 1e-6
    assert r["n_sl"] == 13
    assert r["n_tp"] == 7


def test_summarize_drawdown_matches_hand_calculated():
    # 13 lệnh thua liên tiếp trước (đáy sâu nhất), rồi 7 lệnh thắng phục hồi
    # -> max drawdown phải đúng bằng (10000-8700)/10000 = 13%
    trades = (
        [{"side": "LONG", "entry": 0, "exit": 0, "pnl": -100, "reason": "SL"} for _ in range(13)]
        + [{"side": "LONG", "entry": 0, "exit": 0, "pnl": 200, "reason": "TP"} for _ in range(7)]
    )
    equity = _equity_curve(10_000.0, trades)
    r = summarize(trades, equity, "TEST")

    assert abs(r["max_drawdown_pct"] - 13.0) < 1e-6
    assert abs(r["total_return_pct"] - 1.0) < 1e-6


def test_summarize_all_wins_gives_infinite_pf_no_crash():
    trades = [{"side": "LONG", "entry": 0, "exit": 0, "pnl": 50, "reason": "TP"} for _ in range(5)]
    equity = _equity_curve(10_000.0, trades)
    r = summarize(trades, equity, "ALLWIN")
    assert r["profit_factor"] == float("inf")
    assert r["win_rate_pct"] == 100.0


def test_summarize_empty_trades_no_crash():
    r = summarize([], [10_000.0], "EMPTY")
    assert r["n_trades"] == 0
    assert r["profit_factor"] == 0.0


if __name__ == "__main__":
    test_summarize_matches_hand_calculated_pf_and_winrate()
    test_summarize_drawdown_matches_hand_calculated()
    test_summarize_all_wins_gives_infinite_pf_no_crash()
    test_summarize_empty_trades_no_crash()
    print("Tất cả test backtest PASSED ✅")
