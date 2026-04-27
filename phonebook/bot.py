from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from phonebook.audit import write_query_audit
from phonebook.config import get_settings
from phonebook.db import execute_query
from phonebook.decision import decide_search_results
from phonebook.llm import (
    STOPWORDS,
    department_match_variants,
    normalize_text,
    parse_query_with_llm,
    query_token_variants,
)
from phonebook.permissions import mask_search_results, normalize_role

logger = logging.getLogger(__name__)


@dataclass
class SearchContext:
    source: str = "cli"
    external_user_id: str | None = None
    role: str = "admin"


@dataclass
class SearchDecision:
    status: str
    message: str
    results: list[dict[str, Any]]
    parsed_query: dict[str, Any]
    confidence: float = 0.0
    rationale: list[str] = field(default_factory=list)


def _is_vacancy_row(row: dict[str, Any]) -> bool:
    last_name = normalize_text(row.get("last_name") or "")
    first_name = normalize_text(row.get("first_name") or "")
    return last_name.startswith("ваканс") or first_name.startswith("ваканс")


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
            created_at
        FROM {schema}.phone_directory_search
        WHERE is_active = TRUE
    """
    rows = execute_query(query) or []
    return [row for row in rows if not _is_vacancy_row(row)]


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


def _name_stem_variants(value: str) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()

    stems = {normalized}
    for suffix in ("ий", "ей", "ай", "ой", "ья", "ия"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 2:
            stems.add(normalized[: -len(suffix)])
    for suffix in ("я", "ю", "е", "а", "у", "ь", "й"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 2:
            stems.add(normalized[: -len(suffix)])
    for suffix in ("ем", "ом", "ам", "ям"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 2:
            stems.add(normalized[: -len(suffix)])

    return {stem for stem in stems if len(stem) >= 3}


def _soft_given_name_match(candidate_value: str, expected_values: list[str]) -> bool:
    candidate_stems = _name_stem_variants(candidate_value)
    if not candidate_stems:
        return False

    for value in expected_values:
        expected_stems = _name_stem_variants(value)
        shared_stems = candidate_stems & expected_stems
        if any(len(stem) >= 4 for stem in shared_stems):
            return True
    return False


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
    department_variants = department_match_variants(token)
    fields = {
        "first_name": row.get("first_name") or "",
        "name": " ".join(
            part for part in [row.get("last_name"), row.get("first_name"), row.get("patronymic")] if part
        ),
        "department": row.get("department_name") or "",
        "post": row.get("post") or "",
        "email": row.get("email") or "",
    }

    if _matches_name_tokens(fields["name"], token_variants) or _soft_given_name_match(fields["first_name"], token_variants):
        return 12

    structure_text = " ".join(item for item in [fields["department"], fields["post"]] if item)
    if _contains_any(structure_text, department_variants or token_variants):
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
    elif first_name_variants and (row_first_name in first_name_variants or _soft_given_name_match(row_first_name, list(first_name_variants))):
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
        structure_text = " ".join(item for item in [row.get("department_name") or "", row.get("post") or ""] if item)
        if _contains_any(structure_text, department_match_variants(parsed_query["department_hint"])):
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


def search_phonebook(user_input: str, limit: int = 5) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed_query = parse_query_with_llm(user_input)
    rows = _load_active_rows()

    ranked_rows: list[dict[str, Any]] = []
    for row in rows:
        score, reasons = _score_row(row, parsed_query, user_input)
        if score <= 0:
            continue
        ranked_rows.append({**row, "score": score, "reasons": reasons})

    ranked_rows.sort(
        key=lambda item: (
            -item["score"],
            normalize_text(item.get("last_name") or ""),
            normalize_text(item.get("first_name") or ""),
        )
    )
    return ranked_rows[: max(limit, 5)], parsed_query


def resolve_phonebook_query(
    user_input: str,
    limit: int = 3,
    *,
    context: SearchContext | None = None,
) -> SearchDecision:
    active_context = context or SearchContext()
    results, parsed_query = search_phonebook(user_input, limit=max(limit, 5))
    outcome = decide_search_results(parsed_query, results, limit)
    masked_results = mask_search_results(outcome.results, normalize_role(active_context.role))

    decision = SearchDecision(
        status=outcome.status,
        message=outcome.message,
        results=masked_results,
        parsed_query=parsed_query,
        confidence=outcome.confidence,
        rationale=outcome.rationale,
    )

    logger.info(
        "query=%r source=%s user_id=%s role=%s status=%s confidence=%.2f parsed=%s top_ids=%s",
        user_input,
        active_context.source,
        active_context.external_user_id,
        active_context.role,
        decision.status,
        decision.confidence,
        parsed_query,
        [row["id_phone_directory"] for row in results[:3]],
    )

    write_query_audit(
        source=active_context.source,
        external_user_id=active_context.external_user_id,
        role=normalize_role(active_context.role),
        query_text=user_input,
        parsed_query=parsed_query,
        decision_status=decision.status,
        decision_message=decision.message,
        confidence=decision.confidence,
        top_ids=[row["id_phone_directory"] for row in results[:5]],
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

    debug_view = {key: value for key, value in parsed_query.items() if key != "general_terms" or value}
    print(f"Разобрано ({parsed_query.get('source', 'unknown')}): {debug_view}")
    print(f"Режим ответа: {decision.status}")
    print(f"Уверенность: {decision.confidence:.2f}")
    if decision.rationale:
        print(f"Причины: {', '.join(decision.rationale)}")
    print(decision.message)

    if not results:
        return

    print(f"\nНайдено кандидатов: {len(results)}\n")
    for index, row in enumerate(results, start=1):
        print(f"{index}. {_format_person(row)}")
        print()
