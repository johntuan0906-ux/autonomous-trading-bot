"""
Lấy tin tức kinh tế / Fed / chính trị / tiền điện tử và tính điểm cảm xúc
(sentiment) cho từng cặp giao dịch.

QUAN TRỌNG — GIỚI HẠN CỦA MODULE NÀY: đây là một mô hình HEURISTIC đơn
giản (VADER + trọng số từ khoá thủ công), KHÔNG phải một hệ thống NLP
chuyên sâu và KHÔNG được kiểm chứng là có khả năng dự báo thị trường.
Hãy coi đây là một bộ lọc bổ trợ cho tín hiệu kỹ thuật, không phải một
nguồn "alpha" đáng tin cậy — tự chịu trách nhiệm nếu tinh chỉnh lại
ngưỡng/trọng số.
"""
import time
import logging

import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("futures_bot.news")

_analyzer = SentimentIntensityAnalyzer()


class NewsSentimentEngine:
    def __init__(self, cfg: dict, env: dict):
        self.enabled = cfg.get("enabled", True)
        self.refresh_seconds = cfg.get("refresh_minutes", 15) * 60
        self.symbol_keywords = cfg.get("symbol_keywords", {})
        self.macro_keywords = cfg.get("macro_keywords", [])
        self.keyword_overrides = {
            k.lower(): v for k, v in cfg.get("keyword_weight_overrides", {}).items()
        }
        self.cryptopanic_key = env.get("cryptopanic_api_key", "")
        self.newsapi_key = env.get("newsapi_api_key", "")

        self._cache = {}          # symbol -> (timestamp, score)
        self._macro_cache = None  # (timestamp, score)

    # ---------------- Nguồn dữ liệu ----------------
    def _fetch_cryptopanic(self, currency: str) -> list:
        if not self.cryptopanic_key:
            return []
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {"auth_token": self.cryptopanic_key, "currencies": currency, "public": "true"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return [p.get("title", "") for p in resp.json().get("results", [])]
        except requests.RequestException as e:
            logger.warning(f"Lỗi gọi CryptoPanic ({currency}): {e}")
            return []

    def _fetch_newsapi(self, query: str) -> list:
        if not self.newsapi_key:
            return []
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query, "apiKey": self.newsapi_key,
            "language": "en", "sortBy": "publishedAt", "pageSize": 20,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return [a.get("title", "") for a in resp.json().get("articles", []) if a.get("title")]
        except requests.RequestException as e:
            logger.warning(f"Lỗi gọi NewsAPI ({query}): {e}")
            return []

    # ---------------- Tính điểm ----------------
    def _score_headlines(self, headlines: list) -> float:
        if not headlines:
            return 0.0
        scores = []
        for text in headlines:
            base = _analyzer.polarity_scores(text)["compound"]
            lower = text.lower()
            override_sum = sum(w for kw, w in self.keyword_overrides.items() if kw in lower)
            scores.append(max(min(base + override_sum, 1.0), -1.0))
        return sum(scores) / len(scores)

    def _get_macro_score(self) -> float:
        now = time.time()
        if self._macro_cache and now - self._macro_cache[0] < self.refresh_seconds:
            return self._macro_cache[1]

        headlines = []
        for kw in self.macro_keywords:
            headlines.extend(self._fetch_newsapi(kw))
        score = self._score_headlines(headlines)
        self._macro_cache = (now, score)
        return score

    def get_score(self, symbol: str) -> float:
        """Điểm tin tức tổng hợp cho 1 symbol, trong khoảng [-1, 1].
        Trả về 0.0 (trung lập) nếu tắt tính năng hoặc chưa cấu hình API key."""
        if not self.enabled:
            return 0.0

        now = time.time()
        cached = self._cache.get(symbol)
        if cached and now - cached[0] < self.refresh_seconds:
            return cached[1]

        keywords = self.symbol_keywords.get(symbol, [])
        headlines = []
        for kw in keywords:
            headlines.extend(self._fetch_cryptopanic(kw))
        specific_score = self._score_headlines(headlines)
        macro_score = self._get_macro_score()

        # Tin tức riêng của coin quan trọng hơn tin vĩ mô chung một chút
        combined = max(min(0.65 * specific_score + 0.35 * macro_score, 1.0), -1.0)

        self._cache[symbol] = (now, combined)
        return combined
