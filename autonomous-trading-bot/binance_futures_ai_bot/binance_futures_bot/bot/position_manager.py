"""
Theo dõi trạng thái vị thế đang mở trên các cặp để đảm bảo KHÔNG có lệnh
chồng chéo (mỗi symbol chỉ 1 vị thế tại 1 thời điểm) và điều phối việc
xoay vòng đánh giá giữa các cặp. Luôn đồng bộ trực tiếp từ sàn (nguồn sự
thật duy nhất) thay vì tự suy đoán trạng thái nội bộ, để tránh lệch pha
nếu có can thiệp thủ công hoặc bot bị khởi động lại giữa chừng.
"""


class PositionManager:
    def __init__(self, symbols: list):
        self.symbols = symbols
        self._open = {}  # symbol -> dict thông tin vị thế

    def sync_from_exchange(self, exchange_client):
        self._open = {}
        for symbol in self.symbols:
            pos = exchange_client.get_open_position(symbol)
            if pos:
                self._open[symbol] = pos

    def has_position(self, symbol: str) -> bool:
        return symbol in self._open

    def get_position(self, symbol: str):
        return self._open.get(symbol)

    def open_symbols(self) -> list:
        return list(self._open.keys())

    def available_symbols(self, risk_manager) -> list:
        """Các symbol hiện KHÔNG có vị thế và KHÔNG trong cooldown -> đủ
        điều kiện được xem xét mở lệnh mới (đây là cơ chế đảm bảo lệnh
        không trùng nhau giữa các cặp xoay vòng)."""
        return [
            s for s in self.symbols
            if not self.has_position(s) and not risk_manager.in_cooldown(s)
        ]

    def free_slots(self, max_concurrent: int) -> int:
        return max(0, max_concurrent - len(self._open))
