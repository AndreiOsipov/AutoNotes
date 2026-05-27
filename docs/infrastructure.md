# Docker-инфраструктура AutoNotes

Production-ready стек: **Nginx → Backend (FastAPI) → PostgreSQL** с изоляцией сетей и секретами через `.env`.

## Рекомендуемая структура каталогов

```
AutoNotes/
├── Dockerfile                  # Backend-образ
├── docker-compose.yml          # Основной стек: db + backend + nginx
├── .env.example
├── .dockerignore
├── docker/
│   └── entrypoint.sh           # Alembic + uvicorn
├── infra/
│   ├── docker-compose.dev.yml  # Dev-override (merge, не дубликат)
│   └── nginx/
│       └── nginx.conf
├── certs/                      # JWT-ключи и опционально TLS для HTTPS (*.pem; в .gitignore)
└── docs/infrastructure.md
```

## Схема сетей и связи контейнеров

```
                    ┌─────────────────────────────────────┐
  Host :80          │  network: proxy (bridge)            │
  ───────────────►  │  ┌─────────┐      ┌─────────────┐ │
                    │  │  nginx  │─────►│   backend   │ │
                    │  └─────────┘      └──────┬──────┘ │
                    └──────────────────────────│────────┘
                                               │
                    ┌──────────────────────────│────────┐
                    │  network: data (internal: true)   │
                    │                          ▼        │
                    │                   ┌──────────┐    │
                    │                   │ postgres │    │
                    │                   └──────────┘    │
                    │  (нет маршрута в интернет)        │
                    └───────────────────────────────────┘
```

| Сервис   | Сети   | Порты на host | Кто может подключиться        |
|----------|--------|---------------|-------------------------------|
| nginx    | proxy  | 80 (443*)     | Интернет / клиенты            |
| backend  | proxy, data | нет      | Только nginx + db             |
| postgres | data   | нет           | Только backend                |

\* HTTPS — см. раздел ниже.

### Service discovery

Docker встроенный DNS: имя сервиса из `docker-compose.yml` = hostname.

- Backend подключается к БД: `db:5432`
- Nginx проксирует на: `backend:8000`

Не используйте `localhost` между контейнерами — это всегда сам контейнер.

## Быстрый старт

```bash
cp .env.example .env
# Пароли в .env; JWT-ключи в ./certs/ (см. .env.example)

mkdir -p certs
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem

docker compose up -d --build
curl http://localhost/health
```

Разработка с пробросом портов (merge двух файлов в одну конфигурацию):

```bash
docker compose -f docker-compose.yml -f infra/docker-compose.dev.yml up --build
```

API через nginx: `http://localhost:8080` (dev), health: `curl http://localhost:8080/health`.

## `expose` vs `ports`

| Директива | Эффект |
|-----------|--------|
| **expose** | Документирует порт для других сервисов в **той же Docker-сети**. На host не публикуется. |
| **ports** | Публикует `host:container` — доступ с машины и извне. |

**Практика:**

- **backend**: только `expose: 8000` — API снаружи недоступен.
- **postgres**: без `ports` — только internal network `data`.
- **nginx**: `ports: "80:80"` — единственная точка входа.

## Внутренние vs внешние сети

- **`proxy`** — обычный bridge: nginx видит backend.
- **`data` с `internal: true`** — контейнеры не имеют исходящего доступа в интернет и **не доступны** с host напрямую. Postgres изолирован от nginx и от публичной сети.

Дополнительно можно вынести мониторинг в отдельную сеть `observability` и подключать только нужные сервисы.

## Масштабирование

```bash
docker compose up -d --scale backend=3
```

При нескольких репликах backend расширьте `infra/nginx/nginx.conf` — например, `upstream` с `server backend:8000` (Compose DNS отдаёт все IP реплик по имени `backend`).

Учтите:

- **Состояние**: сессии/JWT без sticky sessions обычно OK; загрузки файлов — общий volume или S3.
- **ML-модели**: каждая реплика грузит torch/transformers — нужны лимиты памяти.
- **Postgres**: один инстанс; для HA — Patroni / managed RDS вне compose.
- **Миграции**: только один контейнер должен гонять `alembic upgrade` (флаг `RUN_MIGRATIONS`).

## HTTPS — варианты

### 1. TLS на Nginx (рекомендуется в compose)

1. Получите сертификаты (Let's Encrypt / корпоративный CA) и положите в `./certs/` рядом с JWT-ключами (например, `fullchain.pem`, `privkey.pem`).
2. Смонтируйте в nginx:

```yaml
volumes:
  - ./certs:/etc/nginx/certs:ro
ports:
  - "443:443"
```

3. Добавьте `server { listen 443 ssl; ... }` в `infra/nginx/nginx.conf`.
4. В `.env`: `SESSION_COOKIE_SECURE=true`.

### 2. Внешний reverse proxy

Cloud Load Balancer / Traefik / Caddy терминирует TLS и проксирует HTTP на nginx:80.

### 3. Docker Swarm / Kubernetes

TLS на Ingress; compose используется только локально/staging.

**HTTP→HTTPS redirect** — отдельный `server` на :80 с `return 301 https://$host$request_uri;`.

## Healthchecks

| Сервис  | Проверка |
|---------|----------|
| db      | `pg_isready` |
| backend | `GET /health` |
| nginx   | `GET /health` через proxy |

`depends_on: condition: service_healthy` — backend стартует после Postgres, nginx после backend.

## Безопасность (чеклист)

- [ ] Сильные пароли в `.env`, файл в `.gitignore`
- [ ] Postgres без published ports
- [ ] Backend без published ports
- [ ] `server_tokens off`, security headers в nginx
- [ ] `read_only` + `tmpfs` для nginx
- [ ] `no-new-privileges:true`
- [ ] Non-root user в backend Dockerfile
- [ ] JWT keys только read-only mount
- [ ] `SESSION_COOKIE_SECURE=true` за HTTPS
- [ ] Регулярные обновления образов (`postgres:16-alpine`, `nginx:1.27-alpine`)

## Переменные окружения

См. [.env.example](../.env.example). Критичные:

- `POSTGRES_*` — учётные данные БД
- `DB` — SQLAlchemy URL (в compose переопределяется на `@db:5432`)
- `JWT_*_PATH` — пути к PEM в контейнере (`/app/certs/...`)
- `TORCH_EXTRA` — сборка образа backend (`cpu` / `cuda130`)

## GPU backend (опционально)

Для NVIDIA GPU на Linux добавьте в `docker-compose.yml` (или override):

```yaml
backend:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  environment:
    TORCH_EXTRA: cuda130
```

Требуется [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
