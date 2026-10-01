from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Direction = Literal["LONG", "SHORT"]

@dataclass
class Signal:
    symbol: str
    direction: Direction
    score: float
    technical: float
    news: float
    regime: float
    entry: float
    stop: float
    target: float
    reason: str

@dataclass
class Position:
    symbol: str
    direction: Direction
    qty: float
    entry: float
    stop: float
    target: float
