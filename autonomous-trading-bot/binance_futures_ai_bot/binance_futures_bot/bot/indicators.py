"""
Tính toán các chỉ báo phân tích kỹ thuật và tổng hợp thành một điểm số
trong khoảng [-1, 1]: dương = thiên về LONG (xu hướng tăng), âm = thiên
về SHORT (xu hướng giảm). Chỉ dùng pandas/numpy thuần — không phụ thuộc
TA-Lib (thư viện C hay gặp lỗi khi cài đặt) để package dễ cài trên mọi máy.
"""
import numpy as np
import pandas as pd

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def klines_to_dataframe(klines: list) -> pd.DataFrame:
    df = pd.DataFrame(klines, columns=KLINE_COLUMNS)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))

    # avg_loss = 0 là trường hợp hợp lệ (tăng liên tục, không có nến giảm
    # nào trong kỳ) -> RSI phải = 100, KHÔNG được rơi vào nhánh NaN/trung
    # lập phía dưới. Phải xử lý tách bạch với "chưa đủ dữ liệu".
    all_up = (avg_loss == 0) & (avg_gain > 0)
    flat = (avg_loss == 0) & (avg_gain == 0)  # giá đi ngang tuyệt đối
    result = result.where(~all_up, 100.0)
    result = result.where(~flat, 50.0)

    # Chỉ những điểm đầu chuỗi chưa đủ min_periods (NaN thật sự) mới được
    # coi là trung lập.
    return result.fillna(50)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series: pd.Series, period: int = 20, num_std: float = 2.0):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    return sma + num_std * std, sma, sma - num_std * std


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def compute_technical_score(df: pd.DataFrame, params: dict) -> dict:
    """Trả về dict: score tổng hợp [-1,1], atr hiện tại, giá hiện tại, và
    chi tiết từng thành phần (phục vụ log/debug)."""
    close = df["close"]

    ema_fast_s = ema(close, params["ema_fast"])
    ema_slow_s = ema(close, params["ema_slow"])
    price = float(close.iloc[-1])
    ema_fast_last, ema_slow_last = float(ema_fast_s.iloc[-1]), float(ema_slow_s.iloc[-1])

    # 1) Điểm xu hướng: vị trí giá so với 2 đường EMA nhanh/chậm
    if price > ema_fast_last > ema_slow_last:
        trend_score = 1.0
    elif price < ema_fast_last < ema_slow_last:
        trend_score = -1.0
    elif price > ema_slow_last:
        trend_score = 0.4
    elif price < ema_slow_last:
        trend_score = -0.4
    else:
        trend_score = 0.0

    # 2) Điểm động lượng RSI — dùng làm tín hiệu XÁC NHẬN động lượng theo
    # hướng xu hướng (RSI>50 ủng hộ phe mua, RSI<50 ủng hộ phe bán), ánh xạ
    # tuyến tính quanh mốc 50. Cố tình KHÔNG coi "quá mua/quá bán" là tín
    # hiệu đảo chiều thuần tuý — nếu làm vậy, rsi_score sẽ mang dấu NGƯỢC
    # với trend_score đúng lúc xu hướng đang mạnh nhất (RSI cao là bình
    # thường trong 1 xu hướng tăng khoẻ), khiến 2 điểm tự triệt tiêu nhau
    # và bot gần như không bao giờ vào lệnh kể cả khi xu hướng rất rõ ràng.
    rsi_val = float(rsi(close, params["rsi_period"]).iloc[-1])
    rsi_score = (rsi_val - 50) / 50 * 0.6
    if rsi_val >= 85 or rsi_val <= 15:  # quá cực đoan -> giảm nhẹ, không đảo dấu
        rsi_score *= 0.5
    rsi_score = max(min(rsi_score, 0.6), -0.6)

    # 3) Điểm MACD (ưu tiên tín hiệu giao cắt mới nhất)
    _, _, hist = macd(close, params["macd_fast"], params["macd_slow"], params["macd_signal"])
    h_last, h_prev = float(hist.iloc[-1]), float(hist.iloc[-2])
    if h_last > 0 and h_prev <= 0:
        macd_score = 0.5
    elif h_last < 0 and h_prev >= 0:
        macd_score = -0.5
    else:
        macd_score = 0.25 if h_last > 0 else (-0.25 if h_last < 0 else 0.0)

    # 4) Điểm Bollinger Bands — dùng theo hướng "band walk": giá bám/vượt
    # dải trên trong xu hướng mạnh là tín hiệu TIẾP DIỄN (cùng lý do như
    # mục 2 — tránh ngược dấu với trend_score). Đây là một lựa chọn thiết
    # kế, không phải "đúng duy nhất": nếu muốn chiến lược mean-reversion
    # thuần tuý thay vì trend-following, hãy đảo dấu 2 khối này.
    upper, _, lower = bollinger_bands(close, params["bb_period"], params["bb_std"])
    if price >= float(upper.iloc[-1]):
        bb_score = 0.3
    elif price <= float(lower.iloc[-1]):
        bb_score = -0.3
    else:
        bb_score = 0.0

    atr_val = float(atr(df, params.get("atr_period", 14)).iloc[-1])

    weights = {"trend": 0.4, "rsi": 0.2, "macd": 0.25, "bb": 0.15}
    total = (
        trend_score * weights["trend"]
        + rsi_score * weights["rsi"]
        + macd_score * weights["macd"]
        + bb_score * weights["bb"]
    )
    total = max(min(total, 1.0), -1.0)

    return {
        "score": total,
        "atr": atr_val,
        "price": price,
        "details": {
            "trend_score": trend_score,
            "rsi_score": rsi_score,
            "rsi_value": rsi_val,
            "macd_score": macd_score,
            "bb_score": bb_score,
        },
    }
