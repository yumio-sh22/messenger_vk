from collections.abc import Generator
import time

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def wait_for_database(retries: int = 30, delay_seconds: float = 2.0) -> None:
    last_error: OperationalError | None = None
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as error:
            last_error = error
            if attempt == retries:
                break
            time.sleep(delay_seconds)
    raise RuntimeError(f"Database is not available after {retries} attempts") from last_error


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
