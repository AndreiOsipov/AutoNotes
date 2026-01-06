from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine, Field

class Users(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    disabled: bool = False

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

sql_db_file = "database.db"
sqlite_url = f"sqlite:///{sql_db_file}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

SessionDep = Annotated[Session, Depends(get_session)]