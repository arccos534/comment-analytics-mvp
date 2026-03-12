from __future__ import annotations

TOPIC_RULES: dict[str, set[str]] = {
    "Цена": {"цена", "дорого", "тариф", "стоимость", "тарифов"},
    "Поддержка": {"поддержка", "ответ", "сервис", "команда"},
    "Качество": {"качество", "стабильность", "баг", "багов", "нестабильно"},
    "Доставка": {"доставка", "скорость", "быстро"},
    "Интерфейс": {"интерфейс", "удобно", "удобнее"},
}


class TopicGrouper:
    def group(self, keywords: list[str], text: str) -> list[str]:
        lower = text.lower()
        topics: list[str] = []
        for topic_name, markers in TOPIC_RULES.items():
            if any(marker in lower or marker in keywords for marker in markers):
                topics.append(topic_name)
        return topics or ["Общее обсуждение"]
