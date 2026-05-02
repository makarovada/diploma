"""Абстрактный коннектор источника: check / discover / read (фаза 2, Ingest-подобный контракт)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator

from datanorma.core.ingest_protocol import IngestCatalog, IngestStream, SyncMode


@dataclass
class SourceCheckResult:
    ok: bool
    message: str
    details: dict[str, Any] | None = None


class BaseSource(ABC):
    """Базовый класс коннектора. Реализации: Ozon, 1С, Sheets, REST-builder."""

    integration_code: str

    @abstractmethod
    def check(self) -> SourceCheckResult:
        """Проверка подключения (как Ingest check / CONNECTION_STATUS)."""

    @abstractmethod
    def discover(self) -> IngestCatalog:
        """Каталог потоков и JSON Schema полей."""

    @abstractmethod
    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Чтение одной записи за другой в виде dict (сырая строка источника)."""

    def ingest_stream(
        self,
        name: str,
        json_schema: dict[str, Any],
        *,
        sync_modes: tuple[SyncMode, ...] = (SyncMode.full_refresh, SyncMode.incremental),
        default_cursor_field: list[str] | None = None,
        source_defined_cursor: bool | None = None,
    ) -> IngestStream:
        return IngestStream(
            name=name,
            json_schema=json_schema,
            supported_sync_modes=list(sync_modes),
            default_cursor_field=default_cursor_field,
            source_defined_cursor=source_defined_cursor,
        )
