"""Коннектор Яндекс Метрика: Management API (check) + Statistics Reporting API (discover/read)."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import httpx

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.http.client import request_json
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema
from datanorma.sources.source_config import cfg_int, cfg_str

_log = logging.getLogger(__name__)

METRIKA_MANAGEMENT_BASE = "https://api-metrika.yandex.net/management/v1"
STAT_V1_DATA = "https://api-metrika.yandex.net/stat/v1/data"

STREAM_CURSOR_FIELDS: dict[str, list[str]] = {
    "summary": ["date"],
    "visits": ["date_time"],
    "hits": ["date_time"],
    "goals_reaches": ["reach_datetime"],
}
# Отчёты строятся по ym:s:date (агрегаты по дню); date_time в строках — производное поле для курсора.


def _sanitize_key(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", name.replace(":", "_")).strip("_").lower() or "dim"


def _parse_report_rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Преобразует ответ stat/v1/data в плоские dict (имена полей из метрик/измерений)."""
    query = body.get("query") if isinstance(body.get("query"), dict) else {}
    dim_meta = query.get("dimensions") or []
    metric_meta = query.get("metrics") or []
    dim_names = []
    for d in dim_meta:
        if isinstance(d, dict) and d.get("name"):
            dim_names.append(str(d["name"]))
    metric_names = [str(m.get("name", f"m{i}")) for i, m in enumerate(metric_meta) if isinstance(m, dict)]

    rows_out: list[dict[str, Any]] = []
    for item in body.get("data") or []:
        if not isinstance(item, dict):
            continue
        row: dict[str, Any] = {}
        dims = item.get("dimensions") or []
        for i, d in enumerate(dims):
            key = _sanitize_key(dim_names[i]) if i < len(dim_names) else f"dim_{i}"
            if isinstance(d, dict):
                row[key] = d.get("name") or d.get("id")
            else:
                row[key] = d
        mets = item.get("metrics")
        if isinstance(mets, list):
            for j, name in enumerate(metric_names):
                val = mets[j] if j < len(mets) else None
                mk = _sanitize_key(name)
                row[mk] = val
        elif isinstance(mets, (int, float, str)):
            mk = _sanitize_key(metric_names[0]) if metric_names else "metric_0"
            row[mk] = mets
        rows_out.append(row)
    return rows_out


