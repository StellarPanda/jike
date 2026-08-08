from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib import error, request

from fastapi import HTTPException

from .config import settings


SYSTEM_PROMPT = """You generate safe PostgreSQL read-only queries.
Return exactly one SQL statement and nothing else.
The statement must be a SELECT, WITH, or UNION query that reads data only.
Use only tables and columns from the supplied schema.
Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, or comments.
Do not wrap the SQL in Markdown fences.
"""


@dataclass(frozen=True)
class GeneratedQuery:
    query_text: str
    model: str


def build_schema_context(
    tables: list[dict[str, object]],
    columns: list[dict[str, object]],
) -> str:
    columns_by_table: dict[str, list[dict[str, object]]] = {}
    for column in columns:
        columns_by_table.setdefault(str(column["table_id"]), []).append(column)

    lines: list[str] = []
    for table in tables:
        qualified_name = f'{table["schema_name"]}.{table["table_name"]}'
        lines.append(f"TABLE {qualified_name} ({table['table_type']})")
        for column in columns_by_table.get(str(table["id"]), []):
            flags = []
            if column["is_primary_key"]:
                flags.append("PRIMARY KEY")
            if not column["is_nullable"]:
                flags.append("NOT NULL")
            suffix = f" [{', '.join(flags)}]" if flags else ""
            lines.append(f'  - {column["column_name"]}: {column["data_type"]}{suffix}')

    return "\n".join(lines) or "No user tables are available."


def _extract_query(content: str) -> str:
    text = content.strip()
    fenced_match = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    if text.startswith("{"):
        try:
            payload = json.loads(text)
            text = str(payload.get("sql", "")).strip()
        except json.JSONDecodeError:
            pass

    if not text:
        raise HTTPException(status_code=502, detail="The model returned an empty SQL query")

    return text.rstrip(";").strip()


def generate_query(natural_language: str, schema_context: str) -> GeneratedQuery:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Add it to backend/.env or the shell environment.",
        )

    prompt = (
        "Database schema:\n"
        f"{schema_context}\n\n"
        "User request:\n"
        f"{natural_language.strip()}\n\n"
        "Return one PostgreSQL read-only SQL statement."
    )
    body = json.dumps(
        {
            "model": settings.openai_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    endpoint = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    http_request = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=settings.openai_timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider returned HTTP {exc.code}: {response_body[:500]}",
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach LLM provider: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="LLM provider returned invalid JSON") from exc

    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="LLM provider response did not contain message content") from exc

    return GeneratedQuery(query_text=_extract_query(str(content)), model=settings.openai_model)
