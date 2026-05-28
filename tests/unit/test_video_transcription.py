import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.models import VideoTranscription
from src.services import get_user_stats


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_user_stats_calculation(session: Session):
    test_user_id = uuid.uuid4()
    start_time = datetime.now(UTC) - timedelta(minutes=10)

    # Явно передаем путь к видео и текст, чтобы не ловить ошибки базы
    video = VideoTranscription(
        user_id=test_user_id,
        created_at=start_time,
        completed_at=datetime.now(UTC),
        video_path="test.mp4",
        transcription="",  # Гарантируем отсутствие None
        transcription_ready=False,
    )
    session.add(video)
    session.commit()

    # 3. Проверяем статистику
    stats = get_user_stats(session, user_id=test_user_id)

    assert stats["total_videos"] == 1
    # Время должно быть ровно 600 секунд (10 минут)
    assert stats["avg_processing_time"] == 600
