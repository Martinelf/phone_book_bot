from phonebook.max_bot import _parse_grant_command, _parse_revoke_command


def test_parse_grant_command_with_role_and_name():
    user_id, role, display_name = _parse_grant_command("/grant 12345 admin Ivan Ivanov")

    assert user_id == "12345"
    assert role == "admin"
    assert display_name == "Ivan Ivanov"


def test_parse_grant_command_with_name_only_defaults_role():
    user_id, role, display_name = _parse_grant_command("/grant 12345 Ivan Ivanov")

    assert user_id == "12345"
    assert role == "user"
    assert display_name == "Ivan Ivanov"


def test_parse_revoke_command_extracts_user_id():
    assert _parse_revoke_command("/revoke 12345") == "12345"
