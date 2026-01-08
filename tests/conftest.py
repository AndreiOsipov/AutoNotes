import pytest
from fastapi.testclient import TestClient

from main import app
from unittest.mock import MagicMock

@pytest.fixture
def client():
    """
    Общий HTTP-клиент для всех API-тестов
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