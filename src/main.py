from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from src.api import Tags, all_router, tags_metadata
from src.core import get_settings
from src.db import create_db_and_tables
from src.subtitles.subtitles import ImageCaption, Subtitles, TextSummarizer

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Subtitles()  # Точно ли это надо?
    ImageCaption()  # Точно ли это надо?
    TextSummarizer()  # Точно ли это надо?
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.include_router(all_router)


@app.get(
    "/",
    tags=[Tags.META],
    status_code=status.HTTP_200_OK,
    summary="Информация о сервисе",
    description="Возвращает базовую информацию о сервисе: статус и доступность API.",
)
def root():
    return {"message": "Hello World"}


@app.get(
    "/health",
    tags=[Tags.META],
    status_code=status.HTTP_200_OK,
    summary="Проверка состояния сервиса",
    description="Проверяет, что сервис работает и отвечает на запросы. Используется системами мониторинга.",
)
async def health():
    return {"status": "ok"}
