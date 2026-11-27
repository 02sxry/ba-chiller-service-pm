from sqlalchemy import select
from sqlalchemy.dialects import mssql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.core.db import lock_query
from app.domain.models import Base, NotificationJob


def test_metadata_compiles_for_sql_server() -> None:
    for table in Base.metadata.sorted_tables:
        CreateTable(table).compile(dialect=mssql.dialect())


def test_sql_server_worker_lock_hint_compiles() -> None:
    from sqlalchemy import create_mock_engine

    with Session(create_mock_engine("mssql+pyodbc://", lambda *args: None)) as session:
        query = lock_query(select(NotificationJob), NotificationJob, session, skip_locked=True)
    compiled = str(query.compile(dialect=mssql.dialect()))
    assert "WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK)" in compiled
