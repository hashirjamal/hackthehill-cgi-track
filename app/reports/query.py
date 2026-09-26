"""Shared pieces for the reporting endpoints: pagination, sorting and filters over SQL.

Column names and sort expressions come from each endpoint's own whitelist, never from the request.
Request values are always bound parameters. The views are Postgres SQL, so these endpoints need Postgres.
"""
import math
from typing import Any, Generic, TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_PAGE_SIZE = 200
T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int  # rows matching the filters, across all pages
    total_pages: int
    sort: list[str]  # the sort actually applied, e.g. ["days_overdue:desc"]


class Pagination:
    """`page` starts at 1. A page past the end returns no items."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number, from 1"),
        page_size: int = Query(25, ge=1, le=MAX_PAGE_SIZE, description=f"Rows per page, up to {MAX_PAGE_SIZE}"),
    ):
        self.page = page
        self.page_size = page_size


class Where:
    """Collects filter conditions. Each method ignores a value of None, so unset filters cost nothing."""

    def __init__(self, prefix: str = "w"):
        """Use a different prefix for each Where in one query, so their parameter names do not clash."""
        self._prefix = prefix
        self._clauses: list[str] = []
        self.params: dict[str, Any] = {}

    def _bind(self, value: Any) -> str:
        name = f"{self._prefix}{len(self.params)}"
        self.params[name] = value
        return f":{name}"

    def raw(self, clause: str):
        """A fixed condition written in code (never from the request), e.g. status = 'Open'."""
        self._clauses.append(clause)

    def any_of(self, column: str, values: list[Any] | None):
        """column matches any of the values (a repeated query parameter)."""
        if values:
            self._clauses.append(f"{column} = ANY({self._bind(list(values))})")

    def compare(self, column: str, op: str, value: Any):
        if value is not None:
            assert op in ("=", ">=", "<=", ">", "<")
            self._clauses.append(f"{column} {op} {self._bind(value)}")

    def flag(self, column: str, value: bool | None):
        """A boolean column that may be NULL: true means IS TRUE, false means anything else."""
        if value is not None:
            self._clauses.append(f"{column} IS {'TRUE' if value else 'NOT TRUE'}")

    def is_set(self, column: str, value: bool | None):
        """true keeps rows where the column has a value, false keeps rows where it is NULL."""
        if value is not None:
            self._clauses.append(f"{column} IS {'NOT NULL' if value else 'NULL'}")

    def prefix(self, columns: list[str], q: str | None):
        """Case-insensitive 'starts with' on any of the columns."""
        if q:
            bound = self._bind(q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
            self._clauses.append("(" + " OR ".join(f"{c} ILIKE {bound}" for c in columns) + ")")

    @property
    def sql(self) -> str:
        return "WHERE " + " AND ".join(self._clauses) if self._clauses else ""


def order_by(sort: str | None, allowed: dict[str, str], default: str, tiebreaker: str) -> tuple[str, list[str]]:
    """Parse `sort=name:dir,name:dir`. `allowed` maps a sort name to a SQL expression.

    The tie-breaker keeps pages stable when the sort values repeat. NULLs always sort last.
    """
    parts, applied = [], []
    for item in (sort or default).split(","):
        name, _, direction = item.strip().partition(":")
        direction = (direction or "asc").lower()
        if name not in allowed or direction not in ("asc", "desc"):
            raise HTTPException(
                status_code=422,
                detail=f"cannot sort by {item.strip()!r}. Use name or name:asc|desc with name one of {sorted(allowed)}",
            )
        parts.append(f"{allowed[name]} {direction.upper()} NULLS LAST")
        applied.append(f"{name}:{direction}")
    return "ORDER BY " + ", ".join(parts + [tiebreaker]), applied


def fetch_page(
    db: Session,
    *,
    columns: str,
    source: str,
    where: Where,
    order: str,
    applied_sort: list[str],
    pagination: Pagination,
    params: dict[str, Any] | None = None,
) -> dict:
    """Run the count and the page query. `source` is a table, view or `(subquery) alias`.

    `params` are extra bound values used inside `source` itself (see the backlog-flow endpoint).
    """
    bound = {**(params or {}), **where.params}
    total = db.execute(text(f"SELECT count(*) FROM {source} {where.sql}"), bound).scalar_one()
    rows = db.execute(
        text(f"SELECT {columns} FROM {source} {where.sql} {order} LIMIT :_limit OFFSET :_offset"),
        {**bound, "_limit": pagination.page_size, "_offset": (pagination.page - 1) * pagination.page_size},
    ).mappings().all()
    return {
        "items": [dict(r) for r in rows],
        "page": pagination.page,
        "page_size": pagination.page_size,
        "total": total,
        "total_pages": math.ceil(total / pagination.page_size),
        "sort": applied_sort,
    }
