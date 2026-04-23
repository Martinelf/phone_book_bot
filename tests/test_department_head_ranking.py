from phonebook.bot import _score_row
from phonebook.llm import heuristic_parse_query


def test_department_head_ranks_above_analyst_for_analytics_department_request():
    parsed = heuristic_parse_query("кто начальник отдела аналитики")
    head_row = {
        "last_name": "Иванов",
        "first_name": "Александр",
        "patronymic": None,
        "post": "Начальник отдела",
        "department_name": "ОТДЕЛ ИНФОРМАЦИОННО-АНАЛИТИЧЕСКОГО ОБЕСПЕЧЕНИЯ",
        "email": "",
    }
    analyst_row = {
        "last_name": "Петров",
        "first_name": "Петр",
        "patronymic": None,
        "post": "Бизнес аналитик",
        "department_name": "ОТДЕЛ ИНФОРМАЦИОННО-АНАЛИТИЧЕСКОГО ОБЕСПЕЧЕНИЯ",
        "email": "",
    }

    head_score, _ = _score_row(head_row, parsed, "кто начальник отдела аналитики")
    analyst_score, _ = _score_row(analyst_row, parsed, "кто начальник отдела аналитики")

    assert head_score > analyst_score
