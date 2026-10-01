"""Unit test thuần (không cần mạng/API key) cho module indicators.
Chạy: python -m pytest tests/ -v   hoặc   python tests/test_indicators.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.indicators import compute_technical_score, ema, rsi  # noqa: E402

INDICATOR_PARAMS = {
    "ema_fast": 50, "ema_slow": 200, "rsi_period": 14,
    "rsi_overbought": 70, "rsi_oversold": 30,
    "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    "bb_period": 20, "bb_std": 2.0, "atr_period": 14,
}


def test_ema_converges_to_constant_series():
    s = pd.Series([100.0] * 60)
    assert abs(ema(s, 20).iloc[-1] - 100.0) < 1e-6


def test_rsi_is_high_for_strong_uptrend():
    s = pd.Series(np.linspace(100, 200, 60))
    assert rsi(s, 14).iloc[-1] > 70


def test_rsi_is_low_for_strong_downtrend():
    s = pd.Series(np.linspace(200, 100, 60))
    assert rsi(s, 14).iloc[-1] < 30


def _make_fake_ohlcv(n=250, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1.0})


def test_compute_technical_score_range():
    df = _make_fake_ohlcv()
    result = compute_technical_score(df, INDICATOR_PARAMS)
    assert -1.0 <= result["score"] <= 1.0
    assert result["atr"] >= 0
    assert result["price"] > 0


def test_compute_technical_score_strong_uptrend_is_positive():
    n = 250
    close = np.linspace(100, 300, n)  # xu hướng tăng mạnh, liên tục
    df = pd.DataFrame({
        "open": close, "high": close + 1, "low": close - 1,
        "close": close, "volume": 1.0,
    })
    result = compute_technical_score(df, INDICATOR_PARAMS)
    assert result["score"] > 0, "Xu hướng tăng mạnh và liên tục phải cho điểm dương"


if __name__ == "__main__":
    test_ema_converges_to_constant_series()
    test_rsi_is_high_for_strong_uptrend()
    test_rsi_is_low_for_strong_downtrend()
    test_compute_technical_score_range()
    test_compute_technical_score_strong_uptrend_is_positive()
    print("Tất cả test PASSED ✅")
