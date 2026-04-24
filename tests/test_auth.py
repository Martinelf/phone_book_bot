from types import SimpleNamespace

from phonebook.auth import authorize_max_event, extract_max_user_id


def test_extract_max_user_id_from_nested_message_sender():
    event = SimpleNamespace(
        message=SimpleNamespace(
            sender=SimpleNamespace(user_id=123456789),
        )
    )

    assert extract_max_user_id(event) == "123456789"


def test_authorize_max_event_allows_user_from_allowlist(monkeypatch):
    monkeypatch.setattr(
        "phonebook.auth.get_settings",
        lambda: {
            "auth_max_enabled": "true",
            "pg_schema": "bot_test",
            "auth_max_table": "authorized_users",
        },
    )
    monkeypatch.setattr(
        "phonebook.auth.execute_query",
        lambda _query, _params, fetch="one": {
            "source": "max",
            "external_user_id": "42",
            "display_name": "Allowed User",
            "role": "user",
            "is_active": True,
        },
    )

    event = SimpleNamespace(message=SimpleNamespace(sender=SimpleNamespace(user_id=42)))
    decision = authorize_max_event(event)

    assert decision.allowed is True
    assert decision.external_user_id == "42"
    assert decision.role == "user"
    assert decision.reason == "allowed"


def test_authorize_max_event_denies_user_not_in_allowlist(monkeypatch):
    monkeypatch.setattr(
        "phonebook.auth.get_settings",
        lambda: {
            "auth_max_enabled": "true",
            "pg_schema": "bot_test",
            "auth_max_table": "authorized_users",
        },
    )
    monkeypatch.setattr(
        "phonebook.auth.execute_query",
        lambda _query, _params, fetch="one": None,
    )

    event = SimpleNamespace(message=SimpleNamespace(sender=SimpleNamespace(user_id=77)))
    decision = authorize_max_event(event)

    assert decision.allowed is False
    assert decision.external_user_id == "77"
    assert decision.reason == "not_allowed"


def test_authorize_max_event_denies_when_user_id_missing(monkeypatch):
    monkeypatch.setattr(
        "phonebook.auth.get_settings",
        lambda: {
            "auth_max_enabled": "true",
            "pg_schema": "bot_test",
            "auth_max_table": "authorized_users",
        },
    )

    event = SimpleNamespace(message=SimpleNamespace(sender=SimpleNamespace()))
    decision = authorize_max_event(event)

    assert decision.allowed is False
    assert decision.external_user_id is None
    assert decision.reason == "missing_user_id"
