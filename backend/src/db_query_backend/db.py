from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .config import settings


SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS database_connections (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        database_type TEXT NOT NULL,
        connection_url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS table_metadata (
        id TEXT PRIMARY KEY,
        database_id TEXT NOT NULL,
        schema_name TEXT NOT NULL,
        table_name TEXT NOT NULL,
        table_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS column_metadata (
        id TEXT PRIMARY KEY,
        table_id TEXT NOT NULL,
        column_name TEXT NOT NULL,
        data_type TEXT NOT NULL,
        is_nullable INTEGER NOT NULL,
        is_primary_key INTEGER NOT NULL,
        ordinal_position INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS query_history (
        id TEXT PRIMARY KEY,
        database_id TEXT NOT NULL,
        query_text TEXT NOT NULL,
        query_source TEXT NOT NULL,
        execution_status TEXT NOT NULL,
        error_message TEXT,
        created_at TEXT NOT NULL
    )
    """,
)


def ensure_data_dir() -> None:
    Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    connection = sqlite3.connect(settings.sqlite_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with closing(get_connection()) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def check_database() -> bool:
    with closing(get_connection()) as connection:
        connection.execute("SELECT 1")
    return True
