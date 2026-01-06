from contextlib import asynccontextmanager
import shutil

from fastapi import FastAPI, UploadFile, HTTPException, Query
from db import SessionDep, VideoTranscriptionPublic, VideoTranscription, ReviewCreate, ReviewResponse, create_db_and_tables
from utils import VIDEO_DIR

from reviews.reviews import ReviewCRUD
from typing import List

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/process/", response_model=VideoTranscriptionPublic)
def process_video(video: UploadFile, session: SessionDep):
    
    video_transcription = VideoTranscription(
        transcription = "",
        transcription_ready = False,
    )
    session.add(video_transcription)
    session.commit()
    session.refresh(video_transcription)
    video_path = str(VIDEO_DIR / str(video_transcription.id)) + "_" + str(video.filename)
    with open(video_path, 'wb') as f:
        shutil.copyfileobj(video.file, f)
    return video_transcription


@app.get("/results/{transcription_id}", response_model=VideoTranscriptionPublic)
def download_reult(
    transcription_id: int,
    session: SessionDep):
    
    transcription = session.get(VideoTranscription, transcription_id)
    if not transcription:
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    return transcription


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






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )