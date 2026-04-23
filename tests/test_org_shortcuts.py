from phonebook.bot import _score_row
from phonebook.llm import heuristic_parse_query


def test_rkc_shortcut_matches_service_name_in_post():
    parsed = heuristic_parse_query("руководитель ркц")
    row = {
        "last_name": "Сметанин",
        "first_name": "Аленид",
        "patronymic": None,
        "post": 'Заместитель руководителя - руководитель службы "Региональный координационный центр"',
        "department_name": "АДМИНИСТРАЦИЯ",
        "email": "",
    }

    score, reasons = _score_row(row, parsed, "руководитель ркц")

    assert score >= 48
    assert "совпала должность" in reasons
    assert "совпал отдел" in reasons


def test_cit_shortcut_matches_administration_as_general_center_scope():
    parsed = heuristic_parse_query("руководитель цит")
    row = {
        "last_name": "Дружинин",
        "first_name": "Василий",
        "patronymic": None,
        "post": "Руководитель",
        "department_name": "АДМИНИСТРАЦИЯ",
        "email": "",
    }

    score, reasons = _score_row(row, parsed, "руководитель цит")

    assert score >= 48
    assert "совпала должность" in reasons
    assert "совпал отдел" in reasons
