from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from datanorma.core.ingest_protocol import SyncMode
from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "amocrm"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _embedded(stream: str, rows: list):
    return {"_embedded": {stream: rows}, "_links": {}}


def _src(tmp_path):
    paths = DataPathsResource(repo_root=str(tmp_path))
    return create_source(
        "amocrm",
        paths=paths,
        source_config={"base_url": "https://test.amocrm.ru", "token": "tok"},
    )


def test_check_without_creds_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("amocrm", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = _embedded("leads", [{"id": 1, "updated_at": 1700000000}])
    with patch("datanorma.sources.amocrm.request_json", return_value=(200, body)):
        src = create_source(
            "amocrm",
            paths=paths,
            source_config={"base_url": "https://test.amocrm.ru", "token": "tok"},
        )
        res = src.check()
    assert res.ok is True


def test_discover_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _get(method, url, **kwargs):
        if "/leads/pipelines" in url:
            return 200, _embedded("pipelines", [{"id": 9, "name": "Воронка"}])
        if "/leads" in url:
            return 200, _embedded("leads", [{"id": 1, "updated_at": 1700000000}])
        if "/contacts" in url:
            return 200, _embedded("contacts", [{"id": 2, "updated_at": 1700000000}])
        if "/companies" in url:
            return 200, _embedded("companies", [{"id": 3, "updated_at": 1700000000}])
        if "/tasks" in url:
            return 200, _embedded("tasks", [{"id": 4, "complete_till": 1700000000}])
        raise AssertionError(url)

    with patch("datanorma.sources.amocrm.request_json", side_effect=_get):
        src = create_source(
            "amocrm",
            paths=paths,
            source_config={"base_url": "https://test.amocrm.ru", "token": "tok"},
        )
        catalog = src.discover()
        assert {s.name for s in catalog.streams} >= {"leads", "contacts", "companies"}


def test_read_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = _embedded("leads", [{"id": 1, "updated_at": 1700000000}])
    with patch("datanorma.sources.amocrm.request_json", return_value=(200, body)):
        src = create_source(
            "amocrm",
            paths=paths,
            source_config={"base_url": "https://test.amocrm.ru", "token": "tok"},
        )
        rows = list(src.read("leads", sync_mode="full_refresh"))
        assert len(rows) >= 1


def test_discover_five_streams(tmp_path) -> None:
    def _get(method, url, **kwargs):
        if "/leads/pipelines" in url:
            return 200, _embedded("pipelines", [{"id": 9, "name": "Воронка"}])
        if "/leads" in url:
            return 200, _embedded("leads", [{"id": 1, "updated_at": 1700000000}])
        if "/contacts" in url:
            return 200, _embedded("contacts", [{"id": 2, "updated_at": 1700000000}])
        if "/companies" in url:
            return 200, _embedded("companies", [{"id": 3, "updated_at": 1700000000}])
        if "/tasks" in url:
            return 200, _embedded("tasks", [{"id": 4, "complete_till": 1700000000}])
        raise AssertionError(url)

    with patch("datanorma.sources.amocrm.request_json", side_effect=_get):
        catalog = _src(tmp_path).discover()
        names = {s.name for s in catalog.streams}
    assert names == {"leads", "contacts", "companies", "tasks", "pipelines"}


def test_pagination_follows_next_link(tmp_path) -> None:
    page1 = _load_fixture("leads_page1.json")
    page2 = _load_fixture("leads_page2.json")

    def _get(method, url, *, params=None, **kwargs):
        page = (params or {}).get("page", 1)
        return (200, page1) if page == 1 else (200, page2)

    with patch("datanorma.sources.amocrm.request_json", side_effect=_get):
        rows = list(_src(tmp_path).read("leads", sync_mode="full_refresh"))
    assert len(rows) == 3
    first = rows[0]
    assert "_links" not in first
    assert "_embedded" not in first
    assert first["tags"] == "vip,повтор"
    assert first["contact_ids"] == [101, 102]
    assert first["updated_at_iso"].startswith("2025-01")


def test_read_leads_incremental(tmp_path) -> None:
    page1 = _load_fixture("leads_page1.json")
    page2 = _load_fixture("leads_page2.json")

    def _get(method, url, *, params=None, **kwargs):
        page = (params or {}).get("page", 1)
        return (200, page1) if page == 1 else (200, page2)

    with patch("datanorma.sources.amocrm.request_json", side_effect=_get):
        rows = list(_src(tmp_path).read("leads", sync_mode="incremental", last_cursor="1736848800"))
    ids = {r["id"] for r in rows}
    assert ids == {2, 3}


def test_normalize_contacts_custom_fields(tmp_path) -> None:
    body = _load_fixture("contacts_page1.json")
    with patch("datanorma.sources.amocrm.request_json", return_value=(200, body)):
        rows = list(_src(tmp_path).read("contacts", sync_mode="full_refresh"))
    assert rows[0]["cf_phone"] == "+79991234567"
    assert rows[0]["cf_email"] == "ivan@example.com"
    assert "_links" not in rows[0]


def test_pipelines_full_refresh_only(tmp_path) -> None:
    def _get(method, url, **kwargs):
        if "/leads/pipelines" in url:
            return 200, _embedded("pipelines", [{"id": 9, "name": "Воронка", "_links": {"self": {"href": "x"}}}])
        if "/tasks" in url:
            return 200, _embedded("tasks", [{"id": 4, "complete_till": 1700000000}])
        return 200, _embedded("leads", [{"id": 1, "updated_at": 1700000000}])

    with patch("datanorma.sources.amocrm.request_json", side_effect=_get):
        src = _src(tmp_path)
        catalog = src.discover()
        pipelines = next(s for s in catalog.streams if s.name == "pipelines")
        assert SyncMode.full_refresh in pipelines.supported_sync_modes
        assert SyncMode.incremental not in pipelines.supported_sync_modes
        rows = list(src.read("pipelines", sync_mode="incremental", last_cursor="123"))
    assert rows and "_links" not in rows[0]
