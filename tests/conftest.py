import pytest
from fastapi.testclient import TestClient

from main import app


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
