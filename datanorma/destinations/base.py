"""Базовый контракт приёмника данных: проверка конфигурации и запись потока."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class WriteMode(str, Enum):
    append = "append"
    full_refresh = "full_refresh"
    upsert = "upsert"
    replace_table = "replace_table"


@dataclass
class DestinationCheckResult:
    ok: bool
    message: str
    details: dict[str, Any] | None = None


@dataclass
class DestinationWriteResult:
    ok: bool
    message: str
    rows_written: int = 0
    details: dict[str, Any] = field(default_factory=dict)


class BaseDestination(ABC):
    """Реализации: PostgreSQL, CSV/XLSX, ClickHouse (HTTP)."""

    code: str

    @abstractmethod
    def check(self, config: dict[str, Any]) -> DestinationCheckResult:
        """Проверка доступа (сеть, файловая система, учётные данные)."""

    @abstractmethod
    def write(
        self,
        stream_name: str,
        records: Iterable[dict[str, Any]],
        schema: dict[str, Any],
        mode: WriteMode,
        config: dict[str, Any],
    ) -> DestinationWriteResult:
        """Запись батча в приёмник."""
