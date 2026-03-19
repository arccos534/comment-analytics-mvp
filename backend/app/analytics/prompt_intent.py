from __future__ import annotations

from dataclasses import dataclass, replace
import re

GENERIC_PROMPT_SCOPE_TERMS = {
    "анализ",
    "аналитику",
    "аналитика",
    "анализируй",
    "анализировать",
    "какая",
    "какие",
    "какой",
    "какую",
    "каком",
    "какому",
    "каких",
    "каким",
    "какое",
    "новость",
    "новости",
    "пост",
    "посты",
    "публикация",
    "публикации",
    "аудитория",
    "аудитории",
    "люди",
    "людей",
    "комментарии",
    "комментариев",
    "реакция",
    "реакции",
    "реакцию",
    "тема",
    "темы",
    "сюжет",
    "сюжеты",
    "что",
    "почему",
    "какую",
    "выдели",
    "покажи",
    "найди",
    "отчет",
    "отчёт",
    "который",
    "которая",
    "которые",
    "которому",
    "которых",
    "которым",
    "реагирует",
    "реагируют",
    "относятся",
    "относится",
    "воспринимают",
    "воспринимает",
    "негативно",
    "позитивно",
    "негативной",
    "позитивной",
    "негативную",
    "позитивную",
}

PROMPT_STOPWORDS = GENERIC_PROMPT_SCOPE_TERMS | {
    "больше",
    "меньше",
    "самая",
    "самые",
    "самый",
    "самых",
    "наиболее",
    "наименее",
    "максимальный",
    "минимальный",
    "вызвала",
    "вызвали",
    "вызывают",
    "вызвал",
    "думают",
    "думает",
    "вызвала",
    "реально",
    "нужно",
    "надо",
    "если",
    "только",
    "поэтому",
    "среди",
    "про",
    "это",
    "эту",
    "этой",
    "этот",
    "такой",
    "такие",
    "прошедший",
    "месяц",
    "неделя",
    "неделю",
    "месяца",
    "месяцем",
    "лучший",
    "лучшие",
    "лучшая",
    "лучшего",
    "сильный",
    "сильные",
    "успешный",
    "успешные",
    "популярный",
    "популярные",
    "непопулярные",
    "интерес",
    "интереса",
    "интересом",
    "цепляет",
    "цепляют",
    "зашел",
    "зашла",
    "зашли",
}

PRIMARY_MODE_PRIORITY = [
    "excel_export",
    "source_comparison",
    "post_underperformance",
    "post_popularity",
    "post_sentiment",
    "theme_underperformance",
    "theme_popularity",
    "theme_sentiment",
    "theme_interest",
    "topic_report",
]

