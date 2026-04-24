# Phonebook Bot

`Phonebook Bot` — MVP для поиска сотрудника по свободному текстовому запросу с основным интерфейсом через `MAX`.

Текущий пайплайн:

`запрос пользователя -> разбор признаков -> фиксированный поиск по БД -> ранжирование -> confidence-policy`

Проект не генерирует произвольный SQL через LLM. LLM здесь опциональна и используется только для извлечения признаков из текста. Если Ollama недоступна, бот работает через fallback-эвристику.

## Что умеет

- искать сотрудника по имени, фамилии, прозвищу, должности и отделу
- учитывать алиасы сотрудников и разговорные названия отделов
- ранжировать кандидатов и возвращать `top-k`
- различать режимы `confident`, `ambiguous`, `low_confidence`, `no_match`, `not_understood`
- работать через MAX, CLI, `eval` и опционально `Streamlit`
- писать диагностические логи в файл и консоль

## Архитектура

- [phonebook/llm.py](D:/DS/phone_book_bot-main/phonebook/llm.py:1) — разбор запроса, fallback-эвристики и нормализация
- [phonebook/bot.py](D:/DS/phone_book_bot-main/phonebook/bot.py:1) — ранжирование, confidence-policy и формат ответа
- [phonebook/max_bot.py](D:/DS/phone_book_bot-main/phonebook/max_bot.py:1) — polling-бот для MAX через `maxapi`
- [phonebook/auth.py](D:/DS/phone_book_bot-main/phonebook/auth.py:1) — авторизация по `user_id` для MAX
- [phonebook/db.py](D:/DS/phone_book_bot-main/phonebook/db.py:1) — доступ к PostgreSQL через `pg8000`
- [phonebook/logging_config.py](D:/DS/phone_book_bot-main/phonebook/logging_config.py:1) — логирование
- [sql/synthetic_phonebook.sql](D:/DS/phone_book_bot-main/sql/synthetic_phonebook.sql:1) — синтетическая схема и тестовые данные
- [scripts/run_max_bot.py](D:/DS/phone_book_bot-main/scripts/run_max_bot.py:1) — простой запуск MAX-бота
- [scripts/init_synthetic_db.py](D:/DS/phone_book_bot-main/scripts/init_synthetic_db.py:1) — инициализация синтетической БД
- [scripts/run_eval.py](D:/DS/phone_book_bot-main/scripts/run_eval.py:1) — локальный eval
- [docker-compose.yml](D:/DS/phone_book_bot-main/docker-compose.yml:1) — `postgres` + сервис бота

## Быстрый старт без Docker

### 1. Окружение

```bash
conda create -n phonebook-bot python=3.11 -y
conda activate phonebook-bot
cd D:\DS\phone_book_bot-main
pip install -r requirements.txt
copy .env.example .env
```

### 2. Настройка `.env`

Минимально нужны:

```env
PG_HOST=localhost
PG_PORT=5432
PG_DB=phone_book_demo
PG_ADMIN_DB=postgres
PG_USER=postgres
PG_PASSWORD=1234
PG_SCHEMA=bot_test
MAX_TOKEN=твой_токен_бота
MAX_SKIP_UPDATES=true
AUTH_MAX_ENABLED=true
AUTH_MAX_TABLE=authorized_users
```

Опционально:

```env
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:2b
LOG_LEVEL=INFO
LOG_FILE=logs/phonebook.log
```

### 3. Синтетическая БД

```bash
python scripts\init_synthetic_db.py
```

### 3.1. Таблица доступа для MAX

Примените SQL:

```bash
psql -d phone_book_demo -f sql\authorized_users.sql
```

После этого заполните таблицу `bot_test.authorized_users` своими `user_id` из MAX.

### 4. Запуск MAX-бота

```bash
python scripts\run_max_bot.py
```

Или:

```bash
python -m phonebook.max_bot
```

## Docker

Если нужен воспроизводимый запуск для другого человека, используй Docker.

### Что поднимается

- `postgres` с автоматической инициализацией синтетической БД
- `max-bot` как основной сервис приложения

### Запуск

1. Заполни `.env` как минимум для `MAX_TOKEN` и `PG_PASSWORD`.
2. Подними сервисы:

```bash
docker compose up --build
```

### Что важно

- внутри compose приложение ходит в БД по `PG_HOST=postgres`
- Ollama в compose не включена; если она есть на хосте, контейнер обращается к `host.docker.internal`
- без `MAX_TOKEN` сервис бота не стартует
- при `AUTH_MAX_ENABLED=true` MAX-бот отвечает только пользователям из `bot_test.authorized_users`

## CLI и Streamlit

Это вспомогательные режимы для локальной отладки.

### CLI

```bash
python main.py
```

### Streamlit

```bash
python -m streamlit run apps\streamlit_app.py
```

## Eval

```bash
python scripts\run_eval.py
```

В отчёте есть:

- `top-1`
- `top-3`
- `no-answer`
- разбивка по категориям
- разбивка по confidence-статусам

## Тесты

```bash
pytest
```

## Confidence-policy

Бот принимает отдельное решение перед выдачей результата:

- `confident` — уверенный ответ, кандидаты показываются
- `ambiguous` — найдено несколько очень похожих кандидатов
- `low_confidence` — сигнал слишком слабый, бот просит уточнение
- `no_match` — по данным БД никого похожего не нашлось
- `not_understood` — запрос слишком шумный или нерелевантный

Это нужно, чтобы бот не выдумывал ответ на слабом сигнале.

## Логирование

Лог пишется в консоль и файл, по умолчанию:

- [logs/phonebook.log](D:/DS/phone_book_bot-main/logs/phonebook.log)

Что логируется:

- исходный запрос
- источник разбора (`heuristic` или `llm`)
- confidence-статус
- уверенность
- распарсенные признаки
- `top_ids` кандидатов

## Использованная библиотека MAX

Для интеграции с MAX используется `maxapi`:

- PyPI: https://pypi.org/project/maxapi/

В проекте используется режим `start_polling`, а не webhook.

## Текущее состояние

Проект сейчас — рабочий внутренний MVP.

Подходит для:

- R&D
- демонстрации подхода
- тюнинга ранжирования
- запуска локального чат-бота в MAX
- переноса на реальную БД позже

До продового уровня ещё нужны:

- подключение реальной схемы и реальных данных
- более широкий eval
- интеграционные тесты на реальные данные
- политика доступа и маскировка чувствительных полей
