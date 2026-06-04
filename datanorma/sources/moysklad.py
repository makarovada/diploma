"""Коннектор МойСклад JSON API (Remap 1.2)."""

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

MOYSKLAD_BASE = "https://api.moysklad.ru/api/remap/1.2"

_ENTITY_PATHS: dict[str, str] = {
    "demand": "/entity/demand",
    "customerorder": "/entity/customerorder",
    "product": "/entity/product",
    "counterparty": "/entity/counterparty",
    "invoiceout": "/entity/invoiceout",
}
# stock — отчёт без поля updated, поэтому только full_refresh.
_STOCK_STREAM = "stock"
_STOCK_PATH = "/report/stock/all"
_CURSOR_FIELD_RAW = "updated"


def _flatten_moysklad_row(row: dict[str, Any]) -> dict[str, Any]:
    """Уплощает запись МойСклад: meta.href→href, вложенные agent/organization/store→*_name/*_href."""
    out = dict(row)
    meta = out.pop("meta", None)
    if isinstance(meta, dict) and meta.get("href"):
        out["href"] = meta.get("href")
    for key in ("agent", "organization", "store"):
        val = out.get(key)
        if isinstance(val, dict):
            name = val.get("name")
            nested_meta = val.get("meta") if isinstance(val.get("meta"), dict) else {}
            href = nested_meta.get("href")
            if name is not None:
                out[f"{key}_name"] = name
            if href:
                out[f"{key}_href"] = href
            out.pop(key, None)
    positions = out.get("positions")
    if isinstance(positions, dict):
        pmeta = positions.get("meta") if isinstance(positions.get("meta"), dict) else {}
        if pmeta.get("href"):
            out["positions_href"] = pmeta.get("href")
        out.pop("positions", None)
    return out


