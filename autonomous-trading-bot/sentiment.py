"""Macro + crypto sentiment MULTI-SOURCE v2 (bao chi/kinh te/chinh tri/xung dot).

Nguon: CryptoPanic + CoinDesk + CoinTelegraph + FED + ECB + IMF + UN +
AlJazeera + GoogleNews(world/crypto) + GDELT. Tin moi weight cao (half-life 6h).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

try:
    import feedparser  # type: ignore
except Exception:  # pragma: no cover
    feedparser = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
    _VADER = SentimentIntensityAnalyzer()
except Exception:  # pragma: no cover
    _VADER = None

DEFAULT_RSS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.ecb.europa.eu/rss/press.html",
    "https://www.imf.org/en/News/rss",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    # them theo checklist user: Coinglass, Glassnode, TradingView crypto ideas
    "https://www.coinglass.com/rss/news",
    "https://insights.glassnode.com/rss/",
    "https://www.tradingview.com/feed/crypto/",
    # lich kinh te FOMC/CPI/NFP: Investing.com + ForexFactory (mien phi)
    "https://www.investing.com/rss/news_25.rss",
    "https://www.forexfactory.com/ff_calendar_thisweek.xml",
    "https://news.google.com/rss/search?q=war%20OR%20conflict%20OR%20FED%20rate&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=crypto%20OR%20bitcoin%20OR%20SEC&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=FOMC%20OR%20CPI%20OR%20NFP%20OR%20OPEC&hl=en-US&gl=US&ceid=US:en",
]

_BULLISH = ["etf approval", "rate cut", "dovish", "bullish", "adoption",
    "stimulus", "breakthrough", "surge", "rally", "approv", "easing",
    "ceasefire", "peace deal", "recovery", "jobs beat", "soft landing"]
_BEARISH = ["hack", "lawsuit", "sec crackdown", "ban", "rate hike", "hawkish",
    "fud", "crash", "plunge", "fraud", "bankrupt", "exploit", "war",
    "invasion", "airstrike", "missile", "sanctions", "coup", "terror",
    "embargo", "default", "recession", "oil shock", "nuclear"]
_URGENT = ["war", "invasion", "airstrike", "missile", "nuclear", "coup",
    "terror", "martial law", "default", "recession", "rate hike"]


@dataclass
class SentimentResult:
    score: float
    n_articles: int
    headlines: list
    source: str = "mixed"
    urgent_bearish: int = 0


def score_text(text: str) -> tuple:
    text = (text or "").strip()
    if not text:
        return 0.0, False
    t = text.lower()
    urgent = any(k in t for k in _URGENT) and any(k in t for k in _BEARISH)
    if _VADER is not None:
        s = float(_VADER.polarity_scores(text)["compound"])
    else:
        b = sum(1 for k in _BULLISH if k in t)
        x = sum(1 for k in _BEARISH if k in t)
        s = 0.0 if (b == 0 and x == 0) else (b - x) / max(b + x, 1)
    if urgent and s > -0.3:
        s = min(s, -0.5)
    return s, urgent


def _llm_score(texts: list) -> float | None:
    import os
    if os.getenv("USE_LLM_SENTIMENT", "false").lower() not in ("1", "true", "yes"):
        return None
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Score headlines -1..+1. Number only."},
                      {"role": "user", "content": "\n- ".join(texts[:20])}],
            max_tokens=10)
        return max(-1.0, min(1.0, float(resp.choices[0].message.content.strip())))
    except Exception:
        return None


def fetch_cryptopanic(token: str = "", limit: int = 20) -> list:
    if not token:
        return []
    try:
        r = requests.get("https://cryptopanic.com/api/v1/posts/",
            params={"auth_token": token, "public": "true", "kind": "news"}, timeout=10)
        r.raise_for_status()
        return [p.get("title", "") for p in r.json().get("results", [])[:limit] if p.get("title")]
    except Exception:
        return []
def _age_h(entry) -> float | None:
    for key in ("published_parsed", "updated_parsed"):
        try:
            ts = getattr(entry, key, None)
            if ts:
                dt = datetime(*ts[:6], tzinfo=timezone.utc)
                return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
        except Exception:
            continue
    return None


def fetch_rss(feeds: list | None = None, per_feed: int = 8) -> list:
    """Tra [(headline, weight)] — tin moi weight cao (half-life 6h)."""
    if feedparser is None:
        return []
    out: list = []
    for url in feeds or DEFAULT_RSS:
        try:
            parsed = feedparser.parse(url)
            for e in (parsed.entries or [])[:per_feed]:
                title = getattr(e, "title", "") or ""
                summary = re.sub(r"<[^>]+>", " ", getattr(e, "summary", "") or "")[:300]
                if not title:
                    continue
                age = _age_h(e)
                w = 0.5 ** (age / 6.0) if age is not None else 0.7
                out.append((f"{title}. {summary}".strip(), round(max(w, 0.15), 3)))
        except Exception:
            continue
    return out


def fetch_gdelt(limit: int = 15) -> list:
    """GDELT DOC API: xung dot/kinh te 24h qua, khong can key."""
    try:
        r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": "war OR conflict OR sanctions OR FED OR crypto",
                    "mode": "ArtList", "maxrecords": limit, "format": "json",
                    "sort": "DateDesc"}, timeout=12)
        r.raise_for_status()
        return [(a.get("title", ""), 1.0) for a in r.json().get("articles", []) if a.get("title")]
    except Exception:
        return []


class SentimentCache:
    def __init__(self, ttl_sec: int = 120):
        self.ttl = ttl_sec
        self._ts = 0.0
        self._value = SentimentResult(score=0.0, n_articles=0, headlines=[])

    def get(self, token: str = "") -> SentimentResult:
        now = time.time()
        if now - self._ts < self.ttl and self._value.n_articles:
            return self._value
        weighted = fetch_rss() + fetch_gdelt()
        headlines = [h for h, _ in weighted] + fetch_cryptopanic(token)
        if not headlines:
            return self._value
        llm = _llm_score(headlines)
        if llm is not None:
            score, urgent_n = llm, 0
        else:
            num = den = 0.0
            urgent_n = 0
            for h, w in weighted or [(h, 1.0) for h in headlines]:
                s, urg = score_text(h)
                num += s * w
                den += w
                urgent_n += 1 if urg else 0
            score = num / max(den, 1e-9)
        self._value = SentimentResult(score=round(max(-1.0, min(1.0, score)), 4),
            n_articles=len(headlines), headlines=headlines[:10], urgent_bearish=urgent_n)
        self._ts = now
        return self._value

    def inject(self, score: float, n: int = 5) -> SentimentResult:
        self._value = SentimentResult(score=score, n_articles=n, headlines=[])
        self._ts = time.time()
        return self._value
