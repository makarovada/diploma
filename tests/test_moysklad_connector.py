from __future__ import annotations

from unittest.mock import patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def test_check_without_token_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("moysklad", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = {"rows": [{"meta": {"href": "x", "type": "organization"}}], "meta": {"size": 1}}
    with patch("datanorma.sources.moysklad.request_json", return_value=(200, body)):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        res = src.check()
    assert res.ok is True


def test_discover_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    row = {"id": "a", "updated": "2026-05-01 12:00:00", "name": "t"}

    def _get(method, url, **kwargs):
        return 200, {"rows": [row], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        catalog = src.discover()
        assert {s.name for s in catalog.streams} >= {"demand", "customerorder", "product", "counterparty"}


def test_read_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    row = {"id": "a", "updated": "2026-05-01 12:00:00"}

    def _get(method, url, **kwargs):
        return 200, {"rows": [row], "meta": {"size": 1}}

    with patch("datanorma.sources.moysklad.request_json", side_effect=_get):
        src = create_source("moysklad", paths=paths, source_config={"token": "tok"})
        rows = list(src.read("demand", sync_mode="full_refresh"))
        assert len(rows) >= 1
