"""Коннектор Wildberries Statistics API: check / discover / read."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.http.client import request_json
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.normalization.rules import StreamRules
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.sources.source_config import cfg_int, cfg_str

_log = logging.getLogger(__name__)

WB_STATISTICS_BASE = "https://statistics-api.wildberries.ru"

_STREAM_PATHS: dict[str, str] = {
    "orders": "/api/v1/supplier/orders",
    "sales": "/api/v1/supplier/sales",
    "stocks": "/api/v1/supplier/stocks",
}
_CURSOR_FIELD_RAW = "lastChangeDate"


class WildberriesSource(BaseSource):
    integration_code = "wildberries"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()
        self._last_ingest_mode: str = "wb_api"

    def _api_token(self) -> str:
        return cfg_str(self._source_config, "api_token", self._settings.wildberries_api_token or "")

    def _lookback_days(self) -> int:
        d = cfg_int(self._source_config, "lookback_days", 30)
        return max(1, min(d, 365))

    def _auth_headers(self) -> dict[str, str]:
        token = self._api_token()
        return {"Authorization": token} if token else {}

    @property
    def last_ingest_mode(self) -> str:
        return self._last_ingest_mode

    def _fetch_stream_page(self, stream_name: str, date_from: str, flag: int = 0) -> list[dict[str, Any]]:
        path = _STREAM_PATHS.get(stream_name)
        if not path:
            raise ValueError(f"Wildberries: неизвестный stream {stream_name!r}")
        url = WB_STATISTICS_BASE + path
        params = {"dateFrom": date_from, "flag": flag}
        status, body = request_json("GET", url, headers=self._auth_headers(), params=params)
        if status >= 400:
            raise RuntimeError(f"Wildberries HTTP {status}: {body!r}")
        if isinstance(body, list):
            return [x for x in body if isinstance(x, dict)]
        return []

    def _initial_date_from(self, last_cursor: str | None) -> str:
        if last_cursor and last_cursor.strip():
            return last_cursor.strip()
        since = datetime.now(timezone.utc) - timedelta(days=self._lookback_days())
        return since.strftime("%Y-%m-%dT%H:%M:%S")

    def check(self) -> SourceCheckResult:
        token = self._api_token()
        if not token:
            return SourceCheckResult(
                ok=False,
                message="Укажите api_token в конфигурации источника (Statistics API).",
                details={"mode": "missing_token"},
            )
        date_from = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        try:
            rows = self._fetch_stream_page("orders", date_from, flag=0)
            return SourceCheckResult(
                ok=True,
                message=f"Wildberries Statistics API: получено {len(rows)} строк заказов (выборка за 7 дней).",
                details={"mode": "wb_api", "sample_rows": len(rows)},
            )
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={"mode": "wb_api"})

    def discover(self) -> IngestCatalog:
        token = self._api_token()
        if not token:
            raise ValueError("Wildberries: нужен api_token для discover.")
        streams_out = []
        date_from = self._initial_date_from(None)
        for stream_name in _STREAM_PATHS:
            rows = self._fetch_stream_page(stream_name, date_from, flag=0)[:200]
            schema = records_to_json_schema(rows) if rows else {"type": "object", "properties": {}}
            streams_out.append(
                self.ingest_stream(
                    stream_name,
                    schema,
                    sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                    default_cursor_field=[_CURSOR_FIELD_RAW],
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
        if stream_name not in _STREAM_PATHS:
            raise ValueError(f"Wildberries: неизвестный stream {stream_name!r}")
        token = self._api_token()
        if not token:
            raise ValueError("Wildberries: нужен api_token.")
        eff_cursor = cursor_field or _CURSOR_FIELD_RAW

        # WB API: повторяем запросы, сдвигая dateFrom на max(lastChangeDate), пока есть данные
        date_from = self._initial_date_from(last_cursor if sync_mode == "incremental" else None)
        seen_hashes: set[str] = set()
        max_iterations = 50
        all_rows: list[dict[str, Any]] = []

        for _ in range(max_iterations):
            chunk = self._fetch_stream_page(stream_name, date_from, flag=0)
            if not chunk:
                break
            for row in chunk:
                lcd = str(row.get(_CURSOR_FIELD_RAW) or "")
                h = f"{lcd}:{row.get('nmId')}:{row.get('supplierArticle')}"
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    all_rows.append(row)
            dates = [str(r.get(_CURSOR_FIELD_RAW) or "") for r in chunk if r.get(_CURSOR_FIELD_RAW)]
            if not dates:
                break
            max_dt = max(dates)
            if max_dt <= date_from:
                break
            date_from = max_dt

        filtered = filter_incremental_dict_rows(
            all_rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        cursor_target = "last_change_date"
        primary_key = ["nm_id", "supplier_article"]
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=primary_key,
        )
