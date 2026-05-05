"""Коннектор Bitrix24: check / discover / read (минимальное ядро + fixtures)."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.normalization.rules import StreamRules
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema

_log = logging.getLogger(__name__)


class Bitrix24Source(BaseSource):
    integration_code = "bitrix24"

    _STREAM_FIXTURES: dict[str, str] = {
        "crm_deals": "bitrix24_deals.json",
        "crm_contacts": "bitrix24_contacts.json",
        "crm_leads": "bitrix24_leads.json",
        "crm_companies": "bitrix24_companies.json",
    }

    _CURSOR_FIELD_RAW = "DATE_MODIFY"

    def __init__(self, paths: DataPathsResource) -> None:
        self._paths = paths
        self._settings = get_settings()
        self._last_ingest_mode: str = "fixture"

    @property
    def last_ingest_mode(self) -> str:  # pragma: no cover
        return self._last_ingest_mode

    def _normalize_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        # PHONE/EMAIL в Bitrix часто приходят массивами; разворачиваем в первое значение.
        if isinstance(rec.get("PHONE"), list):
            rec["PHONE"] = rec["PHONE"][0] if rec["PHONE"] else None
        if isinstance(rec.get("EMAIL"), list):
            rec["EMAIL"] = rec["EMAIL"][0] if rec["EMAIL"] else None
        return rec

    def _load_fixture_rows(self, stream_name: str) -> list[dict[str, Any]]:
        fname = self._STREAM_FIXTURES.get(stream_name)
        if not fname:
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
        path = self._paths.sample_file(fname)
        if not path.is_file():
            return []
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [self._normalize_record(x) for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            inner = data.get("result") or data.get("rows") or data.get("records") or data.get("data")
            if isinstance(inner, list):
                return [self._normalize_record(x) for x in inner if isinstance(x, dict)]
        return []

    def check(self) -> SourceCheckResult:
        webhook_url = (self._settings.bitrix24_webhook_url or "").strip()
        if not webhook_url:
            return SourceCheckResult(ok=True, message="Bitrix24 без webhook: доступен sample (fixtures).", details={"mode": "fixture"})
        # API-режим не реализуем в этом этапе.
        return SourceCheckResult(ok=True, message="Bitrix24: webhook задан, используется fixtures.", details={"mode": "fixture"})

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
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
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
        cursor_target = "date_modify"
        # Primary key для upsert не фиксируем: позволяем surrogate id.
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=[],
        )

