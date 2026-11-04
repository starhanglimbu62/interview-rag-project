import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    pass


def _get_postgres_password() -> str:
    password = os.getenv("POSTGRES_PASSWORD")
    environment = os.getenv("APP_ENV", "development").strip().lower()

    if password and password.strip():
        return password

    if environment in {"production", "prod", "staging"}:
        raise ValueError(
            "POSTGRES_PASSWORD is required outside development"
        )

    return "dev_password_change_me"


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    database_url = DATABASE_URL
else:
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "raguser"),
        password=_get_postgres_password(),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "interview_rag"),
    )


engine = create_engine(
    database_url,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for one API request."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
