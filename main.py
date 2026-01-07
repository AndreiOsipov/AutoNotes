from contextlib import asynccontextmanager
import shutil
from users.users_router import router
from fastapi import FastAPI, UploadFile, HTTPException, BackgroundTasks
from db import SessionDep, VideoTranscriptionPublic, VideoTranscription, Session, create_db_and_tables
from utils.utils import VIDEO_DIR
from Subtitles.subtitles import Subtitles, ImageCaption, extract_frames



@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Subtitles()
    # ImageCaption()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(router)

def write_subtitles(video_path: str, video_id, session: Session):
    subtitles = Subtitles()
    image_caption = ImageCaption()
    audio_path = subtitles.extract_audio(video_path)
    frames_paths, timestamps = extract_frames(video_path, video_id)
    describtions = [image_caption.caption_image(path) for path in frames_paths]

    video_subtitles = subtitles.transcribe_audio(audio_path)
    transcription = session.get(VideoTranscription, video_id)
    transcription.transcription = video_subtitles
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