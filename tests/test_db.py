from sqlmodel import create_engine, Session


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)


def get_test_session():
    with Session(engine_test) as session:
        yield session
