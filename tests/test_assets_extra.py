from __future__ import annotations

from pathlib import Path

import pytest

from datanorma.assets import dbt_asset, sync_catalog

pytestmark = pytest.mark.unit


def test_sync_catalog_builds_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Pg:
        def get_engine(self):
            return object()

    monkeypatch.setattr(
        sync_catalog,
        "parse_all_stream_configs",
        lambda *_: {"google_sheet": {"stream": "orders", "sync_mode": "incremental"}},
    )
    monkeypatch.setattr(sync_catalog, "fetch_sync_state_map", lambda _e: {("google_sheet", "orders"): {"cursor": "10"}})
    monkeypatch.setattr(sync_catalog, "extract_stream_cursor", lambda _r: "10")
    out = sync_catalog.sync_catalog(_Pg())
    assert out["mappings_version"] == "rules_v1"
    assert out["streams"]["google_sheet"]["resume_from_state"] is True


def test_dbt_profile_writer_and_subprocess_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Settings:
        database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/datanorma"

        @staticmethod
        def resolved_dbt_project_dir() -> Path:
            return tmp_path

    (tmp_path / "dbt_project.yml").write_text("name: datanorma\nversion: 1.0\n", encoding="utf-8")
    monkeypatch.setattr(dbt_asset, "get_settings", lambda: _Settings())
    monkeypatch.setattr(dbt_asset, "DbtCliResource", None)

    class _Run:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(dbt_asset.subprocess, "run", lambda *a, **k: _Run())
    res = dbt_asset.dbt_run({"status": "ok"})
    assert res["status"] == "ok"
    assert res["returncode"] == 0

    p = dbt_asset._write_temp_profile(tmp_path)
    assert p.exists()
    assert "profiles.yml" in str(p)
