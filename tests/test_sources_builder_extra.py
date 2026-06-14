from __future__ import annotations

import pytest

from datanorma.sources.builder import (
    RestBuilderSource,
    _auth_headers,
    _extract_records,
    _get_by_path,
    json_schema_from_openapi_response,
    load_rest_connector_yaml,
    openapi_to_ingest_json_schema,
    probe_rest_builder_stream,
    rest_builder_config_from_source,
    rest_builder_config_valid,
)

pytestmark = pytest.mark.unit


class _Resp:
    def __init__(self, status_code: int = 200, body=None) -> None:
        self.status_code = status_code
        self._body = body if body is not None else {"items": [{"id": 1}]}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


class _Client:
    def __init__(self, *args, **kwargs) -> None:
        self.responses = [
            _Resp(200, {"items": [{"id": 1}, {"id": 2}]}),
            _Resp(200, {"items": [{"id": 3}]}),
            _Resp(200, {"items": []}),
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return _Resp(200, {"openapi": "3.0.0", "paths": {"/orders": {"get": {"responses": {"200": {"content": {"application/json": {"schema": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}}}}}}}}}}}})

    def request(self, method, url, headers=None, params=None, json=None):
        return self.responses.pop(0) if self.responses else _Resp(200, {"items": []})


def test_builder_helper_functions(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _get_by_path({"a": {"b": 1}}, "a.b") == 1
    assert _extract_records({"items": [{"id": 1}]}, None) == [{"id": 1}]
    assert _extract_records({"data": [{"id": 2}]}, "data") == [{"id": 2}]
    monkeypatch.setenv("CONNECTOR_REST_BEARER", "token")
    headers = _auth_headers(load_rest_connector_yaml("base_url: https://x\nstreams: [{name: s, path: /p}]\nauth: {type: bearer}\n").auth)
    assert "Authorization" in headers


def test_openapi_schema_extract() -> None:
    spec = {
        "paths": {
            "/orders": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}}}}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    node = json_schema_from_openapi_response(spec, "/orders", "get")
    assert node is not None
    schema = openapi_to_ingest_json_schema(node)
    assert schema.get("type") == "object"


def test_rest_builder_check_discover_and_read(monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_text = """
version: 1
base_url: https://api.example.com
openapi_url: https://api.example.com/openapi.json
streams:
  - name: orders
    path: /orders
    method: GET
    records_json_path: items
    pagination:
      type: offset
      limit_param: limit
      offset_param: offset
      limit: 2
      max_pages: 3
"""
    cfg = load_rest_connector_yaml(yaml_text)
    monkeypatch.setattr("datanorma.sources.builder.httpx.Client", _Client)
    src = RestBuilderSource(cfg)
    chk = src.check()
    assert chk.ok is True
    cat = src.discover()
    assert {s.name for s in cat.streams} == {"orders"}
    rows = list(src.read("orders", sync_mode="incremental", cursor_field="id", last_cursor="1"))
    assert any(int(r["id"]) > 1 for r in rows)


def test_auth_inline_token() -> None:
    cfg = load_rest_connector_yaml(
        "base_url: https://x\nstreams: [{name: s, path: /p}]\nauth: {type: bearer, token: inline-secret}\n"
    )
    headers = _auth_headers(cfg.auth)
    assert headers.get("Authorization") == "Bearer inline-secret"


def test_rest_builder_config_from_structured() -> None:
    cfg = rest_builder_config_from_source(
        {
            "base_url": "https://api.example.com",
            "auth_type": "api_key_header",
            "auth_token": "key123",
            "auth_header_name": "X-Api-Key",
            "streams": [
                {
                    "name": "posts",
                    "path": "/posts",
                    "method": "GET",
                    "pagination_type": "none",
                }
            ],
        }
    )
    assert cfg.base_url == "https://api.example.com"
    assert cfg.auth.type == "api_key_header"
    assert cfg.auth.token == "key123"
    assert cfg.streams[0].name == "posts"


def test_rest_builder_config_from_yaml_priority() -> None:
    yaml_text = "base_url: https://yaml.example.com\nstreams: [{name: a, path: /a}]\n"
    cfg = rest_builder_config_from_source({"base_url": "https://ignored.com", "streams": []}, yaml_text)
    assert cfg.base_url == "https://yaml.example.com"


def test_rest_builder_config_valid() -> None:
    assert rest_builder_config_valid({"base_url": "https://x.com", "streams": [{"name": "s", "path": "/p"}]})
    assert not rest_builder_config_valid({"base_url": ""})
    assert not rest_builder_config_valid({})


def test_probe_rest_builder_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = load_rest_connector_yaml(
        "base_url: https://api.example.com\nstreams: [{name: posts, path: /posts, records_json_path: ''}]\n"
    )
    monkeypatch.setattr("datanorma.sources.builder.httpx.Client", _Client)
    result = probe_rest_builder_stream(cfg, stream_index=0)
    assert result["ok"] is True
    assert result["status_code"] == 200
    assert len(result["sample_records"]) >= 1
