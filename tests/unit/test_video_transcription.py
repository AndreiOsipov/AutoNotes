import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, SQLModel, create_engine
from models import VideoTranscription
from services.video_service import get_user_stats

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_user_stats_calculation(session: Session):
    # 1. Создаем тестовое видео (начало 10 минут назад)
    start_time = datetime.utcnow() - timedelta(minutes=10)
    video = VideoTranscription(user_id=1, created_at=start_time, video_path="test.mp4")
    session.add(video)
    session.commit()

    video.completed_at = datetime.utcnow()
    video.transcription_ready = True
    session.add(video)
    session.commit()

    # 3. Проверяем статистику
    stats = get_user_stats(session, user_id=1)
    
    assert stats["total_videos"] == 1
    # Время должно быть около 600 секунд (10 минут)
    assert 599 <= stats["avg_processing_time"] <= 601