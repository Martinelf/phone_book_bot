from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from phonebook.config import get_settings
from phonebook.db import execute_query
from phonebook.llm import STOPWORDS, normalize_text, parse_query_with_llm, query_token_variants

logger = logging.getLogger(__name__)


@dataclass
class SearchDecision:
    status: str
    message: str
    results: list[dict[str, Any]]
    parsed_query: dict[str, Any]


def _load_active_rows() -> list[dict[str, Any]]:
    schema = get_settings()["pg_schema"]
    query = f"""
        SELECT
            id_phone_directory,
            last_name,
            first_name,
            patronymic,
            phone,
            phone_ext,
            mobile_phone,
            email,
            department_id,
            department_name,
            post,
            is_active,
            created_at,
            person_aliases,
            department_aliases
        FROM {schema}.phone_directory_search
        WHERE is_active = TRUE
    """
    return execute_query(query) or []


def _contains(candidate_value: str, expected_value: str) -> bool:
    candidate_norm = normalize_text(candidate_value)
    expected_norm = normalize_text(expected_value)
    if not candidate_norm or not expected_norm:
        return False
    return expected_norm in candidate_norm


def _contains_any(candidate_value: str, expected_values: list[str]) -> bool:
    return any(_contains(candidate_value, value) for value in expected_values if value)


def _token_set(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if token}


def _matches_name_tokens(candidate_value: str, expected_values: list[str]) -> bool:
    candidate_tokens = _token_set(candidate_value)
    if not candidate_tokens:
        return False
    for value in expected_values:
        if normalize_text(value) in candidate_tokens:
            return True
    return False


