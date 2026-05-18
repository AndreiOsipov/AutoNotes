from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from src.core import get_settings

settings = get_settings()

sqlite_url = f"sqlite+aiosqlite:///{settings.DB}"


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


engine = create_async_engine(
    sqlite_url,
    echo=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=SQLModelAsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal(engine) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
