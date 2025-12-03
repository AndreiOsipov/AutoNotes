from typing import Annotated

from fastapi import FastAPI, Path
from pydantic import BaseModel

from utils import create_random_order_id

class UploadedVideo(BaseModel):
    ext: str
    data: int # test data for POC


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/process/")
def process_video(uploaded_video: UploadedVideo):
    order_id = create_random_order_id()
    return order_id


@app.get("/results/{order_id}")
async def download_reult(
    order_id: Annotated[
        int, 
        Path(ge=1, le=1e6, title="order id", description="The ID you received when you sent the video")
        ]
    ):
    return {"message": f"result for {order_id} order"}