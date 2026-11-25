import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL",
    "mssql+pyodbc://admin:admin@localhost:1433/BA_PMnotification?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes",
)


@pytest.fixture
def db() -> Session:
    engine = create_engine(os.environ["DATABASE_URL"])
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()

