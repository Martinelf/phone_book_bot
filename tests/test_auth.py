from types import SimpleNamespace

from phonebook.auth import authorize_max_event, extract_max_user_id, grant_user_access, revoke_user_access


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


def test_grant_user_access_upserts_record(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "phonebook.auth.get_settings",
        lambda: {
            "pg_schema": "bot_test",
            "auth_max_table": "authorized_users",
        },
    )

    def fake_execute_query(query, params=None, fetch="all"):
        calls.append((query, params, fetch))
        if fetch == "one":
            return {
                "source": "max",
                "external_user_id": "77",
                "display_name": "Ivan Ivanov",
                "role": "admin",
                "is_active": True,
            }
        return None

    monkeypatch.setattr("phonebook.auth.execute_query", fake_execute_query)

    row = grant_user_access(
        source="max",
        external_user_id="77",
        role="admin",
        display_name="Ivan Ivanov",
        comment="granted in test",
    )

    assert row["external_user_id"] == "77"
    assert row["role"] == "admin"
    assert "ON CONFLICT" in calls[0][0]
    assert calls[0][1][1] == "77"


def test_revoke_user_access_marks_record_inactive(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "phonebook.auth.get_settings",
        lambda: {
            "pg_schema": "bot_test",
            "auth_max_table": "authorized_users",
        },
    )

    def fake_execute_query(query, params=None, fetch="all"):
        calls.append((query, params, fetch))
        if fetch == "one":
            return {
                "source": "max",
                "external_user_id": "77",
                "display_name": "Ivan Ivanov",
                "role": "user",
                "is_active": True,
            }
        return None

    monkeypatch.setattr("phonebook.auth.execute_query", fake_execute_query)

    revoked = revoke_user_access(source="max", external_user_id="77")

    assert revoked is True
    assert "UPDATE bot_test.authorized_users" in calls[1][0]
