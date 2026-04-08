"""Low-code REST-коннектор из YAML (Connector Builder): auth, pagination, discover по sample-запросу."""

from __future__ import annotations

import os
from typing import Any, Iterator, Literal

import httpx
import yaml
from pydantic import BaseModel, Field

from datanorma.core.airbyte_protocol import AirbyteCatalog, SyncMode
from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.schema_inference import records_to_json_schema


def _get_by_path(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _extract_records(body: Any, records_json_path: str | None) -> list[dict[str, Any]]:
    if records_json_path:
        v = _get_by_path(body, records_json_path)
        if v is None:
            return []
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
        return []
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if isinstance(body, dict):
        for key in ("data", "result", "items", "records"):
            v = body.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


class AuthConfig(BaseModel):
    model_config = {"extra": "ignore"}

    type: Literal["none", "bearer", "api_key_header"] = "none"
    header_name: str = "Authorization"
    env_var: str = ""
    token_prefix: str = "Bearer "


class PaginationConfig(BaseModel):
    model_config = {"extra": "ignore"}

    type: Literal["none", "offset"] = "none"
    limit_param: str = "limit"
    offset_param: str = "offset"
    limit: int = Field(default=50, ge=1, le=5000)
    max_pages: int = Field(default=20, ge=1, le=500)


class StreamSpec(BaseModel):
    model_config = {"extra": "ignore"}

    name: str
    path: str
    method: Literal["GET", "POST"] = "GET"
    records_json_path: str | None = None
    body: dict[str, Any] | None = None
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)


class RestConnectorYaml(BaseModel):
    model_config = {"extra": "ignore"}

    version: int = 1
    base_url: str
    auth: AuthConfig = Field(default_factory=AuthConfig)
    timeout_seconds: float = 60.0
    openapi_url: str | None = None
    streams: list[StreamSpec]


def load_rest_connector_yaml(text: str) -> RestConnectorYaml:
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("YAML connector: ожидается объект в корне")
    return RestConnectorYaml.model_validate(raw)


def _auth_headers(cfg: AuthConfig) -> dict[str, str]:
    if cfg.type == "none":
        return {}
    secret = ""
    if cfg.env_var:
        secret = os.environ.get(cfg.env_var, "").strip()
    if cfg.type == "bearer":
        prefix = cfg.token_prefix or "Bearer "
        token = secret or os.environ.get("CONNECTOR_REST_BEARER", "").strip()
        if not token:
            return {}
        return {cfg.header_name: f"{prefix}{token}".strip()}
    if cfg.type == "api_key_header":
        if not secret:
            return {}
        return {cfg.header_name: secret}
    return {}


def _resolve_ref(root: dict[str, Any], node: Any) -> Any:
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        parts = ref[2:].split("/")
        cur: Any = root
        for p in parts:
            if not isinstance(cur, dict):
                return node
            cur = cur.get(p)
        return _resolve_ref(root, cur)
    return node


def json_schema_from_openapi_response(spec: dict[str, Any], path: str, method: str = "get") -> dict[str, Any] | None:
    """Упрощённое извлечение JSON Schema из OpenAPI 3.x (локальные $ref)."""
    paths = spec.get("paths") or {}
    item = paths.get(path) or paths.get(path.rstrip("/")) or paths.get(path + "/")
    if not isinstance(item, dict):
        return None
    op = item.get(method.lower()) or item.get(method.upper())
    if not isinstance(op, dict):
        return None
    responses = op.get("responses") or {}
    r200 = responses.get("200") or responses.get("201")
    if not isinstance(r200, dict):
        return None
    content = r200.get("content") or {}
    for mt in ("application/json", "application/*+json"):
        block = content.get(mt)
        if isinstance(block, dict) and "schema" in block:
            return _resolve_ref(spec, block["schema"])  # type: ignore[return-value]
    if isinstance(content, dict) and content:
        first = next(iter(content.values()))
        if isinstance(first, dict) and "schema" in first:
            return _resolve_ref(spec, first["schema"])  # type: ignore[return-value]
    return None


def openapi_to_airbyte_json_schema(schema_node: dict[str, Any] | None) -> dict[str, Any]:
    if not schema_node or not isinstance(schema_node, dict):
        return {}
    if schema_node.get("type") == "array" and "items" in schema_node:
        items = schema_node.get("items")
        if isinstance(items, dict):
            return items
    return schema_node


