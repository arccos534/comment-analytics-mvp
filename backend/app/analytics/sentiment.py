from __future__ import annotations

import re

from app.models.enums import SentimentEnum

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9-]{3,}")

POSITIVE_PHRASES = {
    "спасибо огромное": 2.5,
    "большое спасибо": 2.5,
    "спасибо": 1.8,
    "молодцы": 2.0,
    "хорошая работа": 2.2,
    "отличная работа": 2.5,
    "сделали хорошо": 2.0,
    "сделали быстро": 1.5,
    "очень удобно": 1.8,
    "стало лучше": 1.8,
    "наконец-то сделали": 1.7,
    "красота": 1.8,
    "супер": 1.6,
}

NEGATIVE_PHRASES = {
    "позор администрации": 3.2,
    "это позор": 3.0,
    "стыд и позор": 3.2,
    "отмывание денег": 3.0,
    "воровство бюджет": 2.8,
    "бардак полный": 2.7,
    "ужас какой": 2.4,
    "кошмар какой": 2.4,
    "не организованы": 2.0,
    "не работают": 1.8,
    "не убирают": 1.8,
    "ничего не делают": 2.2,
    "так нельзя": 1.6,
    "деньги на ветер": 2.6,
}

POSITIVE_STEMS = {
    "спасиб": 1.6,
    "молодц": 1.8,
    "хорош": 1.0,
    "отличн": 1.5,
    "красот": 1.4,
    "удобн": 1.1,
    "полезн": 1.0,
    "быстр": 0.9,
    "нрав": 1.2,
    "нравит": 1.2,
    "супер": 1.2,
    "прекрас": 1.4,
    "класс": 1.2,
    "чист": 0.8,
    "оператив": 1.0,
}

NEGATIVE_STEMS = {
    "позор": 2.8,
    "стыд": 2.2,
    "ужас": 2.0,
    "кошмар": 2.0,
    "бардак": 2.2,
    "воров": 2.4,
    "корруп": 2.4,
    "отмыван": 2.4,
    "безобраз": 2.1,
    "отврат": 2.1,
    "плох": 1.4,
    "дурн": 1.3,
    "гряз": 1.2,
    "дорог": 1.2,
    "ям": 0.9,
    "слом": 1.2,
    "проблем": 1.1,
    "жалоб": 1.0,
    "кошмарн": 2.0,
    "стыдн": 1.8,
    "хамств": 1.6,
    "плеват": 1.8,
    "наплеват": 2.0,
}

NEGATIONS = {"не", "нет", "ни"}


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _contains_stem(token: str, stems: dict[str, float]) -> float:
    for stem, weight in stems.items():
        if stem in token:
            return weight
    return 0.0


class SentimentAnalyzer:
    def analyze(self, text: str) -> dict[str, SentimentEnum | float]:
        lower = text.lower().strip()
        tokens = _tokenize(lower)

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
            positive_weight = _contains_stem(token, POSITIVE_STEMS)
            negative_weight = _contains_stem(token, NEGATIVE_STEMS)

            if positive_weight:
                if prev_token in NEGATIONS:
                    negative_score += positive_weight + 0.4
                else:
                    positive_score += positive_weight

            if negative_weight:
                if prev_token in NEGATIONS:
                    positive_score += max(0.3, negative_weight - 0.6)
                else:
                    negative_score += negative_weight

        exclamations = lower.count("!")
        if exclamations:
            if negative_score > positive_score:
                negative_score += min(0.6, exclamations * 0.15)
            elif positive_score > negative_score:
                positive_score += min(0.4, exclamations * 0.1)

        total = positive_score + negative_score
        if total == 0:
            return {"sentiment": SentimentEnum.neutral, "score": 0.0}

        score = round((positive_score - negative_score) / total, 4)

        if negative_score >= 1.8 and score <= -0.15:
            sentiment = SentimentEnum.negative
        elif positive_score >= 1.6 and score >= 0.12:
            sentiment = SentimentEnum.positive
        elif score <= -0.22:
            sentiment = SentimentEnum.negative
        elif score >= 0.2:
            sentiment = SentimentEnum.positive
        else:
            sentiment = SentimentEnum.neutral

        return {"sentiment": sentiment, "score": float(score)}
