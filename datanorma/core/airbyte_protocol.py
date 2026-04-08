"""Упрощённые модели сообщений [Airbyte Protocol](https://docs.airbyte.com/understanding-airbyte/airbyte-protocol).

Нужны как контракт для будущих коннекторов / обмена JSON без обязательной зависимости от `airbyte-cdk` в рантайме.
Поля и имена выровнены с типичным JSON, который эмитируют CDK-based source connectors.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SyncMode(StrEnum):
    full_refresh = "full_refresh"
    incremental = "incremental"


class DestinationSyncMode(StrEnum):
    append = "append"
    overwrite = "overwrite"
    append_dedup = "append_dedup"
    refresh_overwrite = "refresh_overwrite"
    refresh_append = "refresh_append"


class StreamDescriptor(BaseModel):
    """Идентификация потока в state / trace."""

    model_config = ConfigDict(extra="allow")

    name: str
    namespace: str | None = None


class AirbyteStream(BaseModel):
    """Описание потока в каталоге (Catalog)."""

    model_config = ConfigDict(extra="allow")

    name: str
    json_schema: dict[str, Any] = Field(default_factory=dict)
    supported_sync_modes: list[SyncMode] | None = None
    source_defined_cursor: bool | None = None
    default_cursor_field: list[str] | None = None
    namespace: str | None = None
    source_defined_primary_key: list[list[str]] | None = None


class AirbyteCatalog(BaseModel):
    model_config = ConfigDict(extra="allow")

    streams: list[AirbyteStream] = Field(default_factory=list)


class ConfiguredAirbyteStream(BaseModel):
    """Поток с выбранным режимом синхронизации (configured catalog)."""

    model_config = ConfigDict(extra="allow")

    stream: AirbyteStream
    sync_mode: SyncMode | None = None
    destination_sync_mode: DestinationSyncMode | None = None
    cursor_field: list[str] | None = None
    primary_key: list[list[str]] | None = None


class ConfiguredAirbyteCatalog(BaseModel):
    model_config = ConfigDict(extra="allow")

    streams: list[ConfiguredAirbyteStream] = Field(default_factory=list)


class AirbyteRecordMessage(BaseModel):
    """RECORD: одна логическая строка источника."""

    model_config = ConfigDict(extra="allow")

    stream: str
    data: dict[str, Any]
    emitted_at: int = Field(..., description="Unix time, миллисекунды")
    meta: dict[str, Any] | None = None


class AirbyteStateMessage(BaseModel):
    """STATE: курсор / чекпоинт инкрементальной синхронизации."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Literal["STREAM", "GLOBAL", "LEGACY"] | None = None
    stream: StreamDescriptor | None = None
    global_: dict[str, Any] | None = Field(default=None, alias="global")
    data: dict[str, Any] | None = None
    stream_state: dict[str, Any] | None = None


class AirbyteLogMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    level: Literal["FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"] | str = "INFO"
    message: str = ""


class AirbyteTraceMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: Literal["ERROR", "ESTIMATE", "STREAM_STATUS", "CONNECTION_STATUS"] | str = "ERROR"
    emitted_at: int | None = None
    error: dict[str, Any] | None = None


class AirbyteMessageType(StrEnum):
    RECORD = "RECORD"
    STATE = "STATE"
    LOG = "LOG"
    SPEC = "SPEC"
    CONNECTION_STATUS = "CONNECTION_STATUS"
    CATALOG = "CATALOG"
    TRACE = "TRACE"
    CONTROL = "CONTROL"


class AirbyteMessage(BaseModel):
    """Корневое сообщение протокола (одна строка JSON на сообщение в STDIO-режиме)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: AirbyteMessageType | str
    record: AirbyteRecordMessage | None = None
    state: AirbyteStateMessage | None = None
    log: AirbyteLogMessage | dict[str, Any] | None = None
    catalog: AirbyteCatalog | None = None
    trace: AirbyteTraceMessage | dict[str, Any] | None = None
    connectionStatus: dict[str, Any] | None = Field(default=None, alias="connectionStatus")
    spec: dict[str, Any] | None = None
