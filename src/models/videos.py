from datetime import datetime

from sqlmodel import Field, SQLModel


class VideoTranscriptionPublic(SQLModel):
    id: int
    transcription: str = Field(default="", nullable=False)
    transcription_ready: bool = Field(default=False)
    user_id: int


class VideoTranscription(VideoTranscriptionPublic, table=True):
    # Поля только для базы (с ID и временем)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    video_path: str | None = Field(default=None)
