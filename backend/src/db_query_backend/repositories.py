from __future__ import annotations

from contextlib import closing
from typing import Any

from .db import get_connection


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with closing(get_connection()) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with closing(get_connection()) as connection:
        row = connection.execute(query, params).fetchone()
    return dict(row) if row is not None else None


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with closing(get_connection()) as connection:
        connection.execute(query, params)
        connection.commit()


def executemany(query: str, params: list[tuple[Any, ...]]) -> None:
    with closing(get_connection()) as connection:
        connection.executemany(query, params)
        connection.commit()
