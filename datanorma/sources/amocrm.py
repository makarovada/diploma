"""Коннектор amoCRM API v4: leads / contacts / companies."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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
    "tasks": "/api/v4/tasks",
    "pipelines": "/api/v4/leads/pipelines",
}
_STREAM_EMBED: dict[str, str] = {
    "leads": "leads",
    "contacts": "contacts",
    "companies": "companies",
    "tasks": "tasks",
    "pipelines": "pipelines",
}
_STREAM_CURSOR_FIELDS: dict[str, str] = {
    "leads": "updated_at",
    "contacts": "updated_at",
    "companies": "updated_at",
    "tasks": "complete_till",
}
# pipelines — справочник без поля модификации, только full_refresh.
_FULL_REFRESH_ONLY: frozenset[str] = frozenset({"pipelines"})
# Стримы, по которым умеем серверную фильтрацию по filter[updated_at][from].
_UPDATED_AT_STREAMS: frozenset[str] = frozenset({"leads", "contacts", "companies"})
_CURSOR_FIELD_RAW = "updated_at"
_PAGE_LIMIT = 250


def _normalize_row(stream_name: str, row: dict[str, Any]) -> dict[str, Any]:
    """Убирает _links, добавляет updated_at_iso и уплощает специфичные поля leads/contacts."""
    out = {k: v for k, v in row.items() if k != "_links"}
    ts = out.get("updated_at")
    if isinstance(ts, (int, float)):
        out["updated_at_iso"] = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    embedded = row.get("_embedded") if isinstance(row.get("_embedded"), dict) else {}
    if stream_name == "leads":
        tags = embedded.get("tags")
        if isinstance(tags, list):
            out["tags"] = ",".join(str(t.get("name")) for t in tags if isinstance(t, dict) and t.get("name"))
        contacts = embedded.get("contacts")
        if isinstance(contacts, list):
            out["contact_ids"] = [c.get("id") for c in contacts if isinstance(c, dict) and c.get("id") is not None]
    if stream_name == "contacts":
        cfv = row.get("custom_fields_values")
        if isinstance(cfv, list):
            for field in cfv:
                if not isinstance(field, dict):
                    continue
                code = field.get("field_code") or field.get("field_id") or field.get("field_name")
                values = field.get("values")
                if code and isinstance(values, list) and values:
                    first = values[0]
                    out[f"cf_{str(code).lower()}"] = first.get("value") if isinstance(first, dict) else first
    out.pop("_embedded", None)
    return out


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
        key = _STREAM_EMBED.get(stream_name)
        if not key:
            raise ValueError(stream_name)
        return key

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
                chunk = [_normalize_row(stream_name, x) for x in raw if isinstance(x, dict)]
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
            if stream_name in _FULL_REFRESH_ONLY:
                streams_out.append(
                    self.ingest_stream(
                        stream_name,
                        schema,
                        sync_modes=(SyncMode.full_refresh,),
                        default_cursor_field=None,
                        source_defined_cursor=False,
                    )
                )
            else:
                streams_out.append(
                    self.ingest_stream(
                        stream_name,
                        schema,
                        sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                        default_cursor_field=[_STREAM_CURSOR_FIELDS[stream_name]],
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
        if (
            stream_name in _UPDATED_AT_STREAMS
            and sync_mode == "incremental"
            and last_cursor
            and last_cursor.strip().isdigit()
        ):
            updated_from = int(last_cursor.strip())

        rows = self._fetch_pages(stream_name, updated_from)
        if stream_name in _FULL_REFRESH_ONLY:
            yield from rows
            return
        eff_cursor = cursor_field or _STREAM_CURSOR_FIELDS.get(stream_name, _CURSOR_FIELD_RAW)
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        cursor_target = _STREAM_CURSOR_FIELDS.get(stream_name)
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental" if cursor_target else "full_refresh",
            cursor_field=cursor_target,
            primary_key=[],
        )
