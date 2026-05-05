"""Коннектор Яндекс Метрика (Management API + sample): check / discover / read."""

from __future__ import annotations

import json
import logging
from typing import Any, Iterator

import httpx

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema

_log = logging.getLogger(__name__)

METRIKA_MANAGEMENT_BASE = "https://api-metrika.yandex.net/management/v1"

STREAM_FIXTURE_NAMES: dict[str, str] = {
    "summary": "yandex_metrika_summary.json",
    "visits": "yandex_metrika_visits.json",
    "hits": "yandex_metrika_hits.json",
    "goals_reaches": "yandex_metrika_goals_reaches.json",
}

STREAM_CURSOR_FIELDS: dict[str, list[str]] = {
    "summary": ["date"],
    "visits": ["date_time"],
    "hits": ["date_time"],
    "goals_reaches": ["reach_datetime"],
}


def _load_fixture_rows(paths: DataPathsResource, stream: str) -> list[dict[str, Any]]:
    name = STREAM_FIXTURE_NAMES.get(stream)
    if not name:
        return []
    path = paths.sample_file(name)
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        inner = data.get("data") or data.get("rows") or data.get("records")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    return []


def _check_counter_oauth(token: str, counter_id: str) -> SourceCheckResult:
    url = f"{METRIKA_MANAGEMENT_BASE}/counter/{counter_id.strip()}"
    headers = {"Authorization": f"OAuth {token.strip()}"}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, headers=headers)
        ok = r.status_code == 200
        return SourceCheckResult(
            ok=ok,
            message=f"Management API счётчика: HTTP {r.status_code}.",
            details={"mode": "yandex_metrika_api", "counter_id": counter_id.strip(), "status": r.status_code},
        )
    except Exception as exc:
        return SourceCheckResult(
            ok=False,
            message=f"Yandex Metrika API: {exc}",
            details={"mode": "yandex_metrika_api", "counter_id": counter_id.strip()},
        )


class YandexMetrikaSource(BaseSource):
    integration_code = "yandex_metrika"

    def __init__(self, paths: DataPathsResource) -> None:
        self._paths = paths
        self._settings = get_settings()

    def check(self) -> SourceCheckResult:
        token = (self._settings.yandex_metrika_oauth_token or "").strip()
        counter_id = (self._settings.yandex_metrika_counter_id or "").strip()
        if token and counter_id:
            return _check_counter_oauth(token, counter_id)
        missing = []
        for stream in STREAM_FIXTURE_NAMES:
            rows = _load_fixture_rows(self._paths, stream)
            if not rows:
                missing.append(stream)
        if missing:
            return SourceCheckResult(
                ok=False,
                message="Нет YANDEX_METRIKA_OAUTH_TOKEN/YANDEX_METRIKA_COUNTER_ID и неполный набор sample-файлов.",
                details={"mode": "fixture", "missing_streams": missing},
            )
        return SourceCheckResult(
            ok=True,
            message="Режим без OAuth: доступны sample для discover/read.",
            details={"mode": "fixture"},
        )

    def discover(self) -> IngestCatalog:
        streams_out = []
        for stream_name in STREAM_FIXTURE_NAMES:
            rows = _load_fixture_rows(self._paths, stream_name)
            schema = records_to_json_schema(rows) if rows else {"type": "object", "properties": {}}
            streams_out.append(
                self.ingest_stream(
                    stream_name,
                    schema,
                    sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                    default_cursor_field=STREAM_CURSOR_FIELDS.get(stream_name),
                    source_defined_cursor=True,
                )
            )
        return IngestCatalog(streams=streams_out)

    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        if stream_name not in STREAM_FIXTURE_NAMES:
            raise ValueError(f"Yandex Metrika: неизвестный stream {stream_name!r}")
        rows = _load_fixture_rows(self._paths, stream_name)
        if not rows:
            _log.warning("Yandex Metrika: пустая фикстура для %s", stream_name)
            return
        eff_cursor = cursor_field
        if not eff_cursor and STREAM_CURSOR_FIELDS.get(stream_name):
            eff_cursor = STREAM_CURSOR_FIELDS[stream_name][0]
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> "StreamRules":
        cursor_fields = STREAM_CURSOR_FIELDS.get(stream_name) or []
        cursor_field = cursor_fields[0] if cursor_fields else None
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            cursor_field=cursor_field,
            primary_key=cursor_fields or None,
            sync_mode="incremental",
        )
