# Phonebook Bot

`Phonebook Bot` - MVP для поиска сотрудников по свободному текстовому запросу. Основной интерфейс рассчитан на `MAX`, но проект можно запускать и локально: через CLI, `Streamlit` и eval-сценарии.

Текущий пайплайн:

`запрос -> разбор признаков -> фиксированный поиск по БД -> ранжирование -> confidence-policy`

LLM в проекте опциональна. Она используется только для извлечения признаков из текста. Если Ollama недоступна, бот переключается на эвристический fallback.

## Что умеет

- искать сотрудника по имени, фамилии, прозвищу, должности и отделу
- учитывать алиасы сотрудников и разговорные названия отделов
- ранжировать кандидатов и возвращать `top-k`
- различать режимы `confident`, `ambiguous`, `low_confidence`, `no_match`, `not_understood`
- ограничивать доступ через allowlist `bot_test.authorized_users`
- поддерживать роли `user` и `admin`
- работать через MAX, CLI, `eval` и опционально `Streamlit`
- писать диагностические логи в консоль и в файл

## Структура проекта

- `phonebook/llm.py` - разбор запроса, нормализация и fallback-эвристики
- `phonebook/bot.py` - поиск, ранжирование и итоговое решение
- `phonebook/max_bot.py` - polling-бот для MAX
- `phonebook/auth.py` - авторизация пользователей MAX через allowlist
- `phonebook/db.py` - доступ к PostgreSQL через `pg8000`
- `phonebook/logging_config.py` - настройка логирования
- `scripts/init_synthetic_db.py` - загрузка синтетической БД из SQL-файла
- `scripts/run_max_bot.py` - удобный локальный запуск MAX-бота
- `scripts/run_eval.py` - локальный eval по файлу `eval/phonebook_queries.jsonl`
- `apps/streamlit_app.py` - простой веб-интерфейс для отладки
- `sql/authorized_users.sql` - таблица allowlist для MAX
- `sql/phone_directory_search.sql` - SQL-функция поиска
- `sql/query_audit_log.sql` - таблица аудита запросов

## Требования

- Python 3.11
- PostgreSQL 14+ или совместимая версия
- `MAX_TOKEN`, только если нужен запуск MAX-бота
- Ollama, только если нужен LLM-разбор вместо fallback-эвристики

## Быстрый старт

### 1. Установить зависимости

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Если удобнее, можно использовать уже существующий `venv` или Conda.

### 2. Настроить `.env`

Минимальный шаблон уже есть в `.env.example`.

Обязательные переменные для локальной работы с БД:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DB=phone_book_demo
PG_ADMIN_DB=postgres
PG_USER=postgres
PG_PASSWORD=change_me
PG_SCHEMA=bot_test
```

Если нужен MAX-бот, дополнительно задай:

```env
MAX_TOKEN=your_max_token
MAX_SKIP_UPDATES=true
AUTH_MAX_ENABLED=true
AUTH_MAX_TABLE=authorized_users
```

Опциональные настройки:

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:2b
LOG_LEVEL=INFO
LOG_FILE=logs/phonebook.log
AUDIT_ENABLED=false
AUDIT_TABLE=query_audit_log
```

### 3. Подготовить БД

Проект ожидает PostgreSQL и SQL-объекты в схеме `bot_test`.

В репозитории уже есть служебные SQL-файлы:

- `sql/authorized_users.sql`
- `sql/phone_directory_search.sql`
- `sql/query_audit_log.sql`

Важно: `scripts/init_synthetic_db.py` и `docker-compose.yml` ожидают файл `sql/synthetic_phonebook.sql`, но сейчас его нет в репозитории. Поэтому перед запуском одного из этих сценариев нужно:

1. добавить `sql/synthetic_phonebook.sql` в проект, если он у тебя есть отдельно
2. или адаптировать `scripts/init_synthetic_db.py` и `docker-compose.yml` под свою схему и данные

После появления файла инициализация выглядит так:

```powershell
python scripts\init_synthetic_db.py
```

Таблицу доступа для MAX можно применить отдельно:

```powershell
psql -d phone_book_demo -f sql\authorized_users.sql
```

### 4. Запустить приложение

CLI:

```powershell
python main.py
```

MAX-бот:

```powershell
python scripts\run_max_bot.py
```

или

```powershell
python -m phonebook.max_bot
```

Streamlit:

```powershell
python -m streamlit run apps\streamlit_app.py
```

Eval:

```powershell
python scripts\run_eval.py
```

Тесты:

```powershell
pytest
```

## Docker

`docker-compose.yml` поднимает:

- `postgres`
- `max-bot`

Базовый запуск:

```powershell
docker compose up --build
```

Но здесь действует то же ограничение: compose-манифест ожидает файл `sql/synthetic_phonebook.sql`. Пока его нет в репозитории, Docker-сценарий нужно либо дополнить этим файлом, либо изменить volume/инициализацию под фактическую схему.

Что ещё важно:

- внутри compose приложение ходит в БД по `PG_HOST=postgres`
- Ollama в compose не поднимается; по умолчанию используется `host.docker.internal`
- без `MAX_TOKEN` сервис `max-bot` завершится с ошибкой

## Доступ в MAX

Если `AUTH_MAX_ENABLED=true`, бот отвечает только пользователям из allowlist.

Первого администратора нужно добавить в `bot_test.authorized_users` вручную:

```sql
INSERT INTO bot_test.authorized_users (source, external_user_id, display_name, role, comment)
VALUES ('max', '<your_user_id>', 'Your Name', 'admin', 'bootstrap admin');
```

После этого доступами можно управлять из самого бота.

Команды:

- `/whoami` - показать свой `user_id` и роль
- `/grant <user_id> [role] [display name]` - выдать или обновить доступ
- `/revoke <user_id>` - отключить доступ
- `/access` - краткая справка по командам доступа

Роли:

- `user` - обычный доступ к поиску
- `admin` - полный доступ к данным и управлению allowlist

Если нужно временно отключить проверку доступа для разработки, установи `AUTH_MAX_ENABLED=false`.

## Confidence-policy

Перед ответом бот принимает отдельное решение:

- `confident` - уверенный ответ, кандидаты показываются сразу
- `ambiguous` - найдено несколько очень похожих кандидатов
- `low_confidence` - сигнал слишком слабый, бот просит уточнение
- `no_match` - по данным БД никто не найден
- `not_understood` - запрос нерелевантный или слишком шумный

Это нужно, чтобы бот не выдавал случайный ответ при слабом совпадении.

## Логирование

По умолчанию лог пишется в консоль и в файл `logs/phonebook.log`.

Логирование настраивается переменными:

- `LOG_LEVEL`
- `LOG_FILE`

В файл попадают, в частности:

- исходный запрос
- источник разбора (`heuristic` или `llm`)
- confidence-статус
- итоговая уверенность
- распарсенные признаки
- `top_ids` кандидатов

## MAX API

Для интеграции с MAX используется библиотека `maxapi`.

- PyPI: [maxapi](https://pypi.org/project/maxapi/)

В проекте используется режим `start_polling`, а не webhook.
