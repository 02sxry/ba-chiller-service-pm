from sqlalchemy import select
from sqlalchemy.dialects import mssql
from sqlalchemy.schema import CreateTable

from app.domain.models import Base, NotificationJob


def test_metadata_compiles_for_sql_server() -> None:
    for table in Base.metadata.sorted_tables:
        CreateTable(table).compile(dialect=mssql.dialect())


def test_sql_server_worker_lock_hint_compiles() -> None:
    query = select(NotificationJob).with_hint(
        NotificationJob,
        "WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK, ROWLOCK)",
        dialect_name="mssql",
    )
    compiled = str(query.compile(dialect=mssql.dialect()))
    assert "WITH (UPDLOCK, READPAST, READCOMMITTEDLOCK, ROWLOCK)" in compiled
