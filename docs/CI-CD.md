# Документация CI/CD

AutoNotes использует **GitHub Actions** для проверки кода, тестов и релизов, а **Docker Compose** — для сборки и развёртывания стека в production и dev-окружении.

## Содержание

- [Обзор пайплайна](#обзор-пайплайна)
- [GitHub Actions](#github-actions)
- [Ветки и релизный процесс](#ветки-и-релизный-процесс)
- [Docker-образ](#docker-образ)
- [Docker Compose](#docker-compose)
- [Makefile](#makefile)
- [Секреты и переменные](#секреты-и-переменные)
- [Локальная разработка vs production](#локальная-разработка-vs-production)
- [Чеклист перед релизом](#чеклист-перед-релизом)

---

## Обзор пайплайна

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Разработка (feature branches)                                          │
│  push / pull_request → main, develop                                    │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ci.yml                                                                 │
│  ├── ruff          — линт и проверка форматирования                     │
│  ├── test          — pytest + Testcontainers                            │
│  └── check-migrations — alembic upgrade + alembic check                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PR main → production (merge)                                           │
└───────────────┬─────────────────────────────┬─────────────────────────────┘
                ▼                             ▼
        ┌───────────────┐             ┌───────────────────┐
        │  tag.yml      │             │  dockerhub.yml    │
        │  git tag      │             │  push image       │
        │  v{version}   │             │  Docker Hub       │
        └───────────────┘             └───────────────────┘
```

| Компонент | Файл / каталог | Назначение |
|-----------|----------------|------------|
| CI | `.github/workflows/ci.yml` | Линт, тесты, миграции |
| Тегирование | `.github/workflows/tag.yml` | Git-тег по версии из `pyproject.toml` |
| Публикация образа | `.github/workflows/dockerhub.yml` | Сборка и push в Docker Hub |
| Образ backend | `Dockerfile` | Multi-stage build, uv, torch extra |
| Оркестрация | `docker-compose.yml` | db + backend + nginx |
| Dev-override | `infra/docker-compose.dev.yml` | Проброс портов для разработки |
| Entrypoint | `docker/entrypoint.sh` | Миграции Alembic перед стартом |
| Команды | `Makefile` | Обёртки над compose, pytest, ruff |

---

## GitHub Actions

### `ci.yml` — Python CI

**Триггеры:**

| Событие | Условие |
|---------|---------|
| `push` | Все ветки, **кроме** `main`, `develop`, `production` |
| `pull_request` | В `main` или `develop` |

Игнорируются изменения только в `README.md`, `.env.example`, `LICENSE`, `docs/`.

#### Job `ruff`

- Runner: `ubuntu-latest`
- `uvx ruff check .` — линтинг
- `uvx ruff format --check .` — проверка форматирования

Миграции в `migrations/` исключены из ruff (`pyproject.toml`).

#### Job `test`

- Python **3.11**, зависимости: `uv sync --extra cpu --group dev`
- Генерация RSA-ключей в `certs/`
- `TESTCONTAINER=true` — PostgreSQL через Testcontainers
- `uv run pytest`

Переменные окружения задаются inline в workflow (JWT, Postgres, `TESTCONTAINER`). Подробнее — [TEST.md](./TEST.md).

#### Job `check-migrations`

- PostgreSQL **16-alpine** как GitHub Actions service на порту `5432`
- `TESTCONTAINER=false` — подключение к service Postgres
- `uv run alembic upgrade head` → `uv run alembic check`

Проверяет, что миграции Alembic соответствуют ORM-моделям в `src/models/`.

Все три job выполняются **параллельно**.

---

### `dockerhub.yml` — публикация в Docker Hub

**Триггер:** закрытый PR в ветку `production` (`types: [closed]`).

**Условие запуска:**

- PR был **смержен**;
- base branch: `production`;
- head branch: `main`.

**Шаги:**

1. Checkout с полной историей (`fetch-depth: 0`)
2. Получение последнего git-тега (`git tag --sort=-version:refname`)
3. Логин в Docker Hub (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`)
4. Сборка и push образа (`docker/build-push-action@v6`):
   - `build-args: TORCH_EXTRA=cpu`
   - Теги: `{username}/autonotes:{latest_tag}` и `{username}/autonotes:latest`

---

### `tag.yml` — версионирование

**Триггер:** закрытый PR в ветку `main` (`types: [closed]`).

**Условие запуска** (в workflow):

- PR смержен;
- base branch: `production`;
- head branch: `main`.

**Шаги:**

1. Извлечение `version` из `pyproject.toml`
2. Создание git-тега `v{version}` и push в origin

> **Замечание:** триггер срабатывает на PR в `main`, а условие `if` проверяет `base.ref == 'production'`. При необходимости синхронизируйте триггер и условие с фактическим релизным процессом (как в `dockerhub.yml`).

---

## Ветки и релизный процесс

Предполагаемая модель веток:

| Ветка | Назначение |
|-------|------------|
| `main` | Основная ветка разработки |
| `develop` | Интеграционная ветка |
| `production` | Production-релизы |
| feature-ветки | CI на push (кроме защищённых веток) |

**Типичный релиз:**

1. Разработка в feature-ветке → CI на push
2. PR в `main` / `develop` → полный CI (`ruff`, `test`, `check-migrations`)
3. Обновление `version` в `pyproject.toml`
4. PR `main` → `production`, merge
5. Автоматически: git-тег + push образа в Docker Hub

---

## Docker-образ

Файл: `Dockerfile` (multi-stage).

### Stage `builder`

- Базовый образ: `python:3.12-slim-bookworm`
- Установка **uv**, `uv sync --frozen --no-dev --extra ${TORCH_EXTRA}`
- Аргумент сборки: `TORCH_EXTRA` (`cpu` | `cuda130` | `rocm`)

### Stage `runtime`

- Копирование `.venv` из builder
- Non-root пользователь `app` (UID/GID 1000)
- `PYTHONPATH=/app`
- Healthcheck: `GET /health` каждые 30 с
- Entrypoint: `docker/entrypoint.sh`
- CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips *`

### Entrypoint (`docker/entrypoint.sh`)

```sh
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
exec "$@"
```

При старте контейнера миграции накатываются автоматически (если `RUN_MIGRATIONS=true`).

### `.dockerignore`

В образ не попадают: `.git`, `.github`, `.venv`, секреты (`*.pem`, `.env`), кэши медиа, тестовые артефакты. Markdown-файлы исключены (кроме `README.md`).

---

## Docker Compose

### Production (`docker-compose.yml`)

Стек из трёх сервисов:

```
Client → nginx:80 → backend:8000 → db:5432
```

| Сервис | Образ | Сети | Порты на host |
|--------|-------|------|---------------|
| `db` | `postgres:16-alpine` | `data` (internal) | нет |
| `backend` | build из `Dockerfile` | `proxy`, `data` | `expose: 8000` |
| `nginx` | `nginx:1.27-alpine` | `proxy` | `${NGINX_HTTP_PORT:-80}:80` |

**Volumes:**

- `postgres_data` — данные PostgreSQL
- `media_data` → `/app/src/subtitles` — видео, аудио, конспекты
- `./certs` → `/app/certs:ro` — JWT-ключи

**Healthchecks и зависимости:**

- `backend` ждёт healthy `db`
- `nginx` ждёт healthy `backend`

**Запуск:**

```bash
cp .env.example .env
# Настроить .env и certs/
make up-prod
# или: docker compose up -d --build
```

### Dev-override (`infra/docker-compose.dev.yml`)

Merge поверх основного compose:

```bash
make up
# docker compose -f docker-compose.yml -f infra/docker-compose.dev.yml up --build
```

| Сервис | Дополнительные порты |
|--------|---------------------|
| `db` | `5432:5432` |
| `backend` | `8000:8000` |
| `nginx` | `8080:80` (по умолчанию) |

### Nginx (`infra/nginx/nginx.conf`)

- Reverse proxy на `backend:8000`
- `client_max_body_size 512m` — загрузка видео
- Заголовки `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`

Подробнее об инфраструктуре — [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md).

---

## Makefile

| Команда | Действие |
|---------|----------|
| `make up` | Dev-стек (compose + dev-override, foreground) |
| `make up-prod` | Production-стек в фоне |
| `make down` | Остановка compose |
| `make migrate` | `uv run alembic upgrade head` |
| `make check-migrations` | `uv run alembic check` |
| `make lint` | `uvx ruff check .` |
| `make test` | `uv run pytest` |

---

## Секреты и переменные

### GitHub Secrets (для `dockerhub.yml`)

| Secret | Назначение |
|--------|------------|
| `DOCKERHUB_USERNAME` | Логин Docker Hub |
| `DOCKERHUB_TOKEN` | Access token Docker Hub |

### Переменные сборки Docker

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `TORCH_EXTRA` | `cpu` | Extra для PyTorch (`cpu`, `cuda130`, `rocm`) |

### Переменные runtime (`.env`)

Критичные для compose:

| Переменная | Описание |
|------------|----------|
| `POSTGRES_*` | Учётные данные БД |
| `RUN_MIGRATIONS` | Запуск Alembic при старте backend |
| `NGINX_HTTP_PORT` | Порт nginx на host |
| `JWT_*_PATH` | Пути к RSA-ключам в контейнере |
| `SESSION_COOKIE_SECURE` | `true` за HTTPS в production |

Шаблон: [.env.example](./.env.example).

---

## Локальная разработка vs production

| Аспект | Локально (dev) | Production |
|--------|----------------|------------|
| Compose | `docker-compose.yml` + `infra/docker-compose.dev.yml` | `docker-compose.yml` |
| Доступ к API | `:8080` (nginx) или `:8000` (backend) | `:80` (nginx) |
| Postgres | Порт `5432` проброшен | Только internal network |
| Миграции | `RUN_MIGRATIONS=true` в entrypoint | То же |
| CI | Testcontainers / service Postgres | — |
| Образ | Локальная сборка | Docker Hub после merge в `production` |

### GPU-сборка (опционально)

Для NVIDIA GPU на Linux:

```bash
TORCH_EXTRA=cuda130 docker compose up -d --build
```

Требуется [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Подробности — в [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md).

---

## Чеклист перед релизом

- [ ] Все CI job зелёные (`ruff`, `test`, `check-migrations`)
- [ ] Версия обновлена в `pyproject.toml`
- [ ] Миграции Alembic добавлены и проверены (`make check-migrations`)
- [ ] `.env` на сервере настроен (пароли, JWT, `SESSION_COOKIE_SECURE`)
- [ ] RSA-ключи в `certs/` (не в git)
- [ ] PR `main` → `production` смержен
- [ ] Образ появился в Docker Hub с корректным тегом
- [ ] `curl http://<host>/health` возвращает `{"status":"ok"}`

---

## Связанные документы

- [BACKEND.md](./BACKEND.md) — документация backend (`src/`)
- [TEST.md](./TEST.md) — тесты и CI job `test`
- [docs/INFRASTRUCTURE.md](./docs/INFRASTRUCTURE.md) — сети, HTTPS, безопасность
- [README.md](./README.md) — быстрый старт проекта
- [.github/workflows/](./.github/workflows/) — исходники workflow
