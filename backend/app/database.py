from collections.abc import Generator

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)


def get_db() -> Generator[Session, None, None]:
    db = sessionmaker(
        get_engine(),
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )()
    try:
        yield db
    finally:
        db.close()
