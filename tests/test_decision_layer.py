from phonebook.bot import SearchContext, resolve_phonebook_query


def test_resolve_query_returns_not_specific_enough_for_department_only_request(monkeypatch):
    def fake_search(_user_input: str, limit: int = 5):
        return (
            [
                {"id_phone_directory": 1, "score": 42, "last_name": "Иванов", "first_name": "Петр"},
                {"id_phone_directory": 2, "score": 39, "last_name": "Петров", "first_name": "Иван"},
                {"id_phone_directory": 3, "score": 38, "last_name": "Сидоров", "first_name": "Антон"},
            ],
            {
                "first_name": None,
                "last_name": None,
                "patronymic": None,
                "position_hint": None,
                "department_hint": "администрация",
                "general_terms": [],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)

    decision = resolve_phonebook_query("кто в администрации")

    assert decision.status == "not_specific_enough"
    assert decision.results == []


def test_resolve_query_allows_department_plus_specific_term(monkeypatch):
    def fake_search(_user_input: str, limit: int = 5):
        return (
            [
                {"id_phone_directory": 1, "score": 36, "last_name": "Иванов", "first_name": "Игорь"},
                {"id_phone_directory": 2, "score": 24, "last_name": "Петров", "first_name": "Павел"},
                {"id_phone_directory": 3, "score": 24, "last_name": "Сидоров", "first_name": "Антон"},
            ],
            {
                "first_name": None,
                "last_name": None,
                "patronymic": None,
                "position_hint": None,
                "department_hint": "отдел управления данными",
                "general_terms": ["игорь"],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)

    decision = resolve_phonebook_query("игорь из уд")

    assert decision.status == "confident"
    assert decision.results[0]["first_name"] == "Игорь"


def test_score_logic_matches_informal_or_inflected_name_without_dictionary_alias():
    from phonebook.bot import _score_token

    row = {
        "last_name": "Иванов",
        "first_name": "Виталий",
        "patronymic": None,
        "post": "",
        "department_name": "ОТДЕЛ УПРАВЛЕНИЯ ДАННЫМИ",
        "email": "",
    }

    assert _score_token("виталю", row) >= 12
    assert _score_token("виталя", row) >= 12


def test_resolve_query_returns_ambiguous_for_close_candidates(monkeypatch):
    def fake_search(_user_input: str, limit: int = 5):
        return (
            [
                {"id_phone_directory": 1, "score": 51, "last_name": "Иванов", "first_name": "Петр"},
                {"id_phone_directory": 2, "score": 47, "last_name": "Иванов", "first_name": "Иван"},
            ],
            {
                "first_name": None,
                "last_name": "иванов",
                "patronymic": None,
                "position_hint": None,
                "department_hint": None,
                "general_terms": [],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)

    decision = resolve_phonebook_query("иванов")

    assert decision.status == "ambiguous"
    assert len(decision.results) == 2


def test_resolve_query_masks_sensitive_fields_by_role(monkeypatch):
    def fake_search(_user_input: str, limit: int = 5):
        return (
            [
                {
                    "id_phone_directory": 1,
                    "score": 72,
                    "last_name": "Иванов",
                    "first_name": "Петр",
                    "mobile_phone": "+79990001122",
                    "email": "ivanov@example.org",
                }
            ],
            {
                "first_name": "петр",
                "last_name": "иванов",
                "patronymic": None,
                "position_hint": None,
                "department_hint": None,
                "general_terms": [],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)

    user_decision = resolve_phonebook_query("иванов петр", context=SearchContext(source="max", role="user"))
    admin_decision = resolve_phonebook_query("иванов петр", context=SearchContext(source="max", role="admin"))

    assert user_decision.status == "confident"
    assert user_decision.results[0]["mobile_phone"] is None
    assert user_decision.results[0]["email"] is None
    assert admin_decision.results[0]["mobile_phone"] == "+79990001122"
    assert admin_decision.results[0]["email"] == "ivanov@example.org"


def test_resolve_query_writes_audit_entry(monkeypatch):
    audit_calls = []

    def fake_search(_user_input: str, limit: int = 5):
        return (
            [{"id_phone_directory": 7, "score": 81, "last_name": "Иванов", "first_name": "Петр"}],
            {
                "first_name": "петр",
                "last_name": "иванов",
                "patronymic": None,
                "position_hint": None,
                "department_hint": None,
                "general_terms": [],
                "source": "heuristic",
            },
        )

    def fake_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)
    monkeypatch.setattr("phonebook.bot.write_query_audit", fake_audit)

    decision = resolve_phonebook_query(
        "иванов петр",
        context=SearchContext(source="max", external_user_id="123", role="admin"),
    )

    assert decision.status == "confident"
    assert audit_calls
    assert audit_calls[0]["source"] == "max"
    assert audit_calls[0]["external_user_id"] == "123"
    assert audit_calls[0]["decision_status"] == "confident"
