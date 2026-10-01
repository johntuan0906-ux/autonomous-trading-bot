"""
Đọc file .env (thông tin nhạy cảm) và config/config.yaml (tham số chiến lược),
gộp lại thành một dict cấu hình duy nhất cho toàn bộ bot.
"""
import os
import warnings
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


def load_config(config_path: str = None) -> dict:
    """Đọc .env + config.yaml, trả về dict cấu hình đầy đủ."""
    load_dotenv()

    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file cấu hình: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg["env"] = {
        "api_key": os.getenv("BINANCE_API_KEY", ""),
        "api_secret": os.getenv("BINANCE_API_SECRET", ""),
        "use_testnet": os.getenv("USE_TESTNET", "true").lower() == "true",
        "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
        "cryptopanic_api_key": os.getenv("CRYPTOPANIC_API_KEY", ""),
        "newsapi_api_key": os.getenv("NEWSAPI_API_KEY", ""),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    }

    _validate(cfg)
    return cfg


def _validate(cfg: dict) -> None:
    if not cfg["env"]["api_key"] or not cfg["env"]["api_secret"]:
        warnings.warn(
            "Chưa cấu hình BINANCE_API_KEY / BINANCE_API_SECRET trong .env — "
            "bot sẽ chỉ chạy được ở chế độ mô phỏng, không thể lấy dữ liệu thật từ Binance."
        )
    if not cfg.get("symbols"):
        raise ValueError("Danh sách 'symbols' trong config.yaml không được để trống.")
    if not (0 <= cfg["risk"]["risk_per_trade_pct"] <= 100):
        raise ValueError("risk_per_trade_pct phải nằm trong khoảng 0-100.")
