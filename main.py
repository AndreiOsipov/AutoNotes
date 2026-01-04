from contextlib import asynccontextmanager
import shutil

from fastapi import FastAPI, UploadFile, HTTPException
from db import SessionDep, VideoTranscriptionPublic, VideoTranscription, create_db_and_tables
from utils import VIDEO_DIR


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