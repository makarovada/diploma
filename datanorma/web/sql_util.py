"""Безопасное имя таблицы витрины из окружения."""

from __future__ import annotations

import re

from datanorma.config import get_settings

_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def warehouse_table_sql() -> str:
    t = (get_settings().datanorma_warehouse_table or "canonical_sales").strip() or "canonical_sales"
    if not _SAFE_IDENT.match(t):
        return "canonical_sales"
    return t


def typed_table_sql() -> str:
    t = (get_settings().datanorma_typed_table or "typed_canonical_sales").strip() or "typed_canonical_sales"
    if not _SAFE_IDENT.match(t):
        return "typed_canonical_sales"
    return t
