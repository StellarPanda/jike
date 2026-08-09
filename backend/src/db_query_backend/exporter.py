from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime

from .schemas import QueryExecutionResponse


def _csv_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def build_export_file(result: QueryExecutionResponse, export_format: str) -> tuple[bytes, str, str]:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    safe_format = export_format.lower()

    if safe_format == "csv":
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow([column.title for column in result.columns])
        for row in result.rows:
            writer.writerow([_csv_value(row.get(column.key)) for column in result.columns])
        return (
            buffer.getvalue().encode("utf-8"),
            "text/csv; charset=utf-8",
            f"query-result-{timestamp}.csv",
        )

    if safe_format == "json":
        payload = {
            "executedQuery": result.executed_query,
            "rowCount": result.row_count,
            "columns": [column.model_dump() for column in result.columns],
            "rows": result.rows,
        }
        return (
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            "application/json; charset=utf-8",
            f"query-result-{timestamp}.json",
        )

    raise ValueError("Export format must be csv or json")
