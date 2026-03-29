"""Сырой слой: Google Sheets (service account) или CSV-экспорт из samples."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import logging

import dagster as dg

from datanorma.resources.paths import DataPathsResource

_log = logging.getLogger(__name__)


def _load_sample_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_via_gspread(
    sa_path: str,
    spreadsheet_id: str,
    worksheet: str | int,
) -> list[dict]:
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


@dg.asset(
    group_name="raw",
    description="Таблица продаж: GSPREAD_* или data/samples/google_sheet_export.csv",
    compute_kind="google_sheets",
)
def raw_google_sheet_orders(paths: DataPathsResource) -> dict:
    sa = os.environ.get("GSPREAD_SERVICE_ACCOUNT_FILE", "").strip()
    sheet_id = os.environ.get("GSPREAD_SPREADSHEET_ID", "").strip()
    ws_raw = os.environ.get("GSPREAD_WORKSHEET", "0").strip()

    if sa and sheet_id:
        try:
            worksheet: str | int = int(ws_raw) if ws_raw.isdigit() else ws_raw
            records = _load_via_gspread(sa, sheet_id, worksheet)
            ingest_mode = "gspread"
            source_ref = f"spreadsheet:{sheet_id}"
            _log.info("Google Sheets: строк %s", len(records))
        except Exception as exc:
            _log.warning("gspread ошибка (%s), читаем CSV sample", exc)
            sample = paths.sample_file("google_sheet_export.csv")
            records = _load_sample_csv(sample)
            ingest_mode = "fixture_fallback"
            source_ref = str(sample)
    else:
        sample = paths.sample_file("google_sheet_export.csv")
        if not sample.is_file():
            raise FileNotFoundError(f"Нет sample: {sample}")
        records = _load_sample_csv(sample)
        ingest_mode = "fixture_csv"
        source_ref = str(sample)

    return {
        "source_system": "google_sheet",
        "ingest_mode": ingest_mode,
        "source_ref": source_ref,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(records),
        "rows": records,
    }
