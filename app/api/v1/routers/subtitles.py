from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.schemas.subtitles import SubtitlesResponse
from app.services.subtitles import generate_subtitles_and_save

router = APIRouter()

@router.post("/", response_model=SubtitlesResponse)
async def create_subtitles(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Передаём сам UploadFile или байты, а не только имя
    return await generate_subtitles_and_save(file, db)
