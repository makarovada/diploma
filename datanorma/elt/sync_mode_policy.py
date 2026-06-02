"""Сопоставление режимов источника/приёмника (как в Airbyte) с WriteMode приёмника."""

from __future__ import annotations

import json
from typing import Any

from datanorma.core.ingest_protocol import DestinationSyncMode
from datanorma.destinations.base import WriteMode

# Режимы, доступные в UI/API (парные, как в Airbyte)
ALLOWED_DESTINATION_SYNC_MODES: frozenset[str] = frozenset(m.value for m in DestinationSyncMode)

DEFAULT_DESTINATION_SYNC_MODE = DestinationSyncMode.refresh_overwrite.value


def parse_primary_key_field(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    if "," in s:
        return [p.strip() for p in s.split(",") if p.strip()]
    return [s]


def parse_cursor_field(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    if "," in s:
        return [p.strip() for p in s.split(",") if p.strip()]
    return [s]


def cursor_to_storage(cursor: list[str] | str | None) -> str | None:
    cols = parse_cursor_field(cursor)
    if not cols:
        return None
    return cols[0] if len(cols) == 1 else json.dumps(cols, ensure_ascii=False)


def primary_key_to_storage(pk: list[str] | str | None) -> str | None:
    cols = parse_primary_key_field(pk)
    if not cols:
        return None
    return ",".join(cols) if len(cols) == 1 else json.dumps(cols, ensure_ascii=False)


def destination_sync_mode_for_legacy(sync_mode: str) -> str:
    """Миграция/старые записи: только sync_mode без destination_sync_mode."""
    sm = (sync_mode or "").strip().lower()
    if sm == "incremental":
        return DestinationSyncMode.append.value
    return DestinationSyncMode.refresh_overwrite.value


def effective_source_sync_mode(*, sync_mode: str, destination_sync_mode: str | None) -> str:
    dsm = (destination_sync_mode or "").strip() or destination_sync_mode_for_legacy(sync_mode)
    if dsm in (
        DestinationSyncMode.refresh_overwrite.value,
        DestinationSyncMode.refresh_append.value,
        DestinationSyncMode.overwrite.value,
    ):
        return "full_refresh"
    if dsm in (DestinationSyncMode.append.value, DestinationSyncMode.append_dedup.value):
        sm = (sync_mode or "").strip().lower()
        return "incremental" if sm == "incremental" else "incremental"
    return (sync_mode or "full_refresh").strip() or "full_refresh"


def resolve_write_mode(*, sync_mode: str, destination_sync_mode: str | None) -> WriteMode:
    dsm = (destination_sync_mode or "").strip() or destination_sync_mode_for_legacy(sync_mode)
    if dsm == DestinationSyncMode.refresh_overwrite.value:
        return WriteMode.full_refresh
    if dsm == DestinationSyncMode.refresh_append.value:
        return WriteMode.append
    if dsm == DestinationSyncMode.append.value:
        return WriteMode.append
    if dsm == DestinationSyncMode.append_dedup.value:
        return WriteMode.upsert
    if dsm == DestinationSyncMode.overwrite.value:
        return WriteMode.replace_table
    if (sync_mode or "").strip() == "incremental":
        return WriteMode.append
    return WriteMode.full_refresh


def validate_stream_sync_config(
    *,
    sync_mode: str,
    destination_sync_mode: str | None,
    cursor_field: str | list[str] | None,
    primary_key: str | list[str] | None,
) -> list[str]:
    errors: list[str] = []
    dsm = (destination_sync_mode or "").strip() or destination_sync_mode_for_legacy(sync_mode)
    if dsm not in ALLOWED_DESTINATION_SYNC_MODES:
        errors.append(f"Неизвестный destination_sync_mode: {dsm}")
        return errors

    eff_sm = effective_source_sync_mode(sync_mode=sync_mode, destination_sync_mode=dsm)
    if eff_sm == "incremental" and not parse_cursor_field(cursor_field):
        errors.append("Для инкрементального режима укажите поле курсора (cursor_field).")

    if dsm == DestinationSyncMode.append_dedup.value:
        pk = parse_primary_key_field(primary_key)
        if not pk:
            errors.append("Для дедупликации (append_dedup) укажите первичный ключ потока.")

    return errors