class RestBuilderSource(BaseSource):
    """Коннектор из YAML-описания REST API."""

    def __init__(self, cfg: RestConnectorYaml, *, integration_code: str = "rest_builder") -> None:
        self._cfg = cfg
        self.integration_code = integration_code
        self._openapi_spec: dict[str, Any] | None = None
        self._openapi_disabled = False

    def _load_openapi(self) -> dict[str, Any] | None:
        if self._openapi_disabled:
            return None
        if self._openapi_spec is not None:
            return self._openapi_spec
        url = (self._cfg.openapi_url or "").strip()
        if not url:
            self._openapi_disabled = True
            return None
        with httpx.Client(timeout=self._cfg.timeout_seconds) as client:
            r = client.get(url)
            r.raise_for_status()
            data = r.json()
        self._openapi_spec = data if isinstance(data, dict) else {}
        return self._openapi_spec

    def check(self) -> SourceCheckResult:
        if not self._cfg.streams:
            return SourceCheckResult(ok=False, message="В YAML нет streams.", details={})
        st0 = self._cfg.streams[0]
        headers = _auth_headers(self._cfg.auth)
        url = self._cfg.base_url.rstrip("/") + "/" + st0.path.lstrip("/")
        try:
            with httpx.Client(timeout=self._cfg.timeout_seconds) as client:
                if st0.method == "GET":
                    params: dict[str, Any] = {}
                    if st0.pagination.type == "offset":
                        params[st0.pagination.limit_param] = 1
                        params[st0.pagination.offset_param] = 0
                    r = client.request(st0.method, url, headers=headers, params=params or None)
                else:
                    r = client.request(st0.method, url, headers=headers, json=st0.body or {})
            ok = r.status_code < 500
            return SourceCheckResult(
                ok=ok,
                message=f"Проверка stream «{st0.name}»: HTTP {r.status_code}.",
                details={"stream": st0.name, "status": r.status_code},
            )
        except Exception as exc:
            return SourceCheckResult(
                ok=False,
                message=str(exc),
                details={"stream": st0.name, "url": url},
            )

    def discover(self) -> AirbyteCatalog:
        openapi = self._load_openapi()
        streams_out = []
        headers = _auth_headers(self._cfg.auth)
        with httpx.Client(timeout=self._cfg.timeout_seconds) as client:
            for st in self._cfg.streams:
                records: list[dict[str, Any]] = []
                json_schema: dict[str, Any] | None = None
                if openapi:
                    js = json_schema_from_openapi_response(openapi, st.path, st.method.lower())
                    if js:
                        json_schema = openapi_to_airbyte_json_schema(js)  # type: ignore[assignment]

                url = self._cfg.base_url.rstrip("/") + "/" + st.path.lstrip("/")
                try:
                    if st.method == "GET":
                        params = {}
                        if st.pagination.type == "offset":
                            params[st.pagination.limit_param] = min(st.pagination.limit, 20)
                            params[st.pagination.offset_param] = 0
                        resp = client.request(st.method, url, headers=headers, params=params or None)
                    else:
                        resp = client.request(st.method, url, headers=headers, json=st.body or {})
                    resp.raise_for_status()
                    body = resp.json()
                    records = _extract_records(body, st.records_json_path)
                except Exception:
                    records = []

                if json_schema is None or not json_schema:
                    json_schema = records_to_json_schema(records)
                if not json_schema:
                    json_schema = {"type": "object", "properties": {}, "description": "empty sample"}

                streams_out.append(
                    self.airbyte_stream(
                        st.name,
                        json_schema,
                        sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                        default_cursor_field=None,
                        source_defined_cursor=False,
                    )
                )
        return AirbyteCatalog(streams=streams_out)

    def read(
        self,
        stream_name: str,
        *,
        sync_mode: str = "full_refresh",
        cursor_field: str | None = None,
        last_cursor: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        st = next((s for s in self._cfg.streams if s.name == stream_name), None)
        if st is None:
            raise ValueError(f"Unknown stream {stream_name!r}")
        headers = _auth_headers(self._cfg.auth)
        url = self._cfg.base_url.rstrip("/") + "/" + st.path.lstrip("/")
        seen: set[str] = set()
        with httpx.Client(timeout=self._cfg.timeout_seconds) as client:
            if st.pagination.type == "none":
                if st.method == "GET":
                    resp = client.request(st.method, url, headers=headers)
                else:
                    resp = client.request(st.method, url, headers=headers, json=st.body or {})
                resp.raise_for_status()
                body = resp.json()
                for row in _extract_records(body, st.records_json_path):
                    yield row
                return

            offset = 0
            for _page in range(st.pagination.max_pages):
                params = {
                    st.pagination.limit_param: st.pagination.limit,
                    st.pagination.offset_param: offset,
                }
                resp = client.request(st.method, url, headers=headers, params=params)
                resp.raise_for_status()
                body = resp.json()
                chunk = _extract_records(body, st.records_json_path)
                if not chunk:
                    break
                for row in chunk:
                    if cursor_field and last_cursor and sync_mode == "incremental":
                        val = row.get(cursor_field)
                        if val is not None and str(val) <= str(last_cursor):
                            continue
                    key = str(row)
                    if key in seen:
                        continue
                    seen.add(key)
                    yield row
                offset += st.pagination.limit
                if len(chunk) < st.pagination.limit:
                    break
