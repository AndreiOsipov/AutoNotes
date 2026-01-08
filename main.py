from contextlib import asynccontextmanager
import shutil
import json
from pathlib import Path
from users.users_router import router
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from db import SessionDep, VideoTranscriptionPublic, VideoTranscription, Session, create_db_and_tables
from utils.utils import VIDEO_DIR, TEXT_DIR, SUMMARY_POSTFIX
from subtitles.subtitles import Subtitles, ImageCaption, TextSummarizer
from NotesSynchronizer.notes_synchronizer import NotesSynchronizer


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
    
    transcription = session.get(VideoTranscription, video_id)
    transcription.transcription = full_transcription
    transcription.transcription_ready = True
    
    session.add(transcription)
    session.commit()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/process/", response_model=VideoTranscriptionPublic)
def process_video(video: UploadFile, session: SessionDep, background_tasks: BackgroundTasks):
    video_transcription = VideoTranscription(
        transcription = "",
        transcription_ready = False,
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
    session: SessionDep):
    
    transcription = session.get(VideoTranscription, transcription_id)
    if not transcription:
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    return transcription


@app.get("/summary/{transcription_id}")
def download_summary(transcription_id: int):
    video_summary_file = str(TEXT_DIR / f"{transcription_id}_{SUMMARY_POSTFIX}")
    if not(Path(video_summary_file).exists()):
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    
    with open(video_summary_file, 'r', encoding='utf-8') as f:
        return json.load(f)