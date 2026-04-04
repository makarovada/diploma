"""Безопасное имя таблицы витрины из окружения."""

from __future__ import annotations

import os
import re

_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def warehouse_table_sql() -> str:
    t = (os.environ.get("DATANORMA_WAREHOUSE_TABLE") or "canonical_sales").strip() or "canonical_sales"
    if not _SAFE_IDENT.match(t):
        return "canonical_sales"
    return t
