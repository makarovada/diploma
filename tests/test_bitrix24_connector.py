from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "bitrix24"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _deal_row():
    return {"ID": "1", "DATE_MODIFY": "2026-05-01T10:00:00+03:00", "TITLE": "D1"}


def _src(tmp_path):
    paths = DataPathsResource(repo_root=str(tmp_path))
    return create_source(
        "bitrix24",
        paths=paths,
        source_config={"webhook_url": "https://example.bitrix24.ru/rest/1/xxx/"},
    )


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


def test_check_accepts_profile_json_webhook_url(tmp_path) -> None:
    def _post(method, url, **kwargs):
        assert "crm.deal.list" in url
        assert "/profile.json/" not in url
        return 200, {"result": [_deal_row()]}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        src = create_source(
            "bitrix24",
            paths=DataPathsResource(repo_root=str(tmp_path)),
            source_config={
                "webhook_url": "https://example.bitrix24.ru/rest/1/xxx/profile.json",
            },
        )
        res = src.check()
    assert res.ok is True


def test_normalize_bitrix24_webhook_url() -> None:
    from datanorma.sources.bitrix24 import normalize_bitrix24_webhook_url

    assert normalize_bitrix24_webhook_url("https://x.bitrix24.ru/rest/1/abc/") == "https://x.bitrix24.ru/rest/1/abc"
    assert (
        normalize_bitrix24_webhook_url("https://x.bitrix24.ru/rest/1/abc/profile.json")
        == "https://x.bitrix24.ru/rest/1/abc"
    )


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


def test_discover_six_streams(tmp_path) -> None:
    def _post(method, url, **kwargs):
        return 200, {"result": [_deal_row()]}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        catalog = _src(tmp_path).discover()
        names = {s.name for s in catalog.streams}
    assert names == {
        "crm_deals",
        "crm_contacts",
        "crm_leads",
        "crm_companies",
        "crm_tasks",
        "crm_activities",
    }


def test_read_leads_paginated(tmp_path) -> None:
    page1 = _load_fixture("leads_page1.json")
    page2 = _load_fixture("leads_page2.json")

    def _post(method, url, *, json_body=None, **kwargs):
        start = (json_body or {}).get("start", 0)
        return (200, page1) if start == 0 else (200, page2)

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        rows = list(_src(tmp_path).read("crm_leads", sync_mode="full_refresh"))
    assert len(rows) == 3


def test_read_incremental_filter_applied(tmp_path) -> None:
    captured: dict = {}

    def _post(method, url, *, json_body=None, **kwargs):
        captured.clear()
        captured.update(json_body or {})
        return 200, {"result": []}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        list(_src(tmp_path).read("crm_deals", sync_mode="incremental", last_cursor="2026-01-15T00:00:00+03:00"))
    assert ">DATE_MODIFY" in (captured.get("filter") or {})


def test_read_tasks_extracts_result_dict(tmp_path) -> None:
    def _post(method, url, **kwargs):
        if "tasks.task.list" in url:
            return 200, {"result": {"tasks": [{"id": "1", "title": "T1", "changedDate": "2026-01-16T09:00:00+03:00"}]}}
        return 200, {"result": []}

    with patch("datanorma.sources.bitrix24.request_json", side_effect=_post):
        rows = list(_src(tmp_path).read("crm_tasks", sync_mode="full_refresh"))
    assert len(rows) == 1
    assert rows[0]["title"] == "T1"
