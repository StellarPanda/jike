from __future__ import annotations

import platform
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import settings
from .db import check_database, initialize_database
from .schemas import (
    CreateDatabaseRequest,
    DatabaseConnectionDetail,
    DatabaseConnectionListItem,
    ExportQueryRequest,
    GenerateQueryRequest,
    GenerateQueryResponse,
    HealthResponse,
    MetadataResponse,
    QueryExecutionRequest,
    QueryExecutionResponse,
    QueryHistoryItem,
    QueryValidationResponse,
    RefreshMetadataResponse,
    ValidateQueryRequest,
)
from .services import (
    create_database,
    delete_database,
    execute_sql,
    export_sql,
    generate_sql,
    get_database,
    get_metadata,
    get_query_history,
    list_databases,
    refresh_metadata,
    validate_query,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        sqlite_path=str(settings.sqlite_path),
        database_ready=check_database(),
        python_version=platform.python_version(),
    )


@app.get(
    f"{settings.api_prefix}/databases",
    response_model=list[DatabaseConnectionListItem],
)
def get_databases() -> list[DatabaseConnectionListItem]:
    return list_databases()


@app.post(
    f"{settings.api_prefix}/databases",
    response_model=DatabaseConnectionDetail,
    status_code=201,
)
def create_database_connection(
    payload: CreateDatabaseRequest,
) -> DatabaseConnectionDetail:
    return create_database(payload)


@app.get(
    f"{settings.api_prefix}/databases/{{database_id}}",
    response_model=DatabaseConnectionDetail,
)
def get_database_connection(database_id: str) -> DatabaseConnectionDetail:
    return get_database(database_id)


@app.delete(f"{settings.api_prefix}/databases/{{database_id}}", status_code=204)
def delete_database_connection(database_id: str) -> None:
    delete_database(database_id)


@app.post(
    f"{settings.api_prefix}/databases/{{database_id}}/refresh-metadata",
    response_model=RefreshMetadataResponse,
)
def refresh_database_metadata(database_id: str) -> RefreshMetadataResponse:
    return refresh_metadata(database_id)


@app.get(
    f"{settings.api_prefix}/databases/{{database_id}}/metadata",
    response_model=MetadataResponse,
)
def get_database_metadata(database_id: str) -> MetadataResponse:
    return get_metadata(database_id)


@app.post(
    f"{settings.api_prefix}/query/validate",
    response_model=QueryValidationResponse,
)
def validate_database_query(payload: ValidateQueryRequest) -> QueryValidationResponse:
    return validate_query(payload)


@app.post(
    f"{settings.api_prefix}/query/execute",
    response_model=QueryExecutionResponse,
)
def execute_database_query(payload: QueryExecutionRequest) -> QueryExecutionResponse:
    return execute_sql(payload)


@app.post(f"{settings.api_prefix}/query/export")
def export_database_query(payload: ExportQueryRequest) -> Response:
    from .exporter import build_export_file

    result = export_sql(payload)
    content, media_type, filename = build_export_file(result, payload.export_format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post(
    f"{settings.api_prefix}/query/generate",
    response_model=GenerateQueryResponse,
)
def generate_database_query(payload: GenerateQueryRequest) -> GenerateQueryResponse:
    return generate_sql(payload)


@app.get(
    f"{settings.api_prefix}/databases/{{database_id}}/query-history",
    response_model=list[QueryHistoryItem],
)
def get_database_query_history(database_id: str) -> list[QueryHistoryItem]:
    return get_query_history(database_id)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "db_query_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
