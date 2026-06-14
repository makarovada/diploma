"""Фаза 2: BaseSource, registry, schema inference, REST builder (без сети где возможно)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.builder import RestBuilderSource, load_rest_connector_yaml
from datanorma.sources.registry import create_source
from datanorma.sources.schema_inference import records_to_json_schema, value_to_json_schema

pytestmark = pytest.mark.unit


def test_value_to_json_schema_object() -> None:
    s = value_to_json_schema({"a": 1, "b": "x"})
    assert s["type"] == "object"
    assert "properties" in s


def test_records_merge_schema() -> None:
    sch = records_to_json_schema([{"x": 1}, {"x": "2"}])
    assert "anyOf" in sch["properties"]["x"] or sch["properties"]["x"].get("type") in ("integer", "string")


def test_create_yandex_metrika_source_discover(tmp_path: Path) -> None:
    paths = DataPathsResource(repo_root=str(tmp_path))

    def _rq(method, url, *, params=None, **kwargs):
        m = str((params or {}).get("metrics") or "")
        mlist = [x.strip() for x in m.split(",") if x.strip()]
        body = {
            "query": {"dimensions": [{"name": "ym:s:date"}], "metrics": [{"name": n} for n in mlist]},
            "data": [{"dimensions": [{"name": "2026-05-01"}], "metrics": [0] * len(mlist)}],
        }
        return 200, body

    with patch("datanorma.sources.yandex_metrika.request_json", side_effect=_rq):
        src = create_source(
            "yandex_metrika",
            paths=paths,
            source_config={"oauth_token": "t", "counter_id": "1"},
        )
        cat = src.discover()
    assert {s.name for s in cat.streams} == {"summary", "visits", "hits", "goals_reaches"}



def test_rest_builder_load_yaml() -> None:
    yml = """
version: 1
base_url: "https://example.com"
auth:
  type: none
streams:
  - name: s1
    path: /x
    method: GET
"""
    cfg = load_rest_connector_yaml(yml)
    assert cfg.base_url == "https://example.com"
    assert cfg.streams[0].name == "s1"


def test_rest_builder_discover_uses_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    yml = """
version: 1
base_url: "https://example.com"
auth:
  type: none
streams:
  - name: posts
    path: /posts
    method: GET
    records_json_path: ""
"""
    cfg = load_rest_connector_yaml(yml)
    src = RestBuilderSource(cfg)

    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list:
            return [{"id": 1, "title": "a"}]

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = None
    fake_client.request.return_value = FakeResp()

    monkeypatch.setattr("datanorma.sources.builder.httpx.Client", lambda **_: fake_client)
    cat = src.discover()
    assert cat.streams[0].name == "posts"
    props = cat.streams[0].json_schema.get("properties") or {}
    assert "id" in props
