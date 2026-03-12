from __future__ import annotations

from functools import lru_cache

from app.models.enums import SentimentEnum

POSITIVE_TERMS = {
    "нравится",
    "классно",
    "отлично",
    "быстро",
    "удобно",
    "спасибо",
    "лучше",
    "полезно",
    "приятно",
}
NEGATIVE_TERMS = {
    "плохо",
    "дорого",
    "завышенной",
    "раздражает",
    "баг",
    "минус",
    "кусается",
    "нестабильно",
    "не хватает",
}


class SentimentAnalyzer:
    def analyze(self, text: str) -> dict[str, SentimentEnum | float]:
        lower = text.lower()
        positive = sum(1 for token in POSITIVE_TERMS if token in lower)
        negative = sum(1 for token in NEGATIVE_TERMS if token in lower)
        score = (positive - negative) / max(positive + negative, 1)

        if score > 0.15:
            sentiment = SentimentEnum.positive
        elif score < -0.15:
            sentiment = SentimentEnum.negative
        else:
            sentiment = SentimentEnum.neutral
        return {"sentiment": sentiment, "score": float(score)}
