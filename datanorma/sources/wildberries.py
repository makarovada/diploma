"""Коннектор Wildberries: check / discover / read (минимальное ядро + fixtures)."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.normalization.rules import StreamRules

_log = logging.getLogger(__name__)


class WildberriesSource(BaseSource):
    integration_code = "wildberries"

    _STREAM_FIXTURES: dict[str, str] = {
        "orders": "wildberries_orders.json",
        "sales": "wildberries_sales.json",
        "stocks": "wildberries_stocks.json",
    }
    _CURSOR_FIELD_RAW = "lastChangeDate"

    def __init__(self, paths: DataPathsResource) -> None:
        self._paths = paths
        self._settings = get_settings()
        self._last_ingest_mode: str = "fixture"

    @property
    def last_ingest_mode(self) -> str:  # pragma: no cover (контракт для UI)
        return self._last_ingest_mode

    def _load_fixture_rows(self, stream_name: str) -> list[dict[str, Any]]:
        fname = self._STREAM_FIXTURES.get(stream_name)
        if not fname:
            raise ValueError(f"Wildberries: неизвестный stream {stream_name!r}")
        path = self._paths.sample_file(fname)
        if not path.is_file():
            return []
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            inner = data.get("result") or data.get("rows") or data.get("records") or data.get("data")
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        return []

    def check(self) -> SourceCheckResult:
        token = (self._settings.wildberries_api_token or "").strip()
        if not token:
            return SourceCheckResult(
                ok=True,
                message="Wildberries без токена: доступен sample (fixtures).",
                details={"mode": "fixture"},
            )
        # API-режим не реализуем в этом этапе; всё равно используем fixtures.
        return SourceCheckResult(ok=True, message="Wildberries: токен задан, используется fixtures.", details={"mode": "fixture"})

    def discover(self) -> IngestCatalog:
        streams_out = []
        for stream_name in self._STREAM_FIXTURES.keys():
            rows = self._load_fixture_rows(stream_name)
            schema = records_to_json_schema(rows[:200]) if rows else {"type": "object", "properties": {}}
            stream = self.ingest_stream(
                stream_name,
                schema,
                sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                default_cursor_field=[self._CURSOR_FIELD_RAW],
                source_defined_cursor=True,
            )
            streams_out.append(stream)
        return IngestCatalog(streams=streams_out)

    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        if stream_name not in self._STREAM_FIXTURES:
            raise ValueError(f"Wildberries: неизвестный stream {stream_name!r}")
        rows = self._load_fixture_rows(stream_name)
        self._last_ingest_mode = "fixture"

        eff_cursor = cursor_field or self._CURSOR_FIELD_RAW
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        # Дефолты: lastChangeDate → datetime, priceWithDisc/totalPrice → currency_amount, nmId → integer.
        # Cursor/incremental идёт по lastChangeDate.
        cursor_target = "last_change_date"
        primary_key = ["nm_id", "supplier_article"]
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=primary_key,
        )

