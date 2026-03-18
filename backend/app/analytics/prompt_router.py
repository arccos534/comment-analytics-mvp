from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.analytics.prompt_intent import (
    apply_analysis_mode_override,
    build_prompt_intent,
    normalize_prompt_text,
)
from app.analytics.relevance import RelevanceScorer
from app.core.config import get_settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger(__name__)

METRIC_ONLY_MODES = {"source_comparison", "post_popularity", "post_underperformance"}
THEME_MODES = {"theme_sentiment", "theme_interest", "theme_popularity", "theme_underperformance"}
COMMENT_MODES = {"post_sentiment", "theme_sentiment", "theme_interest", "topic_report"}

EXPLANATION_RE = re.compile(
    r"(почему|объясни|объяснение|что люди думают|что думает аудитория|как аудитория|с чем связано|за счет чего)"
)
COMMENT_RE = re.compile(
    r"(коммент|мнение|что люди думают|реакц|позитив|негатив|жалоб|крити|поддерж|тональн)"
)
THEME_RE = re.compile(r"(тем|сюжет|мотив)")
METRIC_RE = re.compile(r"(просмотр|лайк|реакц|комментар|репост|подписчик|охват|вовлеч)")


@dataclass(slots=True)
class PromptRoute:
    analysis_mode: str
    needs_llm_reasoning: bool
    needs_comment_analysis: bool
    needs_theme_analysis: bool
    confidence: float
    router_source: str
    reason: str
    intent: object


SEMANTIC_TEMPLATES = [
    {
        "prompt": "какой пост набрал больше всего просмотров",
        "mode": "post_popularity",
        "needs_llm_reasoning": False,
        "needs_comment_analysis": False,
        "needs_theme_analysis": False,
        "reason": "metric_views_request",
    },
    {
        "prompt": "какой пост набрал больше всего лайков",
        "mode": "post_popularity",
        "needs_llm_reasoning": False,
        "needs_comment_analysis": False,
        "needs_theme_analysis": False,
        "reason": "metric_reactions_request",
    },
    {
        "prompt": "какой пост набрал меньше всего просмотров",
        "mode": "post_underperformance",
        "needs_llm_reasoning": False,
        "needs_comment_analysis": False,
        "needs_theme_analysis": False,
        "reason": "metric_low_views_request",
    },
    {
        "prompt": "какой пост набрал меньше всего лайков",
        "mode": "post_underperformance",
        "needs_llm_reasoning": False,
        "needs_comment_analysis": False,
        "needs_theme_analysis": False,
        "reason": "metric_low_reactions_request",
    },
    {
        "prompt": "в каком канале наиболее активная аудитория",
        "mode": "source_comparison",
        "needs_llm_reasoning": False,
        "needs_comment_analysis": False,
        "needs_theme_analysis": False,
        "reason": "source_metrics_request",
    },
    {
        "prompt": "какая новость вызвала больше всего негатива и почему",
        "mode": "post_sentiment",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": False,
        "reason": "post_negative_reaction_request",
    },
    {
        "prompt": "какая новость вызвала больше всего позитива и почему",
        "mode": "post_sentiment",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": False,
        "reason": "post_positive_reaction_request",
    },
    {
        "prompt": "какие темы вызывают негативную реакцию и почему",
        "mode": "theme_sentiment",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": True,
        "reason": "negative_theme_request",
    },
    {
        "prompt": "какие темы вызывают позитивную реакцию и почему",
        "mode": "theme_sentiment",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": True,
        "reason": "positive_theme_request",
    },
    {
        "prompt": "какие темы собирают больше всего интереса аудитории",
        "mode": "theme_interest",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": True,
        "reason": "theme_interest_request",
    },
    {
        "prompt": "выдели 5 самые популярные темы",
        "mode": "theme_popularity",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": False,
        "needs_theme_analysis": True,
        "reason": "popular_themes_request",
    },
    {
        "prompt": "выдели 5 самые непопулярные темы",
        "mode": "theme_underperformance",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": False,
        "needs_theme_analysis": True,
        "reason": "weak_themes_request",
    },
    {
        "prompt": "что люди думают про эту новость",
        "mode": "post_sentiment",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": False,
        "reason": "what_people_think_request",
    },
    {
        "prompt": "выдели топ 20 процентов самых популярных постов и топ 20 процентов самых слабых постов и объясни почему",
        "mode": "mixed",
        "needs_llm_reasoning": True,
        "needs_comment_analysis": True,
        "needs_theme_analysis": False,
        "reason": "mixed_success_bucket_request",
    },
]


class PromptRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.relevance = RelevanceScorer()

    def route(
        self,
        prompt_text: str | None,
        *,
        has_explicit_scope: bool = False,
        override_mode: str | None = None,
    ) -> PromptRoute:
        intent = build_prompt_intent(prompt_text, has_explicit_scope=has_explicit_scope)
        intent = apply_analysis_mode_override(intent, override_mode, has_explicit_scope=has_explicit_scope)

        rule_route = self._route_by_rules(intent, prompt_text, override_mode)
        if rule_route.confidence >= 0.9:
            return rule_route

        semantic_route = self._route_by_semantics(prompt_text, has_explicit_scope=has_explicit_scope, override_mode=override_mode)
        if semantic_route and semantic_route.confidence >= 0.8:
            return semantic_route

        cheap_llm_route = self._route_with_cheap_llm(prompt_text, has_explicit_scope=has_explicit_scope, override_mode=override_mode)
        if cheap_llm_route:
            return cheap_llm_route

        return PromptRoute(
            analysis_mode=intent.primary_mode,
            needs_llm_reasoning=True,
            needs_comment_analysis=("comment_reaction" in intent.analysis_axes),
            needs_theme_analysis=(intent.primary_mode in THEME_MODES),
            confidence=max(rule_route.confidence, 0.45),
            router_source="fallback",
            reason="safe_fallback",
            intent=intent,
        )

    def _route_by_rules(self, intent, prompt_text: str | None, override_mode: str | None) -> PromptRoute:
        normalized = normalize_prompt_text(prompt_text)
        has_explanation = bool(EXPLANATION_RE.search(normalized))
        has_comment_terms = bool(COMMENT_RE.search(normalized))
        has_theme_terms = bool(THEME_RE.search(normalized))
        has_metric_terms = bool(METRIC_RE.search(normalized))

        if override_mode:
            return PromptRoute(
                analysis_mode=intent.primary_mode,
                needs_llm_reasoning=self._needs_llm_reasoning(intent.primary_mode, has_explanation, has_comment_terms, has_theme_terms),
                needs_comment_analysis=self._needs_comment_analysis(intent.primary_mode, has_explanation, has_comment_terms),
                needs_theme_analysis=self._needs_theme_analysis(intent.primary_mode, has_theme_terms),
                confidence=0.99,
                router_source="rule",
                reason="analysis_mode_override",
                intent=intent,
            )

        if intent.primary_mode in METRIC_ONLY_MODES and has_metric_terms and not has_explanation and not has_comment_terms and not has_theme_terms:
            return PromptRoute(
                analysis_mode=intent.primary_mode,
                needs_llm_reasoning=False,
                needs_comment_analysis=False,
                needs_theme_analysis=False,
                confidence=0.97,
                router_source="rule",
                reason="deterministic_metric_request",
                intent=intent,
            )

        if intent.primary_mode == "mixed" and has_explanation:
            return PromptRoute(
                analysis_mode="mixed",
                needs_llm_reasoning=True,
                needs_comment_analysis=True,
                needs_theme_analysis=False,
                confidence=0.93,
                router_source="rule",
                reason="mixed_with_explanation",
                intent=intent,
            )

        if intent.primary_mode == "post_sentiment":
            return PromptRoute(
                analysis_mode="post_sentiment",
                needs_llm_reasoning=True,
                needs_comment_analysis=True,
                needs_theme_analysis=False,
                confidence=0.9 if has_comment_terms or has_explanation else 0.82,
                router_source="rule",
                reason="post_sentiment_request",
                intent=intent,
            )

        if intent.primary_mode in THEME_MODES:
            return PromptRoute(
                analysis_mode=intent.primary_mode,
                needs_llm_reasoning=True,
                needs_comment_analysis=intent.primary_mode in {"theme_sentiment", "theme_interest"} or has_comment_terms or has_explanation,
                needs_theme_analysis=True,
                confidence=0.88 if has_theme_terms else 0.74,
                router_source="rule",
                reason="theme_request",
                intent=intent,
            )

        return PromptRoute(
            analysis_mode=intent.primary_mode,
            needs_llm_reasoning=self._needs_llm_reasoning(intent.primary_mode, has_explanation, has_comment_terms, has_theme_terms),
            needs_comment_analysis=self._needs_comment_analysis(intent.primary_mode, has_explanation, has_comment_terms),
            needs_theme_analysis=self._needs_theme_analysis(intent.primary_mode, has_theme_terms),
            confidence=0.6,
            router_source="rule",
            reason="general_intent_match",
            intent=intent,
        )

    def _route_by_semantics(
        self,
        prompt_text: str | None,
        *,
        has_explicit_scope: bool,
        override_mode: str | None,
    ) -> PromptRoute | None:
        normalized = normalize_prompt_text(prompt_text)
        if not normalized:
            return None

        best_template: dict | None = None
        best_score = -1.0
        second_score = -1.0
        for template in SEMANTIC_TEMPLATES:
            score = self.relevance.score(normalized, normalize_prompt_text(template["prompt"]))
            if score > best_score:
                second_score = best_score
                best_score = score
                best_template = template
            elif score > second_score:
                second_score = score

        if not best_template:
            return None

        confidence = min(0.95, max(0.0, best_score))
        if best_score - second_score < 0.08:
            confidence = min(confidence, 0.76)

        intent = build_prompt_intent(prompt_text, has_explicit_scope=has_explicit_scope)
        intent = apply_analysis_mode_override(intent, best_template["mode"], has_explicit_scope=has_explicit_scope)
        intent = apply_analysis_mode_override(intent, override_mode, has_explicit_scope=has_explicit_scope)

        return PromptRoute(
            analysis_mode=intent.primary_mode,
            needs_llm_reasoning=bool(best_template["needs_llm_reasoning"]),
            needs_comment_analysis=bool(best_template["needs_comment_analysis"]),
            needs_theme_analysis=bool(best_template["needs_theme_analysis"]),
            confidence=confidence,
            router_source="semantic",
            reason=str(best_template["reason"]),
            intent=intent,
        )

    def _route_with_cheap_llm(
        self,
        prompt_text: str | None,
        *,
        has_explicit_scope: bool,
        override_mode: str | None,
    ) -> PromptRoute | None:
        if not (
            OpenAI
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
            and prompt_text
        ):
            return None

        try:
            client = OpenAI(
                base_url=self.settings.openai_compatible_base_url,
                api_key=self.settings.openai_compatible_api_key,
            )
            completion = client.chat.completions.create(
                model=self.settings.openai_prompt_router_model,
                max_completion_tokens=max(int(self.settings.openai_prompt_router_max_completion_tokens or 160), 80),
                temperature=0,
                messages=[
                    {"role": "system", "content": self._cheap_router_system_prompt()},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "prompt_text": prompt_text,
                                "has_explicit_scope": has_explicit_scope,
                                "analysis_mode_override": (override_mode or "").strip() or None,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = (completion.choices[0].message.content or "").strip()
            payload = self._parse_json_object(content)
            if not payload:
                return None
            analysis_mode = str(payload.get("analysis_mode") or "").strip() or "topic_report"
            confidence = float(payload.get("confidence") or 0.0)
            intent = build_prompt_intent(prompt_text, has_explicit_scope=has_explicit_scope)
            intent = apply_analysis_mode_override(intent, analysis_mode, has_explicit_scope=has_explicit_scope)
            intent = apply_analysis_mode_override(intent, override_mode, has_explicit_scope=has_explicit_scope)
            return PromptRoute(
                analysis_mode=intent.primary_mode,
                needs_llm_reasoning=bool(payload.get("needs_llm_reasoning")),
                needs_comment_analysis=bool(payload.get("needs_comment_analysis")),
                needs_theme_analysis=bool(payload.get("needs_theme_analysis")),
                confidence=max(0.5, min(confidence, 0.89)),
                router_source="cheap_llm",
                reason="cheap_llm_router",
                intent=intent,
            )
        except Exception:
            logger.exception("Cheap prompt router failed")
            return None

    def _cheap_router_system_prompt(self) -> str:
        return (
            "Classify a Russian analytics prompt and return strict JSON.\n"
            "Allowed analysis_mode values: "
            "source_comparison, post_popularity, post_underperformance, post_sentiment, "
            "theme_sentiment, theme_interest, theme_popularity, theme_underperformance, topic_report, mixed.\n"
            "Return JSON object with keys: analysis_mode, needs_llm_reasoning, needs_comment_analysis, needs_theme_analysis, confidence.\n"
            "Use false for needs_llm_reasoning on pure metric requests about views, likes, reactions, comments, reposts, subscribers, or source ranking.\n"
            "Use true for needs_comment_analysis when the user asks what people think, audience reaction, positive/negative reaction, tone, complaints, support, or why.\n"
            "Use true for needs_theme_analysis when the user asks about themes, motifs, plots, or top topics.\n"
            "Keep confidence between 0 and 1."
        )

    def _parse_json_object(self, text: str) -> dict | None:
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        candidate = text[start : end + 1] if start != -1 and end != -1 and end > start else text
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _needs_llm_reasoning(self, mode: str, has_explanation: bool, has_comment_terms: bool, has_theme_terms: bool) -> bool:
        if mode in METRIC_ONLY_MODES and not has_explanation and not has_comment_terms and not has_theme_terms:
            return False
        return mode not in METRIC_ONLY_MODES or has_explanation or has_comment_terms or has_theme_terms

    def _needs_comment_analysis(self, mode: str, has_explanation: bool, has_comment_terms: bool) -> bool:
        if mode in METRIC_ONLY_MODES:
            return False
        if mode in COMMENT_MODES:
            return True
        return has_explanation or has_comment_terms

    def _needs_theme_analysis(self, mode: str, has_theme_terms: bool) -> bool:
        if mode in THEME_MODES:
            return True
        return has_theme_terms and mode not in METRIC_ONLY_MODES
