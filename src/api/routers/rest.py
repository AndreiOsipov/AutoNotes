import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
)
from sqlmodel import Session, asc, desc, join, select

from src.api import SessionDep, get_current_active_user
from src.models import (
    Review,
    ReviewCreate,
    ReviewResponse,
    Users,
    VideoTranscription,
    VideoTranscriptionPublic,
)
from src.NotesSynchronizer.notes_synchronizer import NotesSynchronizer
from src.services import get_user_stats
from src.subtitles.subtitles import ImageCaption, Subtitles, TextSummarizer
from src.utils.utils import SUMMARY_POSTFIX, TEXT_DIR, VIDEO_DIR

router = APIRouter()


def write_subtitles(video_path: str, video_id, session: Session):
    transcription = session.get(VideoTranscription, video_id)
    transcription.created_at = datetime.now(UTC)
    subtitles = Subtitles()
    image_caption = ImageCaption()
    summarizer = TextSummarizer()

    synchronizer = NotesSynchronizer(subtitles, image_caption, summarizer)
    notes = synchronizer.synchronize(video_path, video_id)
    video_summary = synchronizer.generate_summary(notes)

    video_summary_file = str(TEXT_DIR / f"{video_id}_{SUMMARY_POSTFIX}")

    with open(video_summary_file, "w", encoding="utf-8") as f:
        json.dump(video_summary.summary_dict, f, ensure_ascii=False, indent=2)

    full_transcription = " ".join([note.audio_text for note in notes])

    transcription.transcription = full_transcription
    transcription.transcription_ready = True
    transcription.completed_at = datetime.now(UTC)
    session.add(transcription)
    session.commit()


@router.post("/process/", response_model=VideoTranscriptionPublic)
def process_video(
    video: UploadFile,
    session: SessionDep,
    background_tasks: BackgroundTasks,
    current_user: Users = Depends(get_current_active_user),
):
    video_transcription = VideoTranscription(
        transcription="", transcription_ready=False, user_id=current_user.id
    )
    session.add(video_transcription)
    session.commit()
    session.refresh(video_transcription)
    video_path = VIDEO_DIR / f"{video_transcription.id}_{video.filename}"
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    background_tasks.add_task(
        write_subtitles, video_path, video_transcription.id, session
    )
    return video_transcription


@router.get(
    "/transcription/{transcription_id}",
    response_model=VideoTranscriptionPublic,
)
def download_transcription(
    transcription_id: int,
    session: SessionDep,
    current_user: Users = Depends(get_current_active_user),
):
    transcription = session.get(VideoTranscription, transcription_id)
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail=f"transcription with id {transcription_id} not found",
        )
    return transcription


@router.get("/summary/{transcription_id}")
def download_summary(
    transcription_id: int,
    current_user: Users = Depends(get_current_active_user),
):
    video_summary_file = str(TEXT_DIR / f"{transcription_id}_{SUMMARY_POSTFIX}")
    if not (Path(video_summary_file).exists()):
        raise HTTPException(
            status_code=404,
            detail=f"transcription with id {transcription_id} not found",
        )

    with open(video_summary_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/users/stats")
def read_stats(
    session: SessionDep, current_user: Users = Depends(get_current_active_user)
):
    return get_user_stats(session, current_user.id)


# Создание отзыва
@router.post("/reviews/", response_model=ReviewResponse)
def create_review(
    review: ReviewCreate,
    session: SessionDep,
    current_user: Users = Depends(get_current_active_user),
):
    review = Review(
        username=current_user.username,
        user_id=current_user.id,
        transcription_id=review.transcription_id,
        rating=review.rating,
        comment=review.comment,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


# Запрос отзывов без transcription_id (отзывы на сервис)
@router.get("/reviews", response_model=List[ReviewResponse])
def get_service_reviews(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|best|worst)$"),
):
    statement = (
        select(
            Review.id,
            Users.name,
            Review.transcription_id,
            Review.rating,
            Review.comment,
            Review.created_dt_tm,
        )
        .select_from(join(Review, Users, Review.user_id == Users.id))
        .where(Review.transcription_id.is_(None))
    )
    if sort_by == "newest":
        statement = statement.order_by(desc(Review.created_dt_tm))
    elif sort_by == "oldest":
        statement = statement.order_by(asc(Review.created_dt_tm))
    elif sort_by == "best":
        statement = statement.order_by(desc(Review.rating), desc(Review.created_dt_tm))
    elif sort_by == "worst":
        statement = statement.order_by(asc(Review.rating), desc(Review.created_dt_tm))

    statement = statement.limit(limit)
    return session.exec(statement).all()


# Запрос отзывов на transcription
@router.get("/reviews/{transcription_id}", response_model=List[ReviewResponse])
def get_transcription_reviews(
    session: SessionDep,
    transcription_id: int,
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|best|worst)$"),
):
    statement = (
        select(
            Review.id,
            Users.name,
            Review.transcription_id,
            Review.rating,
            Review.comment,
            Review.created_dt_tm,
        )
        .select_from(join(Review, Users, Review.user_id == Users.id))
        .where(Review.transcription_id == transcription_id)
    )
    if sort_by == "newest":
        statement = statement.order_by(desc(Review.created_dt_tm))
    elif sort_by == "oldest":
        statement = statement.order_by(asc(Review.created_dt_tm))
    elif sort_by == "best":
        statement = statement.order_by(desc(Review.rating), desc(Review.created_dt_tm))
    elif sort_by == "worst":
        statement = statement.order_by(asc(Review.rating), desc(Review.created_dt_tm))

    statement = statement.limit(limit)
    return session.exec(statement).all()
