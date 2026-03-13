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
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "has",
    "are",
    "was",
    "were",
}


class KeywordExtractor:
    def extract(self, text: str, limit: int = 5) -> list[str]:
        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{3,}", text.lower())
        counts = Counter(token for token in tokens if token not in STOPWORDS)
        return [token for token, _ in counts.most_common(limit)]
