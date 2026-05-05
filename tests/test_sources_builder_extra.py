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
