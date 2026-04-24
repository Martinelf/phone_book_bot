from phonebook.db import execute_query
execute_query(
    INSERT INTO bot_test.authorized_users (source, external_user_id, display_name, role, comment) VALUES (%s, %s, %s,
%s, %s),
    (max, 261988673, Белковский Вадим, user, доступ для MAX),
  )

print(user added)