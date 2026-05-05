"""Приёмники данных (Фаза 7): проверка и запись в PostgreSQL, файлы, ClickHouse."""

from datanorma.destinations.base import (
    BaseDestination,
    DestinationCheckResult,
    DestinationWriteResult,
    WriteMode,
)
from datanorma.destinations.registry import (
    DESTINATION_KINDS,
    destination_check,
    destination_write,
    get_destination_class,
    normalize_destination_kind,
)

__all__ = [
    "DESTINATION_KINDS",
    "BaseDestination",
    "DestinationCheckResult",
    "DestinationWriteResult",
    "WriteMode",
    "destination_check",
    "destination_write",
    "get_destination_class",
    "normalize_destination_kind",
]
