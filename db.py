from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, Field
from datetime import datetime, timezone
from pydantic import ConfigDict

class VideoTranscriptionPublic(SQLModel):
    id: int
    transcription: str
    transcription_ready: bool

class VideoTranscription(VideoTranscriptionPublic, table=True):
    id: int | None = Field(default=None, primary_key=True)
    video_path: str | None = Field(default=None)

# Модель под создание отзыва
class ReviewCreate(SQLModel):
    cust_id: int
    transcription_id: int | None
    rating: int = Field(ge=1, le=5)
    comment: str = Field(max_length=2000)

# Модель под запрос отзыва
class ReviewResponse(SQLModel):
    cust_id: int
    transcription_id: int | None
    rating: int
    comment: str
    created_dt_tm: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Отзывы
class Review(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cust_id: int = Field(index=True)
    transcription_id: int | None = Field(
        default=None,
        foreign_key="videotranscription.id", 
        index=True
    )
    rating: int = Field(ge=1, le=5)
    comment: str = Field(max_length=2000)
    created_dt_tm: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


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