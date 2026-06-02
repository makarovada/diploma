"""Коннектор Яндекс Метрика: моки Management + Reporting API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source

pytestmark = pytest.mark.unit


def _stat_body() -> dict:
    return {
        "query": {
            "dimensions": [{"name": "ym:s:date"}],
            "metrics": [
                {"name": "ym:s:visits"},
                {"name": "ym:s:users"},
                {"name": "ym:s:bounceRate"},
                {"name": "ym:s:pageviews"},
            ],
        },
        "data": [
            {
                "dimensions": [{"name": "2026-05-01"}],
                "metrics": [10, 8, 0.4, 100],
            }
        ],
    }


def test_check_without_creds_fails(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source("yandex_metrika", paths=paths, source_config={})
    res = src.check()
    assert res.ok is False


def test_check_management_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    resp = MagicMock()
    resp.status_code = 200
    with patch("datanorma.sources.yandex_metrika.httpx.Client") as cli:
        cli.return_value.__enter__.return_value.get.return_value = resp
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        res = src.check()
    assert res.ok is True


def _stat_for_metrics(metrics: str) -> dict:
    mlist = [x.strip() for x in metrics.split(",")]
    return {
        "query": {
            "dimensions": [{"name": "ym:s:date"}],
            "metrics": [{"name": n} for n in mlist],
        },
        "data": [
            {
                "dimensions": [{"name": "2026-05-01"}],
                "metrics": list(range(len(mlist))),
            }
        ],
    }


def test_discover_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _rq(method, url, *, params=None, **kwargs):
        assert "stat/v1/data" in url
        m = (params or {}).get("metrics") or ""
        return 200, _stat_for_metrics(str(m))

    with patch("datanorma.sources.yandex_metrika.request_json", side_effect=_rq):
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        cat = src.discover()
        assert {s.name for s in cat.streams} == {"summary", "visits", "hits", "goals_reaches"}


def test_read_summary_mock(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = _stat_body()
    with patch("datanorma.sources.yandex_metrika.request_json", return_value=(200, body)):
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        rows = list(src.read("summary"))
        assert rows and "date" in rows[0]
