"""Коннектор Google Sheets (gspread) или CSV sample для офлайн-демо."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Iterator

from datanorma.config import get_settings
from datanorma.sources.source_config import cfg_str
from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
from datanorma.ingest.cursor_filter import filter_incremental_dict_rows
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema
from datanorma.normalization.default_stream_rules import default_stream_rules_from_json_schema

_log = logging.getLogger(__name__)

_FIXTURE_MODES = frozenset({"fixture_csv", "fixture_fallback"})


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
    if ws is None:
        raise ValueError(f"Лист {worksheet!r} не найден в таблице {spreadsheet_id}")
    return ws.get_all_records()


def _load_via_gspread_oauth(creds: Any, spreadsheet_id: str, worksheet: str | int) -> list[dict[str, Any]]:
    import gspread

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    if isinstance(worksheet, int):
        ws = sh.get_worksheet(worksheet)
    else:
        ws = sh.worksheet(worksheet)
    if ws is None:
        raise ValueError(f"Лист {worksheet!r} не найден в таблице {spreadsheet_id}")
    return ws.get_all_records()


def _oauth_credentials_from_cfg(cfg: dict[str, Any]) -> Any | None:
    refresh = cfg_str(cfg, "oauth_refresh_token", "").strip()
    if not refresh:
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        from datanorma.integrations.google_oauth_client import GOOGLE_OAUTH_SCOPES, load_google_oauth_web_client

        client_id, client_secret = load_google_oauth_web_client()
    except (FileNotFoundError, ValueError, ImportError) as exc:
        raise ValueError(f"Google OAuth не настроен на сервере: {exc}") from exc

    access = cfg_str(cfg, "oauth_access_token", "").strip() or None
    creds = Credentials(
        token=access,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(GOOGLE_OAUTH_SCOPES),
    )
    if (not creds.token or creds.expired) and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _load_via_gspread_info(sa_info: dict[str, Any], spreadsheet_id: str, worksheet: str | int) -> list[dict[str, Any]]:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(spreadsheet_id)
    if isinstance(worksheet, int):
        ws = sh.get_worksheet(worksheet)
    else:
        ws = sh.worksheet(worksheet)
    if ws is None:
        raise ValueError(f"Лист {worksheet!r} не найден в таблице {spreadsheet_id}")
    return ws.get_all_records()


def _service_account_info_from_cfg(cfg: dict[str, Any]) -> dict[str, Any] | None:
    raw = cfg.get("service_account_json")
    if raw is None:
        raw = cfg.get("service_account")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"service_account_json: некорректный JSON ({exc.msg})") from exc
        if not isinstance(parsed, dict):
            raise ValueError("service_account_json должен быть JSON-объектом")
        return parsed
    return None


def _parse_worksheet(ws_raw: str) -> str | int:
    text = (ws_raw or "0").strip() or "0"
    return int(text) if text.isdigit() else text


def _has_live_sheets_config(cfg: dict[str, Any], settings: Any) -> bool:
    sheet_id = cfg_str(cfg, "spreadsheet_id", settings.gspread_spreadsheet_id.strip())
    if not sheet_id:
        return False
    if cfg_str(cfg, "oauth_refresh_token", "").strip():
        return True
    if _service_account_info_from_cfg(cfg) is not None:
        return True
    sa = cfg_str(cfg, "service_account_file", settings.gspread_service_account_file.strip())
    return bool(sa)


def _load_live_google_sheet(
    cfg: dict[str, Any],
    settings: Any,
) -> tuple[list[dict[str, Any]], str, str, str, str | int]:
    sheet_id = cfg_str(cfg, "spreadsheet_id", settings.gspread_spreadsheet_id.strip())
    ws_raw = cfg_str(cfg, "worksheet", settings.gspread_worksheet.strip() or "0")
    if not sheet_id:
        raise ValueError("Укажите spreadsheet_id в конфигурации источника.")

    worksheet = _parse_worksheet(ws_raw)
    oauth_creds = _oauth_credentials_from_cfg(cfg)
    sa_info = _service_account_info_from_cfg(cfg)
    sa = cfg_str(cfg, "service_account_file", settings.gspread_service_account_file.strip())

    if oauth_creds is not None:
        records = _load_via_gspread_oauth(oauth_creds, sheet_id, worksheet)
        return records, "gspread_oauth", f"spreadsheet:{sheet_id}", ws_raw, worksheet
    if sa_info is not None:
        records = _load_via_gspread_info(sa_info, sheet_id, worksheet)
        return records, "gspread_inline_sa", f"spreadsheet:{sheet_id}", ws_raw, worksheet
    if sa:
        records = _load_via_gspread(sa, sheet_id, worksheet)
        return records, "gspread", f"spreadsheet:{sheet_id}", ws_raw, worksheet

    raise ValueError(
        "Для Google Sheets укажите spreadsheet_id и авторизацию: "
        "кнопка «Подключить Google» (oauth_refresh_token) или service account."
    )


class GoogleSheetsSource(BaseSource):
    integration_code = "google_sheet"

    def __init__(self, paths: DataPathsResource, *, source_config: dict[str, Any] | None = None) -> None:
        self._paths = paths
        self._source_config = source_config or {}
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
        cfg = self._source_config
        s = self._settings

        if _has_live_sheets_config(cfg, s):
            records, mode, ref, _ws_raw, _worksheet = _load_live_google_sheet(cfg, s)
            return records, mode, ref

        sample = self._paths.sample_file("google_sheet_export.csv")
        if not sample.is_file():
            raise FileNotFoundError(f"Нет sample: {sample}")
        return _load_sample_csv(sample), "fixture_csv", str(sample)

    def check(self) -> SourceCheckResult:
        cfg = self._source_config
        s = self._settings
        try:
            if _has_live_sheets_config(cfg, s):
                records, mode, ref, ws_raw, worksheet = _load_live_google_sheet(cfg, s)
                sheet_id = cfg_str(cfg, "spreadsheet_id", s.gspread_spreadsheet_id.strip())
                if len(records) == 0:
                    return SourceCheckResult(
                        ok=False,
                        message=(
                            f"Лист «{ws_raw}» доступен, но данных нет: проверьте заголовки в первой строке "
                            "и что таблица не пуста."
                        ),
                        details={
                            "mode": mode,
                            "source_ref": ref,
                            "spreadsheet_id": sheet_id,
                            "worksheet": str(worksheet),
                            "row_count": 0,
                        },
                    )
                preview_cols = list(records[0].keys())[:6]
                return SourceCheckResult(
                    ok=True,
                    message=(
                        f"Google Sheets: прочитано {len(records)} строк с листа «{ws_raw}» "
                        f"(таблица …{sheet_id[-8:] if len(sheet_id) > 8 else sheet_id}). "
                        f"Колонки: {', '.join(preview_cols)}"
                    ),
                    details={
                        "mode": mode,
                        "source_ref": ref,
                        "spreadsheet_id": sheet_id,
                        "worksheet": str(worksheet),
                        "row_count": len(records),
                        "columns": preview_cols,
                    },
                )

            records, mode, ref = self._load_records_best_effort()
            if mode in _FIXTURE_MODES:
                return SourceCheckResult(
                    ok=False,
                    message=(
                        "Источник в демо-режиме (CSV-фикстура). "
                        "Укажите spreadsheet_id и подключите Google в форме источника."
                    ),
                    details={"mode": mode, "source_ref": ref, "row_count": len(records)},
                )
            return SourceCheckResult(
                ok=True,
                message=f"Доступ к данным: {len(records)} строк (режим {mode}).",
                details={"mode": mode, "source_ref": ref, "row_count": len(records)},
            )
        except Exception as exc:
            _log.warning("Google Sheets check failed: %s", exc)
            err = exc.args[0] if getattr(exc, "args", None) and isinstance(exc.args[0], str) else str(exc)
            return SourceCheckResult(ok=False, message=err, details={})

    def discover(self) -> IngestCatalog:
        records, _mode, _ref = self._load_records_best_effort()
        if len(records) == 0:
            raise ValueError("Нет строк для построения схемы: таблица пуста или неверный лист.")
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

    def default_stream_rules(self, stream_name: str, json_schema: dict) -> "StreamRules":
        cursor_field = "order_id"
        return default_stream_rules_from_json_schema(
            stream_name=stream_name,
            json_schema=json_schema,
            cursor_field=cursor_field,
            primary_key=[cursor_field],
            sync_mode="incremental",
        )
