"""Gui thong bao Telegram (OPEN/CLOSE/ERROR/KILL). Khong co token/chat -> im lang."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger("notify")
_API = "https://api.telegram.org/bot{token}/{method}"


def send(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id or not text:
        return False
    try:
        r = requests.post(_API.format(token=token, method="sendMessage"),
                          json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
        if not r.ok:
            log.warning("telegram fail: %s", r.text[:200])
            return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("telegram error: %s", e)
        return False


def fmt_open(symbol: str, direction: str, qty: float, entry: float, sl: float,
             tp: float, alpha: float, order_id=None, extra: str = "") -> str:
    emoji = "\U0001f7e2 LONG" if direction == "LONG" else "\U0001f534 SHORT"
    return (f"{emoji} {symbol}\nqty={qty} entry={entry} SL={sl} TP={tp}\n"
            f"alpha={alpha} order={order_id}{extra}")


def fmt_close(symbol: str, reason: str) -> str:
    return f"\U0001f522 CLOSE {symbol}: {reason}"


def fmt_kill(reason: str) -> str:
    return f"\u26d4\ufe0f KILL-SWITCH: {reason}"
