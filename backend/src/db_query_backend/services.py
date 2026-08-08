from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from .postgres import execute_query, fetch_metadata, verify_connection
from .query_engine import validate_readonly_query
from .repositories import execute, executemany, fetch_all, fetch_one
from .schemas import (
    ColumnMetadataItem,
    CreateDatabaseRequest,
    DatabaseConnectionDetail,
    DatabaseConnectionListItem,
    MetadataResponse,
    QueryExecutionRequest,
    QueryExecutionResponse,
    QueryHistoryItem,
    QueryResultColumn,
    QueryValidationResponse,
    RefreshMetadataResponse,
    TableMetadataItem,
    ValidateQueryRequest,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def list_databases() -> list[DatabaseConnectionListItem]:
    rows = fetch_all(
        """
        SELECT id, name, database_type, created_at, updated_at
        FROM database_connections
        ORDER BY created_at DESC
        """
    )
    return [DatabaseConnectionListItem.model_validate(row) for row in rows]


def get_database(database_id: str) -> DatabaseConnectionDetail:
    row = fetch_one(
        """
        SELECT id, name, database_type, connection_url, created_at, updated_at
        FROM database_connections
        WHERE id = ?
        """,
        (database_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Database connection not found")

    return DatabaseConnectionDetail.model_validate(row)


def create_database(payload: CreateDatabaseRequest) -> DatabaseConnectionDetail:
    try:
        verify_connection(payload.connection_url)
    except Exception as exc:  # pragma: no cover - depends on external DB
        raise HTTPException(status_code=400, detail=f"Failed to connect to PostgreSQL: {exc}") from exc

    now = _now()
    database_id = str(uuid4())

    execute(
        """
        INSERT INTO database_connections (
            id, name, database_type, connection_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            database_id,
            payload.name,
            payload.database_type,
            payload.connection_url,
            now,
            now,
        ),
    )

    refresh_metadata(database_id)
    return get_database(database_id)


def delete_database(database_id: str) -> None:
    detail = get_database(database_id)

    table_rows = fetch_all(
        "SELECT id FROM table_metadata WHERE database_id = ?",
        (detail.id,),
    )
    table_ids = [row["id"] for row in table_rows]

    if table_ids:
        placeholders = ",".join("?" for _ in table_ids)
        execute(
            f"DELETE FROM column_metadata WHERE table_id IN ({placeholders})",
            tuple(table_ids),
        )

    execute("DELETE FROM table_metadata WHERE database_id = ?", (detail.id,))
    execute("DELETE FROM query_history WHERE database_id = ?", (detail.id,))
    execute("DELETE FROM database_connections WHERE id = ?", (detail.id,))


def refresh_metadata(database_id: str) -> RefreshMetadataResponse:
    detail = get_database(database_id)

    try:
        metadata_rows = fetch_metadata(detail.connection_url)
    except Exception as exc:  # pragma: no cover - depends on external DB
        raise HTTPException(status_code=400, detail=f"Failed to load metadata: {exc}") from exc

    existing_tables = fetch_all(
        "SELECT id FROM table_metadata WHERE database_id = ?",
        (database_id,),
    )
    table_ids = [row["id"] for row in existing_tables]
    if table_ids:
        placeholders = ",".join("?" for _ in table_ids)
        execute(
            f"DELETE FROM column_metadata WHERE table_id IN ({placeholders})",
            tuple(table_ids),
        )

    execute("DELETE FROM table_metadata WHERE database_id = ?", (database_id,))

    grouped_tables: dict[tuple[str, str, str], str] = {}
    table_inserts: list[tuple[str, str, str, str, str, str, str]] = []
    column_inserts: list[tuple[str, str, str, str, int, int, int]] = []
    now = _now()

    for row in metadata_rows:
        table_key = (
            str(row["table_schema"]),
            str(row["table_name"]),
            str(row["table_type"]),
        )
        table_id = grouped_tables.get(table_key)
        if table_id is None:
            table_id = str(uuid4())
            grouped_tables[table_key] = table_id
            table_inserts.append(
                (
                    table_id,
                    database_id,
                    table_key[0],
                    table_key[1],
                    table_key[2],
                    now,
                    now,
                )
            )

        column_inserts.append(
            (
                str(uuid4()),
                table_id,
                str(row["column_name"]),
                str(row["data_type"]),
                1 if str(row["is_nullable"]).upper() == "YES" else 0,
                1 if bool(row["is_primary_key"]) else 0,
                int(row["ordinal_position"]),
            )
        )

    if table_inserts:
        executemany(
            """
            INSERT INTO table_metadata (
                id, database_id, schema_name, table_name, table_type, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            table_inserts,
        )

    if column_inserts:
        executemany(
            """
            INSERT INTO column_metadata (
                id, table_id, column_name, data_type, is_nullable, is_primary_key, ordinal_position
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            column_inserts,
        )

    execute(
        "UPDATE database_connections SET updated_at = ? WHERE id = ?",
        (now, database_id),
    )

    return RefreshMetadataResponse(
        database_id=database_id,
        table_count=len(table_inserts),
        column_count=len(column_inserts),
    )


def get_metadata(database_id: str) -> MetadataResponse:
    get_database(database_id)

    tables = [
        TableMetadataItem.model_validate(row)
        for row in fetch_all(
            """
            SELECT id, database_id, schema_name, table_name, table_type
            FROM table_metadata
            WHERE database_id = ?
            ORDER BY schema_name, table_name
            """,
            (database_id,),
        )
    ]

    columns = [
        ColumnMetadataItem.model_validate(row)
        for row in fetch_all(
            """
            SELECT id, table_id, column_name, data_type, is_nullable, is_primary_key, ordinal_position
            FROM column_metadata
            WHERE table_id IN (
                SELECT id FROM table_metadata WHERE database_id = ?
            )
            ORDER BY table_id, ordinal_position
            """,
            (database_id,),
        )
    ]

    return MetadataResponse(tables=tables, columns=columns)


def validate_query(payload: ValidateQueryRequest) -> QueryValidationResponse:
    get_database(payload.database_id)
    result = validate_readonly_query(payload.query_text)

    return QueryValidationResponse(
        database_id=payload.database_id,
        statement_type=result.statement_type,
        normalized_query=result.normalized_query,
        applied_limit=result.applied_limit,
        limit_value=result.limit_value,
    )


def execute_sql(payload: QueryExecutionRequest) -> QueryExecutionResponse:
    database = get_database(payload.database_id)
    validated = validate_readonly_query(payload.query_text)
    now = _now()
    history_id = str(uuid4())

    try:
        column_names, rows = execute_query(database.connection_url, validated.normalized_query)
    except Exception as exc:  # pragma: no cover - depends on external DB
        execute(
            """
            INSERT INTO query_history (
                id, database_id, query_text, query_source, execution_status, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                history_id,
                payload.database_id,
                validated.normalized_query,
                payload.query_source,
                "error",
                str(exc),
                now,
            ),
        )
        raise HTTPException(status_code=400, detail=f"Query execution failed: {exc}") from exc

    execute(
        """
        INSERT INTO query_history (
            id, database_id, query_text, query_source, execution_status, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            history_id,
            payload.database_id,
            validated.normalized_query,
            payload.query_source,
            "success",
            None,
            now,
        ),
    )

    return QueryExecutionResponse(
        database_id=payload.database_id,
        executed_query=validated.normalized_query,
        row_count=len(rows),
        columns=[QueryResultColumn(key=name, title=name) for name in column_names],
        rows=rows,
    )


def get_query_history(database_id: str) -> list[QueryHistoryItem]:
    get_database(database_id)
    rows = fetch_all(
        """
        SELECT id, database_id, query_text, query_source, execution_status, error_message, created_at
        FROM query_history
        WHERE database_id = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (database_id,),
    )
    return [QueryHistoryItem.model_validate(row) for row in rows]
