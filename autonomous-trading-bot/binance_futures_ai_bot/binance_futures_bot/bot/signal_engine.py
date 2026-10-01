"""
Kết hợp điểm phân tích kỹ thuật và điểm tin tức thành một tín hiệu giao
dịch duy nhất: LONG / SHORT / HOLD, kèm độ mạnh để so sánh giữa các cặp
khi xoay vòng (dùng cho việc xếp hạng ưu tiên lúc số lệnh mở đồng thời
bị giới hạn).
"""
from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    action: str            # "LONG" | "SHORT" | "HOLD"
    score: float             # điểm tổng hợp trong [-1, 1]
    technical_score: float
    news_score: float
    price: float
    atr: float


def evaluate_signal(symbol: str, tech: dict, news_score: float, cfg: dict) -> Signal:
    # Kết hợp dạng CỘNG, không phải trung bình có trọng số chuẩn hoá:
    # technical_weight mặc định = 1.0 (giữ nguyên điểm kỹ thuật), news_weight
    # là mức cộng/trừ thêm từ tin tức. Nhờ vậy khi chưa cấu hình API tin tức
    # (news_score luôn = 0, trung lập), composite = đúng bằng điểm kỹ thuật,
    # KHÔNG bị pha loãng — nếu dùng trung bình có trọng số kiểu
    # 0.6*tech + 0.4*0, một xu hướng kỹ thuật rõ ràng vẫn có thể không bao
    # giờ chạm ngưỡng vào lệnh chỉ vì thiếu tin tức.
    w_tech, w_news = cfg["technical_weight"], cfg["news_weight"]
    composite = max(min(w_tech * tech["score"] + w_news * news_score, 1.0), -1.0)

    if composite >= cfg["long_threshold"]:
        action = "LONG"
    elif composite <= cfg["short_threshold"]:
        action = "SHORT"
    else:
        action = "HOLD"

    return Signal(
        symbol=symbol, action=action, score=composite,
        technical_score=tech["score"], news_score=news_score,
        price=tech["price"], atr=tech["atr"],
    )


def rank_signals(signals: list) -> list:
    """So sánh & xếp hạng các symbol theo độ mạnh tín hiệu (giá trị tuyệt
    đối) — dùng khi nhiều cặp cùng phát tín hiệu nhưng số lệnh mở đồng
    thời bị giới hạn, ưu tiên tín hiệu mạnh nhất trước."""
    actionable = [s for s in signals if s.action != "HOLD"]
    return sorted(actionable, key=lambda s: abs(s.score), reverse=True)
