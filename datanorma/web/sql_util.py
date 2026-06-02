"""Безопасное имя таблицы витрины из окружения."""

from __future__ import annotations

import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError

from datanorma.config import get_settings

_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def warehouse_table_sql() -> str:
    t = (get_settings().datanorma_warehouse_table or "normalized").strip() or "normalized"
    if not _SAFE_IDENT.match(t):
        return "normalized"
    return t


def typed_table_sql() -> str:
    t = (get_settings().datanorma_typed_table or "normalized").strip() or "normalized"
    if not _SAFE_IDENT.match(t):
        return "normalized"
    return t


def warehouse_row_count(conn: Connection) -> int:
    """Число строк витрины; 0 если таблица ещё не создана (dbt/миграции)."""
    t = warehouse_table_sql()
    try:
        if t not in inspect(conn).get_table_names():
            return 0
        return int(conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one())
    except ProgrammingError as exc:
        if "UndefinedTable" in str(exc) or "does not exist" in str(exc):
            return 0
        raise
