"""Коннектор Яндекс Метрика: моки Management + Reporting API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.registry import create_source
from datanorma.sources.yandex_metrika import _parse_report_rows, _sanitize_key

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "yandex_metrika"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


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


def test_check_fail_403(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    resp = MagicMock()
    resp.status_code = 403
    with patch("datanorma.sources.yandex_metrika.httpx.Client") as cli:
        cli.return_value.__enter__.return_value.get.return_value = resp
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        res = src.check()
    assert res.ok is False
    assert res.details and "date_range" in res.details


def test_read_summary_incremental(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    body = _load_fixture("stat_v1_data_summary.json")
    with patch("datanorma.sources.yandex_metrika.request_json", return_value=(200, body)):
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        rows = list(src.read("summary", sync_mode="incremental", last_cursor="2026-01-15"))
    dates = {r["date"] for r in rows}
    assert dates == {"2026-01-16"}


def test_read_unknown_stream_raises(tmp_path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))
    src = create_source(
        "yandex_metrika",
        paths=paths,
        source_config={"oauth_token": "t", "counter_id": "1"},
    )
    with pytest.raises(ValueError):
        list(src.read("does_not_exist"))


def test_parse_report_rows_empty() -> None:
    assert _parse_report_rows({"query": {}, "data": []}) == []
    assert _parse_report_rows({}) == []


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ym:s:date", "ym_s_date"),
        ("ym:s:bounceRate", "ym_s_bouncerate"),
        ("ym:s:newUsers", "ym_s_newusers"),
        (":::", "dim"),
    ],
)
def test_sanitize_key(raw: str, expected: str) -> None:
    assert _sanitize_key(raw) == expected
