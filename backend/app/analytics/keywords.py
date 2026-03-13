from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "по",
    "из",
    "за",
    "для",
    "что",
    "это",
    "как",
    "или",
    "но",
    "не",
    "да",
    "а",
    "к",
    "ко",
    "у",
    "о",
    "об",
    "от",
    "до",
    "мы",
    "вы",
    "они",
    "он",
    "она",
    "оно",
    "все",
    "вот",
    "если",
    "еще",
    "уже",
    "только",
    "просто",
    "тоже",
    "там",
    "тут",
    "этот",
    "эта",
    "эти",
    "того",
    "такой",
    "такая",
    "такие",
    "their",
    "there",
    "this",
    "that",
    "with",
    "from",
    "have",
    "were",
}

GENERIC_WORDS = {
    "город",
    "новость",
    "новости",
    "комментарий",
    "комментарии",
    "пост",
    "поста",
    "люди",
    "человек",
    "сегодня",
    "вчера",
    "здесь",
}


class KeywordExtractor:
    def extract(self, text: str, limit: int = 5) -> list[str]:
        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{4,}", text.lower())
        counts = Counter(
            token
            for token in tokens
            if token not in STOPWORDS and token not in GENERIC_WORDS and not token.isdigit()
        )
        return [token for token, _ in counts.most_common(limit)]
