from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = make_url(settings.database_url)
engine_options: dict[str, object] = {"pool_pre_ping": True}
if database_url.drivername == "mssql+pyodbc":
    # pyodbc's bulk insert path is considerably faster for SQL Server.
    engine_options["fast_executemany"] = True
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def lock_query(query: Any, model: Any, db: Session, *, skip_locked: bool = False) -> Any:
    """Apply a row lock using the syntax supported by the active database."""
    if db.get_bind().dialect.name == "mssql":
        lock_hint = "WITH (UPDLOCK, ROWLOCK)"
        if skip_locked:
            lock_hint = "WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK, ROWLOCK)"
        return query.with_hint(model, lock_hint, dialect_name="mssql")
    return query.with_for_update(skip_locked=skip_locked)


def bool_filter(column: Any, value: bool) -> Any:
    """Build a boolean comparison that works with SQL Server BIT columns."""
    return column == (1 if value else 0)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session

