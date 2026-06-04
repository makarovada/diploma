"""Коннектор Bitrix24: входящий webhook + CRM list methods."""

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

_STREAM_METHODS: dict[str, str] = {
    "crm_deals": "crm.deal.list",
    "crm_contacts": "crm.contact.list",
    "crm_leads": "crm.lead.list",
    "crm_companies": "crm.company.list",
    "crm_tasks": "tasks.task.list",
    "crm_activities": "crm.activity.list",
}
_STREAM_CURSOR_FIELDS: dict[str, str] = {
    "crm_deals": "DATE_MODIFY",
    "crm_contacts": "DATE_MODIFY",
    "crm_leads": "DATE_MODIFY",
    "crm_companies": "DATE_MODIFY",
    "crm_tasks": "CHANGED_DATE",
    "crm_activities": "LAST_UPDATED",
}
_DEFAULT_CURSOR_FIELD = "DATE_MODIFY"
_CURSOR_FIELD_RAW = _DEFAULT_CURSOR_FIELD

_PAGE_SIZE = 50


def normalize_bitrix24_webhook_url(raw: str) -> str:
    """Базовый URL входящего webhook без /profile.json и лишних слэшей."""
    url = str(raw or "").strip()
    if not url:
        return ""
    url = url.replace("/profile.json/", "/").replace("/profile.json", "")
    if url.endswith("/profile.json"):
        url = url[: -len("/profile.json")]
    return url.rstrip("/")


def _cursor_for(stream_name: str) -> str:
    return _STREAM_CURSOR_FIELDS.get(stream_name, _DEFAULT_CURSOR_FIELD)


class Bitrix24Source(BaseSource):
    integration_code = "bitrix24"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()
        self._last_ingest_mode: str = "bitrix24_api"

    def _webhook_url(self) -> str:
        raw = cfg_str(self._source_config, "webhook_url", self._settings.bitrix24_webhook_url or "")
        return normalize_bitrix24_webhook_url(raw)

    @property
    def last_ingest_mode(self) -> str:
        return self._last_ingest_mode

    def _normalize_record(self, rec: dict[str, Any]) -> dict[str, Any]:
        if isinstance(rec.get("PHONE"), list):
            rec["PHONE"] = rec["PHONE"][0] if rec["PHONE"] else None
        if isinstance(rec.get("EMAIL"), list):
            rec["EMAIL"] = rec["EMAIL"][0] if rec["EMAIL"] else None
        return rec

    def _call_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        base = self._webhook_url()
        if not base:
            raise ValueError("Bitrix24: пустой webhook_url.")
        url = f"{base}/{method}.json"
        status, body = request_json("POST", url, json_body=params)
        if status >= 400:
            raise RuntimeError(f"Bitrix24 HTTP {status}: {body!r}")
        if not isinstance(body, dict):
            raise RuntimeError(f"Bitrix24: неожиданный ответ {type(body)}")
        return body

    @staticmethod
    def _extract_rows(body: dict[str, Any]) -> list[dict[str, Any]]:
        """result может быть list (crm.*.list) или dict с ключом tasks (tasks.task.list)."""
        result = body.get("result")
        if isinstance(result, dict):
            tasks = result.get("tasks")
            return [x for x in tasks if isinstance(x, dict)] if isinstance(tasks, list) else []
        if isinstance(result, list):
            return [x for x in result if isinstance(x, dict)]
        return []

    def _paginate(self, method: str, base_params: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        start = 0
        while True:
            params = {**base_params, "start": start}
            body = self._call_method(method, params)
            chunk = self._extract_rows(body)
            out.extend(self._normalize_record(dict(x)) for x in chunk)
            if "next" not in body or not chunk:
                break
            start = int(body.get("next") or 0)
            _log.debug("Bitrix24 %s: пагинация start=%s", method, start)
        return out

    def _fetch_all(self, stream_name: str) -> list[dict[str, Any]]:
        method = _STREAM_METHODS.get(stream_name)
        if not method:
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
        cursor = _cursor_for(stream_name)
        return self._paginate(
            method,
            {"order": {cursor: "ASC"}},
        )

    def _fetch_incremental(self, stream_name: str, last_cursor: str | None) -> list[dict[str, Any]]:
        method = _STREAM_METHODS.get(stream_name)
        if not method:
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
        cursor = _cursor_for(stream_name)
        filt: dict[str, Any] = {}
        if last_cursor:
            filt[f">{cursor}"] = last_cursor
        base: dict[str, Any] = {"order": {cursor: "ASC"}}
        if filt:
            base["filter"] = filt
        return self._paginate(method, base)

    def _sample_rows(self, stream_name: str, limit: int = 80) -> list[dict[str, Any]]:
        method = _STREAM_METHODS.get(stream_name)
        if not method:
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
        cursor = _cursor_for(stream_name)
        body = self._call_method(
            method,
            {"start": 0, "order": {cursor: "DESC"}},
        )
        rows = [self._normalize_record(dict(x)) for x in self._extract_rows(body)]
        return rows[:limit]

    def check(self) -> SourceCheckResult:
        webhook_url = self._webhook_url()
        if not webhook_url:
            return SourceCheckResult(ok=False, message="Укажите webhook_url входящего webhook Bitrix24.", details={})
        try:
            body = self._call_method(
                "crm.deal.list",
                {"select": ["ID"], "start": 0},
            )
            n = len(body.get("result") or []) if isinstance(body.get("result"), list) else 0
            return SourceCheckResult(
                ok=True,
                message=f"Bitrix24 webhook отвечает (crm.deal.list: {n} записей в первой странице).",
                details={"mode": "bitrix24_api"},
            )
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={"mode": "bitrix24_api"})

    def discover(self) -> IngestCatalog:
        if not self._webhook_url():
            raise ValueError("Bitrix24: нужен webhook_url.")
        streams_out = []
        for stream_name in _STREAM_METHODS:
            rows = self._sample_rows(stream_name, limit=200)
            schema = records_to_json_schema(rows) if rows else {"type": "object", "properties": {}}
            streams_out.append(
                self.ingest_stream(
                    stream_name,
                    schema,
                    sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                    default_cursor_field=[_cursor_for(stream_name)],
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
        if stream_name not in _STREAM_METHODS:
            raise ValueError(f"Bitrix24: неизвестный stream {stream_name!r}")
        if not self._webhook_url():
            raise ValueError("Bitrix24: нужен webhook_url.")

        if sync_mode == "incremental" and last_cursor:
            rows = self._fetch_incremental(stream_name, last_cursor)
        else:
            rows = self._fetch_all(stream_name)

        eff_cursor = cursor_field or _cursor_for(stream_name)
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        cursor_target = _cursor_for(stream_name).lower()
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=[],
        )
