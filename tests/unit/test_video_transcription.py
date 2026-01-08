import pytest
from datetime import UTC, datetime, timedelta
from sqlmodel import Session, SQLModel, create_engine
from db import VideoTranscription
from services.video_service import get_user_stats


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_user_stats_calculation(session: Session):
    # 1. Создаем тестовое видео (начало 10 минут назад)
    now = datetime.now(UTC)
    start_time = now - timedelta(minutes=10)
    video = VideoTranscription(user_id=1, created_at=start_time)
    session.add(video)
    session.commit()

    video.completed_at = now
    video.transcription_ready = True
    session.add(video)
    session.commit()

    # 3. Проверяем статистику
    stats = get_user_stats(session, user_id=1)

    assert stats["total_videos"] == 1
    # Время должно быть ровно 600 секунд (10 минут)
    assert stats["avg_processing_time"] == 600