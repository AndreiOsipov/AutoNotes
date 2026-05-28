from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from src.db import get_session
from src.api.dependencies import get_db_manager
from src.main import app

TEST_DB_PATH = Path(__file__).resolve().parent / "test.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

# Module-level flag to ensure migrations run only once per Python process
_migrations_applied = False


def _ensure_migrations():
    """Применяет миграции Alembic к тестовой БД (один раз за процесс)."""
    global _migrations_applied
    if _migrations_applied:
        return
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(TEST_DATABASE_URL))
    command.upgrade(alembic_cfg, "head")
    _migrations_applied = True


@pytest.fixture(scope="session")
def engine():
    """Асинхронный движок для тестовой БД (создаётся один раз за сессию)."""
    # Применяем миграции при создании движка
    _ensure_migrations()
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield eng
    eng.sync_engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    """Фабрика сессий SQLAlchemy для всей сессии."""
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """Новая сессия БД для каждого теста с очисткой данных."""
    async with session_factory() as session:
        # Очищаем все таблицы перед тестом (используем text() для корректной работы с aiosqlite)
        for table in reversed(SQLModel.metadata.sorted_tables):
            try:
                await session.execute(text(f"DELETE FROM {table.name}"))
            except Exception:
                pass
        await session.commit()

        yield session
        await session.rollback()

        # Очищаем все таблицы после теста
        for table in reversed(SQLModel.metadata.sorted_tables):
            try:
                await session.execute(text(f"DELETE FROM {table.name}"))
            except Exception:
                pass
        await session.commit()


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Асинхронный HTTP-клиент, в котором реальная база данных
    подменена на тестовую.
    """

    # Функция для переопределения зависимости FastAPI
    def override_get_async_session():
        yield db_session

    async def override_get_db_manager():
        from src.db import DBManager

        # DBManager expects a callable that returns AsyncSession.
        # We wrap the test session so DBManager uses it, and we skip
        # auto-cleanup since pytest manages the session lifecycle.
        class _PassthroughDBManager(DBManager):
            async def __aexit__(self, *args) -> None:
                # Don't close/rollback the test session
                pass

        manager = _PassthroughDBManager(lambda: db_session)
        await manager.__aenter__()
        try:
            yield manager
        finally:
            await manager.__aexit__(None, None, None)

    app.dependency_overrides[get_session] = override_get_async_session
    app.dependency_overrides[get_db_manager] = override_get_db_manager

    # Используем ASGITransport для обхода необходимости поднимать реальный сервер
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client

    # Очищаем переопределения после теста
    app.dependency_overrides.clear()


@pytest.fixture
def valid_user_data() -> dict:
    """Фикстура с валидным payload для регистрации."""
    return {
        "name": "test_user",
        "email": "user@mail.com",
        "password": "secure_password_123",
        "confirm_password": "secure_password_123",
    }


@pytest.fixture
def another_user_data() -> dict:
    return {
        "name": "another_user",
        "email": "auser@mail.com",
        "password": "super_secure_456",
        "confirm_password": "super_secure_456",
    }


@pytest.fixture
def client():
    """
    Общий HTTP-клиент для всех синхронных API-тестов
    """
    return TestClient(app)


@pytest.fixture
def sample_video():
    """Тестовые данные для POST /process/"""
    return {"ext": "mp4", "data": 123}


@pytest.fixture
def fixed_seed():
    return 42


@pytest.fixture
def mock_video():
    """Мок видео с аудио"""
    video = MagicMock()
    video.audio = MagicMock()
    return video


@pytest.fixture
def mock_video_no_audio():
    """Мок видео без аудио"""
    video = MagicMock()
    video.audio = None
    return video


@pytest.fixture
def mock_pipeline_result():
    """Мок результата транскрипции"""
    return {"text": "Привет мир"}


@pytest.fixture(scope="function")
def mock_db(db_session):
    """Alias для db_session"""
    return db_session


@pytest.fixture
def review_data():
    """Тестовые данные для одного отзыва"""
    return {
        "id": 1,
        "rating": 5,
        "text": "Отличный сервис!",
        "transcription_id": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def review_list_data():
    """Список тестовых отзывов для фильтрации"""
    return [
        {
            "id": 1,
            "rating": 5,
            "text": "Отличный сервис!",
            "transcription_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        {
            "id": 2,
            "rating": 4,
            "text": "Хороший сервис",
            "transcription_id": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        {
            "id": 3,
            "rating": 3,
            "text": "Средний сервис",
            "transcription_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    ]


@pytest.fixture
def create_service_review_payload():
    """Валидный payload для отзыва на сервис"""
    return {
        "rating": 4,
        "text": "Хороший сервис в целом",
        "transcription_id": None,
    }


@pytest.fixture
def invalid_review_payload():
    """Невалидный payload (рейтинг > 5)"""
    return {
        "rating": 6,
        "text": "Плохой отзыв",
        "transcription_id": 1,
    }