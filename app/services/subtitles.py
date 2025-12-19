# app/services/subtitles.py
from sqlalchemy.orm import Session
from app.models.subtitles import Subtitles

async def generate_subtitles_and_save(file: UploadFile, db: Session):
    # читаем данные файла
    contents = await file.read()

    # здесь вызываешь свою логику транскрипции, получаешь текст
    subtitles_text = await your_transcribe_func(contents)

    db_obj = Subtitles(
        file_name=file.filename,
        subtitles_text=subtitles_text,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    return db_obj  # FastAPI сам приведёт к SubtitlesResponse
