"""Коннектор 1С: CSV/XLSX выгрузка — pandas + inference схемы."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from datanorma.config import get_settings
from datanorma.sources.source_config import cfg_str
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema

_log = logging.getLogger(__name__)


def _read_1c_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path, engine="openpyxl")
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path, encoding="utf-8")
    raise ValueError(f"Неподдерживаемый формат 1С-выгрузки: {path}")


class OneCSource(BaseSource):
    integration_code = "1c"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
        self._settings = get_settings()
        self._last_ingest_mode: str = "1c_sample_csv"
        self._last_columns: list[str] = []

    @property
    def last_ingest_mode(self) -> str:
        return self._last_ingest_mode

    @property
    def last_columns(self) -> list[str]:
        return list(self._last_columns)

    def _resolve_path(self) -> tuple[Path, str]:
        cfg_path = cfg_str(self._source_config, "export_path")
        if cfg_path:
            return Path(cfg_path), "1c_file_connection"
        override = self._settings.datanorma_1c_export_path.strip()
        if override:
            return Path(override), "1c_file_env"
        sample = self._paths.sample_file("1c_export.csv")
        return sample, "1c_sample_csv"

    def resolved_export_path(self) -> Path:
        return self._resolve_path()[0]

    def check(self) -> SourceCheckResult:
        path, mode = self._resolve_path()
        if not path.is_file():
            return SourceCheckResult(
                ok=False,
                message=f"Файл выгрузки 1С не найден: {path}",
                details={"path": str(path), "mode": mode},
            )
        try:
            df = _read_1c_table(path)
            return SourceCheckResult(
                ok=True,
                message=f"Файл 1С читается, строк: {len(df)}",
                details={"path": str(path.resolve()), "mode": mode, "columns": list(df.columns)},
            )
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={"path": str(path)})

    def discover(self) -> IngestCatalog:
        path, _mode = self._resolve_path()
        if not path.is_file():
            raise FileNotFoundError(f"Файл выгрузки 1С не найден: {path}")
        df = _read_1c_table(path)
        records = df.head(200).fillna("").to_dict(orient="records")
        schema = records_to_json_schema(records)
        stream = self.ingest_stream(
            "orders",
            schema,
            sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
            default_cursor_field=None,
            source_defined_cursor=False,
        )
        return IngestCatalog(streams=[stream])

    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        if stream_name != "orders":
            raise ValueError(f"1С: неизвестный stream {stream_name!r}, ожидается orders")
        path, mode = self._resolve_path()
        self._last_ingest_mode = mode
        if not path.is_file():
            raise FileNotFoundError(
                f"Файл выгрузки 1С не найден: {path}. "
                "В конфигурации источника задайте export_path, либо DATANORMA_1C_EXPORT_PATH, либо положите sample в data/samples."
            )
        df = _read_1c_table(path)
        self._last_columns = list(df.columns)
        records = df.fillna("").to_dict(orient="records")
        records = filter_incremental_dict_rows(
            records,
            cursor_field=cursor_field,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        _log.info("1С read: строк %s из %s", len(records), path)
        yield from records

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> "StreamRules":
        # Для 1С в текущей схеме курсор не задан, primary_key не ограничиваем.
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            cursor_field=None,
            primary_key=None,
            sync_mode="full_refresh",
        )
