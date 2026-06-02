from __future__ import annotations

from unittest.mock import patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def _deal_row():
    return {"ID": "1", "DATE_MODIFY": "2026-05-01T10:00:00+03:00", "TITLE": "D1"}


def test_check_without_webhook_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("bitrix24", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _post(method, url, **kwargs):
        assert "crm.deal.list" in url
        return 200, {"result": [_deal_row()]}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        src = create_source(
            "bitrix24",
            paths=paths,
            source_config={"webhook_url": "https://example.bitrix24.ru/rest/1/xxx/"},
        )
        res = src.check()
    assert res.ok is True


def test_discover_sample_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _post(method, url, **kwargs):
        return 200, {"result": [_deal_row()]}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        src = create_source(
            "bitrix24",
            paths=paths,
            source_config={"webhook_url": "https://example.bitrix24.ru/rest/1/xxx/"},
        )
        catalog = src.discover()
        names = {s.name for s in catalog.streams}
        assert names >= {"crm_deals", "crm_contacts", "crm_leads", "crm_companies"}


def test_read_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _post(method, url, **kwargs):
        return 200, {"result": [_deal_row()]}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        src = create_source(
            "bitrix24",
            paths=paths,
            source_config={"webhook_url": "https://example.bitrix24.ru/rest/1/xxx/"},
        )
        rows = list(src.read("crm_deals"))
        assert len(rows) >= 1
