from __future__ import annotations

from pathlib import Path

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.sheets import GoogleSheetsSource

pytestmark = pytest.mark.unit


def test_google_sheets_accepts_inline_service_account_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    calls: dict[str, object] = {}

    def _fake_load(sa_info: dict, spreadsheet_id: str, worksheet: str | int):
        calls["sa_info"] = sa_info
        calls["spreadsheet_id"] = spreadsheet_id
        calls["worksheet"] = worksheet
        return [{"order_id": "42", "amount": "10"}]

    monkeypatch.setattr("datanorma.sources.sheets._load_via_gspread_info", _fake_load)

    src = GoogleSheetsSource(
        paths,
        source_config={
            "spreadsheet_id": "sheet-123",
            "worksheet": "orders",
            "service_account_json": {"type": "service_account", "project_id": "demo"},
        },
    )

    rows = list(src.read("orders", sync_mode="full_refresh"))

    assert len(rows) == 1
    assert rows[0]["order_id"] == "42"
    assert src.last_ingest_mode == "gspread_inline_sa"
    assert calls["spreadsheet_id"] == "sheet-123"
    assert calls["worksheet"] == "orders"


def test_google_sheets_accepts_oauth_refresh_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    calls: dict[str, object] = {}

    def _fake_oauth(creds, spreadsheet_id: str, worksheet: str | int):
        calls["creds"] = creds
        calls["spreadsheet_id"] = spreadsheet_id
        calls["worksheet"] = worksheet
        return [{"order_id": "7"}]

    monkeypatch.setattr("datanorma.sources.sheets._oauth_credentials_from_cfg", lambda _cfg: object())
    monkeypatch.setattr("datanorma.sources.sheets._load_via_gspread_oauth", _fake_oauth)

    src = GoogleSheetsSource(
        paths,
        source_config={
            "spreadsheet_id": "sheet-oauth",
            "worksheet": "0",
            "oauth_refresh_token": "refresh-demo",
        },
    )

    rows = list(src.read("orders", sync_mode="full_refresh"))

    assert len(rows) == 1
    assert src.last_ingest_mode == "gspread_oauth"
    assert calls["spreadsheet_id"] == "sheet-oauth"


def test_check_uses_live_sheet_not_csv_when_oauth_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _fake_oauth(_creds, spreadsheet_id: str, worksheet: str | int):
        return [
            {"order_id": "1", "amount": "100"},
            {"order_id": "2", "amount": "200"},
            {"order_id": "3", "amount": "300"},
        ]

    monkeypatch.setattr("datanorma.sources.sheets._oauth_credentials_from_cfg", lambda _cfg: object())
    monkeypatch.setattr("datanorma.sources.sheets._load_via_gspread_oauth", _fake_oauth)

    src = GoogleSheetsSource(
        paths,
        source_config={
            "spreadsheet_id": "sheet-live",
            "worksheet": "0",
            "oauth_refresh_token": "refresh-demo",
        },
    )
    result = src.check()

    assert result.ok is True
    assert "3 строк" in result.message
    assert result.details.get("mode") == "gspread_oauth"
    assert result.details.get("row_count") == 3


def test_check_fails_when_gspread_errors_instead_of_csv_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _boom(*_a, **_k):
        raise PermissionError("403 Forbidden")

    monkeypatch.setattr("datanorma.sources.sheets._oauth_credentials_from_cfg", lambda _cfg: object())
    monkeypatch.setattr("datanorma.sources.sheets._load_via_gspread_oauth", _boom)

    src = GoogleSheetsSource(
        paths,
        source_config={
            "spreadsheet_id": "sheet-live",
            "worksheet": "0",
            "oauth_refresh_token": "refresh-demo",
        },
    )
    result = src.check()

    assert result.ok is False
    assert "403" in result.message or "Forbidden" in result.message


def test_check_rejects_demo_csv_without_live_config(tmp_path: Path) -> None:
    sample = tmp_path / "data" / "samples"
    sample.mkdir(parents=True)
    (sample / "google_sheet_export.csv").write_text(
        "order_id,amount\n1,10\n2,20\n",
        encoding="utf-8",
    )
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = GoogleSheetsSource(paths, source_config={})
    result = src.check()

    assert result.ok is False
    assert "демо" in result.message.lower() or "CSV" in result.message
