from __future__ import annotations

import re
from functools import lru_cache

from app.core.config import get_settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{3,}", value.lower()))


@lru_cache(maxsize=1)
def _load_model():
    settings = get_settings()
    if not SentenceTransformer:
        return None


@lru_cache(maxsize=64)
def _encode_baseline(text: str):
    model = _load_model()
    if not model or not text:
        return None
    try:
        return model.encode(text, normalize_embeddings=True)
    except Exception:
        return None
    try:
        return SentenceTransformer(settings.sentence_transformer_model)
    except Exception:
        return None


class RelevanceScorer:
    def score(self, text: str, baseline: str) -> float:
        if not baseline:
            return 1.0

        model = _load_model()
        if model:
            try:
                text_embedding = model.encode(text, normalize_embeddings=True)
                baseline_embedding = _encode_baseline(baseline)
                if baseline_embedding is None:
                    raise ValueError("baseline embedding unavailable")
                cosine = float(text_embedding @ baseline_embedding)
                return round(max(0.0, min(1.0, (cosine + 1) / 2)), 4)
            except Exception:
                pass

        text_tokens = _tokenize(text)
        baseline_tokens = _tokenize(baseline)
        overlap = len(text_tokens & baseline_tokens)
        union = len(text_tokens | baseline_tokens) or 1
        return round(overlap / union, 4)

    def score_comment_prompt(self, text: str, prompt_text: str) -> float:
        baseline = (prompt_text or "").strip()
        return self.score(text, baseline)

    def score_post_topic(self, text: str, theme: str | None, keywords: list[str]) -> float:
        baseline = " ".join(part for part in [theme or "", " ".join(keywords)] if part).strip()
        if not baseline:
            return 1.0
        return self.score(text, baseline)
