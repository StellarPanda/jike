from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class HealthResponse(CamelModel):
    status: str
    app_name: str
    app_version: str
    sqlite_path: str
    database_ready: bool
    python_version: str


class CreateDatabaseRequest(CamelModel):
    name: str
    connection_url: str
    database_type: str = "postgres"


class DatabaseConnectionListItem(CamelModel):
    id: str
    name: str
    database_type: str
    created_at: str
    updated_at: str


class DatabaseConnectionDetail(DatabaseConnectionListItem):
    connection_url: str


class TableMetadataItem(CamelModel):
    id: str
    database_id: str
    schema_name: str
    table_name: str
    table_type: str


class ColumnMetadataItem(CamelModel):
    id: str
    table_id: str
    column_name: str
    data_type: str
    is_nullable: int
    is_primary_key: int
    ordinal_position: int


class MetadataResponse(CamelModel):
    tables: list[TableMetadataItem]
    columns: list[ColumnMetadataItem]


class RefreshMetadataResponse(CamelModel):
    database_id: str
    table_count: int
    column_count: int


class ValidateQueryRequest(CamelModel):
    database_id: str
    query_text: str


class QueryExecutionRequest(ValidateQueryRequest):
    query_source: str = "manual"


class QueryValidationResponse(CamelModel):
    database_id: str
    statement_type: str
    normalized_query: str
    applied_limit: bool
    limit_value: int
    is_valid: bool = True


class QueryResultColumn(CamelModel):
    key: str
    title: str


class QueryExecutionResponse(CamelModel):
    database_id: str
    executed_query: str
    row_count: int
    columns: list[QueryResultColumn]
    rows: list[dict[str, object | None]]


class QueryHistoryItem(CamelModel):
    id: str
    database_id: str
    query_text: str
    query_source: str
    execution_status: str
    error_message: str | None = None
    created_at: str
