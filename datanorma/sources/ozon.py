"""Коннектор Ozon Seller API (FBS postings) — check / discover / read."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import httpx

from datanorma.config import OZON_API_BASE, get_settings
from datanorma.core.airbyte_protocol import AirbyteCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_postings
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema

_log = logging.getLogger(__name__)


def _load_fixture(paths: DataPathsResource) -> list[dict[str, Any]]:
    path = paths.sample_file("ozon_postings.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    postings = data.get("result", {}).get("postings")
    if postings is None:
        postings = data.get("postings", [])
    return list(postings)


def _fetch_postings_api(client_id: str, api_key: str, limit: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    to = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    payload = {
        "dir": "DESC",
        "filter": {"since": since, "to": to},
        "limit": min(max(limit, 1), 1000),
        "offset": 0,
        "with": {"analytics_data": True, "financial_data": True, "barcodes": False},
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{OZON_API_BASE}/v3/posting/fbs/list",
            headers={
                "Client-Id": client_id,
                "Api-Key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
    return list(body.get("result", {}).get("postings", []))


class OzonSource(BaseSource):
    integration_code = "ozon"

    def __init__(self, paths: DataPathsResource) -> None:
        self._paths = paths
        self._settings = get_settings()
        self._last_ingest_mode: str = "fixture"

    @property
    def last_ingest_mode(self) -> str:
        return self._last_ingest_mode

    def check(self) -> SourceCheckResult:
        client_id = self._settings.ozon_client_id.strip()
        api_key = self._settings.ozon_api_key.strip()
        if not client_id or not api_key:
            p = self._paths.sample_file("ozon_postings.json")
            if p.is_file():
                return SourceCheckResult(
                    ok=True,
                    message="Режим без API-ключей: доступен sample для discover/read.",
                    details={"mode": "fixture", "sample": str(p)},
                )
            return SourceCheckResult(ok=False, message="Нет OZON_CLIENT_ID/OZON_API_KEY и нет sample.", details={})
        try:
            _fetch_postings_api(client_id, api_key, limit=min(self._settings.ozon_fetch_limit, 5))
            return SourceCheckResult(
                ok=True,
                message="Ozon Seller API отвечает (posting/fbs/list).",
                details={"mode": "ozon_api"},
            )
        except Exception as exc:
            return SourceCheckResult(
                ok=False,
                message=f"Ozon API ошибка: {exc}",
                details={"mode": "ozon_api"},
            )

    def discover(self) -> AirbyteCatalog:
        postings: list[dict[str, Any]] = []
        client_id = self._settings.ozon_client_id.strip()
        api_key = self._settings.ozon_api_key.strip()
        if client_id and api_key:
            try:
                postings = _fetch_postings_api(client_id, api_key, limit=min(self._settings.ozon_fetch_limit, 50))
            except Exception:
                postings = _load_fixture(self._paths)
        else:
            postings = _load_fixture(self._paths)
        schema = records_to_json_schema(postings)
        stream = self.airbyte_stream(
            "postings",
            schema,
            sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
            default_cursor_field=["posting_number"],
            source_defined_cursor=True,
        )
        return AirbyteCatalog(streams=[stream])

    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        if stream_name != "postings":
            raise ValueError(f"Ozon: неизвестный stream {stream_name!r}, ожидается postings")

        client_id = self._settings.ozon_client_id.strip()
        api_key = self._settings.ozon_api_key.strip()
        limit = self._settings.ozon_fetch_limit

        if client_id and api_key:
            try:
                postings = _fetch_postings_api(client_id, api_key, limit=limit)
                self._last_ingest_mode = "ozon_api"
            except Exception as exc:
                _log.warning("Ozon API недоступен (%s), читаем фикстуру", exc)
                postings = _load_fixture(self._paths)
                self._last_ingest_mode = "fixture_fallback"
        else:
            postings = _load_fixture(self._paths)
            self._last_ingest_mode = "fixture"

        postings = filter_incremental_postings(
            postings,
            cursor_field=cursor_field,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from postings
