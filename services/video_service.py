from sqlmodel import Session, select
from db import VideoTranscription


def get_user_stats(session: Session, user_id: int):
    """Считает количество видео и среднее время обработки для юзера"""
    statement = select(VideoTranscription).where(
        VideoTranscription.user_id == user_id, VideoTranscription.completed_at != None
    )
    videos = session.exec(statement).all()

    if not videos:
        return {"total_videos": 0, "avg_processing_time": 0}

    durations = [(v.completed_at - v.created_at).total_seconds() for v in videos]

    avg_time = sum(durations) / len(durations)

    return {"total_videos": len(videos), "avg_processing_time": round(avg_time, 2)}
