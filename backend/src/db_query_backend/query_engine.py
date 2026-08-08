from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlglot import exp, parse
from sqlglot.errors import ParseError


DEFAULT_LIMIT = 1000
MAX_LIMIT = 5000


@dataclass(frozen=True)
class ValidatedQuery:
    statement_type: str
    normalized_query: str
    applied_limit: bool
    limit_value: int


def validate_readonly_query(query_text: str) -> ValidatedQuery:
    stripped_query = query_text.strip()
    if not stripped_query:
        raise HTTPException(status_code=400, detail="Query text is required")

    try:
        expressions = parse(stripped_query, read="postgres")
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid SQL syntax: {exc}") from exc

    if len(expressions) != 1:
        raise HTTPException(status_code=400, detail="Only a single SQL statement is allowed")

    expression = expressions[0]
    if not isinstance(expression, exp.Query):
        raise HTTPException(status_code=400, detail="Only read-only SELECT queries are allowed")

    limit_expression = expression.args.get("limit")
    applied_limit = False
    limit_value = DEFAULT_LIMIT

    if limit_expression is None:
        expression.set(
            "limit",
            exp.Limit(expression=exp.Literal.number(DEFAULT_LIMIT)),
        )
        applied_limit = True
    else:
        limit_literal = limit_expression.expression
        if not isinstance(limit_literal, exp.Literal) or not limit_literal.is_int:
            raise HTTPException(status_code=400, detail="LIMIT must be a concrete integer")

        limit_value = int(limit_literal.this)
        if limit_value > MAX_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"LIMIT cannot exceed {MAX_LIMIT}",
            )

    normalized_query = expression.sql(dialect="postgres", pretty=True)
    return ValidatedQuery(
        statement_type=expression.key.upper(),
        normalized_query=normalized_query,
        applied_limit=applied_limit,
        limit_value=limit_value,
    )
