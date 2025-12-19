import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.api.v1.routers import subtitles

app = FastAPI(title="Subtitles API", version="1.0.0")

app.include_router(subtitles.router, prefix="/api/v1/subtitles", tags=["subtitles"])

class Item(BaseModel):
    text: str

@app.get("/api")
async def root():
    return {"message": "Subtitles API is running!"}


@app.post("/transcribe")
async def transcribe_video(video: UploadFile = File(...)):
    subtitles = f"{video.filename}:Текстовая версия видео"
    return {"subtitles": subtitles}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "app\\static")
# print(STATIC_DIR)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )