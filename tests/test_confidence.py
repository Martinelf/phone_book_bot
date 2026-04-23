from phonebook.bot import _score_row, resolve_phonebook_query


def test_resolve_query_returns_found_when_there_are_results(monkeypatch):
    def fake_search(_user_input: str, limit: int = 3):
        return (
            [
                {
                    "id_phone_directory": 21,
                    "score": 64,
                    "reasons": ["совпала фамилия", "совпала должность"],
                    "last_name": "Иванов",
                    "first_name": "Петр",
                }
            ][:limit],
            {
                "first_name": None,
                "last_name": "иванов",
                "patronymic": None,
                "position_hint": "менеджер",
                "department_hint": None,
                "general_terms": [],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)
    decision = resolve_phonebook_query("найди проектного менеджера Иванова")

    assert decision.status == "found"
    assert decision.results[0]["id_phone_directory"] == 21


def test_resolve_query_returns_not_found_when_there_are_no_results(monkeypatch):
    def fake_search(_user_input: str, limit: int = 3):
        return (
            [],
            {
                "first_name": None,
                "last_name": None,
                "patronymic": None,
                "position_hint": None,
                "department_hint": None,
                "general_terms": ["борща"],
                "source": "heuristic",
            },
        )

    monkeypatch.setattr("phonebook.bot.search_phonebook", fake_search)
    decision = resolve_phonebook_query("покажи рецепт борща")

    assert decision.status == "not_found"
    assert decision.results == []


def test_score_row_matches_male_last_name_when_query_uses_genitive_form():
    row = {
        "last_name": "Иванов",
        "first_name": "Петр",
        "patronymic": None,
        "post": "",
        "department_name": "",
        "department_aliases": "",
        "person_aliases": "",
        "email": "",
    }
    parsed_query = {
        "first_name": None,
        "last_name": "иванова",
        "patronymic": None,
        "position_hint": None,
        "department_hint": None,
        "general_terms": [],
    }

    score, reasons = _score_row(row, parsed_query, "дай контакт Иванова")

    assert score >= 40
    assert "совпала фамилия" in reasons


def test_score_row_matches_first_name_from_genitive_form():
    row = {
        "last_name": "Сметанин",
        "first_name": "Аленид",
        "patronymic": "Эдуардович",
        "post": "",
        "department_name": "",
        "department_aliases": "",
        "person_aliases": "",
        "email": "",
    }
    parsed_query = {
        "first_name": None,
        "last_name": None,
        "patronymic": None,
        "position_hint": None,
        "department_hint": None,
        "general_terms": ["аленида"],
    }

    score, reasons = _score_row(row, parsed_query, "дай контакт Аленида")

    assert score >= 12
    assert "совпало слово 'аленида'" in reasons


def test_score_row_matches_last_name_with_adjective_ending():
    row = {
        "last_name": "Толстой",
        "first_name": "Лев",
        "patronymic": "Николаевич",
        "post": "",
        "department_name": "",
        "department_aliases": "",
        "person_aliases": "",
        "email": "",
    }
    parsed_query = {
        "first_name": None,
        "last_name": "толстого",
        "patronymic": None,
        "position_hint": None,
        "department_hint": None,
        "general_terms": [],
    }

    score, reasons = _score_row(row, parsed_query, "дай номер Толстого")

    assert score >= 40
    assert "совпала фамилия" in reasons
