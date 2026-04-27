from __future__ import annotations

from dataclasses import dataclass
from typing import Any


GENERIC_POSITION_HINTS = {
    "аналитик",
    "инженер",
    "менеджер",
    "поддержка",
    "продажи",
    "руководитель",
}


@dataclass
class DecisionOutcome:
    status: str
    message: str
    confidence: float
    rationale: list[str]
    results: list[dict[str, Any]]


def _structured_signal_count(parsed_query: dict[str, Any]) -> int:
    return sum(
        1
        for key in ("first_name", "last_name", "patronymic", "position_hint", "department_hint")
        if parsed_query.get(key)
    )


def _has_name_signal(parsed_query: dict[str, Any]) -> bool:
    return any(parsed_query.get(key) for key in ("first_name", "last_name", "patronymic"))


def _general_signal_count(parsed_query: dict[str, Any]) -> int:
    return len(parsed_query.get("general_terms") or [])


def _is_not_understood(parsed_query: dict[str, Any]) -> bool:
    return not any(
        [
            parsed_query.get("first_name"),
            parsed_query.get("last_name"),
            parsed_query.get("patronymic"),
            parsed_query.get("position_hint"),
            parsed_query.get("department_hint"),
            parsed_query.get("general_terms"),
        ]
    )


def _is_too_broad(parsed_query: dict[str, Any], ranked_rows: list[dict[str, Any]], limit: int) -> tuple[bool, list[str]]:
    rationale: list[str] = []
    structured_signals = _structured_signal_count(parsed_query)
    has_name_signal = _has_name_signal(parsed_query)
    position_hint = parsed_query.get("position_hint")
    department_hint = parsed_query.get("department_hint")
    general_terms = parsed_query.get("general_terms") or []
    top_score = ranked_rows[0]["score"] if ranked_rows else 0
    second_score = ranked_rows[1]["score"] if len(ranked_rows) > 1 else 0
    score_gap = top_score - second_score

    if has_name_signal:
        return False, rationale

    if department_hint and structured_signals == 1 and not general_terms and len(ranked_rows) >= limit:
        rationale.append("запрос ограничен только подразделением")
        return True, rationale

    if position_hint in GENERIC_POSITION_HINTS and structured_signals == 1 and not general_terms and len(ranked_rows) >= limit:
        rationale.append("запрос ограничен только общей ролью")
        return True, rationale

    if structured_signals == 0 and len(general_terms) <= 1 and len(ranked_rows) >= limit:
        rationale.append("запрос слишком общий")
        return True, rationale

    if department_hint and general_terms and len(ranked_rows) >= limit:
        if top_score >= 30 and score_gap >= 10:
            return False, rationale
        rationale.append("подразделение задано, но уточняющее слово недостаточно различает кандидатов")
        return True, rationale

    return False, rationale


def decide_search_results(
    parsed_query: dict[str, Any],
    ranked_rows: list[dict[str, Any]],
    limit: int,
) -> DecisionOutcome:
    if _is_not_understood(parsed_query):
        return DecisionOutcome(
            status="not_understood",
            message="Не удалось понять запрос. Уточните сотрудника, роль или подразделение.",
            confidence=0.0,
            rationale=["нет поисковых признаков"],
            results=[],
        )

    if not ranked_rows:
        return DecisionOutcome(
            status="no_match",
            message="Ничего не найдено.",
            confidence=0.0,
            rationale=["по запросу нет совпадений"],
            results=[],
        )

    too_broad, broad_rationale = _is_too_broad(parsed_query, ranked_rows, limit)
    if too_broad:
        return DecisionOutcome(
            status="not_specific_enough",
            message="Запрос слишком широкий. Уточните сотрудника, роль или конкретное подразделение.",
            confidence=0.15,
            rationale=broad_rationale,
            results=[],
        )

    top_results = ranked_rows[:limit]
    top_score = top_results[0]["score"]
    second_score = top_results[1]["score"] if len(top_results) > 1 else 0
    score_gap = top_score - second_score
    structured_signals = _structured_signal_count(parsed_query)
    general_signals = _general_signal_count(parsed_query)
    has_name_signal = _has_name_signal(parsed_query)

    rationale = [
        f"top_score={top_score}",
        f"score_gap={score_gap}",
        f"structured_signals={structured_signals}",
        f"general_signals={general_signals}",
    ]
    confidence = min(0.99, max(0.05, top_score / 100))

    if len(top_results) > 1 and score_gap < 8:
        return DecisionOutcome(
            status="ambiguous",
            message="Нашлось несколько похожих вариантов. Уточните запрос или выберите нужного сотрудника.",
            confidence=min(confidence, 0.55),
            rationale=rationale + ["малый отрыв между кандидатами"],
            results=top_results,
        )

    total_signals = structured_signals + general_signals
    if top_score >= 30 and score_gap >= 10 and total_signals >= 2:
        return DecisionOutcome(
            status="confident",
            message="Найдены сотрудники.",
            confidence=max(confidence, 0.6),
            rationale=rationale + ["запрос достаточно конкретный по сумме сигналов"],
            results=top_results,
        )

    if top_score < 24 or (top_score < 40 and total_signals < 2 and not has_name_signal):
        return DecisionOutcome(
            status="low_confidence",
            message="Есть слабые совпадения. Лучше уточнить фамилию, роль или подразделение.",
            confidence=min(confidence, 0.45),
            rationale=rationale + ["недостаточно сильный сигнал"],
            results=top_results,
        )

    return DecisionOutcome(
        status="confident",
        message="Найдены сотрудники.",
        confidence=confidence,
        rationale=rationale + ["достаточно сильный сигнал"],
        results=top_results,
    )
