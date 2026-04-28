from __future__ import annotations

from typing import Any

DEFAULT_ROLE = "user"
KNOWN_ROLES = {"user", "admin"}

ROLE_FIELD_POLICY = {
    "user": {"mobile_phone": False, "email": False},
    "admin": {"mobile_phone": True, "email": True},
}


def normalize_role(role: str | None) -> str:
    normalized = (role or DEFAULT_ROLE).strip().lower()
    return normalized if normalized in KNOWN_ROLES else DEFAULT_ROLE


def mask_search_results(results: list[dict[str, Any]], role: str | None) -> list[dict[str, Any]]:
    normalized_role = normalize_role(role)
    policy = ROLE_FIELD_POLICY[normalized_role]
    masked_results: list[dict[str, Any]] = []

    for row in results:
        masked_row = dict(row)
        if not policy["mobile_phone"]:
            masked_row["mobile_phone"] = None
        if not policy["email"]:
            masked_row["email"] = None
        masked_results.append(masked_row)

    return masked_results
