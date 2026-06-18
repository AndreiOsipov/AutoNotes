from fastapi import APIRouter

from .constants import API_V1_PREFIX
from .routers import auth_router, rest_router

all_router = APIRouter()


all_router.include_router(auth_router, prefix=API_V1_PREFIX)
all_router.include_router(rest_router, prefix=API_V1_PREFIX)
