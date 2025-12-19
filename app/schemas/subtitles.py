from pydantic import BaseModel

class SubtitlesResponse(BaseModel):
    id: int
    text: str
    format: str

    class Config:
        from_attributes = True

