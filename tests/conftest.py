import pytest
from sqlmodel import SQLModel
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import app
from db import get_session
from unittest.mock import MagicMock
from tests.test_db import engine_test, get_test_session


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


TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


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
    return {
        "ext": "mp4",
        "data": 123
    }


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


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine


@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


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
