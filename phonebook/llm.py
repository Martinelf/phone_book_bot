from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import requests

from phonebook.config import get_settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json_mapping(filename: str) -> dict[str, str]:
    payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in payload.items()}


def _load_json_object(filename: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9\s-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


NAME_ALIASES = {
    normalize_text(alias): normalize_text(canonical)
    for alias, canonical in _load_json_mapping("name_aliases.json").items()
}

BASE_DEPARTMENT_ALIASES = {
    normalize_text(alias): normalize_text(canonical)
    for alias, canonical in _load_json_mapping("department_aliases.json").items()
}

CORPORATE_SEMANTICS = {
    normalize_text(alias): {
        "department_hint": normalize_text((payload or {}).get("department_hint")),
        "match_variants": [
            normalize_text(item)
            for item in (payload or {}).get("match_variants", [])
            if normalize_text(item)
        ],
    }
    for alias, payload in _load_json_object("corporate_semantics.json").items()
}

POSITION_HINTS = {
    "админ": "администратор",
    "сисадмин": "системный администратор",
    "devops": "devops",
    "аналитик": "аналитик",
    "рекрутер": "рекрутер",
    "юрист": "юрист",
    "саппорт": "поддержка",
    "поддержка": "поддержка",
    "продаж": "продажи",
    "менеджер": "менеджер",
    "начальник": "начальник",
    "начальница": "начальник",
    "директор": "руководитель",
    "руководитель": "руководитель",
    "инженер": "инженер",
}

DEPARTMENT_HINTS = {
    "ит": "ит",
    "айти": "айти",
    "инфра": "инфра",
    "финанс": "финансы",
    "закуп": "закупки",
    "кадр": "кадры",
    "hr": "hr",
    "аналит": "аналитика",
    "data": "data",
    "пингвин": "пингвины",
    "поляр": "полярники",
    "саппорт": "саппорт",
    "поддерж": "поддержка",
    "продаж": "продажи",
    "юрист": "юристы",
}

EASTER_EGG_ALIASES = {
    "тони": ("аленид",),
}

LAST_NAME_ENDINGS = (
    "ов",
    "ова",
    "ев",
    "ева",
    "ин",
    "ина",
    "ын",
    "ына",
    "ский",
    "ская",
    "цкий",
    "цкая",
    "ой",
    "ый",
    "ий",
    "ая",
    "яя",
)

STOPWORDS = {
    "кто",
    "у",
    "нас",
    "нужен",
    "нужна",
    "нужно",
    "найди",
    "найти",
    "ищу",
    "ищите",
    "покажи",
    "подскажи",
    "скажи",
    "дай",
    "дайте",
    "мне",
    "нам",
    "из",
    "с",
    "для",
    "по",
    "от",
    "в",
    "на",
    "тот",
    "та",
    "этот",
    "эта",
    "человек",
    "сотрудник",
    "сотрудника",
    "сотруднику",
    "сотруднике",
    "контакт",
    "контакты",
    "контактный",
    "телефон",
    "телефоны",
    "номер",
    "номера",
    "мобильный",
    "мобильного",
    "доб",
    "добавочный",
    "должность",
    "какой",
    "какая",
    "какое",
    "какого",
    "каком",
    "какую",
    "где",
    "работает",
    "работают",
    "работал",
    "работаете",
    "отдел",
    "отдела",
    "отделе",
    "отделу",
    "отделом",
}


def _contains_normalized_phrase(value: str, phrase: str) -> bool:
    if not value or not phrase:
        return False
    pattern = rf"(?<![a-zа-я0-9]){re.escape(phrase)}(?![a-zа-я0-9])"
    return re.search(pattern, value) is not None


def _build_department_aliases() -> dict[str, str]:
    aliases = dict(BASE_DEPARTMENT_ALIASES)
    for alias, payload in CORPORATE_SEMANTICS.items():
        department_hint = payload.get("department_hint")
        if department_hint:
            aliases[alias] = department_hint
    return aliases


DEPARTMENT_ALIASES = _build_department_aliases()
DEPARTMENT_HINTS = {
    normalize_text(alias): normalize_text(department)
    for alias, department in DEPARTMENT_HINTS.items()
}
DEPARTMENT_HINTS.update(DEPARTMENT_ALIASES)


def _iter_matching_semantics(value: str | None) -> list[dict[str, Any]]:
    normalized = normalize_text(value)
    if not normalized:
        return []

    matching: list[dict[str, Any]] = []
    for alias, payload in CORPORATE_SEMANTICS.items():
        department_hint = payload.get("department_hint") or ""
        match_variants = payload.get("match_variants") or []
        if normalized == alias or normalized == department_hint or normalized in match_variants:
            matching.append(payload)
    return matching


def resolve_department_hint(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None

    aliases = sorted(DEPARTMENT_HINTS.items(), key=lambda item: len(item[0]), reverse=True)
    for alias, department in aliases:
        if _contains_normalized_phrase(normalized, alias):
            return department
    return None


def department_query_variants(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    variants: list[str] = []

    def add(candidate: str | None) -> None:
        candidate_norm = normalize_text(candidate)
        if candidate_norm and candidate_norm not in variants:
            variants.append(candidate_norm)

    add(normalized)
    resolved = resolve_department_hint(normalized)
    add(resolved)

    reference_value = resolved or normalized
    for alias, department in DEPARTMENT_ALIASES.items():
        if department == reference_value:
            add(alias)
            add(department)

    for payload in _iter_matching_semantics(reference_value):
        add(payload.get("department_hint"))
        for variant in payload.get("match_variants") or []:
            add(variant)

    return variants


def department_match_variants(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    variants: list[str] = []

    def add(candidate: str | None) -> None:
        candidate_norm = normalize_text(candidate)
        if candidate_norm and candidate_norm not in variants:
            variants.append(candidate_norm)

    resolved = resolve_department_hint(normalized)
    add(resolved or normalized)

    reference_value = resolved or normalized
    for alias, department in DEPARTMENT_ALIASES.items():
        if department == reference_value:
            add(alias)
            add(department)

    for payload in _iter_matching_semantics(reference_value):
        add(payload.get("department_hint"))
        for variant in payload.get("match_variants") or []:
            add(variant)

    return variants


def _tokenize(value: str) -> list[str]:
    return [token for token in normalize_text(value).split() if token]


def _matches_hint(token: str, hint_key: str) -> bool:
    if len(hint_key) <= 2:
        return token == hint_key
    return token == hint_key or token.startswith(hint_key)


def _normalize_possible_last_name(token: str) -> str:
    if token.endswith(("ову", "еву", "ину")):
        return token[:-1] + "а"
    if token.endswith(("овой", "евой", "иной")):
        return token[:-2] + "а"
    if token.endswith(("скую", "цкую")):
        return token[:-2] + "ая"
    return token


def _pick_last_name_variant(token: str) -> str:
    normalized = normalize_text(token)
    base_variant = _normalize_possible_last_name(token)
    variants = [base_variant, *query_token_variants(token)]
    candidates: list[str] = []
    for variant in variants:
        if variant.endswith(LAST_NAME_ENDINGS) and variant not in candidates:
            candidates.append(variant)
    if not candidates:
        return _normalize_possible_last_name(token)

    preference_groups = (
        (("ову", "ова", "овым", "ове"), ("ова", "ов")),
        (("еву", "ева", "евым", "еве"), ("ева", "ев")),
        (("ину", "ина", "иным", "ине"), ("ина", "ин")),
        (("овой",), ("ова", "ов")),
        (("евой",), ("ева", "ев")),
        (("иной",), ("ина", "ин")),
        (("скому", "ского", "ским"), ("ский",)),
        (("ской", "скую"), ("ская",)),
        (("цкому", "цкого", "цким"), ("цкий",)),
        (("цкой", "цкую"), ("цкая",)),
        (("ого", "ому", "ым", "ом"), ("ой", "ый", "ий")),
        (("ей", "ую"), ("ая", "яя")),
        (("юю",), ("яя",)),
    )

    for sources, preferred_suffixes in preference_groups:
        if normalized.endswith(sources):
            for suffix in preferred_suffixes:
                for candidate in candidates:
                    if candidate.endswith(suffix):
                        return candidate

    if normalized.endswith(LAST_NAME_ENDINGS):
        return normalized

    return candidates[0]


def _generate_known_name_forms(name: str) -> set[str]:
    normalized = normalize_text(name)
    if not normalized:
        return set()

    forms = {normalized}
    hushers = ("г", "к", "х", "ж", "ч", "ш", "щ", "ц")

    if normalized.endswith("ия") and len(normalized) > 3:
        stem = normalized[:-2]
        forms.update({stem + "ии", stem + "ию", stem + "ией", stem + "иею"})
        return forms

    if normalized.endswith("я") and len(normalized) > 2:
        stem = normalized[:-1]
        forms.update({stem + "и", stem + "е", stem + "ю", stem + "ей", stem + "ею"})
        return forms

    if normalized.endswith("а") and len(normalized) > 2:
        stem = normalized[:-1]
        genitive = stem + ("и" if stem.endswith(hushers) else "ы")
        forms.update({genitive, stem + "е", stem + "у", stem + "ой", stem + "ою"})
        return forms

    if normalized.endswith(("й", "ь")) and len(normalized) > 2:
        stem = normalized[:-1]
        forms.update({stem + "я", stem + "ю", stem + "ем", stem + "е"})
        return forms

    if normalized[-1].isalpha():
        forms.update({normalized + "а", normalized + "у", normalized + "ом", normalized + "е"})

    return forms


def _build_known_name_forms() -> dict[str, tuple[str, ...]]:
    forms: dict[str, set[str]] = {}

    def register(source: str, canonical: str) -> None:
        related = {normalize_text(source), normalize_text(canonical)}
        for form in _generate_known_name_forms(source):
            forms.setdefault(form, set()).update(related)
        for form in _generate_known_name_forms(canonical):
            forms.setdefault(form, set()).update(related)

    for source, canonical in NAME_ALIASES.items():
        register(source, canonical)

    for source, aliases in EASTER_EGG_ALIASES.items():
        for alias in aliases:
            register(source, alias)

    return {
        form: tuple(sorted(variants, key=lambda item: (item not in NAME_ALIASES.values(), item)))
        for form, variants in forms.items()
    }


KNOWN_NAME_FORMS = _build_known_name_forms()
KNOWN_GIVEN_NAMES = set(NAME_ALIASES.values())


def _add_known_name_case_variants(normalized: str, add_variant) -> None:
    for candidate in KNOWN_NAME_FORMS.get(normalized, ()):
        add_variant(candidate)
        canonical = NAME_ALIASES.get(candidate)
        if canonical:
            add_variant(canonical)


def _add_generic_name_case_variants(normalized: str, add_variant) -> None:
    if len(normalized) <= 2:
        return

    if normalized.endswith(("а", "я", "у", "ю", "е", "ем", "ом", "ам", "ям")):
        return

    if normalized.endswith("ь"):
        stem = normalized[:-1]
        add_variant(stem + "я")
        add_variant(stem + "ю")
        add_variant(stem + "ем")
        add_variant(stem + "е")
        return

    if normalized.endswith("й"):
        stem = normalized[:-1]
        add_variant(stem + "я")
        add_variant(stem + "ю")
        add_variant(stem + "ем")
        add_variant(stem + "е")
        return

    if normalized[-1].isalpha() and normalized[-1] not in {"а", "я", "й", "ь", "о", "е", "и", "ы", "у", "ю"}:
        add_variant(normalized + "а")
        add_variant(normalized + "у")
        add_variant(normalized + "ом")
        add_variant(normalized + "е")


def query_token_variants(token: str | None) -> list[str]:
    normalized = normalize_text(token)
    if not normalized:
        return []

    variants: list[str] = []

    def add(value: str) -> None:
        if value and len(value) > 1 and value not in variants:
            variants.append(value)

    looks_like_known_name = normalized in KNOWN_GIVEN_NAMES or normalized in KNOWN_NAME_FORMS

    add(normalized)
    add(_normalize_possible_last_name(normalized))

    if normalized.endswith("ого") and len(normalized) > 4:
        stem = normalized[:-3]
        add(stem + "ий")
        add(stem + "ый")
        add(stem + "ой")
    if normalized.endswith("ему") and len(normalized) > 4:
        stem = normalized[:-3]
        add(stem + "ий")
        add(stem + "ый")
        add(stem + "ой")
    if normalized.endswith("ым") and len(normalized) > 3:
        stem = normalized[:-2]
        add(stem + "ый")
        add(stem + "ой")
    if normalized.endswith("им") and len(normalized) > 3:
        add(normalized[:-2] + "ий")
    if normalized.endswith("ом") and len(normalized) > 3:
        stem = normalized[:-2]
        add(stem + "ий")
        add(stem + "ый")
        add(stem + "ой")
    if normalized.endswith("ой") and len(normalized) > 3 and not looks_like_known_name:
        add(normalized[:-2] + "ая")
    if normalized.endswith("ей") and len(normalized) > 3 and not looks_like_known_name:
        add(normalized[:-2] + "яя")
        add(normalized[:-2] + "ая")
    if normalized.endswith("ую") and len(normalized) > 3 and not looks_like_known_name:
        add(normalized[:-2] + "ая")
    if normalized.endswith("юю") and len(normalized) > 3 and not looks_like_known_name:
        add(normalized[:-2] + "яя")

    for source, target in (
        ("ову", "ов"),
        ("ова", "ов"),
        ("овой", "ова"),
        ("овым", "ов"),
        ("ове", "ов"),
        ("еву", "ев"),
        ("ева", "ев"),
        ("евой", "ева"),
        ("евым", "ев"),
        ("еве", "ев"),
        ("ину", "ин"),
        ("ина", "ин"),
        ("иной", "ина"),
        ("иным", "ин"),
        ("ине", "ин"),
        ("скому", "ский"),
        ("ского", "ский"),
        ("ским", "ский"),
        ("ской", "ская"),
        ("скую", "ская"),
    ):
        if normalized.endswith(source) and len(normalized) > len(source) + 1:
            add(normalized[: -len(source)] + target)

    for source, target in (
        ("овича", "ович"),
        ("овичу", "ович"),
        ("овичем", "ович"),
        ("евича", "евич"),
        ("евичу", "евич"),
        ("евичем", "евич"),
        ("ича", "ич"),
        ("ичу", "ич"),
        ("ичем", "ич"),
        ("овны", "овна"),
        ("овне", "овна"),
        ("овной", "овна"),
        ("евны", "евна"),
        ("евне", "евна"),
        ("евной", "евна"),
        ("ичной", "ична"),
        ("ичне", "ична"),
    ):
        if normalized.endswith(source) and len(normalized) > len(source) + 1:
            add(normalized[: -len(source)] + target)

    if normalized.endswith("ия") and len(normalized) > 3:
        add(normalized[:-2] + "ий")
    if normalized.endswith("ея") and len(normalized) > 3:
        add(normalized[:-2] + "ей")
    if normalized.endswith("а") and len(normalized) > 3:
        add(normalized[:-1])
    if normalized.endswith("я") and len(normalized) > 3:
        stem = normalized[:-1]
        add(stem)
        add(stem + "й")
        add(stem + "ь")
    if normalized.endswith("ю") and len(normalized) > 3:
        add(normalized[:-1] + "я")
        add(normalized[:-1] + "й")
        add(normalized[:-1] + "ь")
    if normalized.endswith("е") and len(normalized) > 3:
        add(normalized[:-1] + "й")
        add(normalized[:-1] + "ь")
    if normalized.endswith("ем") and len(normalized) > 4:
        add(normalized[:-2] + "й")
        add(normalized[:-2] + "ь")

    _add_known_name_case_variants(normalized, add)
    _add_generic_name_case_variants(normalized, add)

    for alias in EASTER_EGG_ALIASES.get(normalized, ()):
        add(alias)

    return variants


def _extract_json(raw_text: str) -> dict[str, Any]:
    if not raw_text:
        return {}

    candidate = raw_text.strip()
    fenced = re.search(r"```json\s*(.*?)\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        generic = re.search(r"\{[\s\S]*\}", candidate)
        if generic:
            candidate = generic.group(0).strip()

    parsed = json.loads(candidate)
    return parsed if isinstance(parsed, dict) else {}


def heuristic_parse_query(user_input: str) -> dict[str, Any]:
    normalized = normalize_text(user_input)
    tokens = _tokenize(user_input)

    first_name = None
    last_name = None
    patronymic = None
    position_hint = None
    department_hint = resolve_department_hint(normalized)

    for token in tokens:
        for variant in query_token_variants(token):
            if variant in NAME_ALIASES:
                first_name = NAME_ALIASES[variant]
                break
        if first_name:
            break

    for token in tokens:
        token_variants = query_token_variants(token)
        looks_like_department = any(key in variant for variant in token_variants for key in DEPARTMENT_HINTS)
        looks_like_position = any(key in variant for variant in token_variants for key in POSITION_HINTS)
        normalized_last_name = _pick_last_name_variant(token)
        if (
            normalized_last_name.endswith(LAST_NAME_ENDINGS)
            and token not in STOPWORDS
            and not looks_like_department
            and not looks_like_position
        ):
            last_name = normalized_last_name
            break

    for token in tokens:
        for variant in query_token_variants(token):
            if variant.endswith(("ович", "евич", "ична", "овна", "евна")):
                patronymic = variant
                break
        if patronymic:
            break

    for token in tokens:
        for key, value in POSITION_HINTS.items():
            if _matches_hint(token, key):
                position_hint = value
                break
        if position_hint:
            break

    if not department_hint:
        for token in tokens:
            for key, value in DEPARTMENT_HINTS.items():
                if _matches_hint(token, key):
                    department_hint = value
                    break
            if department_hint:
                break

    if last_name and position_hint and last_name.endswith(("ова", "ева", "ина")):
        last_name = last_name[:-1]

    phrase_match = re.search(r"(?:из|из отдела|из департамента)\s+([a-zа-я0-9\s-]{3,40})", normalized)
    if phrase_match and not department_hint:
        phrase_hint = phrase_match.group(1).strip()
        department_hint = resolve_department_hint(phrase_hint) or phrase_hint

    reserved_terms = (
        set(query_token_variants(first_name))
        | set(query_token_variants(last_name))
        | set(query_token_variants(patronymic))
        | set(query_token_variants(position_hint))
    )
    for department_variant in department_query_variants(department_hint):
        reserved_terms.update(_tokenize(department_variant))

    general_terms: list[str] = []
    for token in tokens:
        if token in STOPWORDS or len(token) <= 2:
            continue
        for variant in query_token_variants(token):
            if (
                variant in STOPWORDS
                or len(variant) <= 2
                or variant in reserved_terms
                or variant in general_terms
            ):
                continue
            general_terms.append(variant)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "patronymic": patronymic,
        "position_hint": position_hint,
        "department_hint": department_hint,
        "general_terms": general_terms[:8],
        "source": "heuristic",
    }


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    ollama_url = settings["ollama_url"].rstrip("/")
    model = settings["ollama_model"]

    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.0},
    }

    try:
        response = requests.post(f"{ollama_url}/api/chat", json=chat_payload, timeout=12)
        if response.status_code == 404:
            raise requests.HTTPError("404_not_found", response=response)
        response.raise_for_status()
        payload = response.json()
        return ((payload.get("message") or {}).get("content")) or ""
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        if response is None or response.status_code != 404:
            raise

    generate_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}\n\nASSISTANT:\n"
    generate_payload = {
        "model": model,
        "prompt": generate_prompt,
        "stream": False,
        "options": {"temperature": 0.0},
    }
    response = requests.post(f"{ollama_url}/api/generate", json=generate_payload, timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload.get("response", "") or ""


def parse_query_with_llm(user_input: str) -> dict[str, Any]:
    heuristic_result = heuristic_parse_query(user_input)

    system_prompt = (
        "Ты разбираешь пользовательские запросы для телефонного справочника сотрудников. "
        "Твоя задача: извлечь только признаки поиска и вернуть только JSON."
    )
    user_prompt = f"""
Разбери запрос пользователя и верни JSON со строго такими ключами:
- first_name: имя или null
- last_name: фамилия или null
- patronymic: отчество или null
- position_hint: должность или роль, если она упоминается
- department_hint: отдел или подразделение, если оно упоминается
- general_terms: массив важных слов для поиска, без стоп-слов

Правила:
- Если в запросе прозвище вроде "Леха", можешь нормализовать до официального имени.
- Не придумывай ничего, чего нет в запросе.
- Ответ только JSON, без markdown.

Запрос: "{user_input}"
""".strip()

    try:
        raw_text = _call_ollama(system_prompt, user_prompt)
        parsed = _extract_json(raw_text)
        if not parsed:
            return heuristic_result

        parsed["first_name"] = normalize_text(parsed.get("first_name"))
        parsed["last_name"] = normalize_text(parsed.get("last_name"))
        parsed["patronymic"] = normalize_text(parsed.get("patronymic"))
        parsed["position_hint"] = normalize_text(parsed.get("position_hint"))
        parsed_department_hint = normalize_text(parsed.get("department_hint"))
        parsed["department_hint"] = resolve_department_hint(parsed_department_hint) or parsed_department_hint
        parsed["general_terms"] = [
            normalize_text(item)
            for item in (parsed.get("general_terms") or [])
            if normalize_text(item)
        ][:8]
        parsed["source"] = "llm"

        if not any(
            [
                parsed.get("first_name"),
                parsed.get("last_name"),
                parsed.get("patronymic"),
                parsed.get("position_hint"),
                parsed.get("department_hint"),
                parsed.get("general_terms"),
            ]
        ):
            return heuristic_result
        return parsed
    except Exception:
        return heuristic_result
