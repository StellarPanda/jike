from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import psycopg


METADATA_QUERY = """
WITH primary_keys AS (
    SELECT
        kc.table_schema,
        kc.table_name,
        kc.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kc
      ON tc.constraint_name = kc.constraint_name
     AND tc.table_schema = kc.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
)
SELECT
    c.table_schema,
    c.table_name,
    c.table_type,
    col.column_name,
    col.data_type,
    col.is_nullable,
    col.ordinal_position,
    CASE WHEN pk.column_name IS NOT NULL THEN TRUE ELSE FALSE END AS is_primary_key
FROM information_schema.tables c
JOIN information_schema.columns col
  ON c.table_schema = col.table_schema
 AND c.table_name = col.table_name
LEFT JOIN primary_keys pk
  ON pk.table_schema = col.table_schema
 AND pk.table_name = col.table_name
 AND pk.column_name = col.column_name
WHERE c.table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY c.table_schema, c.table_name, col.ordinal_position
"""


def verify_connection(connection_url: str) -> dict[str, str]:
    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database_name, current_user = cursor.fetchone()

    return {
        "database_name": str(database_name),
        "current_user": str(current_user),
    }


def fetch_metadata(connection_url: str) -> list[dict[str, Any]]:
    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(METADATA_QUERY)
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    return [dict(zip(columns, row, strict=False)) for row in rows]


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    return str(value)


def execute_query(connection_url: str, query_text: str) -> tuple[list[str], list[dict[str, Any]]]:
    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query_text)
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    return (
        columns,
        [
            {
                column: _serialize_value(value)
                for column, value in zip(columns, row, strict=False)
            }
            for row in rows
        ],
    )
