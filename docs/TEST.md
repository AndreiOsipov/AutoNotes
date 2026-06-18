# Документация тестов (`tests/`)

Тестовый набор AutoNotes покрывает аутентификацию (интеграционные API-тесты), бизнес-логику статистики видео и ML-синхронизатор заметок. Запуск — через **pytest** с поддержкой **async** и опциональным **Testcontainers** для изолированной PostgreSQL.

## Содержание

- [Обзор](#обзор)
- [Структура каталога `tests/`](#структура-каталога-tests)
- [Конфигурация pytest](#конфигурация-pytest)
- [Окружение и переменные](#окружение-и-переменные)
- [Фикстуры (`conftest.py`)](#фикстуры-conftestpy)
- [Тестовые модули](#тестовые-модули)
- [Запуск тестов](#запуск-тестов)
- [CI/CD](#cicd)
- [Написание новых тестов](#написание-новых-тестов)

---

## Обзор

```
tests/
├── conftest.py                        # Общие фикстуры: БД, HTTP-клиент, тестовые данные
└── unit/
    ├── test_auth.py                   # API: регистрация пользователя
    ├── test_video_transcription.py    # Unit: get_user_stats
    └── test_notes_synchronizer.py     # Unit: NotesSynchronizer и dataclass'ы
```

| Тип | Файл | БД | ML-модели |
|-----|------|----|-----------|
| Интеграционный (API) | `test_auth.py` | PostgreSQL (Testcontainers или внешняя) | Не загружаются |
| Unit | `test_video_transcription.py` | SQLite in-memory (локальная фикстура) | Не загружаются |
| Unit | `test_notes_synchronizer.py` | Не используется | Замоканы |

Всего **11 тестов** в трёх модулях.

---

## Структура каталога `tests/`

### `conftest.py`

Центральный файл фикстур для всего тестового набора. Отвечает за:

- поднятие PostgreSQL через Testcontainers (если `TESTCONTAINER=true`);
- применение и откат миграций Alembic;
- очистку таблиц перед каждым тестом;
- подмену зависимости `get_session` в FastAPI для `AsyncClient`;
- общие payload'ы для регистрации, отзывов и моков видео.

### `unit/`

Каталог с тестами. Несмотря на имя `unit`, `test_auth.py` — интеграционный: он обращается к реальному приложению FastAPI и базе данных.

---

## Конфигурация pytest

Настройки в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = "."
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
testpaths = ["tests"]
filterwarnings = [
    "ignore::DeprecationWarning",
]
env_files = [".test.env"]
```

| Параметр | Значение | Описание |
|----------|----------|----------|
| `pythonpath` | `.` | Импорт модулей из корня проекта (`src.*`) |
| `asyncio_mode` | `auto` | Автоматическое обнаружение `async def` тестов |
| `asyncio_*_loop_scope` | `session` | Один event loop на всю сессию pytest |
| `testpaths` | `["tests"]` | Корень поиска тестов |
| `env_files` | `[".test.env"]` | Файл с тестовыми переменными окружения |

### Dev-зависимости

Устанавливаются через группу `dev`:

```bash
uv sync --extra cpu --group dev
```

| Пакет | Назначение |
|-------|------------|
| `httpx` | `AsyncClient` + `ASGITransport` для API-тестов |
| `pytest-asyncio` | Поддержка async-тестов |
| `pytest-dotenv` | Загрузка `.test.env` |
| `testcontainers[postgresql]` | Изолированный PostgreSQL в Docker |

---

## Окружение и переменные

### Файл `.test.env`

Pytest ожидает файл `.test.env` в корне проекта (указан в `pyproject.toml`). Файлы `*.env` в `.gitignore`, поэтому его нужно создать локально.

Минимальный набор переменных (можно скопировать из `.env.example` и адаптировать):

```env
PROJECT_NAME=AutoNotes Test
PROJECT_DESCRIPTION=Test run
PROJECT_VERSION=1.0.0

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=autonotes_test

JWT_PRIVATE_KEY_PATH=./certs/private.pem
JWT_PUBLIC_KEY_PATH=./certs/public.pem
JWT_ALGORITHM=RS256

ACCESS_TOKEN_EXPIRES_MINUTES=15
REFRESH_TOKEN_EXPIRES_MINUTES=43200
ACCESS_COOKIE_NAME=access_token
REFRESH_COOKIE_NAME=refresh_token
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_DOMAIN=
JWT_ISSUER=autonotes-test
JWT_AUDIENCE=autonotes-api

TESTCONTAINER=true
```

### Режимы работы с БД

Управляется флагом **`TESTCONTAINER`**:

| `TESTCONTAINER` | Поведение |
|-----------------|-----------|
| `true` | Testcontainers поднимает `postgres:17`, пробрасывает порт `5432` на хост. `POSTGRES_SERVER` должен быть `localhost`. |
| `false` | Используется внешний PostgreSQL по `ASYNC_DB_URL` из настроек (как в CI job `check-migrations`). |

В обоих режимах перед тестами Alembic накатывает миграции (`upgrade head`), после сессии — откатывает (`downgrade base`).

### JWT-ключи

Перед запуском тестов нужны RSA-ключи в `certs/`:

```bash
mkdir -p certs
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem
```

В CI ключи генерируются автоматически на каждый прогон.

---

## Фикстуры (`conftest.py`)

### Инфраструктура БД

| Фикстура | Scope | Описание |
|----------|-------|----------|
| `postgres_container` | session | Запуск/остановка Testcontainers PostgreSQL |
| `test_db_url` | session | Async URL подключения к тестовой БД |
| `apply_migrations` | session, autouse | Alembic upgrade/downgrade |
| `engine` | session | Async SQLAlchemy engine |
| `clean_db` | function, autouse | `DELETE` из всех таблиц перед каждым тестом |
| `db_session` | function | Async-сессия с rollback в конце |

### HTTP-клиенты

| Фикстура | Описание |
|----------|----------|
| `async_client` | `httpx.AsyncClient` с `ASGITransport`; подменяет `get_session` на `db_session` |
| `client` | Синхронный `TestClient` (заготовка для будущих тестов) |
| `fastapi_app` | Экземпляр `app` из `src.main` |

> **Важно:** `async_client` переопределяет только `get_session`. Эндпоинты auth используют `DBManagerDep`, который создаёт отдельную сессию через `SessionLocal` из `src/db/database.py`. Обе сессии подключаются к одной и той же БД (тот же URL), а `clean_db` очищает таблицы перед каждым тестом.

### Тестовые данные

| Фикстура | Описание |
|----------|----------|
| `valid_user_data` | Валидный payload регистрации |
| `another_user_data` | Второй пользователь для сценариев с дубликатами |
| `sample_video` | Заготовка для тестов `/process/` |
| `mock_video` / `mock_video_no_audio` | Моки `moviepy` VideoFileClip |
| `mock_pipeline_result` | Мок результата Whisper |
| `review_data` / `review_list_data` | Заготовки для тестов отзывов |
| `create_service_review_payload` | Валидный отзыв на сервис |
| `invalid_review_payload` | Невалидный рейтинг (> 5) |

Часть фикстур (`review_*`, `sample_video`) подготовлена для будущих тестов и пока не используется в существующих модулях.

---

## Тестовые модули

### `unit/test_auth.py` — регистрация пользователя

Интеграционные async-тесты через `async_client`. Используют именованные роуты FastAPI (`app.url_path_for`).

| Тест | Проверяет |
|------|-----------|
| `test_register_user_success` | `POST /api/v1/register` → 201, корректный `UserOut`, пароль не утекает |
| `test_register_user_already_exists` | Повторная регистрация → 400 |
| `test_register_user_validation_error` | Отсутствие обязательного поля → 422 |

Пример:

```python
async def test_register_user_success(async_client: AsyncClient, valid_user_data: dict):
    url = app.url_path_for("auth_register")
    response = await async_client.post(url, json=valid_user_data)
    assert response.status_code == status.HTTP_201_CREATED
```

### `unit/test_video_transcription.py` — статистика пользователя

Изолированный unit-тест сервиса `get_user_stats`. Использует **собственную** фикстуру `session` с SQLite in-memory — не зависит от PostgreSQL и `conftest.py`.

| Тест | Проверяет |
|------|-----------|
| `test_user_stats_calculation` | Подсчёт `total_videos` и `avg_processing_time` (600 сек. за 10 минут обработки) |

### `unit/test_notes_synchronizer.py` — синхронизатор заметок

Unit-тесты без БД и без реальных ML-моделей. Используются локальные моки (`MockSubtitles`, `MockImageCaption`, `MockTextSummarizer`) и `unittest.mock.patch` для `extract_audio` / `extract_frames`.

| Класс / тест | Проверяет |
|--------------|-----------|
| `TestTimestampedNote` | Конвертация `timestamp_ms` → `MM:SS` |
| `TestTimestampedSummary` | Сериализация в `segment_summary_dict` |
| `TestVideoSummary` | Сериализация в `summary_dict` |
| `TestNotesSynchronizer.test_synchronize_success` | Синхронизация аудио-чанков с кадрами |
| `TestNotesSynchronizer.test_generate_summary` | Генерация `VideoSummary` из заметок |

---

## Запуск тестов

### Все тесты

```bash
make test
# или
uv run pytest
```

### С подробным выводом

```bash
uv run pytest -v
```

### Один файл или тест

```bash
uv run pytest tests/unit/test_auth.py -v
uv run pytest tests/unit/test_auth.py::test_register_user_success -v
```

### Только unit-тесты без Testcontainers

Если PostgreSQL уже запущен локально:

```bash
TESTCONTAINER=false uv run pytest
```

### Предварительные шаги (локально)

1. Установить зависимости: `uv sync --extra cpu --group dev`
2. Создать `.test.env` (см. выше)
3. Сгенерировать JWT-ключи в `certs/`
4. Убедиться, что Docker запущен (для `TESTCONTAINER=true`)

---

## CI/CD

Тесты запускаются в GitHub Actions (`.github/workflows/ci.yml`).

### Job `test`

1. Python 3.11, `uv sync --extra cpu --group dev`
2. Генерация RSA-ключей
3. `TESTCONTAINER=true` — PostgreSQL через Testcontainers
4. Переменные окружения задаются inline в workflow
5. `uv run pytest`

### Job `ruff`

Линтинг и проверка форматирования — отдельно от тестов:

```bash
uvx ruff check .
uvx ruff format --check .
```

### Job `check-migrations`

Проверяет, что миграции Alembic соответствуют ORM-моделям. Использует GitHub Actions service `postgres:16-alpine`, не pytest.

---

## Написание новых тестов

### API-тест (интеграционный)

1. Добавить файл в `tests/unit/` (или создать `tests/integration/`).
2. Использовать фикстуру `async_client` для async-эндпоинтов.
3. Для эндпоинтов с `SessionDep` — `get_session` уже подменён.
4. Для эндпоинтов с `DBManagerDep` — убедиться, что `TESTCONTAINER` или внешняя БД доступна; данные очищаются через `clean_db`.

```python
from httpx import AsyncClient
from fastapi import status

async def test_example(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
```

### Unit-тест сервиса

Для изоляции от PostgreSQL — локальная фикстура с SQLite (как в `test_video_transcription.py`) или моки репозиториев.

### Unit-тест ML-компонентов

Не загружать реальные модели Hugging Face в тестах. Использовать моки (паттерн из `test_notes_synchronizer.py`).

### Именование

- Файлы: `test_<модуль>.py`
- Функции: `test_<сценарий>`
- Классы (группировка): `Test<Компонент>`

### Что пока не покрыто тестами

- `POST /api/v1/login`, `GET /api/v1/me`
- Загрузка и обработка видео (`/process/`)
- Эндпоинты отзывов и `/users/stats`
- `AuthService.refresh`
- Реальные ML-пайплайны (`Subtitles`, `ImageCaption`, `TextSummarizer`)

---

## Связанные документы

- [BACKEND.md](./BACKEND.md) — документация backend (`src/`)
- [README.md](./README.md) — обзор проекта
- [pyproject.toml](./pyproject.toml) — конфигурация pytest и dev-зависимости
- [.github/workflows/ci.yml](./.github/workflows/ci.yml) — CI pipeline
