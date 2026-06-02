from __future__ import annotations

from unittest.mock import patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def test_check_without_token_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("wildberries", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_with_token_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    sample = [{"lastChangeDate": "2026-05-01T12:00:00+03:00", "nmId": 1}]
    with patch("datanorma.sources.wildberries.request_json", return_value=(200, sample)):
        src = create_source("wildberries", paths=paths, source_config={"api_token": "t"})
        res = src.check()
    assert res.ok is True


def test_discover_and_read_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    sample = [{"lastChangeDate": "2026-05-01T12:00:00+03:00", "nmId": 1, "supplierArticle": "x"}]

    def _fake(method, url, **kwargs):
        assert "statistics-api.wildberries.ru" in url
        return 200, sample

    with patch("datanorma.sources.wildberries.request_json", side_effect=_fake):
        src = create_source("wildberries", paths=paths, source_config={"api_token": "t"})
        catalog = src.discover()
        assert {s.name for s in catalog.streams} >= {"orders", "sales", "stocks"}
        rows = list(src.read("orders", sync_mode="full_refresh"))
        assert len(rows) >= 1
