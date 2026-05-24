import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# from sqlalchemy.orm import Session, sessionmaker
# from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from src.db import get_session
from src.main import app
from tests.test_db import engine_test, get_test_session

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def fastapi_app():
    return app


@pytest.fixture(scope="session")
async def engine():
    """Асинхронный движок зависит от фикстуры миграций."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    yield engine

    await engine.dispose()


# @pytest.fixture(autouse=True)
# async def clean_db(engine):
#    async with engine.begin() as conn:
#        for table in reversed(Base.metadata.sorted_tables):
#            await conn.execute(table.delete())


@pytest.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Асинхронный HTTP-клиент, в котором реальная база данных
    подменена на тестовую.
    """

    # Функция для переопределения зависимости FastAPI
    def override_get_async_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_async_session

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


# Всё что было до меня

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
app.dependency_overrides[get_session] = get_test_session


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """
    Создание тестовой базы данных
    """
    SQLModel.metadata.drop_all(bind=engine_test)
    SQLModel.metadata.create_all(bind=engine_test)
    yield
    SQLModel.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client():
    """
    Общий HTTP-клиент для всех синхронных API-тестов
    """
    return TestClient(app)


@pytest.fixture
def sample_video():
    """
    Тестовые данные для POST /process/
    """
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


"""@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine"""


"""@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()"""


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