RAW_MODE_PATTERNS: list[tuple[str, str]] = [
    (r"(excel|эксель|xlsx|таблиц)", "excel_export"),
    (r"(в каком канале|какой канал|какое сообщество|какой источник)", "source_comparison"),
    (r"(какой канал лучше|какой источник лучше|какое сообщество лучше)", "source_comparison"),
    (r"(сравн\w*).*(канал|сообщество|источник)", "source_comparison"),
    (r"(подписчик|размер аудитории|активная аудитория|активность аудитории)", "source_comparison"),
    (r"(меньше\s+подписчик\w*.*(выше|лучше).*(вовлеч|активн)|низк\w+\s+подписчик\w*.*(вовлеч|активн))", "low_subscribers_high_engagement_request"),
    (
        r"(какой|какая).*(пост|новост|публикац).*(сам\w*|наиболее).*(успешн|сильн|лучш)",
        "successful_post_request",
    ),
    (
        r"(какие|покажи|выдели|найди).*(лучши|сильн|успешн|лучшими?\s+показател).*(пост|публикац)",
        "successful_posts_request",
    ),
    (r"(пост|публикац).*(лучши|сильн|успешн)", "successful_posts_request"),
    (r"(самые\s+сильные\s+публикац|сильнейш\w+\s+публикац|лучшие\s+посты|лучшие\s+публикац)", "successful_posts_request"),
    (
        r"(какая|какой|какие).*(новост|пост|публикац).*(больше|сильн|максим|сам|наибольш|наиболее).*(негатив|критик|жалоб|хуже)",
        "most_negative_post",
    ),
    (r"(негатив|критик|жалоб).*(новост|пост|публикац).*(больше|сильн|максим|сам)", "most_negative_post"),
    (
        r"(какая|какой|какие).*(новост|пост|публикац).*(больше|сильн|максим|сам|наибольш|наиболее).*(позитив|положит|поддерж|одобр|лучше)",
        "most_positive_post",
    ),
    (r"(позитив|положит|поддерж|одобр).*(новост|пост|публикац).*(больше|сильн|максим|сам)", "most_positive_post"),
    (r"(какая новость вызвала лучш\w+ реакц)", "most_positive_post"),
    (r"(какой пост лучше всего заш[её]л аудитории|какой пост лучше всего зашел аудитории)", "most_positive_post"),
    (r"(лучше всего заш[её]л аудитории|лучше всего зашел аудитории|заш[её]л аудитории)", "most_positive_post"),
    (r"(сам\w+\s+обсуждаем|наиболее\s+обсуждаем)", "most_discussed_news"),
    (r"(больше всего|наибольш\w*|максимальн\w*).*(реакц|лайк)", "most_reacted_post"),
    (r"(реакц|лайк).*(больше всего|наибольш\w*|максимальн\w*)", "most_reacted_post"),
    (r"(больше всего|наибольш\w*|максимальн\w*).*(просмотр|охват)", "most_viewed_post"),
    (r"(просмотр|охват).*(больше всего|наибольш\w*|максимальн\w*)", "most_viewed_post"),
    (r"(меньше всего|наименьш\w*|минимальн\w*|худш\w*|слаб\w*).*(реакц|лайк)", "least_reacted_post"),
    (r"(реакц|лайк).*(меньше всего|наименьш\w*|минимальн\w*|худш\w*|слаб\w*)", "least_reacted_post"),
    (r"(меньше всего|наименьш\w*|минимальн\w*|худш\w*|слаб\w*).*(просмотр|охват)", "least_viewed_post"),
    (r"(просмотр|охват).*(меньше всего|наименьш\w*|минимальн\w*|худш\w*|слаб\w*)", "least_viewed_post"),
    (r"(\d+\s*%|\d+\s*процент\w*).*(успешн|популярн).*(пост|публикац)", "successful_posts_bucket"),
    (r"(верхн\w*).*(пост|публикац).*(процент|%)", "successful_posts_bucket"),
    (r"(\d+\s*%|\d+\s*процент\w*).*(неуспешн|непопулярн|слаб\w*|худш\w*).*(пост|публикац)", "underperforming_posts_bucket"),
    (r"(нижн\w*).*(пост|публикац).*(процент|%)", "underperforming_posts_bucket"),
    (r"(\d+\s+)?(сам\w+\s+)?((?<!не)популярн|успешн|сильн).*(тем|сюжет)", "theme_popularity_ranked"),
    (r"(тем|сюжет).*((?<!не)популярн|успешн|сильн)", "theme_popularity_ranked"),
    (r"(\d+\s+)?(сам\w+\s+)?(непопулярн|слаб|худш).*(тем|сюжет)", "theme_underperformance_ranked"),
    (r"(тем|сюжет).*(непопулярн|слаб|худш)", "theme_underperformance_ranked"),
    (r"(какие\s+темы\s+(не\s+вызывают|меньше\s+всего\s+вызывают).*(интерес|вовлеч)|темы.*не\s+интересны\s+аудитории|темы.*меньше\s+всего\s+интересуют)", "theme_low_interest_request"),
    (r"(что сейчас сильнее всего цепля\w+ людей|что сильнее всего цепля\w+ людей|что людей цепля\w+)", "interest_analysis"),
    (r"(интерес|вовлеч|резонанс|цепля\w+|зашл\w+|вкат\w+|хайпан\w+)", "interest_analysis"),
    (r"(негатив|негативн|критик|возмущ|раздраж)", "negative_analysis"),
    (r"(позитив|положит|нрав|одобр|поддерж)", "positive_analysis"),
    (r"(что|как|какие).*(люди|аудитория).*(думают|относятся|воспринимают|реагируют)", "reaction_analysis"),
    (r"(какую|какая|какие|какой).*(реакц|отношен).*(новост|пост|публикац)", "reaction_analysis"),
    (r"(тем|сюжет)", "theme_analysis"),
    (r"(сравн|отлич|разниц)", "comparison"),
    (r"(причин|почему)", "causal_explanation"),
    (r"(поддержива|одобр|хвал|благодар)", "support_analysis"),
    (r"(жалоб|претензи|критикуют|ругают|недоволь)", "complaints_analysis"),
    (r"(опасени|тревог|боят|страх|риск)", "concerns_analysis"),
    (r"(конфликт|спор|поляриз|раздел)", "polarization_analysis"),
    (r"(главн|ключев|основн.*вывод)", "takeaways_analysis"),
    (r"(за\s+(недел|месяц|квартал|год)|прошедш\w+\s+(недел|месяц|квартал|год))", "periodic_report"),
    (r"(какая новость|какой пост|какая публикация|какие новости)", "specific_news_answer"),
]


