from __future__ import annotations

import re

TOPIC_RULES: dict[str, set[str]] = {
    "Благоустройство": {"благоустройство", "двор", "улица", "район", "город", "среда"},
    "Дороги": {"дорога", "дороги", "асфальт", "ямы", "тротуар", "переход"},
    "Парки и общественные пространства": {"парк", "сквер", "набережная", "площадка", "аллея", "детская"},
    "Транспорт": {"транспорт", "автобус", "маршрут", "метро", "трамвай", "остановка"},
    "Освещение и безопасность": {"свет", "освещение", "темно", "безопасность", "камера", "фонарь"},
    "Чистота": {"мусор", "грязь", "уборка", "чистота", "свалка", "контейнер"},
    "Парковка": {"парковка", "машина", "авто", "двор", "место"},
    "Продукт": {"продукт", "сервис", "приложение", "функция", "обновление"},
    "Цена": {"цена", "дорого", "тариф", "стоимость", "дешево"},
    "Поддержка": {"поддержка", "ответ", "оператор", "саппорт"},
    "Качество": {"качество", "стабильность", "ошибка", "баг", "проблема"},
    "Доставка": {"доставка", "курьер", "заказ", "посылка", "привезли"},
}


class TopicGrouper:
    def group(self, keywords: list[str], text: str) -> list[str]:
        lower = text.lower()
        topics: list[str] = []
        for topic_name, markers in TOPIC_RULES.items():
            if any(marker in lower or marker in keywords for marker in markers):
                topics.append(topic_name)

        if topics:
            return topics[:3]

        fallback = [self._normalize_keyword(keyword) for keyword in keywords if keyword.strip()]
        fallback = [keyword for keyword in fallback if keyword]
        if fallback:
            return fallback[:3]

        text_keywords = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{4,}", lower)
        return [self._normalize_keyword(keyword) for keyword in text_keywords[:2]] or ["Общее обсуждение"]

    def _normalize_keyword(self, keyword: str) -> str:
        cleaned = keyword.strip(" -_")
        if not cleaned:
            return ""
        return cleaned.capitalize()
