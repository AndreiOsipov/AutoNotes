from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, Field
from datetime import datetime


class VideoTranscriptionPublic(SQLModel):
    id: int
    transcription: str = Field(default="", nullable=False)
    transcription_ready: bool = Field(default=False)
    user_id: int


class VideoTranscription(VideoTranscriptionPublic, table=True):
    # Поля только для базы (с ID и временем)
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    video_path: str | None = Field(default=None)


class UserOut(SQLModel):
    id: int
    username: str
    disabled: bool


class User(UserOut, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=20)
    hashed_password: str
    disabled: bool = False


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


sql_db_file = "database.db"
sqlite_url = f"sqlite:///{sql_db_file}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SessionDep = Annotated[Session, Depends(get_session)]
