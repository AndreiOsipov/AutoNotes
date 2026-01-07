from contextlib import asynccontextmanager
import shutil
import json
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from db import SessionDep, VideoTranscriptionPublic, VideoTranscription, Session, create_db_and_tables
from utils.utils import VIDEO_DIR, AUDIO_DIR
from Subtitles.subtitles import Subtitles, ImageCaption, extract_frames
from NotesSynchronizer.notes_synchronizer import NotesSynchronizer

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Subtitles()
    ImageCaption()
    yield


app = FastAPI(lifespan=lifespan)


def write_subtitles(video_path: str, video_id, session: Session):
    audio_path = AUDIO_DIR / f"{video_id}.wav"
    subtitles = Subtitles()
    image_caption = ImageCaption()
    audio_path = subtitles.extract_audio(video_path, audio_path)
    synchronizer = NotesSynchronizer(subtitles, image_caption)
    notes = synchronizer.process_video(video_path, video_id)
    summaries = synchronizer.generate_summary(notes)
    output_dir = Path("output") / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    synchronizer.save_notes(notes, output_dir / "notes.json")
    
    with open(output_dir / "summary.json", 'w', encoding='utf-8') as f:json.dump(summaries, f, ensure_ascii=False, indent=2)
    
    
    full_transcription = " ".join([note.audio_text for note in notes])
    
    transcription = session.get(VideoTranscription, video_id)
    transcription.transcription = full_transcription
    transcription.transcription_ready = True
    
    session.add(transcription)
    session.commit()
    
    print(f"Заметки сохранены в {output_dir}")

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
    video_path = str(VIDEO_DIR / str(video_transcription.id)) + "_" + str(video.filename)
    with open(video_path, 'wb') as f:
        shutil.copyfileobj(video.file, f)

    background_tasks.add_task(write_subtitles, video_path, video_transcription.id, session)
    return video_transcription


@app.get("/results/{transcription_id}", response_model=VideoTranscriptionPublic)
def download_reult(
    transcription_id: int,
    session: SessionDep):
    
    transcription = session.get(VideoTranscription, transcription_id)
    if not transcription:
        raise HTTPException(status_code=404, detail=f"transcription with id {transcription_id} not found")
    return transcription