@dataclass(slots=True)
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


PRIMARY_MODE_REQUIRED_AXES: dict[str, list[str]] = {
    "source_comparison": ["source_metrics"],
    "post_popularity": ["post_scope"],
    "post_underperformance": ["post_scope"],
    "post_sentiment": ["post_scope", "comment_reaction"],
    "theme_sentiment": ["post_scope", "comment_reaction"],
    "theme_interest": ["post_scope", "comment_reaction"],
    "theme_popularity": ["post_scope"],
    "theme_underperformance": ["post_scope"],
    "topic_report": ["post_scope"],
    "mixed": ["post_scope"],
}

REQUESTED_COUNT_WORDS: dict[str, int] = {
    "один": 1,
    "одна": 1,
    "одно": 1,
    "одну": 1,
    "одного": 1,
    "два": 2,
    "две": 2,
    "двух": 2,
    "три": 3,
    "трех": 3,
    "трёх": 3,
    "четыре": 4,
    "четырех": 4,
    "четырёх": 4,
    "пять": 5,
    "пяти": 5,
    "шесть": 6,
    "шести": 6,
    "семь": 7,
    "семи": 7,
    "восемь": 8,
    "восьми": 8,
    "девять": 9,
    "девяти": 9,
    "десять": 10,
    "десяти": 10,
    "пара": 2,
    "пару": 2,
    "двойка": 2,
    "двойку": 2,
    "двойке": 2,
    "тройка": 3,
    "тройку": 3,
    "тройке": 3,
    "пятерка": 5,
    "пятёрка": 5,
    "пятерку": 5,
    "пятёрку": 5,
    "пятерке": 5,
    "пятёрке": 5,
    "десятка": 10,
    "десятку": 10,
    "десятке": 10,
}

REQUESTED_COUNT_WORD_PATTERN = "|".join(
    sorted((re.escape(token) for token in REQUESTED_COUNT_WORDS), key=len, reverse=True)
)


def normalize_prompt_text(value: str | None) -> str:
    return " ".join((value or "").lower().replace("ё", "е").split())


