from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


# Модель под создание отзыва
class ReviewCreate(SQLModel):
    username: str
    transcription_id: int | None = Field(
        default=None, foreign_key="videotranscription.id", index=True
    )

    rating: int = Field(ge=1, le=5)
    comment: str = Field(max_length=2000)


# Модель под запрос отзыва
class ReviewResponse(ReviewCreate):
    created_dt_tm: datetime


# Отзывы
class Review(ReviewResponse, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    created_dt_tm: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
