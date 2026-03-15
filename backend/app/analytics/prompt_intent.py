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
    "года",
    "год",
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
    "который",
    "которая",
    "которые",
    "которое",
    "которого",
    "которых",
    "больше",
    "меньше",
    "собрал",
    "собрала",
    "собрали",
    "собрало",
    "набрала",
    "набрали",
    "получил",
    "получила",
    "получили",
    "найди",
    "найти",
    "покажи",
    "показать",
    "определи",
    "выдели",
    "выяви",
    "расскажи",
    "объясни",
    "сделай",
    "нужно",
    "надо",
    "хочу",
    "ли",
    "наиболее",
    "самой",
    "неделю",
}

GENERIC_PROMPT_SCOPE_TERMS = {
    "новость",
    "новости",
    "пост",
    "посты",
    "люди",
    "думают",
    "думать",
    "была",
    "были",
    "самая",
    "самой",
    "самый",
    "обсуждаемая",
    "обсуждаемой",
    "обсуждаемый",
    "обсуждали",
    "мнение",
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
    "аудитория канала",
    "размер канала",
    "реакции",
    "реакция",
    "лайки",
    "лайков",
    "репосты",
    "репостов",
    "сравни",
    "сравнить",
}

POST_SCOPE_TERMS = {
    "новость",
    "новости",
    "пост",
    "посты",
    "публикация",
    "публикации",
    "тема",
    "темы",
    "сюжет",
    "сюжеты",
    "обсуждаемая",
    "обсуждаемый",
    "обсуждение",
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


@dataclass(frozen=True)
class PromptIntent:
    prompt_text: str
    normalized_text: str
    analysis_axes: list[str]
    prompt_mode: list[str]
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
    tokens = re.findall(r"[a-zа-я0-9-]{4,}", prompt)
    seen: list[str] = []
    for token in tokens:
        if token in PROMPT_STOPWORDS:
            continue
        if token not in seen:
            seen.append(token)
    return [_titleize_phrase(token) for token in seen[:8]]


def extract_prompt_scope_terms(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return []
    tokens = re.findall(r"[a-zа-я0-9-]{4,}", prompt)
    ordered: list[str] = []
    for token in tokens:
        if token in PROMPT_STOPWORDS:
            continue
        if token not in ordered:
            ordered.append(token)
    return ordered[:8]


def infer_analysis_axes(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    if not prompt:
        return ["general"]

    axes: list[str] = []
    if any(term in prompt for term in SOURCE_METRIC_TERMS):
        axes.append("source_metrics")
    if any(term in prompt for term in POST_SCOPE_TERMS):
        axes.append("post_scope")
    if any(term in prompt for term in COMMENT_REACTION_TERMS):
        axes.append("comment_reaction")
    return axes or ["general"]


def infer_prompt_mode(prompt_text: str | None) -> list[str]:
    prompt = normalize_prompt_text(prompt_text)
    modes: list[str] = []
    patterns = [
        (r"сам[а-я]* обсужда", "most_discussed_news"),
        (r"наиболее обсужда", "most_discussed_news"),
        (r"какая новость", "specific_news_answer"),
        (r"какие новости", "specific_news_answer"),
        (r"в каком канале|какой канал|какое сообщество|какой источник", "source_comparison"),
        (r"активн[а-я]* аудитори", "source_comparison"),
        (r"сравн.*канал|сравн.*сообществ|сравн.*источник", "source_comparison"),
        (r"интерес|вовлеч|резонанс", "interest_analysis"),
        (r"негатив|эмоци|критик|возмущ|раздраж", "negative_analysis"),
        (r"позитив|нрав|одобр|поддерж", "positive_analysis"),
        (r"тем[аы]|сюжет", "theme_analysis"),
        (r"сравн|отлич|разниц", "comparison"),
        (r"причин|почему", "causal_explanation"),
        (r"поддержива|одобр|хвал|благодар", "support_analysis"),
        (r"жалоб|претензи|критикуют|ругают|недоволь", "complaints_analysis"),
        (r"опасени|тревог|боят|страх|риски", "concerns_analysis"),
        (r"конфликт|спор|поляриз|раздел", "polarization_analysis"),
        (r"главн|ключев|основн.*вывод", "takeaways_analysis"),
    ]
    for pattern, mode in patterns:
        if re.search(pattern, prompt) and mode not in modes:
            modes.append(mode)
    return modes or ["general_analysis"]


def infer_request_contract(prompt_text: str | None) -> list[str]:
    modes = infer_prompt_mode(prompt_text)
    instructions: list[str] = []

    if "most_discussed_news" in modes:
        instructions.append(
            "Определи конкретную новость или пост с наибольшим объемом обсуждения и объясни, по каким признакам она лидирует."
        )
    if "source_comparison" in modes:
        instructions.append(
            "Сравни каналы, сообщества или источники между собой и назови, где аудитория активнее по совокупности комментариев, реакций или лайков и репостов."
        )
    if "interest_analysis" in modes:
        instructions.append("Определи, какие темы и новости вызывают наибольший интерес аудитории.")
    if "negative_analysis" in modes:
        instructions.append("Определи, какие темы и новости вызывают негативные эмоции или критику.")
    if "positive_analysis" in modes:
        instructions.append("Определи, какие темы и сюжеты аудитория воспринимает скорее позитивно.")
    if "support_analysis" in modes:
        instructions.append("Определи, какие решения, сюжеты или действия аудитория поддерживает или одобряет.")
    if "complaints_analysis" in modes:
        instructions.append("Определи, на что именно люди жалуются и в чем состоят основные претензии.")
    if "concerns_analysis" in modes:
        instructions.append("Определи, что вызывает тревогу, опасения или настороженность аудитории.")
    if "polarization_analysis" in modes:
        instructions.append("Покажи, где мнения аудитории расходятся и какие сюжеты вызывают полярную реакцию.")
    if "theme_analysis" in modes:
        instructions.append("Выдели реальные темы самих новостей и постов, а не случайные слова из комментариев.")
    if "comparison" in modes:
        instructions.append("Сравни реакцию аудитории между основными темами и объясни различия.")
    if "causal_explanation" in modes:
        instructions.append("Объясни причины реакции аудитории на основе содержания постов и комментариев.")
    if "takeaways_analysis" in modes:
        instructions.append("Сформулируй главные содержательные выводы, а не только перечисление метрик.")

    if not instructions:
        instructions.append(
            "Дай конкретный аналитический ответ на запрос пользователя, опираясь на темы постов и реакцию аудитории."
        )
    return instructions


def build_answer_strategy(prompt_text: str | None, analysis_axes: list[str] | None = None) -> dict:
    prompt = normalize_prompt_text(prompt_text)
    axes = set(analysis_axes or [])
    response_shape = "analysis_note"
    first_sentence_rule = "Начни с прямого ответа на пользовательский запрос."
    must_cover: list[str] = []

    if re.search(r"сам[а-я]* обсужда|наиболее обсужда", prompt):
        response_shape = "single_lead_item"
        first_sentence_rule = "Начни с самой обсуждаемой новости или поста и назови ее прямо в первом предложении."
        must_cover.extend(
            [
                "Назови конкретную новость или пост-лидер.",
                "Объясни, почему именно этот сюжет стал самым обсуждаемым.",
            ]
        )
    elif re.search(r"в каком канале|какой канал|какое сообщество|какой источник|активн[а-я]* аудитори|сравн.*канал|сравн.*сообществ|сравн.*источник", prompt):
        response_shape = "source_comparison"
        first_sentence_rule = "Сразу назови канал или сообщество с самой активной аудиторией и объясни, по каким метрикам он лидирует."
        must_cover.extend(
            [
                "Назови канал или сообщество-лидер.",
                "Сравни его с другими источниками по комментариям, реакциям или лайкам и репостам.",
            ]
        )
    elif re.search(r"топ|рейтинг|какие новости|какие темы", prompt):
        response_shape = "ranked_or_grouped_answer"
        first_sentence_rule = "Сразу назови ключевые темы или лидирующие новости, без вступительной воды."
        must_cover.append("Сгруппируй или ранжируй ключевые темы и новости по смыслу запроса.")

    if re.search(r"сравн|разниц|отлич", prompt):
        response_shape = "comparison"
        first_sentence_rule = "Сначала назови главную разницу между объектами сравнения."
        must_cover.append("Покажи различия между темами, сюжетами или типами реакции.")

    if re.search(r"почему|причин", prompt):
        must_cover.append("Объясни причины реакции аудитории, а не только факт реакции.")
    if re.search(r"интерес|вовлеч|резонанс", prompt):
        must_cover.append("Ответь, что именно вызывает интерес аудитории.")
    if re.search(r"негатив|эмоци|критик|возмущ|раздраж", prompt):
        must_cover.append("Ответь, что именно вызывает негативные эмоции.")
    if re.search(r"позитив|нрав|одобр|поддерж", prompt):
        must_cover.append("Ответь, что аудитория воспринимает позитивно.")
    if re.search(r"жалоб|претензи|недоволь|ругают", prompt):
        must_cover.append("Покажи основные жалобы и претензии аудитории.")
    if re.search(r"опасени|тревог|боят|страх|риски", prompt):
        must_cover.append("Покажи, какие риски и опасения люди видят в обсуждаемых сюжетах.")
    if re.search(r"конфликт|спор|поляриз|раздел", prompt):
        must_cover.append("Покажи, какие темы вызывают наиболее полярную реакцию.")
    if re.search(r"вывод|итог|резюме", prompt):
        must_cover.append("Сформулируй короткий содержательный итог по запросу.")
    if "source_metrics" in axes and "post_scope" not in axes and "comment_reaction" not in axes:
        must_cover.append("Опирайся прежде всего на метрики источников, а не на один отдельный пост.")

    if not must_cover:
        must_cover.append("Дай максимально прямой и полезный ответ на пользовательский запрос.")

    return {
        "response_shape": response_shape,
        "first_sentence_rule": first_sentence_rule,
        "must_cover": must_cover,
    }


def build_prompt_intent(prompt_text: str | None, has_explicit_scope: bool = False) -> PromptIntent:
    normalized_text = normalize_prompt_text(prompt_text)
    analysis_axes = infer_analysis_axes(prompt_text)
    scope_terms = extract_prompt_scope_terms(prompt_text)
    generic_scope = not [term for term in scope_terms if term not in GENERIC_PROMPT_SCOPE_TERMS]
    prompt_mode = infer_prompt_mode(prompt_text)
    if "most_discussed_news" in prompt_mode or "specific_news_answer" in prompt_mode:
        generic_scope = True
    source_only = (
        "source_metrics" in analysis_axes
        and "post_scope" not in analysis_axes
        and "comment_reaction" not in analysis_axes
        and not has_explicit_scope
    )
    return PromptIntent(
        prompt_text=(prompt_text or "").strip(),
        normalized_text=normalized_text,
        analysis_axes=analysis_axes,
        prompt_mode=prompt_mode,
        request_contract=infer_request_contract(prompt_text),
        answer_strategy=build_answer_strategy(prompt_text, analysis_axes),
        focus_terms=extract_prompt_focus_terms(prompt_text),
        scope_terms=scope_terms,
        generic_scope=generic_scope,
        source_only=source_only,
    )


def _titleize_phrase(phrase: str) -> str:
    parts = [part for part in phrase.split() if part]
    if not parts:
        return phrase
    return " ".join(parts).capitalize()
