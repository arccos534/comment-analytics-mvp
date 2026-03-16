from __future__ import annotations

import re

from app.models.enums import SentimentEnum

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]{2,}")
WHITESPACE_RE = re.compile(r"\s+")

POSITIVE_PHRASES = {
    "спасибо огромное": 2.6,
    "большое спасибо": 2.4,
    "хорошая новость": 2.2,
    "отличная новость": 2.4,
    "правильно сделали": 2.2,
    "так и надо": 2.0,
    "полностью согласен": 2.2,
    "полностью согласна": 2.2,
    "поддерживаю": 2.1,
    "молодцы": 2.0,
    "очень удобно": 1.8,
    "стало лучше": 1.8,
    "сделали хорошо": 1.8,
    "сделали быстро": 1.4,
    "наконец то сделали": 1.6,
    "хорошо": 1.4,
    "супер": 1.6,
    "здорово": 1.5,
    "классно": 1.5,
    "отлично": 1.8,
    "неплохо": 1.2,
}

NEGATIVE_PHRASES = {
    "это позор": 3.0,
    "стыд и позор": 3.2,
    "позор администрации": 3.2,
    "бардак полный": 2.7,
    "ужас какой": 2.4,
    "кошмар какой": 2.4,
    "так нельзя": 1.7,
    "деньги на ветер": 2.7,
    "ничего не делают": 2.3,
    "не работают": 1.9,
    "не убирают": 1.9,
    "чистой воды мошенники": 3.2,
    "замешан в фальсификате": 3.1,
    "замешаны в фальсификате": 3.1,
    "это фальсификат": 2.9,
    "это подделка": 2.8,
    "обычный обман": 2.8,
    "очередной обман": 2.9,
    "не верю": 1.8,
    "не доверяю": 2.1,
    "кто такие эксперты": 2.3,
    "нужно проверить новость": 1.5,
    "надо проверить новость": 1.5,
    "роскачество мошенники": 3.0,
}

POSITIVE_STEMS = {
    "спасиб": 1.5,
    "молодц": 1.8,
    "хорош": 1.1,
    "отличн": 1.6,
    "красот": 1.4,
    "удобн": 1.1,
    "полезн": 1.0,
    "быстр": 0.8,
    "нрав": 1.2,
    "любл": 1.2,
    "супер": 1.3,
    "прекрас": 1.4,
    "класс": 1.1,
    "оператив": 1.0,
    "поддерж": 1.4,
    "одобр": 1.3,
    "соглас": 1.2,
    "верн": 1.1,
    "правиль": 1.1,
    "рад": 1.1,
    "здоров": 1.2,
    "лучше": 1.0,
}

NEGATIVE_STEMS = {
    "позор": 2.8,
    "стыд": 2.2,
    "ужас": 2.0,
    "кошмар": 2.0,
    "бардак": 2.2,
    "воров": 2.3,
    "корруп": 2.4,
    "отмыван": 2.4,
    "безобраз": 2.0,
    "отврат": 2.1,
    "плох": 1.4,
    "дурн": 1.4,
    "гряз": 1.2,
    "слом": 1.2,
    "проблем": 1.1,
    "жалоб": 1.0,
    "хамств": 1.7,
    "плеват": 1.8,
    "наплеват": 2.0,
    "мошенн": 2.5,
    "обман": 2.3,
    "фальсифик": 2.6,
    "поддел": 2.4,
    "вран": 2.0,
    "лож": 1.8,
    "шантаж": 2.2,
    "развод": 2.2,
    "скам": 2.0,
    "ненавиж": 2.2,
    "фейк": 2.1,
    "суррогат": 2.2,
    "замеша": 1.8,
}

NEGATIONS = {"не", "нет", "ни", "без"}


def _normalize_text(text: str) -> str:
    normalized = (text or "").strip().lower().replace("ё", "е")
    return WHITESPACE_RE.sub(" ", normalized)


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(_normalize_text(text))


def _stem_weight(token: str, stems: dict[str, float]) -> float:
    best = 0.0
    for stem, weight in stems.items():
        if stem in token:
            best = max(best, weight)
    return best


class SentimentAnalyzer:
    def analyze(self, text: str) -> dict[str, SentimentEnum | float]:
        lower = _normalize_text(text)
        tokens = _tokenize(lower)
        if not tokens:
            return {"sentiment": SentimentEnum.neutral, "score": 0.0}

        positive_score = 0.0
        negative_score = 0.0

        for phrase, weight in POSITIVE_PHRASES.items():
            if phrase in lower:
                positive_score += weight

        for phrase, weight in NEGATIVE_PHRASES.items():
            if phrase in lower:
                negative_score += weight

        for index, token in enumerate(tokens):
            prev_token = tokens[index - 1] if index > 0 else ""
            prev_prev_token = tokens[index - 2] if index > 1 else ""
            negated = prev_token in NEGATIONS or prev_prev_token in NEGATIONS

            positive_weight = _stem_weight(token, POSITIVE_STEMS)
            negative_weight = _stem_weight(token, NEGATIVE_STEMS)

            if positive_weight:
                if negated:
                    negative_score += positive_weight + 0.5
                else:
                    positive_score += positive_weight

            if negative_weight:
                if negated:
                    positive_score += max(0.3, negative_weight - 0.7)
                else:
                    negative_score += negative_weight

        if "?" in lower and negative_score > positive_score:
            negative_score += 0.2

        exclamations = lower.count("!")
        if exclamations:
            if negative_score > positive_score:
                negative_score += min(0.8, exclamations * 0.15)
            elif positive_score > negative_score:
                positive_score += min(0.5, exclamations * 0.1)

        total = positive_score + negative_score
        if total == 0:
            return {"sentiment": SentimentEnum.neutral, "score": 0.0}

        score = round((positive_score - negative_score) / total, 4)
        gap = abs(positive_score - negative_score)

        if positive_score > 0 and negative_score > 0:
            if gap < 1.0 or 0.85 <= (positive_score / max(negative_score, 0.1)) <= 1.18:
                return {"sentiment": SentimentEnum.neutral, "score": float(score)}

        if negative_score >= max(1.6, positive_score * 1.18) and score <= -0.08:
            sentiment = SentimentEnum.negative
        elif positive_score >= max(1.4, negative_score * 1.18) and score >= 0.08:
            sentiment = SentimentEnum.positive
        elif score <= -0.24:
            sentiment = SentimentEnum.negative
        elif score >= 0.24:
            sentiment = SentimentEnum.positive
        else:
            sentiment = SentimentEnum.neutral

        return {"sentiment": sentiment, "score": float(score)}
