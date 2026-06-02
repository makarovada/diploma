from __future__ import annotations

from unittest.mock import patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def _embedded(stream: str, rows: list):
    return {"_embedded": {stream: rows}, "_links": {}}


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
        if "/leads" in url:
            return 200, _embedded("leads", [{"id": 1, "updated_at": 1700000000}])
        if "/contacts" in url:
            return 200, _embedded("contacts", [{"id": 2, "updated_at": 1700000000}])
        if "/companies" in url:
            return 200, _embedded("companies", [{"id": 3, "updated_at": 1700000000}])
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
