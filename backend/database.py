"""
Database connection and initialization for AllReceipts.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

from .models import Receipt, Vendor, NtaCache

load_dotenv()


def get_engine():
    """
    Create SQLite engine using DB_PATH from environment.
    Falls back to RECEIPTS_BASE_PATH/receipts.db if not set.
    """
    db_path = os.getenv("DB_PATH")
    if not db_path:
        base_path = os.getenv("RECEIPTS_BASE_PATH", "./AllReceipts")
        db_path = str(Path(base_path) / "receipts.db")

    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return create_engine(f"sqlite:///{db_path}")


def init_db():
    """
    Create all tables if they don't exist.
    Call this on application startup.
    """
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency for FastAPI routes.
    Yields a database session and ensures cleanup.
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session
