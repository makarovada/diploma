"""Фильтрация записей для incremental sync по cursor_field."""

from __future__ import annotations

from typing import Any


def _get_by_path(obj: Any, path: str) -> Any:
    """Простой путь вида 'a.b.c' или одно имя ключа для dict."""
    if obj is None:
        return None
    cur: Any = obj
    for part in path.split("."):
        part = part.strip()
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def record_cursor_value(record: dict[str, Any], cursor_field: str | None) -> str | None:
    if not cursor_field:
        return None
    v = _get_by_path(record, cursor_field)
    if v is None:
        v = record.get(cursor_field)
    if v is None:
        return None
    return str(v).strip()


def filter_incremental_dict_rows(
    rows: list[dict[str, Any]],
    *,
    cursor_field: str | None,
    last_cursor: str | None,
    sync_mode: str,
) -> list[dict[str, Any]]:
    if sync_mode != "incremental" or not cursor_field or not last_cursor:
        return list(rows)
    out: list[dict[str, Any]] = []
    for r in rows:
        cv = record_cursor_value(r, cursor_field)
        if cv is None:
            out.append(r)
            continue
        if cv > last_cursor:
            out.append(r)
    return out


def filter_incremental_postings(
    postings: list[dict[str, Any]],
    *,
    cursor_field: str | None,
    last_cursor: str | None,
    sync_mode: str,
) -> list[dict[str, Any]]:
    return filter_incremental_dict_rows(
        postings,
        cursor_field=cursor_field,
        last_cursor=last_cursor,
        sync_mode=sync_mode,
    )


def max_cursor_from_dict_rows(rows: list[dict[str, Any]], cursor_field: str | None) -> str | None:
    if not cursor_field or not rows:
        return None
    vals: list[str] = []
    for r in rows:
        cv = record_cursor_value(r, cursor_field)
        if cv is not None:
            vals.append(cv)
    return max(vals) if vals else None


def max_cursor_from_postings(postings: list[dict[str, Any]], cursor_field: str | None) -> str | None:
    return max_cursor_from_dict_rows(postings, cursor_field)
