import uuid

from sqlalchemy import Column, String
from sqlmodel import Field, Relationship, SQLModel

from .tokens import RefreshToken


class Users(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
    )
    name: str = Field(
        sa_column=Column(
            String(20),
            nullable=False,
            unique=True,
            index=True,
        )
    )
    email: str | None = Field(
        default=None,
        sa_column=Column(
            String,
            unique=True,
            nullable=True,
            index=True,
        ),
    )
    password_hash: str = Field(sa_column=Column(String(255), nullable=False))
    disabled: bool = False

    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
        },
    )