class MoysKladSource(BaseSource):
    integration_code = "moysklad"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()
        self._last_ingest_mode: str = "moysklad_api"

    def _token(self) -> str:
        return cfg_str(self._source_config, "token", self._settings.moysklad_token or "")

    def _lookback_days(self) -> int:
        d = cfg_int(self._source_config, "lookback_days", 90)
        return max(1, min(d, 730))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token()}",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }

    def _parse_updated_ms(self, row: dict[str, Any]) -> int | None:
        u = row.get(_CURSOR_FIELD_RAW)
        if isinstance(u, str) and u.strip():
            try:
                dt = datetime.fromisoformat(u.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except ValueError:
                return None
        return None

    def _path_for(self, stream_name: str) -> str:
        if stream_name == _STOCK_STREAM:
            return _STOCK_PATH
        path = _ENTITY_PATHS.get(stream_name)
        if not path:
            raise ValueError(f"МойСклад: неизвестный stream {stream_name!r}")
        return path

    def _fetch_entities(self, stream_name: str, updated_gt_ms: int | None) -> list[dict[str, Any]]:
        url = MOYSKLAD_BASE + self._path_for(stream_name)
        is_stock = stream_name == _STOCK_STREAM
        rows: list[dict[str, Any]] = []
        offset = 0
        limit = 500
        while True:
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            # report/stock/all не поддерживает filter=updated>… — всегда full_refresh.
            if updated_gt_ms is not None and not is_stock:
                params["filter"] = f"updated>{updated_gt_ms}"
            status, body = request_json("GET", url, headers=self._headers(), params=params)
            if status >= 400:
                raise RuntimeError(f"МойСклад HTTP {status}: {body!r}")
            if not isinstance(body, dict):
                raise RuntimeError("МойСклад: ожидался JSON object.")
            chunk = body.get("rows") if isinstance(body.get("rows"), list) else []
            for x in chunk:
                if isinstance(x, dict):
                    rows.append(_flatten_moysklad_row(x))
            meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
            size = int(meta.get("size") or len(chunk) or 0)
            if size < limit:
                break
            offset += limit
            _log.debug("МойСклад %s: пагинация offset=%s", stream_name, offset)
            if offset > 500000:
                _log.warning("МойСклад: прерывание после offset %s", offset)
                break
        return rows

    def _fetch_sample(self, stream_name: str, n: int = 50) -> list[dict[str, Any]]:
        url = MOYSKLAD_BASE + self._path_for(stream_name)
        params: dict[str, Any] = {"limit": n, "offset": 0}
        if stream_name != _STOCK_STREAM:
            since = datetime.now(timezone.utc) - timedelta(days=min(self._lookback_days(), 365))
            ms = int(since.timestamp() * 1000)
            params["filter"] = f"updated>{ms}"
        status, body = request_json("GET", url, headers=self._headers(), params=params)
        if status >= 400:
            raise RuntimeError(f"МойСклад HTTP {status}: {body!r}")
        if not isinstance(body, dict):
            return []
        chunk = body.get("rows") if isinstance(body.get("rows"), list) else []
        return [_flatten_moysklad_row(x) for x in chunk if isinstance(x, dict)][:n]

    def check(self) -> SourceCheckResult:
        token = self._token()
        if not token:
            return SourceCheckResult(ok=False, message="Укажите token МойСклад в конфигурации источника.", details={})
        try:
            url = MOYSKLAD_BASE + "/entity/organization"
            status, body = request_json("GET", url, headers=self._headers(), params={"limit": 1})
            if status >= 400:
                return SourceCheckResult(ok=False, message=f"МойСклад HTTP {status}: {body!r}", details={})
            return SourceCheckResult(ok=True, message="МойСклад API: авторизация успешна.", details={"mode": "moysklad_api"})
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={"mode": "moysklad_api"})

    def discover(self) -> IngestCatalog:
        if not self._token():
            raise ValueError("МойСклад: нужен token.")
        streams_out = []
        for stream_name in _ENTITY_PATHS:
            rows = self._fetch_sample(stream_name, n=80)
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
        # stock: отчёт без updated → только full_refresh, без cursor.
        stock_rows = self._fetch_sample(_STOCK_STREAM, n=80)
        stock_schema = records_to_json_schema(stock_rows) if stock_rows else {"type": "object", "properties": {}}
        streams_out.append(
            self.ingest_stream(
                _STOCK_STREAM,
                stock_schema,
                sync_modes=(SyncMode.full_refresh,),
                default_cursor_field=None,
                source_defined_cursor=False,
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
        if stream_name != _STOCK_STREAM and stream_name not in _ENTITY_PATHS:
            raise ValueError(f"МойСклад: неизвестный stream {stream_name!r}")
        if not self._token():
            raise ValueError("МойСклад: нужен token.")

        if stream_name == _STOCK_STREAM:
            # report/stock/all: всегда полная выгрузка, без курсора.
            yield from self._fetch_entities(_STOCK_STREAM, None)
            return

        updated_gt_ms: int | None = None
        if sync_mode == "incremental" and last_cursor and last_cursor.strip().isdigit():
            updated_gt_ms = int(last_cursor.strip())
        elif sync_mode == "full_refresh":
            since = datetime.now(timezone.utc) - timedelta(days=self._lookback_days())
            updated_gt_ms = int(since.timestamp() * 1000)

        rows = self._fetch_entities(stream_name, updated_gt_ms)
        eff_cursor = cursor_field or _CURSOR_FIELD_RAW
        if sync_mode == "incremental" and updated_gt_ms is not None:
            yield from rows
            return
        filtered = filter_incremental_dict_rows(
            rows,
            cursor_field=eff_cursor,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from filtered

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
        cursor_target = "updated"
        rules = default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            sync_mode="incremental",
            cursor_field=cursor_target,
            primary_key=[],
        )
        for col in rules.columns:
            if col.source_field == "sum":
                col.type = "currency_amount"
                col.scale_factor = 0.01
        return rules
