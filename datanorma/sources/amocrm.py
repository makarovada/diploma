"""Коннектор amoCRM API v4: leads / contacts / companies."""

from __future__ import annotations

import logging
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
from datanorma.sources.source_config import cfg_str

_log = logging.getLogger(__name__)

_STREAM_PATHS: dict[str, str] = {
    "leads": "/api/v4/leads",
    "contacts": "/api/v4/contacts",
    "companies": "/api/v4/companies",
}
_CURSOR_FIELD_RAW = "updated_at"
_PAGE_LIMIT = 250


class AmoCRMSource(BaseSource):
    integration_code = "amocrm"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()
        self._last_ingest_mode: str = "amocrm_api"

    def _base_url(self) -> str:
        return cfg_str(self._source_config, "base_url", self._settings.amocrm_base_url or "").rstrip("/")

    def _token(self) -> str:
        return cfg_str(self._source_config, "token", self._settings.amocrm_token or "")

    def _headers(self) -> dict[str, str]:
        t = self._token()
        return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

    def _entity_embed_path(self, stream_name: str) -> str:
        if stream_name == "leads":
            return "leads"
        if stream_name == "contacts":
            return "contacts"
        if stream_name == "companies":
            return "companies"
        raise ValueError(stream_name)

    def _one_page(
        self,
        stream_name: str,
        *,
        page: int,
        limit: int,
        updated_from: int | None,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Returns (rows, has_more)."""
        path = _STREAM_PATHS.get(stream_name)
        if not path:
            raise ValueError(f"amoCRM: неизвестный stream {stream_name!r}")
        base = self._base_url()
        if not base:
            raise ValueError("amoCRM: пустой base_url.")
        url_base = base + path
        params: dict[str, Any] = {"limit": limit, "page": page}
        if updated_from is not None:
            params["filter[updated_at][from]"] = updated_from
        status, body = request_json("GET", url_base, headers=self._headers(), params=params)
        if status >= 400:
            raise RuntimeError(f"amoCRM HTTP {status}: {body!r}")
        embedded = body.get("_embedded") if isinstance(body, dict) else None
        chunk: list[dict[str, Any]] = []
        if isinstance(embedded, dict):
            key = self._entity_embed_path(stream_name)
            raw = embedded.get(key)
            if isinstance(raw, list):
                chunk = [x for x in raw if isinstance(x, dict)]
        links = body.get("_links") if isinstance(body, dict) else None
        has_next_url = isinstance(links, dict) and bool(links.get("next"))
        full_page = len(chunk) >= limit and limit > 0
        has_more = has_next_url or full_page
        return chunk, has_more

    def _fetch_pages(self, stream_name: str, updated_from: int | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        while True:
            chunk, has_more = self._one_page(stream_name, page=page, limit=_PAGE_LIMIT, updated_from=updated_from)
            rows.extend(chunk)
            if not chunk or not has_more:
                break
            page += 1
            if page > 500:
                _log.warning("amoCRM: прерывание пагинации после 500 страниц")
                break
        return rows

    def check(self) -> SourceCheckResult:
        base_url = self._base_url()
        token = self._token()
        if not base_url or not token:
            return SourceCheckResult(
                ok=False,
                message="Укажите base_url и token в конфигурации источника amoCRM.",
                details={},
            )
        try:
            chunk, _ = self._one_page("leads", page=1, limit=1, updated_from=None)
            return SourceCheckResult(
                ok=True,
                message="amoCRM API v4: авторизация успешна (лиды доступны).",
                details={"mode": "amocrm_api", "probe_rows": len(chunk)},
            )
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={"mode": "amocrm_api"})

    def discover(self) -> IngestCatalog:
        if not self._base_url() or not self._token():
            raise ValueError("amoCRM: нужны base_url и token.")
        streams_out = []
        for stream_name in _STREAM_PATHS:
            rows, _ = self._one_page(stream_name, page=1, limit=50, updated_from=None)
            rows = rows[:200]
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
            raise ValueError(f"amoCRM: неизвестный stream {stream_name!r}")
        if not self._base_url() or not self._token():
            raise ValueError("amoCRM: нужны base_url и token.")

        updated_from: int | None = None
        if sync_mode == "incremental" and last_cursor and last_cursor.strip().isdigit():
            updated_from = int(last_cursor.strip())

        rows = self._fetch_pages(stream_name, updated_from)
        eff_cursor = cursor_field or _CURSOR_FIELD_RAW
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        cursor_target = "updated_at"
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=[],
        )
