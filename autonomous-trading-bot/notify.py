"""Gui thong bao Telegram (OPEN/CLOSE/ERROR/KILL). Khong co token/chat -> im lang."""
from __future__ import annotations

import logging
import re

import requests

log = logging.getLogger("notify")
_API = "https://api.telegram.org/bot{token}/{method}"
_TOKEN_RE = re.compile(r"/bot[0-9]+:[A-Za-z0-9_-]+")


def redact(text, token: str = "") -> str:
    """(15/11, B-054/F-05) Bo token khoi thong bao loi truoc khi ghi log.

    Vi sao: loi ket noi cua `requests`/`urllib3` chua NGUYEN URL dang goi
    (`.../bot<token>/sendMessage`) ⇒ chi can 1 lan timeout la token nam trong `logs/*.log`.
    """
    s = str(text)
    if token:
        s = s.replace(str(token), "<token>")
    return _TOKEN_RE.sub("/bot<token>", s)


def send(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id or not text:
        return False
    try:
        r = requests.post(_API.format(token=token, method="sendMessage"),
                          json={"chat_id": chat_id, "text": text[:4000]}, timeout=10)
        if not r.ok:
            log.warning("telegram fail: %s", redact(r.text[:200], token))
            return False
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("telegram error: %s", redact(e, token))
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