def _last_name_variants(value: str | None) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()

    variants = set(query_token_variants(normalized))
    for suffix in ("ова", "ева", "ина"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
            variants.add(normalized[:-1])
            break
    return variants


def _score_token(token: str, row: dict[str, Any]) -> int:
    token_variants = query_token_variants(token)
    fields = {
        "name": " ".join(
            part
            for part in [row.get("last_name"), row.get("first_name"), row.get("patronymic")]
            if part
        ),
        "person_aliases": row.get("person_aliases") or "",
        "department": row.get("department_name") or "",
        "department_aliases": row.get("department_aliases") or "",
        "post": row.get("post") or "",
        "email": row.get("email") or "",
    }

    if _matches_name_tokens(fields["name"], token_variants):
        return 12
    if _matches_name_tokens(fields["person_aliases"], token_variants):
        return 13
    if _contains_any(fields["department"], token_variants) or _contains_any(fields["department_aliases"], token_variants):
        return 9
    if _contains_any(fields["post"], token_variants):
        return 8
    if _contains_any(fields["email"], token_variants):
        return 5
    return 0


def _score_row(row: dict[str, Any], parsed_query: dict[str, Any], original_query: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    has_structured_signal = any(
        parsed_query.get(key)
        for key in ("first_name", "last_name", "patronymic", "position_hint", "department_hint")
    )

    row_first_name = normalize_text(row.get("first_name") or "")
    first_name_raw = normalize_text(parsed_query.get("first_name"))
    first_name_variants = set(query_token_variants(parsed_query.get("first_name")))
    if first_name_raw and row_first_name == first_name_raw:
        score += 35
        reasons.append("совпало имя")
    elif first_name_variants and row_first_name in first_name_variants:
        score += 30
        reasons.append("совпало имя")

    row_last_name = normalize_text(row.get("last_name") or "")
    last_name_raw = normalize_text(parsed_query.get("last_name"))
    last_name_variants = _last_name_variants(parsed_query.get("last_name"))
    if last_name_raw and row_last_name == last_name_raw:
        score += 45
        reasons.append("совпала фамилия")
    elif last_name_variants and row_last_name in last_name_variants:
        score += 40
        reasons.append("совпала фамилия")

    row_patronymic = normalize_text(row.get("patronymic") or "")
    patronymic_raw = normalize_text(parsed_query.get("patronymic"))
    patronymic_variants = set(query_token_variants(parsed_query.get("patronymic")))
    if patronymic_raw and row_patronymic == patronymic_raw:
        score += 20
        reasons.append("совпало отчество")
    elif patronymic_variants and row_patronymic in patronymic_variants:
        score += 16
        reasons.append("совпало отчество")

    if parsed_query.get("position_hint") and _contains(row.get("post") or "", parsed_query["position_hint"]):
        score += 24
        reasons.append("совпала должность")

    if parsed_query.get("position_hint") and parsed_query["position_hint"] != "руководитель":
        if _contains(row.get("post") or "", "руководитель"):
            score -= 10
            reasons.append("штраф за руководящую роль")

    if parsed_query.get("department_hint"):
        department_blob = " ".join(
            item for item in [row.get("department_name"), row.get("department_aliases")] if item
        )
        if _contains_any(department_blob, query_token_variants(parsed_query["department_hint"])):
            score += 24
            reasons.append("совпал отдел")

    for token in parsed_query.get("general_terms") or []:
        token_score = _score_token(token, row)
        if token_score:
            score += token_score
            reasons.append(f"совпало слово '{token}'")

    if score == 0 and not has_structured_signal:
        for token in normalize_text(original_query).split():
            if len(token) <= 2 or token in STOPWORDS:
                continue
            token_score = _score_token(token, row)
            if token_score:
                score += token_score
                reasons.append(f"fallback '{token}'")

    return score, reasons


def search_phonebook(user_input: str, limit: int = 3) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed_query = parse_query_with_llm(user_input)
    rows = _load_active_rows()

    ranked_rows: list[dict[str, Any]] = []
    for row in rows:
        score, reasons = _score_row(row, parsed_query, user_input)
        if score <= 0:
            continue
        ranked_rows.append(
            {
                **row,
                "score": score,
                "reasons": reasons,
            }
        )

    ranked_rows.sort(
        key=lambda item: (
            -item["score"],
            normalize_text(item.get("last_name") or ""),
            normalize_text(item.get("first_name") or ""),
        )
    )
    return ranked_rows[:limit], parsed_query


def resolve_phonebook_query(user_input: str, limit: int = 3) -> SearchDecision:
    results, parsed_query = search_phonebook(user_input, limit=limit)
    if results:
        decision = SearchDecision(
            status="found",
            message="Найдены сотрудники.",
            results=results,
            parsed_query=parsed_query,
        )
    else:
        decision = SearchDecision(
            status="not_found",
            message="Ничего не найдено.",
            results=[],
            parsed_query=parsed_query,
        )

    logger.info(
        "query=%r source=%s status=%s parsed=%s top_ids=%s",
        user_input,
        parsed_query.get("source", "unknown"),
        decision.status,
        parsed_query,
        [row["id_phone_directory"] for row in results[:3]],
    )
    return decision


def _format_person(row: dict[str, Any]) -> str:
    full_name = " ".join(part for part in [row.get("last_name"), row.get("first_name"), row.get("patronymic")] if part)
    lines = [full_name]

    if row.get("post"):
        lines.append(f"  Должность: {row['post']}")
    if row.get("department_name"):
        lines.append(f"  Отдел: {row['department_name']}")
    if row.get("phone"):
        phone_line = f"  Телефон: {row['phone']}"
        if row.get("phone_ext"):
            phone_line += f" доб. {row['phone_ext']}"
        lines.append(phone_line)
    if row.get("mobile_phone"):
        lines.append(f"  Мобильный: {row['mobile_phone']}")
    if row.get("email"):
        lines.append(f"  Email: {row['email']}")
    lines.append(f"  Score: {row['score']}")
    return "\n".join(lines)


def handle_user_query(user_input: str) -> None:
    print("\nОбрабатываю запрос...")
    decision = resolve_phonebook_query(user_input)
    results = decision.results
    parsed_query = decision.parsed_query

    debug_view = {
        key: value
        for key, value in parsed_query.items()
        if key != "general_terms" or value
    }
    print(f"Разобрано ({parsed_query.get('source', 'unknown')}): {debug_view}")
    print(f"Режим ответа: {decision.status}")
    print(decision.message)

    if not results:
        return

    print(f"\nНайдено кандидатов: {len(results)}\n")
    for index, row in enumerate(results, start=1):
        print(f"{index}. {_format_person(row)}")
        print()
