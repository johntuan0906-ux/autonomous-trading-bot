"""Thông báo Telegram tuỳ chọn (không bắt buộc phải cấu hình)."""
import logging
import requests

logger = logging.getLogger("futures_bot.notifier")


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, text: str):
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
        except requests.RequestException as e:
            logger.warning(f"Không gửi được thông báo Telegram: {e}")
