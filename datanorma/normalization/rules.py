"""Модели правил нормализации по stream и колонкам."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ColumnType = Literal[
    "string",
    "integer",
    "number",
    "boolean",
    "date",
    "datetime",
    "currency_amount",
    "currency_code",
    "phone",
    "email",
    "inn",
    "kpp",
    "ogrn",
    "enum",
    "json",
]

OnErrorMode = Literal["null", "raise", "keep_raw"]
SyncMode = Literal["full_refresh", "incremental"]


@dataclass(slots=True)
class ColumnRule:
    """Правило нормализации одной колонки для конкретного stream подключения."""

    source_field: str
    target_field: str
    type: ColumnType
    nullable: bool = True
    required: bool = False
    date_formats: list[str] = field(default_factory=list)
    timezone: str | None = None
    decimal_separator: str | None = None
    thousands_separator: str | None = None
    currency_code: str | None = None
    convert_to_currency: str | None = None
    enum_map: dict[str, str] = field(default_factory=dict)
    enum_default: str | None = None
    phone_default_country: str = "RU"
    trim: bool = True
    lowercase: bool = False
    uppercase: bool = False
    on_error: OnErrorMode = "null"
    description: str | None = None
    scale_factor: float | None = None
    enrich: str | None = None


@dataclass(slots=True)
class StreamRules:
    """Набор правил по колонкам для одного stream."""

    stream_name: str
    primary_key: list[str] = field(default_factory=list)
    cursor_field: str | None = None
    sync_mode: SyncMode = "full_refresh"
    columns: list[ColumnRule] = field(default_factory=list)
    drop_unknown_columns: bool = False
    deduplicate: bool = True
