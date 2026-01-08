import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
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


@pytest.fixture
def client():
    """
    Общий HTTP-клиент для всех синхронных API-тестов
    """
    return TestClient(app)


@pytest_asyncio.fixture
async def asyncio_client():
    """
    Общий HTTP-клиент для всех асинхронных API-тестов
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, 
        base_url="http://test"
    ) as ac:
        yield ac


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