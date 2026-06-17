from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from src.core import get_settings

settings = get_settings()

DB_URL = str(settings.ASYNC_DB_URL)


engine = create_async_engine(
    DB_URL,
    echo=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=SQLModelAsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