class YandexMetrikaSource(BaseSource):
    integration_code = "yandex_metrika"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()

    def _oauth_token(self) -> str:
        return cfg_str(self._source_config, "oauth_token", self._settings.yandex_metrika_oauth_token)

    def _counter_id(self) -> str:
        return cfg_str(self._source_config, "counter_id", self._settings.yandex_metrika_counter_id)

    def _lookback_days(self) -> int:
        d = cfg_int(self._source_config, "lookback_days", 30)
        return max(1, min(d, 365))

    def _date_range(self) -> tuple[str, str]:
        """date1/date2 в формате YYYY-MM-DD."""
        df = cfg_str(self._source_config, "date_from")
        dt = cfg_str(self._source_config, "date_to")
        if df and dt:
            return df[:10], dt[:10]
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=self._lookback_days())
        return start.isoformat(), end.isoformat()

    def _stat_report(
        self,
        *,
        dimensions: str,
        metrics: str,
        preset: str | None = None,
    ) -> list[dict[str, Any]]:
        token = self._oauth_token()
        cid = self._counter_id()
        if not token or not cid:
            raise ValueError("Yandex Metrika: нужны oauth_token и counter_id.")
        date1, date2 = self._date_range()
        headers = {"Authorization": f"OAuth {token}"}
        limit = 10000
        offset = 1  # Metrika использует 1-based offset
        rows_out: list[dict[str, Any]] = []
        while True:
            params: dict[str, Any] = {
                "ids": cid,
                "date1": date1,
                "date2": date2,
                "dimensions": dimensions,
                "metrics": metrics,
                "accuracy": "full",
                "limit": limit,
                "offset": offset,
            }
            if preset:
                params["preset"] = preset
            status, body = request_json("GET", STAT_V1_DATA, headers=headers, params=params)
            if status >= 400:
                raise RuntimeError(f"Yandex Metrika stat/v1/data HTTP {status}: {body!r}")
            if not isinstance(body, dict):
                break
            page = _parse_report_rows(body)
            rows_out.extend(page)
            total_rows = body.get("total_rows")
            total = int(total_rows) if isinstance(total_rows, (int, float)) else len(rows_out)
            if not page or len(rows_out) >= total:
                break
            offset += limit
            _log.debug("Yandex Metrika: пагинация offset=%s, собрано %s из %s", offset, len(rows_out), total)
        return rows_out

    def _stream_report_spec(self, stream_name: str) -> tuple[str, str]:
        if stream_name == "summary":
            return (
                "ym:s:date",
                "ym:s:visits,ym:s:users,ym:s:bounceRate,ym:s:pageviews",
            )
        if stream_name == "visits":
            return (
                "ym:s:date",
                "ym:s:visits,ym:s:newUsers",
            )
        if stream_name == "hits":
            return (
                "ym:s:date",
                "ym:s:pageviews",
            )
        if stream_name == "goals_reaches":
            return (
                "ym:s:date",
                "ym:s:goalReaches",
            )
        raise ValueError(f"Yandex Metrika: неизвестный stream {stream_name!r}")

    def _normalize_summary_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            date_val = r.get("ym_s_date") or r.get("dim_0")
            out.append(
                {
                    "date": str(date_val)[:10] if date_val else "",
                    "visits": r.get("ym_s_visits"),
                    "users": r.get("ym_s_users"),
                    "bounce_rate": r.get("ym_s_bouncerate"),
                    "pageviews": r.get("ym_s_pageviews"),
                }
            )
        return out

    def _normalize_visits_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            d = r.get("ym_s_date") or r.get("dim_0")
            ds = str(d)[:10] if d else ""
            out.append(
                {
                    "date_time": f"{ds}T12:00:00+03:00" if ds else "",
                    "visits": r.get("ym_s_visits"),
                    "new_users": r.get("ym_s_newusers"),
                }
            )
        return out

    def _normalize_hits_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            d = r.get("ym_s_date") or r.get("dim_0")
            ds = str(d)[:10] if d else ""
            out.append(
                {
                    "date_time": f"{ds}T12:00:00+03:00" if ds else "",
                    "pageviews": r.get("ym_s_pageviews"),
                }
            )
        return out

    def _normalize_goals(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            d = r.get("ym_s_date")
            out.append(
                {
                    "reach_datetime": str(d) if d else "",
                    "goal_reaches": r.get("ym_s_goalreaches"),
                }
            )
        return out

    def _normalize_stream(self, stream_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if stream_name == "summary":
            return self._normalize_summary_rows(rows)
        if stream_name == "visits":
            return self._normalize_visits_rows(rows)
        if stream_name == "hits":
            return self._normalize_hits_rows(rows)
        if stream_name == "goals_reaches":
            return self._normalize_goals(rows)
        return rows

    def check(self) -> SourceCheckResult:
        token = self._oauth_token()
        counter_id = self._counter_id()
        if not token or not counter_id:
            return SourceCheckResult(
                ok=False,
                message="Укажите oauth_token и counter_id в конфигурации источника.",
                details={"mode": "missing_credentials"},
            )
        url = f"{METRIKA_MANAGEMENT_BASE}/counter/{counter_id.strip()}"
        headers = {"Authorization": f"OAuth {token.strip()}"}
        date1, date2 = self._date_range()
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(url, headers=headers)
            ok = r.status_code == 200
            return SourceCheckResult(
                ok=ok,
                message=f"Management API счётчика: HTTP {r.status_code}.",
                details={
                    "mode": "yandex_metrika_api",
                    "counter_id": counter_id.strip(),
                    "status": r.status_code,
                    "date_range": {"date1": date1, "date2": date2},
                },
            )
        except Exception as exc:
            return SourceCheckResult(
                ok=False,
                message=f"Yandex Metrika API: {exc}",
                details={"mode": "yandex_metrika_api", "counter_id": counter_id.strip()},
            )

    def discover(self) -> IngestCatalog:
        streams_out = []
        for stream_name in STREAM_CURSOR_FIELDS:
            dims, mets = self._stream_report_spec(stream_name)
            raw = self._stat_report(dimensions=dims, metrics=mets)
            rows = self._normalize_stream(stream_name, raw)[:200]
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
        if stream_name not in STREAM_CURSOR_FIELDS:
            raise ValueError(f"Yandex Metrika: неизвестный stream {stream_name!r}")
        dims, mets = self._stream_report_spec(stream_name)
        raw = self._stat_report(dimensions=dims, metrics=mets)
        rows = self._normalize_stream(stream_name, raw)
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

    def default_stream_rules(self, stream_name: str, json_schema: dict):
        cursor_fields = STREAM_CURSOR_FIELDS.get(stream_name) or []
        cursor_field = cursor_fields[0] if cursor_fields else None
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            cursor_field=cursor_field,
            primary_key=cursor_fields or None,
            sync_mode="incremental",
        )
