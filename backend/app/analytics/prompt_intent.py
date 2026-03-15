from __future__ import annotations

import re
from dataclasses import dataclass

PROMPT_STOPWORDS = {
    "это",
    "этот",
    "эта",
    "эти",
    "такой",
    "такая",
    "такие",
    "также",
    "просто",
    "очень",
    "снова",
    "будет",
    "будут",
    "после",
    "между",
    "через",
    "только",
    "сегодня",
    "вчера",
    "завтра",
    "здесь",
    "там",
    "тоже",
    "тогда",
    "потом",
    "если",
    "вот",
    "все",
    "всего",
    "всем",
    "всех",
    "или",
    "для",
    "при",
    "под",
    "над",
    "про",
    "как",
    "что",
    "чтобы",
    "где",
    "когда",
    "было",
    "были",
    "был",
    "была",
    "год",
    "года",
    "лет",
    "месяц",
    "месяца",
    "неделя",
    "недели",
    "день",
    "дня",
    "дней",
    "час",
    "часа",
    "часов",
    "первый",
    "первая",
    "первые",
    "второй",
    "вторая",
    "вторые",
    "третий",
    "третья",
    "новый",
    "новая",
    "новые",
    "старый",
    "старые",
    "самый",
    "самая",
    "самые",
    "самой",
    "свои",
    "свой",
    "своих",
    "наш",
    "наши",
    "ваш",
    "ваши",
    "сказал",
    "сказала",
    "заявил",
    "заявила",
    "сообщил",
    "сообщила",
    "говорит",
    "пишет",
    "россия",
    "россии",
    "москва",
    "москве",
    "область",
    "области",
    "район",
    "района",
    "край",
    "края",
    "новость",
    "новости",
    "пост",
    "посты",
    "публикация",
    "публикации",
    "сообщение",
    "сообщения",
    "обсуждение",
    "обсуждения",
    "реакция",
    "реакции",
    "лайки",
    "лайков",
    "просмотры",
    "просмотров",
    "охват",
    "охваты",
    "аудитория",
    "аудитории",
    "комментарий",
    "комментарии",
    "комментариях",
    "telegram",
    "телеграм",
    "vk",
    "канал",
    "канале",
    "каналы",
    "сообщество",
    "сообщества",
    "источник",
    "источники",
    "город",
    "города",
    "городе",
    "люди",
    "людей",
    "жители",
    "житель",
    "проанализируй",
    "проанализировать",
    "анализ",
    "какой",
    "какая",
    "какие",
    "какого",
    "каких",
    "какому",
    "каким",
    "которая",
    "который",
    "которые",
    "которое",
    "которых",
    "больше",
    "меньше",
    "собрала",
    "собрал",
    "собрали",
    "получила",
    "получил",
    "получили",
    "найди",
    "найти",
    "покажи",
    "показать",
    "определи",
    "выдели",
    "расскажи",
    "объясни",
    "сделай",
    "нужно",
    "надо",
    "хочу",
    "ли",
    "наиболее",
}

GENERIC_PROMPT_SCOPE_TERMS = {
    "новость",
    "новости",
    "пост",
    "посты",
    "тема",
    "темы",
    "сюжет",
    "сюжеты",
    "люди",
    "думают",
    "мнение",
    "реакция",
    "реакции",
    "лайки",
    "лайков",
    "просмотры",
    "просмотров",
    "охват",
    "охваты",
    "комментарии",
    "комментариев",
    "успешные",
    "успешность",
    "неуспешные",
    "непопулярные",
    "популярные",
    "популярность",
}

SOURCE_METRIC_TERMS = {
    "канал",
    "канале",
    "каналы",
    "сообщество",
    "сообщества",
    "источник",
    "источники",
    "аудитория",
    "аудитории",
    "активная",
    "активность",
    "вовлеченность",
    "метрики",
    "охват",
    "охваты",
    "подписчики",
    "подписчиков",
    "подписчик",
}

