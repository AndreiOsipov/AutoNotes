import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field, Relationship, SQLModel

from .users import Users


# Таблица JWT
class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    user_id: int = Field(
        foreign_key="users.id",
        index=True,
    )
    token_hash: str = Field(sa_column=Column(String(128), unique=True, nullable=False))
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
    )
    expires_at: datetime = Field(
        index=True,
    )
    revoked: bool = Field(default=False)

    user: "Users" = Relationship(back_populates="refresh_tokens")
