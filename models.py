from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

# В models.py
class VideoTranscriptionBase(SQLModel):
    # Общие поля
    transcription: str = ""
    transcription_ready: bool = False

class VideoTranscription(VideoTranscriptionBase, table=True):
    # Поля только для базы (с ID и временем)
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class VideoTranscriptionPublic(VideoTranscriptionBase):
    # Поля, которые увидит пользователь в ответе API
    id: int