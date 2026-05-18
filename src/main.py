from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from db import create_db_and_tables
from src.api import Tags, all_router
from subtitles.subtitles import ImageCaption, Subtitles, TextSummarizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Subtitles()  # Точно ли это надо?
    ImageCaption()  # Точно ли это надо?
    TextSummarizer()  # Точно ли это надо?
    yield


app = FastAPI(lifespan=lifespan)

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
