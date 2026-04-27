from phonebook.llm import CORPORATE_SEMANTICS, DEPARTMENT_ALIASES, NAME_ALIASES, department_match_variants


def test_name_aliases_are_loaded_from_data_file():
    assert NAME_ALIASES["саня"] == "александр"
    assert NAME_ALIASES["настя"] == "анастасия"


def test_department_aliases_are_loaded_from_data_file():
    assert DEPARTMENT_ALIASES["уд"] == "отдел управления данными"
    assert DEPARTMENT_ALIASES["отдел аналитики"] == "отдел информационно-аналитического обеспечения"


def test_corporate_semantics_expand_match_variants():
    assert CORPORATE_SEMANTICS["цит"]["department_hint"] == "администрация"
    assert "центр информационных технологий" in department_match_variants("цит")
    assert "региональный координационный центр" in department_match_variants("ркц")