def _tokenize(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return []
    return re.findall(r"[a-zа-я0-9-]{4,}", prompt)


def _titleize_phrase(value: str) -> str:
    value = value.strip()
    return value[:1].upper() + value[1:] if value else value


def extract_prompt_focus_terms(prompt_text: str | None) -> list[str]:
    seen: list[str] = []
    for token in _tokenize(prompt_text):
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
    phrase_patterns = [
        r"(?:про|о|об|по теме|по запросу)\s+([a-zа-я0-9-]{4,}(?:\s+[a-zа-я0-9-]{4,}){0,4})",
        r"«([^»]+)»",
        r"\"([^\"]+)\"",
    ]
    for pattern in phrase_patterns:
        for match in re.finditer(pattern, prompt):
            value = _clean_scope_phrase(match.group(1))
            if value and value not in ordered:
                ordered.append(value)

    for token in _tokenize(prompt):
        if token not in ordered:
            ordered.append(token)

    return [_titleize_phrase(item) for item in ordered[:12]]


def _clean_scope_phrase(value: str) -> str:
    cleaned = value.strip(" .,!?;:-")
    if not cleaned:
        return ""

    tokens = [token for token in cleaned.split() if token]
    trailing_noise = PROMPT_STOPWORDS | {
        "интерес",
        "интереса",
        "интересом",
        "вовлеченности",
        "вовлеченность",
        "популярные",
        "непопулярные",
        "успешные",
        "сильные",
        "лучшие",
        "лучший",
        "метрики",
        "показатели",
        "аудитории",
        "почему",
        "топ",
    }
    while tokens and normalize_prompt_text(tokens[-1]) in trailing_noise:
        tokens.pop()
    return " ".join(tokens).strip()


def extract_requested_percentage(prompt_text: str | None) -> int | None:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return None

    patterns = [
        r"(\d{1,3})\s*%",
        r"(\d{1,3})\s*процент(?:а|ов)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if not match:
            continue
        value = int(match.group(1))
        if 0 < value <= 100:
            return value
    return None


def extract_requested_count(prompt_text: str | None) -> int | None:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return None

    patterns = [
        r"(?:топ|top)\s*(\d{1,2})",
        r"выдел(?:и|ить)?[^0-9]{0,24}(\d{1,2})",
        r"покажи[^0-9]{0,24}(\d{1,2})",
        r"найди[^0-9]{0,24}(\d{1,2})",
        r"(\d{1,2})\s*(?:сам\w+\s+)?(?:пост\w*|тем\w*|сюжет\w*|источник\w*|канал\w*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if not match:
            continue
        value = int(match.group(1))
        if 0 < value <= 50:
            return value

    word_patterns = [
        rf"(?:топ|top)\s*({REQUESTED_COUNT_WORD_PATTERN})\b",
        rf"выдел(?:и|ить)?[^a-zа-я0-9]{{0,24}}({REQUESTED_COUNT_WORD_PATTERN})\b",
        rf"покажи[^a-zа-я0-9]{{0,24}}({REQUESTED_COUNT_WORD_PATTERN})\b",
        rf"найди[^a-zа-я0-9]{{0,24}}({REQUESTED_COUNT_WORD_PATTERN})\b",
        rf"({REQUESTED_COUNT_WORD_PATTERN})\s*(?:сам\w+\s+)?(?:пост\w*|тем\w*|сюжет\w*|источник\w*|канал\w*)",
    ]
    for pattern in word_patterns:
        match = re.search(pattern, prompt)
        if not match:
            continue
        value = REQUESTED_COUNT_WORDS.get(match.group(1))
        if value and 0 < value <= 50:
            return value
    return None


def infer_source_metric(prompt_text: str | None) -> str:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return "engagement"

    if re.search(r"(подписчик|подписчиков|подписчикам|размер аудитории|по аудитории)", prompt):
        return "subscribers"
    if re.search(r"(просмотр|охват)", prompt):
        return "views"
    if re.search(r"(лайк|реакц)", prompt):
        return "likes"
    if re.search(r"(комментар)", prompt):
        return "comments"
    if re.search(r"(репост)", prompt):
        return "reposts"
    return "engagement"


def infer_prompt_mode(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return ["general_analysis"]

    modes: list[str] = []
    for pattern, mode in RAW_MODE_PATTERNS:
        if re.search(pattern, prompt):
            modes.append(mode)

    direct_alias_patterns = [
        (r"(какой\s+пост\s+самый\s+(успешн|сильн|лучш))", "successful_post_request"),
        (r"(какие\s+посты\s+лучши|покажи\s+самые\s+сильные\s+публикац|лучшие\s+публикац)", "successful_posts_request"),
        (r"(какая\s+новость\s+вызвала\s+лучш\w+\s+реакц|какой\s+пост\s+лучше\s+всего\s+зашел\s+аудитории)", "most_positive_post"),
        (r"(что\s+сейчас\s+сильнее\s+всего\s+цепляет\s+людей|что\s+людям\s+(вообще|ваще)\s+заходит|что\s+людям\s+вкатил\w+|что\s+людям\s+зашл\w+|что\s+людям\s+хайпанул\w+)", "interest_analysis"),
        (r"(какие\s+темы\s+не\s+вызывают\s+интерес|какие\s+темы\s+меньше\s+всего\s+интересуют|какие\s+темы\s+вызывают\s+меньше\s+всего\s+интерес)", "theme_low_interest_request"),
        (r"(у\s+какого\s+источника\s+меньше\s+подписчик\w+,\s*но\s+выше\s+вовлеч)", "low_subscribers_high_engagement_request"),
    ]
    for pattern, mode in direct_alias_patterns:
        if re.search(pattern, prompt):
            modes.append(mode)

    has_post_reference = any(token in prompt for token in ("пост", "публикац", "новост"))
    has_percent_reference = "%" in prompt or "процент" in prompt
    if has_post_reference and has_percent_reference:
        if any(token in prompt for token in ("успеш", "популяр", "сильн", "наиболее")):
            modes.append("successful_posts_bucket")
        if any(token in prompt for token in ("неуспеш", "непопуляр", "слаб", "худш", "наименее")):
            modes.append("underperforming_posts_bucket")

    if not modes:
        modes.append("general_analysis")

    deduped: list[str] = []
    for mode in modes:
        if mode not in deduped:
            deduped.append(mode)
    return deduped


def infer_analysis_axes(prompt_text: str | None) -> list[str]:
    modes = set(infer_prompt_mode(prompt_text))
    axes: list[str] = []

    if "source_comparison" in modes:
        axes.append("source_metrics")
    if "low_subscribers_high_engagement_request" in modes and "source_metrics" not in axes:
        axes.append("source_metrics")

    post_related_modes = {
        "most_discussed_news",
        "most_reacted_post",
        "most_viewed_post",
        "least_reacted_post",
        "least_viewed_post",
        "most_negative_post",
        "most_positive_post",
        "successful_posts_bucket",
        "underperforming_posts_bucket",
        "successful_post_request",
        "successful_posts_request",
        "theme_popularity_ranked",
        "theme_underperformance_ranked",
        "theme_low_interest_request",
        "specific_news_answer",
        "theme_analysis",
        "interest_analysis",
        "negative_analysis",
        "positive_analysis",
        "reaction_analysis",
        "general_analysis",
        "periodic_report",
    }
    if modes & post_related_modes:
        axes.append("post_scope")

    comment_modes = {
        "most_negative_post",
        "most_positive_post",
        "negative_analysis",
        "positive_analysis",
        "reaction_analysis",
        "successful_post_request",
        "successful_posts_request",
        "support_analysis",
        "complaints_analysis",
        "concerns_analysis",
        "polarization_analysis",
        "interest_analysis",
    }
    if modes & comment_modes:
        axes.append("comment_reaction")

    if not axes:
        axes.append("general")

    return axes


def infer_request_contract(
    prompt_text: str | None,
    primary_mode: str | None = None,
    secondary_modes: list[str] | None = None,
) -> list[str]:
    axes = infer_analysis_axes(prompt_text)
    raw_modes = infer_prompt_mode(prompt_text)
    primary = primary_mode or determine_primary_mode(raw_modes, axes, has_explicit_scope=False)
    secondary = secondary_modes or []

    contract: list[str] = []
    if primary == "source_comparison":
        contract.extend(
            [
                "answer_source_first",
                "compare_channels_not_posts",
                "use_source_metrics_and_subscribers",
            ]
        )
        if "low_subscribers_high_engagement_request" in set(raw_modes):
            contract.append("highlight_sources_with_smaller_audience_but_higher_engagement")
    elif primary == "post_popularity":
        contract.extend(
            [
                "name_top_posts",
                "rank_posts_by_views_and_reactions",
                "comments_are_secondary",
            ]
        )
        if {"successful_post_request", "successful_posts_request"} & set(raw_modes):
            contract.extend(
                [
                    "score_success_relative_to_project_average",
                    "include_audience_opinion_for_leading_posts",
                ]
            )
    elif primary == "post_underperformance":
        contract.extend(
            [
                "name_weakest_posts",
                "explain_why_posts_underperform",
                "rank_posts_by_low_views_and_reactions",
            ]
        )
    elif primary == "post_sentiment":
        contract.extend(
            [
                "name_post_with_strongest_reaction",
                "distinguish_positive_and_negative_post_reaction",
                "explain_why_audience_responds_this_way",
            ]
        )
    elif primary == "theme_popularity":
        contract.extend(
            [
                "rank_themes_by_post_metrics",
                "show_posts_inside_each_theme",
                "explain_why_top_themes_work",
            ]
        )
    elif primary == "theme_underperformance":
        contract.extend(
            [
                "rank_weak_themes_by_post_metrics",
                "show_posts_inside_each_theme",
                "explain_why_themes_underperform",
            ]
        )
        if "theme_low_interest_request" in set(raw_modes):
            contract.append("rank_themes_by_low_attention_not_only_by_weak_metrics")
    elif primary == "theme_sentiment":
        contract.extend(
            [
                "name_positive_and_negative_themes",
                "use_comments_as_reaction_evidence",
                "explain_reasons_for_sentiment",
            ]
        )
    elif primary == "theme_interest":
        contract.extend(
            [
                "name_themes_with_strongest_attention",
                "use_post_metrics_and_comments",
                "show_themes_first_posts_as_supporting_evidence",
            ]
        )
    else:
        contract.extend(
            [
                "answer_prompt_directly",
                "stay_on_user_topic",
                "use_posts_and_comments_as_evidence",
            ]
        )

    if "causal_explanation" in raw_modes:
        contract.append("must_explain_why")
    if "periodic_report" in raw_modes:
        contract.append("respect_time_period")
    if secondary:
        contract.append("use_secondary_modes_as_support")

    return contract


def build_answer_strategy(
    prompt_text: str | None,
    analysis_axes: list[str] | None = None,
    primary_mode: str | None = None,
    secondary_modes: list[str] | None = None,
) -> dict:
    axes = analysis_axes or infer_analysis_axes(prompt_text)
    raw_modes = infer_prompt_mode(prompt_text)
    primary = primary_mode or determine_primary_mode(raw_modes, list(axes), has_explicit_scope=False)
    secondary = secondary_modes or determine_secondary_modes(raw_modes, primary, has_explicit_scope=False)

    response_shape = "direct_answer_then_analysis"
    first_sentence_rule = "answer_the_question_immediately"
    must_cover: list[str] = []
    metric_priority = ["views", "likes_or_reactions", "comments", "reposts"]

    if primary == "source_comparison":
        response_shape = "leader_and_laggard_source_then_comparison"
        must_cover = ["top_source", "weak_source", "source_metrics", "subscriber_context"]
        if "low_subscribers_high_engagement_request" in set(raw_modes):
            response_shape = "small_audience_high_engagement_sources"
            must_cover = ["top_source", "subscriber_context", "engagement_gap", "supporting_source_metrics"]
    elif primary == "post_popularity":
        response_shape = "top_posts_then_reasons"
        must_cover = ["leading_posts", "views", "likes_or_reactions", "why_they_win"]
        if {"successful_post_request", "successful_posts_request"} & set(raw_modes):
            response_shape = "successful_posts_then_audience_opinion"
            must_cover = [
                "leading_posts",
                "relative_success_against_average",
                "views",
                "likes_or_reactions",
                "audience_opinion",
            ]
    elif primary == "post_underperformance":
        response_shape = "weak_posts_then_reasons"
        must_cover = ["weak_posts", "low_metrics", "why_they_lag"]
    elif primary == "post_sentiment":
        response_shape = "strongest_reaction_post_then_explanation"
        must_cover = ["lead_post", "reaction_direction", "relevant_comments", "why"]
    elif primary == "theme_popularity":
        response_shape = "top_themes_then_supporting_posts"
        must_cover = ["top_themes", "leading_posts", "views", "likes_or_reactions", "why_themes_work"]
    elif primary == "theme_underperformance":
        response_shape = "weak_themes_then_supporting_posts"
        must_cover = ["weak_themes", "supporting_posts", "low_metrics", "why_themes_fail"]
        if "theme_low_interest_request" in set(raw_modes):
            response_shape = "low_interest_themes_then_supporting_posts"
            must_cover = ["weak_themes", "supporting_posts", "low_attention_signals", "why_interest_is_low"]
    elif primary == "theme_sentiment":
        response_shape = "positive_vs_negative_themes"
        must_cover = ["positive_themes", "negative_themes", "reasons"]
    elif primary == "theme_interest":
        response_shape = "top_interest_themes_then_supporting_posts"
        must_cover = ["top_themes", "supporting_posts", "metrics", "why_interest_is_high"]
    elif primary == "topic_report":
        response_shape = "direct_answer_then_thematic_breakdown"
        must_cover = ["direct_answer", "key_themes", "supporting_evidence"]

    if "causal_explanation" in raw_modes and "why" not in must_cover:
        must_cover.append("why")
    if "periodic_report" in raw_modes:
        must_cover.append("time_period")
    if "source_metrics" in axes and "source_metrics" not in must_cover and primary != "source_comparison":
        must_cover.append("source_metrics_if_relevant")
    if secondary:
        must_cover.append("secondary_modes_support")

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
    focus_terms = extract_prompt_focus_terms(prompt_text)
    scope_terms = extract_prompt_scope_terms(prompt_text)
    meaningful_scope_terms = [
        term
        for term in scope_terms
        if normalize_prompt_text(term) not in PROMPT_STOPWORDS
    ]
    emotion_only_scope = bool(meaningful_scope_terms) and all(
        re.search(r"(позитив|негатив|поддерж|одобр|жалоб|критик|интерес|реакц)", normalize_prompt_text(term))
        for term in meaningful_scope_terms
    )

    generic_reaction_question = bool(
        re.search(
            r"(какую|какая|какие|какой|что).*((реакц|думают|воспринимают|относятся|реагируют|вызывают).*(новост|пост|публикац)|(новост|пост|публикац).*(реакц|думают|воспринимают|относятся|реагируют|вызывают))",
            normalized_text,
        )
    )

    generic_scope = not meaningful_scope_terms or emotion_only_scope or primary_mode in {
        "source_comparison",
        "post_popularity",
        "post_underperformance",
        "post_sentiment",
        "theme_interest",
        "theme_popularity",
        "theme_underperformance",
    } or (generic_reaction_question and not focus_terms)

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
        focus_terms=focus_terms,
        scope_terms=scope_terms,
        generic_scope=generic_scope,
        source_only=source_only,
    )


def apply_analysis_mode_override(
    intent: PromptIntent,
    override_mode: str | None,
    has_explicit_scope: bool = False,
) -> PromptIntent:
    override = (override_mode or "").strip()
    if not override:
        return intent

    allowed_modes = set(PRIMARY_MODE_PRIORITY) | {"post_sentiment", "theme_popularity", "theme_underperformance"}
    if override not in allowed_modes:
        return intent

    secondary_modes = [mode for mode in intent.secondary_modes if mode != override]
    analysis_axes = list(intent.analysis_axes)
    for axis in PRIMARY_MODE_REQUIRED_AXES.get(override, []):
        if axis not in analysis_axes:
            analysis_axes.append(axis)

    source_only = override == "source_comparison" and not has_explicit_scope
    generic_scope = intent.generic_scope or override in {
        "source_comparison",
        "post_popularity",
        "post_underperformance",
        "post_sentiment",
        "theme_interest",
        "theme_popularity",
        "theme_underperformance",
    }

    return replace(
        intent,
        analysis_axes=analysis_axes,
        primary_mode=override,
        secondary_modes=secondary_modes,
        request_contract=infer_request_contract(intent.prompt_text, override, secondary_modes),
        answer_strategy=build_answer_strategy(intent.prompt_text, analysis_axes, override, secondary_modes),
        generic_scope=generic_scope,
        source_only=source_only,
    )


def determine_primary_mode(raw_modes: list[str], analysis_axes: list[str], has_explicit_scope: bool) -> str:
    mode_set = set(raw_modes)
    primary_candidates: list[str] = []
    has_explicit_post_sentiment = bool({"most_negative_post", "most_positive_post"} & mode_set)
    single_post_reaction_request = bool("reaction_analysis" in mode_set and ("specific_news_answer" in mode_set or has_explicit_scope))

    if "excel_export" in mode_set:
        primary_candidates.append("excel_export")
    if "source_comparison" in mode_set or "low_subscribers_high_engagement_request" in mode_set:
        primary_candidates.append("source_comparison")
    if {"least_reacted_post", "least_viewed_post", "underperforming_posts_bucket"} & mode_set:
        primary_candidates.append("post_underperformance")
    if {"most_negative_post", "most_positive_post"} & mode_set or single_post_reaction_request:
        primary_candidates.append("post_sentiment")
    if "theme_low_interest_request" in mode_set:
        primary_candidates.append("theme_underperformance")
    if "theme_underperformance_ranked" in mode_set:
        primary_candidates.append("theme_underperformance")
    if "theme_popularity_ranked" in mode_set:
        primary_candidates.append("theme_popularity")

    ranking_modes = {
        "most_discussed_news",
        "most_reacted_post",
        "most_viewed_post",
        "successful_posts_bucket",
        "successful_post_request",
        "successful_posts_request",
    }
    sentiment_modes = {
        "negative_analysis",
        "positive_analysis",
        "support_analysis",
        "complaints_analysis",
        "concerns_analysis",
        "polarization_analysis",
    }
    if ranking_modes & mode_set or (
        "specific_news_answer" in mode_set
        and "reaction_analysis" not in mode_set
        and "interest_analysis" not in mode_set
        and not (sentiment_modes & mode_set)
        and not has_explicit_post_sentiment
    ):
        primary_candidates.append("post_popularity")
    if sentiment_modes & mode_set and not has_explicit_post_sentiment:
        primary_candidates.append("theme_sentiment")
    if "reaction_analysis" in mode_set and not has_explicit_post_sentiment and not single_post_reaction_request:
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

    if any(
        mode in primary_candidates
        for mode in {
            "source_comparison",
            "post_popularity",
            "post_underperformance",
            "post_sentiment",
            "theme_popularity",
            "theme_underperformance",
            "theme_sentiment",
            "theme_interest",
        }
    ):
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
    single_post_reaction_request = bool("reaction_analysis" in raw_set and ("specific_news_answer" in raw_set or has_explicit_scope))

    if primary_mode != "source_comparison" and ("source_comparison" in raw_set or "low_subscribers_high_engagement_request" in raw_set):
        secondary.append("source_comparison")
    if primary_mode != "post_popularity" and {
        "most_discussed_news",
        "most_reacted_post",
        "most_viewed_post",
        "successful_posts_bucket",
        "successful_post_request",
        "successful_posts_request",
        "specific_news_answer",
    } & raw_set:
        secondary.append("post_popularity")
    if primary_mode != "post_underperformance" and {
        "least_reacted_post",
        "least_viewed_post",
        "underperforming_posts_bucket",
    } & raw_set:
        secondary.append("post_underperformance")
    if primary_mode != "post_sentiment" and ({"most_negative_post", "most_positive_post"} & raw_set or single_post_reaction_request):
        secondary.append("post_sentiment")
    if primary_mode != "theme_popularity" and "theme_popularity_ranked" in raw_set:
        secondary.append("theme_popularity")
    if primary_mode != "theme_underperformance" and ({"theme_underperformance_ranked", "theme_low_interest_request"} & raw_set):
        secondary.append("theme_underperformance")
    if primary_mode != "theme_sentiment" and {
        "negative_analysis",
        "positive_analysis",
        "reaction_analysis",
        "support_analysis",
        "complaints_analysis",
        "concerns_analysis",
        "polarization_analysis",
    } & raw_set and not single_post_reaction_request:
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
