"""Composite Alpha Score + market ranking (Single Best Setup)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Candidate:
    symbol: str
    tech_score: float
    sentiment: float
    atr: float
    close: float
    alpha: float = 0.0
    direction: str = "FLAT"


def composite_alpha(tech: float, sent: float, w_tech: float = 0.65,
                    w_sent: float = 0.35) -> float:
    total = w_tech + w_sent
    w_tech, w_sent = w_tech / total, w_sent / total
    return round(max(-1.0, min(1.0, w_tech * tech + w_sent * sent)), 4)


def rank_markets(candidates: "list[Candidate]", w_tech: float = 0.65,
                 w_sent: float = 0.35, min_score: float = 0.35,
                 min_edge: float = 0.10) -> dict:
    for c in candidates:
        c.alpha = composite_alpha(c.tech_score, c.sentiment, w_tech, w_sent)
        c.direction = "LONG" if c.alpha > 0 else ("SHORT" if c.alpha < 0 else "FLAT")
    ranked = sorted(candidates, key=lambda c: abs(c.alpha), reverse=True)
    if not ranked:
        return {"action": "WAIT", "reason": "no candidates", "ranked": []}
    best = ranked[0]
    if abs(best.alpha) < min_score:
        return {"action": "WAIT", "reason": "best below min", "symbol": None,
                "alpha": best.alpha, "ranked": ranked}
    if len(ranked) > 1 and (abs(best.alpha) - abs(ranked[1].alpha)) < min_edge:
        return {"action": "WAIT", "reason": "ambiguous edge", "symbol": None,
                "alpha": best.alpha, "ranked": ranked}
    if best.alpha == 0:
        return {"action": "WAIT", "reason": "flat alpha", "ranked": ranked}
    return {"action": best.direction, "symbol": best.symbol, "alpha": best.alpha,
            "candidate": best, "ranked": ranked}


def sentiment_veto(direction: str, sentiment: float,
                   block_long_below: float = -0.5,
                   block_short_above: float = 0.5):
    if direction == "LONG" and sentiment <= block_long_below:
        return f"macro FUD {sentiment} blocks LONG"
    if direction == "SHORT" and sentiment >= block_short_above:
        return f"stimulus {sentiment} blocks SHORT"
    return None


class MarketRanker:
    def __init__(self, pairs=None, technical_weight: float = 0.6,
                 sentiment_weight: float = 0.4):
        self.pairs = pairs or ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
        self.technical_weight = technical_weight
        self.sentiment_weight = sentiment_weight

    def calculate_composite_score(self, technical_scores: Dict[str, float],
                                  sentiment_scores: Dict[str, float]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for pair in self.pairs:
            if pair in technical_scores or pair in sentiment_scores:
                out[pair] = composite_alpha(technical_scores.get(pair, 0.0),
                                            sentiment_scores.get(pair, 0.0),
                                            self.technical_weight, self.sentiment_weight)
        return out

    def rank_pairs(self, composite_scores: Dict[str, float]) -> Tuple:
        if not composite_scores:
            return None, None, 0.0
        ranked = sorted(composite_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        top_pair, top_score = ranked[0]
        direction = "LONG" if top_score > 0 else "SHORT"
        return top_pair, direction, abs(top_score) * 100.0
