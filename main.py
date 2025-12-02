from fastapi import FastAPI
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
async def download_reult(order_id: int):
    return {"message": f"result for {order_id} order"}