POST_SCOPE_TERMS = {
    "пост",
    "посты",
    "новость",
    "новости",
    "публикация",
    "публикации",
    "тема",
    "темы",
    "тему",
    "сюжет",
    "сюжеты",
    "успешные",
    "неуспешные",
    "популярные",
    "непопулярные",
}

COMMENT_REACTION_TERMS = {
    "комментарий",
    "комментарии",
    "комментариев",
    "реакция",
    "реакции",
    "думают",
    "мнение",
    "отношение",
    "позитив",
    "негатив",
    "эмоции",
    "жалобы",
    "претензии",
    "критикуют",
    "поддерживают",
    "поддержка",
    "тревога",
}

RAW_MODE_PATTERNS: list[tuple[str, str]] = [
    (r"(excel|эксель|xlsx|таблиц[ауыое]|выгрузк[ауыи])", "excel_export"),
    (r"сам[а-я]* обсужда|наиболее обсужда", "most_discussed_news"),
    (r"(больше всего|наибольш[а-я]*|максимальн[а-я]*).*(реакц|лайк)", "most_reacted_post"),
    (r"(реакц|лайк).*(больше всего|наибольш[а-я]*|максимальн[а-я]*)", "most_reacted_post"),
    (r"(больше всего|наибольш[а-я]*|максимальн[а-я]*).*(просмотр|охват)", "most_viewed_post"),
    (r"(просмотр|охват).*(больше всего|наибольш[а-я]*|максимальн[а-я]*)", "most_viewed_post"),
    (r"(меньше всего|наименьш[а-я]*|минимальн[а-я]*|худш[а-я]*|слаб[а-я]*).*(реакц|лайк)", "least_reacted_post"),
    (r"(реакц|лайк).*(меньше всего|наименьш[а-я]*|минимальн[а-я]*|худш[а-я]*|слаб[а-я]*)", "least_reacted_post"),
    (r"(меньше всего|наименьш[а-я]*|минимальн[а-я]*|худш[а-я]*|слаб[а-я]*).*(просмотр|охват)", "least_viewed_post"),
    (r"(просмотр|охват).*(меньше всего|наименьш[а-я]*|минимальн[а-я]*|худш[а-я]*|слаб[а-я]*)", "least_viewed_post"),
    (r"(успешн|популярн).*(20%|20 процентов|верхн)", "successful_posts_bucket"),
    (r"(наиболее|самые|лучшие).*(успешн|популярн).*(пост|публикац)", "successful_posts_bucket"),
    (r"(неуспешн|непопулярн|слаб[а-я]*|худш[а-я]*).*(20%|20 процентов|нижн)", "underperforming_posts_bucket"),
    (r"(наименее|худшие|слабые).*(успешн|популярн|пост|публикац)", "underperforming_posts_bucket"),
    (r"в каком канале|какой канал|какое сообщество|какой источник", "source_comparison"),
    (r"активн[а-я]* аудитори", "source_comparison"),
    (r"сравн.*канал|сравн.*сообществ|сравн.*источник", "source_comparison"),
    (r"подписчик|размер аудитории|размер канала", "source_comparison"),
    (r"интерес|вовлеч|резонанс", "interest_analysis"),
    (r"негатив|эмоци|критик|возмущ|раздраж", "negative_analysis"),
    (r"позитив|нрав|одобр|поддерж", "positive_analysis"),
    (r"тем[ауыое]|сюжет", "theme_analysis"),
    (r"сравн|отлич|разниц", "comparison"),
    (r"причин|почему", "causal_explanation"),
    (r"поддержива|одобр|хвал|благодар", "support_analysis"),
    (r"жалоб|претензи|критикуют|ругают|недоволь", "complaints_analysis"),
    (r"опасени|тревог|боят|страх|риски", "concerns_analysis"),
    (r"конфликт|спор|поляриз|раздел", "polarization_analysis"),
    (r"главн|ключев|основн.*вывод", "takeaways_analysis"),
    (r"за (недел[юьи]|месяц|месяца|квартал|год)", "periodic_report"),
    (r"какая новость|какой пост|какая публикация|какие новости", "specific_news_answer"),
]

