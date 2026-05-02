"""Коннектор Google Sheets (gspread) или CSV sample — inference схемы."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Iterator

from datanorma.config import get_settings
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema

_log = logging.getLogger(__name__)


def _load_sample_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_via_gspread(sa_path: str, spreadsheet_id: str, worksheet: str | int) -> list[dict[str, Any]]:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    if isinstance(worksheet, int):
        ws = sh.get_worksheet(worksheet)
    else:
        ws = sh.worksheet(worksheet)
    return ws.get_all_records()


class GoogleSheetsSource(BaseSource):
    integration_code = "google_sheet"

    def __init__(self, paths: DataPathsResource) -> None:
        self._paths = paths
        self._settings = get_settings()
        self._last_ingest_mode: str = "fixture_csv"
        self._last_source_ref: str = ""

    @property
    def last_ingest_mode(self) -> str:
        return self._last_ingest_mode

    @property
    def last_source_ref(self) -> str:
        return self._last_source_ref

    def _load_records_best_effort(self) -> tuple[list[dict[str, Any]], str, str]:
        s = self._settings
        sa = s.gspread_service_account_file.strip()
        sheet_id = s.gspread_spreadsheet_id.strip()
        ws_raw = s.gspread_worksheet.strip() or "0"

        if sa and sheet_id:
            try:
                worksheet: str | int = int(ws_raw) if ws_raw.isdigit() else ws_raw
                records = _load_via_gspread(sa, sheet_id, worksheet)
                return records, "gspread", f"spreadsheet:{sheet_id}"
            except Exception as exc:
                _log.warning("gspread ошибка (%s), читаем CSV sample", exc)
                sample = self._paths.sample_file("google_sheet_export.csv")
                return _load_sample_csv(sample), "fixture_fallback", str(sample)

        sample = self._paths.sample_file("google_sheet_export.csv")
        if not sample.is_file():
            raise FileNotFoundError(f"Нет sample: {sample}")
        return _load_sample_csv(sample), "fixture_csv", str(sample)

    def check(self) -> SourceCheckResult:
        try:
            records, mode, ref = self._load_records_best_effort()
            return SourceCheckResult(
                ok=True,
                message=f"Доступ к таблице: {len(records)} строк (режим {mode}).",
                details={"mode": mode, "source_ref": ref},
            )
        except Exception as exc:
            return SourceCheckResult(ok=False, message=str(exc), details={})

    def discover(self) -> IngestCatalog:
        records, _mode, _ref = self._load_records_best_effort()
        sample = records[:200]
        schema = records_to_json_schema(sample)
        stream = self.ingest_stream(
            "orders",
            schema,
            sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
            default_cursor_field=["order_id"],
            source_defined_cursor=True,
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
            raise ValueError(f"Google Sheets: неизвестный stream {stream_name!r}, ожидается orders")
        records, mode, ref = self._load_records_best_effort()
        self._last_ingest_mode = mode
        self._last_source_ref = ref
        records = filter_incremental_dict_rows(
            records,
            cursor_field=cursor_field,
            last_cursor=last_cursor,
            sync_mode=str(sync_mode),
        )
        yield from records
