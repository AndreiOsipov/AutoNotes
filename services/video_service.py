from datetime import datetime
from sqlmodel import Session, select
from models import VideoTranscription

def mark_video_done(session: Session, video_id: int, transcription_text: str):
    """Обновляет запись: ставит текст и фиксирует время окончания"""
    video = session.get(VideoTranscription, video_id)
    if not video:
        return None
    
    video.transcription = transcription_text
    video.transcription_ready = True
    video.finished_at = datetime.utcnow() # Тот самый момент завершения
    
    session.add(video)
    session.commit()
    session.refresh(video)
    return video

def get_user_stats(session: Session, user_id: int):
    """Считает количество видео и среднее время обработки для юзера"""
    statement = select(VideoTranscription).where(
        VideoTranscription.user_id == user_id,
        VideoTranscription.finished_at != None
    )
    videos = session.exec(statement).all()

    if not videos:
        return {"total_videos": 0, "avg_processing_time": 0}

    durations = [
        (v.finished_at - v.created_at).total_seconds() 
        for v in videos
    ]
    
    avg_time = sum(durations) / len(durations)
    
    return {
        "total_videos": len(videos),
        "avg_processing_time": round(avg_time, 2)
    }