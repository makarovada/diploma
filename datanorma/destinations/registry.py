"""Фабрика приёмников по connector_code (как в UI / destination.connector_code)."""

from __future__ import annotations

from typing import Any

from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)
from datanorma.destinations.clickhouse import ClickHouseDestination
from datanorma.destinations.csv_file import CsvFileDestination
from datanorma.destinations.postgres import PostgresDestination
from datanorma.destinations.xlsx_file import XlsxFileDestination

_KIND_TO_CLASS: dict[str, type[BaseDestination]] = {}


def _register(code: str, cls: type[BaseDestination]) -> None:
    _KIND_TO_CLASS[code] = cls


_register("postgres", PostgresDestination)
_register("csv", CsvFileDestination)
_register("xlsx", XlsxFileDestination)
_register("clickhouse", ClickHouseDestination)

DESTINATION_KINDS: tuple[str, ...] = tuple(sorted(_KIND_TO_CLASS.keys()))


def normalize_destination_kind(connector_code: str) -> str:
    k = connector_code.strip().lower().replace("-", "_")
    aliases = {
        "postgresql": "postgres",
        "warehouse": "postgres",
        "pg": "postgres",
        "csv_file": "csv",
        "excel": "xlsx",
        "xlsx_file": "xlsx",
        "ch": "clickhouse",
    }
    return aliases.get(k, k)


def get_destination_class(kind: str) -> type[BaseDestination]:
    k = normalize_destination_kind(kind)
    cls = _KIND_TO_CLASS.get(k)
    if cls is None:
        raise ValueError(
            f"Неизвестный приёмник: {kind!r}. Доступно: {', '.join(DESTINATION_KINDS)}"
        )
    return cls


def destination_check(connector_code: str, config: dict[str, Any]) -> DestinationCheckResult:
    cls = get_destination_class(connector_code)
    inst = cls()
    cfg = dict(config or {})
    if cls.code == "csv" and "path" in cfg:
        cfg = {**cfg, "_check_stream": cfg.get("_check_stream") or "default"}
    return inst.check(cfg)


def destination_write(
    connector_code: str,
    *,
    stream_name: str,
    records: list[dict[str, Any]],
    schema: dict[str, Any],
    mode: WriteMode | str,
    config: dict[str, Any],
) -> DestinationWriteResult:
    cls = get_destination_class(connector_code)
    inst = cls()
    m = mode if isinstance(mode, WriteMode) else WriteMode(str(mode))
    return inst.write(stream_name, records, schema or {}, m, dict(config or {}))
