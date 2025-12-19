from sqlalchemy.orm import Mapped, mapped_column, declarative_base

Base = declarative_base()

class Subtitles(Base):
    __tablename__ = "subtitles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str]
    format: Mapped[str]
