from contextlib import asynccontextmanager
import shutil
import json
from pathlib import Path
from users.users_router import router
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks, Depends, Query
from datetime import datetime, UTC
from db import User, SessionDep, VideoTranscriptionPublic, VideoTranscription, ReviewCreate, ReviewResponse, Session, create_db_and_tables
from utils.utils import VIDEO_DIR, TEXT_DIR, SUMMARY_POSTFIX
from subtitles.subtitles import Subtitles, ImageCaption, TextSummarizer
from NotesSynchronizer.notes_synchronizer import NotesSynchronizer


from users.users import get_current_active_user
from services.video_service import get_user_stats


from reviews.reviews import ReviewCRUD
from typing import List

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Subtitles()
    ImageCaption()
    TextSummarizer()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


def write_subtitles(video_path: str, video_id, session: Session):
    transcription = session.get(VideoTranscription, video_id)
    transcription.created_at = datetime.now(UTC)
    subtitles = Subtitles()
    image_caption = ImageCaption()
    summarizer= TextSummarizer()

    synchronizer = NotesSynchronizer(subtitles, image_caption, summarizer)
    notes = synchronizer.synchronize(video_path, video_id)
    video_summary = synchronizer.generate_summary(notes)
    
    video_summary_file = str(TEXT_DIR / f"{video_id}_{SUMMARY_POSTFIX}")

    with open(video_summary_file, 'w', encoding='utf-8') as f:
        json.dump(video_summary.summary_dict, f, ensure_ascii=False, indent=2)
    
    full_transcription = " ".join([note.audio_text for note in notes])
    
    
    transcription.transcription = full_transcription
    transcription.transcription_ready = True
    transcription.completed_at = datetime.now(UTC)
    session.add(transcription)
    session.commit()


@app.get("/")
def root():
    return {"message": "Hello World"}

@app.post("/process/", response_model=VideoTranscriptionPublic)
def process_video(video: UploadFile, session: SessionDep, background_tasks: BackgroundTasks,current_user: User = Depends(get_current_active_user)):
    video_transcription = VideoTranscription(
        transcription = "",
        transcription_ready = False,
        user_id=current_user.id
    )
    session.add(video_transcription)
    session.commit()
    session.refresh(video_transcription)
    video_path = VIDEO_DIR / f"{video_transcription.id}_{video.filename}"
    with open(video_path, 'wb') as f:
        shutil.copyfileobj(video.file, f)

    background_tasks.add_task(write_subtitles, video_path, video_transcription.id, session)
    return video_transcription


@app.get("/transcription/{transcription_id}", response_model=VideoTranscriptionPublic)
def download_transcription(
    transcription_id: int,
    session: SessionDep, current_user: User = Depends(get_current_active_user)):
    
    transcription = session.get(VideoTranscription, transcription_id)
    if not transcription:
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    return transcription



@app.get("/summary/{transcription_id}")
def download_summary(transcription_id: int, current_user: User = Depends(get_current_active_user)):
    video_summary_file = str(TEXT_DIR / f"{transcription_id}_{SUMMARY_POSTFIX}")
    if not(Path(video_summary_file).exists()):
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    
    with open(video_summary_file, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/users/stats")
def read_stats(session: SessionDep, current_user: User = Depends(get_current_active_user)):
    return get_user_stats(session, current_user.id)
  
# Создание отзыва
@app.post("/reviews/", response_model=ReviewResponse)
async def create_review(
    review: ReviewCreate,
    session: SessionDep):
    try:
        review_data = review.dict()
        created_review = ReviewCRUD.create_review(session, review_data)
        return ReviewResponse(
            username=created_review.username,
            transcription_id=created_review.transcription_id,
            rating=created_review.rating,
            comment=created_review.comment,
            created_dt_tm=created_review.created_dt_tm
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, 
            detail=str(e)
        )


# Запрос отзывов без transcription_id (отзывы на сервис)
@app.get("/reviews", response_model=List[ReviewResponse])
async def get_service_reviews(
    session: SessionDep,
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|best|worst)$")):
    try:
        reviews = ReviewCRUD.get_service_reviews(
            session=session,
            limit=limit,
            sort_by=sort_by
        )
        return reviews
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# Запрос отзывов на transcription
@app.get("/reviews/{transcription_id}", response_model=List[ReviewResponse])
async def get_transcription_reviews(
    transcription_id: int,
    session: SessionDep,
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("newest", pattern="^(newest|oldest|best|worst)$")
):
    try:
        reviews = ReviewCRUD.get_transcription_reviews(
            session=session,
            transcription_id=transcription_id,
            limit=limit,
            sort_by=sort_by
        )
        return reviews
    except ValueError as e:
        if "transcription_id not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