PRIMARY_MODE_PRIORITY = [
    "excel_export",
    "source_comparison",
    "post_underperformance",
    "post_popularity",
    "theme_sentiment",
    "theme_interest",
    "topic_report",
]


@dataclass(frozen=True)
class PromptIntent:
    prompt_text: str
    normalized_text: str
    analysis_axes: list[str]
    prompt_mode: list[str]
    primary_mode: str
    secondary_modes: list[str]
    request_contract: list[str]
    answer_strategy: dict
    focus_terms: list[str]
    scope_terms: list[str]
    generic_scope: bool
    source_only: bool


def normalize_prompt_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace("ё", "е").split())


def extract_prompt_focus_terms(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return []

    seen: list[str] = []
    for token in re.findall(r"[a-zа-я0-9-]{4,}", prompt):
        if token in PROMPT_STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    return [_titleize_phrase(token) for token in seen[:8]]


def extract_prompt_scope_terms(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return []

    ordered: list[str] = []
    for token in re.findall(r"[a-zа-я0-9-]{4,}", prompt):
        if token in PROMPT_STOPWORDS:
            continue
        if token not in ordered:
            ordered.append(token)
    return ordered[:8]


def infer_prompt_mode(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return ["general_analysis"]

    modes: list[str] = []
    for pattern, mode in RAW_MODE_PATTERNS:
        if re.search(pattern, prompt) and mode not in modes:
            modes.append(mode)
    return modes or ["general_analysis"]


def infer_analysis_axes(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    raw_modes = infer_prompt_mode(prompt_text)
    if not prompt:
        return ["general"]

    axes: list[str] = []
    if any(term in prompt for term in SOURCE_METRIC_TERMS) or "source_comparison" in raw_modes:
        axes.append("source_metrics")
    if any(term in prompt for term in POST_SCOPE_TERMS) or _has_post_level_mode(raw_modes):
        axes.append("post_scope")
    if any(term in prompt for term in COMMENT_REACTION_TERMS) or _has_reaction_mode(raw_modes):
        axes.append("comment_reaction")
    return axes or ["general"]


def infer_request_contract(
    prompt_text: str | None,
    primary_mode: str | None = None,
    secondary_modes: list[str] | None = None,
) -> list[str]:
    raw_modes = infer_prompt_mode(prompt_text)
    axes = infer_analysis_axes(prompt_text)
    primary = primary_mode or determine_primary_mode(raw_modes, axes, has_explicit_scope=False)
    secondary = secondary_modes or []
    instructions: list[str] = []

    if primary == "source_comparison":
        instructions.extend(
            [
                "Сравни именно источники между собой, а не отдельные посты.",
                "Используй число подписчиков, число постов, суммарные просмотры, реакции или лайки, комментарии, репосты и средние метрики на пост.",
                "Назови лидирующий и слабый источник, если данных хватает хотя бы на базовое сравнение.",
            ]
        )
    elif primary == "post_popularity":
        instructions.extend(
            [
                "Определи наиболее успешные или популярные посты по просмотрам и реакциям или лайкам.",
                "Комментарии используй как вторичный сигнал, а не как главный критерий успеха.",
                "Если просмотров нет, прямо скажи, что ранжирование построено по реакциям или лайкам, комментариям и репостам.",
            ]
        )
    elif primary == "post_underperformance":
        instructions.extend(
            [
                "Определи наименее успешные посты по просмотрам и реакциям или лайкам.",
                "Не путай слабые посты с просто малообсуждаемыми: сначала смотри на просмотры и реакции или лайки.",
                "Кратко объясни, почему эти публикации оказались внизу.",
            ]
        )
    elif primary == "theme_sentiment":
        instructions.extend(
            [
                "Выдели темы, к которым аудитория относится позитивно или негативно.",
                "Покажи, какие темы собирают жалобы, одобрение, тревогу или полярную реакцию, если это следует из запроса.",
                "Не смешивай реакцию на тему с общей популярностью темы.",
            ]
        )
    elif primary == "theme_interest":
        instructions.extend(
            [
                "Выдели темы, которые вызывают наибольший интерес или резонанс.",
                "Опирайся прежде всего на посты и их метрики, а комментарии используй как подтверждение реакции.",
                "Если тема задана пользователем явно, анализируй только релевантные посты.",
            ]
        )
    else:
        instructions.extend(
            [
                "Дай содержательный тематический отчет по релевантным постам и комментариям.",
                "Выделяй только реальные темы постов и новостей, без обрывков фраз и мусорных слов.",
                "Если данных мало, скажи это прямо, но все равно дай полезный вывод.",
            ]
        )

    normalized_prompt = normalize_prompt_text(prompt_text)
    if "causal_explanation" in secondary or re.search(r"почему|причин", normalized_prompt):
        instructions.append(
            "Обязательно объясни, почему аудитория реагирует именно так: сравни тему, подачу, эмоциональность, оформление, эмодзи, призывность, конфликтность, полезность и новизну."
        )
    if "periodic_report" in secondary or re.search(r"за (недел[юьи]|месяц|месяца|квартал|год)", normalized_prompt):
        instructions.append("Отвечай в рамках указанного периода, а не по всей истории источников.")
    if "comparison" in secondary and primary != "source_comparison":
        instructions.append("Покажи различия между лидерами и аутсайдерами, а не только перечисли их.")
    if primary in {"post_popularity", "post_underperformance"}:
        instructions.append("Если данных достаточно, выдели верхние и нижние 20% постов как лучшие и слабые группы.")

    return instructions


def build_answer_strategy(
    prompt_text: str | None,
    analysis_axes: list[str] | None = None,
    primary_mode: str | None = None,
    secondary_modes: list[str] | None = None,
) -> dict:
    axes = set(analysis_axes or infer_analysis_axes(prompt_text))
    raw_modes = infer_prompt_mode(prompt_text)
    primary = primary_mode or determine_primary_mode(raw_modes, list(axes), has_explicit_scope=False)
    secondary = secondary_modes or determine_secondary_modes(raw_modes, primary, has_explicit_scope=False)

    response_shape = "analysis_note"
    first_sentence_rule = "Начни с прямого ответа на пользовательский запрос."
    must_cover: list[str] = []
    metric_priority: list[str] = ["views", "likes_or_reactions", "comments", "reposts"]

    if primary == "source_comparison":
        response_shape = "source_comparison"
        first_sentence_rule = "Сразу назови источник-лидер и объясни, по каким метрикам он выигрывает."
        must_cover.extend(
            [
                "Назови лидирующий источник.",
                "Если данных хватает, назови и более слабый источник.",
                "Покажи суммарные и средние метрики на пост.",
            ]
        )
        metric_priority = [
            "subscriber_count",
            "avg_views_per_post",
            "avg_likes_or_reactions_per_post",
            "avg_comments_per_post",
            "avg_reposts_per_post",
        ]
    elif primary == "post_popularity":
        response_shape = "ranked_posts"
        first_sentence_rule = "Начни с поста или группы постов, которые набрали лучшие показатели по успеху."
        must_cover.extend(
            [
                "Назови лидеров по успеху.",
                "Если данных хватает, покажи верхние 20% постов.",
                "Объясни, какие темы и особенности подачи делают их сильнее.",
            ]
        )
    elif primary == "post_underperformance":
        response_shape = "ranked_posts"
        first_sentence_rule = "Начни со слабейших публикаций и коротко объясни, почему они отстают."
        must_cover.extend(
            [
                "Назови аутсайдеров по успеху.",
                "Если данных хватает, покажи нижние 20% постов.",
                "Сравни их с более успешными публикациями.",
            ]
        )
    elif primary == "theme_sentiment":
        response_shape = "theme_map"
        first_sentence_rule = "Сразу назови темы с наиболее позитивной и наиболее негативной реакцией."
        must_cover.extend(
            [
                "Назови темы, которые вызывают позитив.",
                "Назови темы, которые вызывают негатив.",
                "Объясни, почему реакция отличается.",
            ]
        )
    elif primary == "theme_interest":
        response_shape = "theme_map"
        first_sentence_rule = "Сразу назови темы, которые собирают наибольший интерес."
        must_cover.extend(
            [
                "Назови самые интересные темы.",
                "Покажи, какие метрики подтверждают интерес.",
                "Если уместно, сравни их с более слабыми темами.",
            ]
        )
    else:
        must_cover.extend(
            [
                "Ответь именно на пользовательский запрос, а не пересказывай общую статистику.",
                "Привяжи вывод к конкретным постам, темам или источникам.",
            ]
        )

    if "source_metrics" in axes and primary != "source_comparison":
        must_cover.append("Если различия между источниками заметны, кратко зафиксируй их как дополнительный контекст.")
    if "comment_reaction" in axes and primary not in {"source_comparison", "post_popularity", "post_underperformance"}:
        must_cover.append("Используй тональность и комментарии как подтверждение того, как аудитория реагирует на темы.")

    return {
        "primary_mode": primary,
        "secondary_modes": secondary,
        "response_shape": response_shape,
        "first_sentence_rule": first_sentence_rule,
        "must_cover": must_cover,
        "metric_priority": metric_priority,
    }


def build_prompt_intent(prompt_text: str | None, has_explicit_scope: bool = False) -> PromptIntent:
    normalized_text = normalize_prompt_text(prompt_text)
    raw_modes = infer_prompt_mode(prompt_text)
    analysis_axes = infer_analysis_axes(prompt_text)
    if has_explicit_scope and "post_scope" not in analysis_axes:
        analysis_axes = [axis for axis in analysis_axes if axis != "general"] + ["post_scope"]

    primary_mode = determine_primary_mode(raw_modes, analysis_axes, has_explicit_scope)
    secondary_modes = determine_secondary_modes(raw_modes, primary_mode, has_explicit_scope)
    scope_terms = extract_prompt_scope_terms(prompt_text)
    meaningful_scope_terms = [term for term in scope_terms if term not in GENERIC_PROMPT_SCOPE_TERMS]
    generic_scope = not meaningful_scope_terms or primary_mode in {
        "source_comparison",
        "post_popularity",
        "post_underperformance",
    }
    source_only = primary_mode == "source_comparison" and not has_explicit_scope and not meaningful_scope_terms

    return PromptIntent(
        prompt_text=(prompt_text or "").strip(),
        normalized_text=normalized_text,
        analysis_axes=analysis_axes,
        prompt_mode=raw_modes,
        primary_mode=primary_mode,
        secondary_modes=secondary_modes,
        request_contract=infer_request_contract(prompt_text, primary_mode, secondary_modes),
        answer_strategy=build_answer_strategy(prompt_text, analysis_axes, primary_mode, secondary_modes),
        focus_terms=extract_prompt_focus_terms(prompt_text),
        scope_terms=scope_terms,
        generic_scope=generic_scope,
        source_only=source_only,
    )


def determine_primary_mode(raw_modes: list[str], analysis_axes: list[str], has_explicit_scope: bool) -> str:
    mode_set = set(raw_modes)
    primary_candidates: list[str] = []

    if "excel_export" in mode_set:
        primary_candidates.append("excel_export")
    if "source_comparison" in mode_set:
        primary_candidates.append("source_comparison")
    if {"least_reacted_post", "least_viewed_post", "underperforming_posts_bucket"} & mode_set:
        primary_candidates.append("post_underperformance")
    if {
        "most_discussed_news",
        "most_reacted_post",
        "most_viewed_post",
        "successful_posts_bucket",
        "specific_news_answer",
    } & mode_set:
        primary_candidates.append("post_popularity")
    if {
        "negative_analysis",
        "positive_analysis",
        "support_analysis",
        "complaints_analysis",
        "concerns_analysis",
        "polarization_analysis",
    } & mode_set:
        primary_candidates.append("theme_sentiment")
    if "interest_analysis" in mode_set:
        primary_candidates.append("theme_interest")
    if "theme_analysis" in mode_set or has_explicit_scope:
        primary_candidates.append("topic_report")

    if not primary_candidates:
        if "source_metrics" in analysis_axes and "post_scope" not in analysis_axes and "comment_reaction" not in analysis_axes:
            primary_candidates.append("source_comparison")
        elif "post_scope" in analysis_axes and "comment_reaction" in analysis_axes:
            primary_candidates.append("theme_sentiment")
        elif "post_scope" in analysis_axes:
            primary_candidates.append("topic_report")
        else:
            primary_candidates.append("topic_report")

    if any(mode in primary_candidates for mode in {"source_comparison", "post_popularity", "post_underperformance", "theme_sentiment", "theme_interest"}):
        primary_candidates = [mode for mode in primary_candidates if mode != "topic_report"]

    ordered = [mode for mode in PRIMARY_MODE_PRIORITY if mode in primary_candidates]
    if len(ordered) == 1:
        return ordered[0]
    if len(ordered) > 1:
        return "mixed"
    return "topic_report"


def determine_secondary_modes(raw_modes: list[str], primary_mode: str, has_explicit_scope: bool) -> list[str]:
    raw_set = set(raw_modes)
    secondary: list[str] = []

    if primary_mode != "source_comparison" and "source_comparison" in raw_set:
        secondary.append("source_comparison")
    if primary_mode != "post_popularity" and {
        "most_discussed_news",
        "most_reacted_post",
        "most_viewed_post",
        "successful_posts_bucket",
        "specific_news_answer",
    } & raw_set:
        secondary.append("post_popularity")
    if primary_mode != "post_underperformance" and {
        "least_reacted_post",
        "least_viewed_post",
        "underperforming_posts_bucket",
    } & raw_set:
        secondary.append("post_underperformance")
    if primary_mode != "theme_sentiment" and {
        "negative_analysis",
        "positive_analysis",
        "support_analysis",
        "complaints_analysis",
        "concerns_analysis",
        "polarization_analysis",
    } & raw_set:
        secondary.append("theme_sentiment")
    if primary_mode != "theme_interest" and "interest_analysis" in raw_set:
        secondary.append("theme_interest")
    if primary_mode != "topic_report" and ("theme_analysis" in raw_set or has_explicit_scope):
        secondary.append("topic_report")
    if "causal_explanation" in raw_set:
        secondary.append("causal_explanation")
    if "comparison" in raw_set:
        secondary.append("comparison")
    if "periodic_report" in raw_set:
        secondary.append("periodic_report")
    if "takeaways_analysis" in raw_set:
        secondary.append("takeaways_analysis")

    deduped: list[str] = []
    for mode in secondary:
        if mode not in deduped:
            deduped.append(mode)
    return deduped


def _has_post_level_mode(raw_modes: list[str]) -> bool:
    return bool(
        {
            "most_discussed_news",
            "most_reacted_post",
            "most_viewed_post",
            "least_reacted_post",
            "least_viewed_post",
            "successful_posts_bucket",
            "underperforming_posts_bucket",
            "specific_news_answer",
            "theme_analysis",
        }
        & set(raw_modes)
    )


def _has_reaction_mode(raw_modes: list[str]) -> bool:
    return bool(
        {
            "negative_analysis",
            "positive_analysis",
            "support_analysis",
            "complaints_analysis",
            "concerns_analysis",
            "polarization_analysis",
            "interest_analysis",
        }
        & set(raw_modes)
    )


def _titleize_phrase(value: str) -> str:
    cleaned = (value or "").strip(" -_.,;:!?")
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]
