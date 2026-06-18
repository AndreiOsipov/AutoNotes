# Документация backend (`src/`)

Backend AutoNotes — REST API на **FastAPI**, который принимает видео, транскрибирует речь, анализирует кадры и формирует структурированный конспект с таймкодами. Данные пользователей, транскрипций и отзывов хранятся в **PostgreSQL**.

## Содержание

- [Обзор архитектуры](#обзор-архитектуры)
- [Структура каталога `src/`](#структура-каталога-src)
- [Точка входа](#точка-входа)
- [Слои приложения](#слои-приложения)
- [API](#api)
- [Аутентификация и авторизация](#аутентификация-и-авторизация)
- [База данных](#база-данных)
- [Обработка видео и ML-пайплайн](#обработка-видео-и-ml-пайплайн)
- [Конфигурация](#конфигурация)
- [Зависимости и ML-стек](#зависимости-и-ml-стек)
- [Запуск и разработка](#запуск-и-разработка)

---

## Обзор архитектуры

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│   Client    │────▶│  FastAPI (src/main.py)                           │
└─────────────┘     │  ├── /api/v1/auth/*   — регистрация, вход        │
                    │  └── /api/v1/*        — видео, отзывы, статистика│
                    └──────────┬───────────────────────┬───────────────┘
                               │                       │
                    ┌──────────▼──────────┐  ┌─────────▼──────────────┐
                    │  PostgreSQL         │  │  ML-пайплайн           │
                    │  (SQLModel/Alembic) │  │  Whisper + BLIP + RuT5 │
                    └─────────────────────┘  └────────────────────────┘
```

Приложение построено по слоистой схеме:

| Слой | Каталог | Назначение |
|------|---------|------------|
| API | `src/api/` | HTTP-роуты, зависимости FastAPI, OpenAPI-теги |
| Схемы | `src/schemas/` | Pydantic-модели запросов/ответов |
| Сервисы | `src/services/` | Бизнес-логика (auth, пользователи, статистика) |
| Репозитории | `src/repositories/` | Доступ к данным в БД |
| Модели | `src/models/` | SQLModel-сущности и таблицы |
| Ядро | `src/core/` | Настройки, JWT, хеширование паролей, исключения |
| БД | `src/db/` | Подключение к PostgreSQL, `DBManager` |
| ML | `src/subtitles/`, `src/NotesSynchronizer/` | Транскрипция, описание кадров, суммаризация |
| Утилиты | `src/utils/` | Пути к рабочим директориям файлов |

---

## Структура каталога `src/`

```
src/
├── main.py                      # Создание FastAPI-приложения, lifespan, health-check
├── api/
│   ├── router.py                # Сборка всех роутеров под /api/v1
│   ├── dependencies.py          # get_current_user, DBManagerDep, SessionDep
│   ├── constants.py             # API_V1_PREFIX = "/api/v1"
│   ├── tags.py                  # OpenAPI-теги (Meta, Auth, Rest)
│   └── routers/
│       ├── auth.py              # register, login, me
│       └── rest.py              # видео, транскрипции, отзывы, статистика
├── core/
│   ├── settings.py              # Pydantic Settings из .env
│   ├── security.py              # Argon2, OAuth2PasswordBearer
│   ├── tokens.py                # JWT access / refresh
│   └── exceptions.py            # Доменные исключения
├── db/
│   ├── database.py              # async engine, SessionLocal, get_session
│   └── db_manager.py            # DBManager — фасад над репозиториями
├── models/
│   ├── users.py                 # Users, RefreshToken
│   ├── videos.py                # VideoTranscription
│   └── reviews.py               # Review, ReviewCreate, ReviewResponse
├── repositories/
│   └── repositories.py          # UserRepository, AuthRepository
├── schemas/
│   ├── config.py                # Базовый APIModel
│   └── user.py                  # UserCreate, UserOut, TokenPair
├── services/
│   ├── services.py              # UserService, AuthService
│   └── video_service.py         # get_user_stats
├── subtitles/
│   ├── subtitles.py             # Whisper, BLIP, RuT5, извлечение аудио/кадров
│   ├── dir_video/               # Загруженные видео
│   ├── dir_audio/               # Извлечённое аудио
│   ├── dir_text/                # JSON-файлы конспектов
│   └── parsed_images/           # Кадры, извлечённые из видео
├── NotesSynchronizer/
│   └── notes_synchronizer.py    # Синхронизация аудио и кадров, генерация summary
└── utils/
    └── utils.py                 # Константы путей (VIDEO_DIR, AUDIO_DIR, …)
```

---

## Точка входа

Файл `src/main.py` создаёт экземпляр `FastAPI` и подключает роутеры.

**Lifespan:** при старте приложения инициализируются синглтоны ML-моделей (`Subtitles`, `ImageCaption`, `TextSummarizer`), чтобы прогреть пайплайны Hugging Face до первого запроса.

**Служебные эндпоинты:**

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/` | Базовое приветствие |
| `GET` | `/health` | Health-check для мониторинга |

В Docker приложение запускается как `uvicorn src.main:app`.

---

## Слои приложения

### API (`src/api/`)

- `all_router` объединяет `auth_router` и `rest_router` с префиксом `/api/v1`.
- `dependencies.py` предоставляет:
  - `SessionDep` — async-сессия SQLAlchemy/SQLModel;
  - `DBManagerDep` — контекстный менеджер с репозиториями `users` и `auth`;
  - `get_current_user` / `get_current_active_user` — извлечение пользователя из JWT (заголовок `Authorization: Bearer` или cookie).

### Схемы (`src/schemas/`)

Pydantic-модели для валидации входных данных и сериализации ответов. Базовый класс `APIModel` запрещает лишние поля (`extra="forbid"`) и поддерживает `from_attributes` для ORM-объектов.

### Сервисы (`src/services/`)

- **`UserService`** — регистрация: проверка уникальности имени и email, хеширование пароля (Argon2), сохранение в БД.
- **`AuthService`** — вход, выпуск пары access/refresh токенов, хранение хеша refresh-токена в БД. Метод `refresh` реализован, но отдельный HTTP-эндпоинт для него пока не подключён.
- **`get_user_stats`** — агрегированная статистика по обработанным видео пользователя.

### Репозитории (`src/repositories/`)

Тонкий слой над `AsyncSession`:

- `UserRepository` — поиск по имени, email, id; создание пользователя.
- `AuthRepository` — CRUD для refresh-токенов.

### `DBManager` (`src/db/db_manager.py`)

Асинхронный контекстный менеджер, который при входе создаёт сессию и инициализирует репозитории. При выходе выполняет `rollback` и закрывает сессию. Используется в auth-роутах через `DBManagerDep`.

---

## API

Все бизнес-эндпоинты доступны под префиксом **`/api/v1`**.

Интерактивная документация: `/docs` (Swagger UI), `/redoc`.

### Аутентификация

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `POST` | `/api/v1/register` | — | Регистрация пользователя |
| `POST` | `/api/v1/login` | — | Вход (OAuth2 Password Flow: `username` + `password`) |
| `GET` | `/api/v1/me` | JWT | Профиль текущего пользователя |

**Регистрация** (`UserCreate`):

- `name` — 5–20 символов, уникальное;
- `email` — валидный email, уникальный;
- `password` / `confirm_password` — 8–128 символов, должны совпадать.

**Ответ входа** (`TokenPair`):

```json
{
  "access_token": "<JWT>",
  "refresh_token": "<random string>",
  "token_type": "bearer"
}
```

Помимо JSON, токены записываются в cookies (`access_token`, `refresh_token`).

### Видео и конспекты

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `POST` | `/api/v1/process/` | JWT | Загрузка видео, запуск фоновой обработки |
| `GET` | `/api/v1/transcription/{id}` | JWT | Статус и текст транскрипции |
| `GET` | `/api/v1/summary/{id}` | JWT | JSON-конспект по id транскрипции |

**Поток обработки видео:**

1. Создаётся запись `VideoTranscription` (`transcription_ready=False`).
2. Файл сохраняется в `subtitles/dir_video/{id}_{filename}`.
3. В `BackgroundTasks` запускается `write_subtitles`:
   - извлечение аудио и кадров;
   - транскрипция Whisper;
   - описание кадров BLIP;
   - синхронизация и суммаризация;
   - запись полного текста в БД и JSON-конспекта в `subtitles/dir_text/{id}_summary.json`.

Клиент может опрашивать `/transcription/{id}`, пока `transcription_ready` не станет `true`.

### Статистика

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `GET` | `/api/v1/users/stats` | JWT | Количество обработанных видео и среднее время обработки (сек.) |

### Отзывы

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| `POST` | `/api/v1/reviews/` | JWT | Создать отзыв |
| `GET` | `/api/v1/reviews` | — | Отзывы на сервис (`transcription_id IS NULL`) |
| `GET` | `/api/v1/reviews/{transcription_id}` | — | Отзывы на конкретную транскрипцию |

Параметры списков: `limit` (1–100), `sort_by` (`newest` | `oldest` | `best` | `worst`).

**Создание отзыва** (`ReviewCreate`):

- `rating` — 1–5;
- `comment` — до 2000 символов;
- `transcription_id` — опционально; если `null`, отзыв считается отзывом на сервис.

---

## Аутентификация и авторизация

### Access-токен (JWT, RS256)

- Подписывается приватным ключом из `JWT_PRIVATE_KEY_PATH`.
- Payload: `sub` (UUID пользователя), `type: "access"`, `iat`, `exp`, `iss`.
- Время жизни: `ACCESS_TOKEN_EXPIRES_MINUTES` (по умолчанию 15 минут).

### Refresh-токен

- Случайная строка (`secrets.token_urlsafe(48)`), **не JWT**.
- В БД хранится только SHA-256 хеш (`RefreshToken.token_hash`).
- Время жизни: `REFRESH_TOKEN_EXPIRES_MINUTES` (по умолчанию 30 дней).

### Передача токена

`get_current_user` принимает токен из:

1. заголовка `Authorization: Bearer <token>`;
2. cookie `access_token` (имя настраивается через `ACCESS_COOKIE_NAME`).

### Хеширование паролей

Используется **Argon2** через `passlib` (`src/core/security.py`).

### Генерация ключей JWT

```bash
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem
```

В Docker ключи монтируются в `/app/certs/`.

---

## База данных

### Подключение

- Async-движок: `postgresql+asyncpg://...` (`settings.ASYNC_DB_URL`).
- Sync URL (`SYNC_DB_URL`) — для Alembic и синхронных операций.
- Фабрика сессий: `SessionLocal` в `src/db/database.py`.

### Таблицы

| Таблица | Модель | Описание |
|---------|--------|----------|
| `users` | `Users` | Пользователи: id (UUID), name, email, password_hash, disabled |
| `refreshtoken` | `RefreshToken` | Refresh-сессии: token_hash, expires_at, revoked |
| `videotranscription` | `VideoTranscription` | Транскрипции: текст, флаги готовности, user_id, timestamps |
| `review` | `Review` | Отзывы: rating, comment, transcription_id, user_id |

Миграции — **Alembic**, каталог `migrations/`. Начальная миграция: `80d32b92d640_init.py`.

При запуске в Docker миграции применяются автоматически, если `RUN_MIGRATIONS=true`.

---

## Обработка видео и ML-пайплайн

### Компоненты (`src/subtitles/subtitles.py`)

Все ML-классы наследуют `SingleProcessor` — синглтон, загружающий Hugging Face `pipeline` один раз на процесс.

| Класс | Модель | Задача |
|-------|--------|--------|
| `Subtitles` | `antony66/whisper-large-v3-russian` | Распознавание речи (русский), с таймкодами |
| `ImageCaption` | `Salesforce/blip-image-captioning-large` | Описание содержимого кадра |
| `TextSummarizer` | `IlyaGusev/rut5_base_sum_gazeta` | Суммаризация текста на русском |

Устройство вычислений: CUDA при наличии, иначе CPU. Тип данных: `float16`.

### Вспомогательные функции

- **`extract_audio`** — извлекает аудиодорожку из видео через `moviepy`.
- **`extract_frames`** — через OpenCV берёт кадры с шагом `frame_distance=150`, сохраняет в `parsed_images/{video_id}/`.

### Синхронизатор (`src/NotesSynchronizer/notes_synchronizer.py`)

`NotesSynchronizer` объединяет аудио-транскрипт и описания кадров:

1. Извлекает аудио и транскрибирует с таймкодами (чанки Whisper).
2. Извлекает кадры и генерирует подписи BLIP.
3. Сопоставляет кадры с аудио-чанками по временным меткам.
4. Формирует список `TimestampedNote` (текст + описание слайдов + combined_text).
5. Генерирует `VideoSummary`:
   - `concise` — краткий конспект (max 150 токенов);
   - `detailed` — развёрнутый (max 300);
   - `key_points` — ключевые фразы по эвристике;
   - `timestamped_summaries` — фрагменты с таймкодами `MM:SS`.

Результат сохраняется как JSON в `subtitles/dir_text/{id}_summary.json`.

### Рабочие директории (`src/utils/utils.py`)

| Константа | Путь | Назначение |
|-----------|------|------------|
| `VIDEO_DIR` | `subtitles/dir_video` | Загруженные видео |
| `AUDIO_DIR` | `subtitles/dir_audio` | WAV-файлы |
| `TEXT_DIR` | `subtitles/dir_text` | JSON-конспекты |
| `IMAGES_DIR` | `subtitles/parsed_images` | Кадры из видео |

Пути считаются относительно `Path.cwd()` (рабочая директория процесса).

---

## Конфигурация

Настройки загружаются из `.env` через `pydantic-settings` (`src/core/settings.py`). Кэшируются через `@lru_cache` в `get_settings()`.

### Основные переменные

| Переменная | Описание |
|------------|----------|
| `PROJECT_NAME`, `PROJECT_DESCRIPTION`, `PROJECT_VERSION` | Метаданные OpenAPI |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_DB` | PostgreSQL |
| `JWT_PRIVATE_KEY_PATH`, `JWT_PUBLIC_KEY_PATH`, `JWT_ALGORITHM` | JWT (RS256) |
| `ACCESS_TOKEN_EXPIRES_MINUTES`, `REFRESH_TOKEN_EXPIRES_MINUTES` | TTL токенов |
| `ACCESS_COOKIE_NAME`, `REFRESH_COOKIE_NAME` | Имена cookies |
| `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_DOMAIN` | Параметры cookies |
| `JWT_ISSUER`, `JWT_AUDIENCE` | Claims JWT |
| `TESTCONTAINER` | Флаг для тестов с testcontainers |

Шаблон: `.env.example` в корне проекта.

---

## Зависимости и ML-стек

Управление зависимостями — **uv** (`pyproject.toml`).

### Базовые зависимости

FastAPI, SQLModel, asyncpg, Alembic, PyJWT, passlib (Argon2), moviepy, opencv-python, librosa и др.

### ML extra (torch + transformers)

PyTorch и Transformers устанавливаются **только через optional extra**, чтобы не тянуть GPU-сборку по умолчанию:

```bash
# CPU (по умолчанию в Docker)
uv sync --extra cpu

# CUDA 13.0 (Linux/Windows)
uv sync --extra cuda130

# ROCm (Linux)
uv sync --extra rocm
```

Extras взаимоисключающие. В Docker-сборке extra задаётся аргументом `TORCH_EXTRA` (см. `Dockerfile`, `docker-compose.yml`).

---

## Запуск и разработка

### Docker (рекомендуется)

```bash
cp .env.example .env
make up
# или: docker compose up -d --build
```

Backend доступен через nginx (порт из `NGINX_HTTP_PORT`, по умолчанию 80).

### Локально без Docker

```bash
uv sync --extra cpu
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Требуется запущенный PostgreSQL и настроенный `.env`. JWT-ключи — в `certs/`.

### Тесты

```bash
uv run pytest
```

Конфигурация pytest — в `pyproject.toml`, тестовые переменные — в `.test.env`.

### Доменные исключения

Определены в `src/core/exceptions.py` и перехватываются в роутерах с маппингом в HTTP-статусы:

| Исключение | HTTP |
|------------|------|
| `InvalidCredentialsError` | 401 |
| `UserAlreadyExistsError`, `EmailAlreadyExistsError` | 400 |
| `RefreshTokenNotFoundError`, `RefreshTokenExpiredError` | (сервисный слой, эндпоинт refresh не подключён) |

---

## Связанные документы

- [README.md](./README.md) — обзор проекта и быстрый старт
- [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md) — инфраструктура, Docker, nginx
- [pyproject.toml](./pyproject.toml) — зависимости и конфигурация инструментов
- [migrations/](./migrations/) — схема БД (Alembic)
