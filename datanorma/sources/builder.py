"""Low-code REST-коннектор из YAML (Connector Builder): auth, pagination, discover по sample-запросу."""

from __future__ import annotations

import os
from typing import Any, Iterator, Literal

import httpx
import yaml
from pydantic import BaseModel, Field

from datanorma.core.ingest_protocol import IngestCatalog, SyncMode
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
    token: str = ""
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


def _auth_secret(cfg: AuthConfig) -> str:
    secret = (cfg.token or "").strip()
    if cfg.env_var:
        secret = os.environ.get(cfg.env_var, "").strip() or secret
    return secret


def _auth_headers(cfg: AuthConfig) -> dict[str, str]:
    if cfg.type == "none":
        return {}
    secret = _auth_secret(cfg)
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


def _yaml_text_from_source(cfg: dict[str, Any] | None, yaml_text: str | None) -> str | None:
    if yaml_text and str(yaml_text).strip():
        return str(yaml_text).strip()
    if not isinstance(cfg, dict):
        return None
    for key in ("yaml_body", "connector_builder_yaml"):
        val = cfg.get(key)
        if val and str(val).strip():
            return str(val).strip()
    return None


def _structured_stream_from_dict(raw: dict[str, Any]) -> StreamSpec:
    pag_raw = raw.get("pagination") if isinstance(raw.get("pagination"), dict) else {}
    pag_type = str(raw.get("pagination_type") or pag_raw.get("type") or "none").strip().lower()
    if pag_type not in ("none", "offset"):
        pag_type = "none"
    records_path = raw.get("records_json_path")
    if records_path is not None and str(records_path).strip() == "":
        records_path = None
    body = raw.get("body")
    return StreamSpec(
        name=str(raw.get("name") or "").strip(),
        path=str(raw.get("path") or "").strip(),
        method=str(raw.get("method") or "GET").upper(),  # type: ignore[arg-type]
        records_json_path=str(records_path).strip() if records_path else None,
        body=body if isinstance(body, dict) else None,
        pagination=PaginationConfig(
            type=pag_type,  # type: ignore[arg-type]
            limit_param=str(raw.get("limit_param") or pag_raw.get("limit_param") or "limit"),
            offset_param=str(raw.get("offset_param") or pag_raw.get("offset_param") or "offset"),
            limit=int(raw.get("limit") or pag_raw.get("limit") or 50),
            max_pages=int(raw.get("max_pages") or pag_raw.get("max_pages") or 20),
        ),
    )


def _structured_config_from_source(cfg: dict[str, Any]) -> RestConnectorYaml:
    base_url = str(cfg.get("base_url") or "").strip()
    if not base_url:
        raise ValueError("rest_builder: укажите base_url или yaml_body")
    streams_raw = cfg.get("streams")
    if not isinstance(streams_raw, list) or not streams_raw:
        raise ValueError("rest_builder: укажите непустой список streams или yaml_body")
    streams: list[StreamSpec] = []
    for item in streams_raw:
        if not isinstance(item, dict):
            continue
        st = _structured_stream_from_dict(item)
        if st.name and st.path:
            streams.append(st)
    if not streams:
        raise ValueError("rest_builder: в streams нет валидных endpoint (name + path)")

    auth_raw = cfg.get("auth") if isinstance(cfg.get("auth"), dict) else {}
    auth_type = str(cfg.get("auth_type") or auth_raw.get("type") or "none").strip().lower()
    if auth_type not in ("none", "bearer", "api_key_header"):
        auth_type = "none"
    auth_token = str(cfg.get("auth_token") or auth_raw.get("token") or "").strip()
    auth_header = str(cfg.get("auth_header_name") or auth_raw.get("header_name") or "Authorization").strip()
    token_prefix = str(cfg.get("token_prefix") or auth_raw.get("token_prefix") or "Bearer ").strip()

    openapi_url = cfg.get("openapi_url") or auth_raw.get("openapi_url")
    openapi_str = str(openapi_url).strip() if openapi_url else None
    if openapi_str == "":
        openapi_str = None

    timeout_raw = cfg.get("timeout_seconds", 60.0)
    try:
        timeout_seconds = float(timeout_raw)
    except (TypeError, ValueError):
        timeout_seconds = 60.0

    return RestConnectorYaml(
        version=1,
        base_url=base_url.rstrip("/"),
        auth=AuthConfig(
            type=auth_type,  # type: ignore[arg-type]
            header_name=auth_header or "Authorization",
            token=auth_token,
            token_prefix=token_prefix or "Bearer ",
            env_var=str(auth_raw.get("env_var") or "").strip(),
        ),
        timeout_seconds=timeout_seconds,
        openapi_url=openapi_str,
        streams=streams,
    )


def rest_builder_config_valid(cfg: dict[str, Any] | None, yaml_text: str | None = None) -> bool:
    try:
        rest_builder_config_from_source(cfg, yaml_text)
        return True
    except ValueError:
        return False


def rest_builder_config_from_source(
    cfg: dict[str, Any] | None,
    yaml_text: str | None = None,
) -> RestConnectorYaml:
    text = _yaml_text_from_source(cfg, yaml_text)
    if text:
        return load_rest_connector_yaml(text)
    if not isinstance(cfg, dict):
        raise ValueError("rest_builder: нужен config с yaml_body или structured fields (base_url + streams)")
    return _structured_config_from_source(cfg)


def rest_builder_config_to_yaml(cfg: RestConnectorYaml) -> str:
    payload: dict[str, Any] = {
        "version": cfg.version,
        "base_url": cfg.base_url,
        "auth": {
            "type": cfg.auth.type,
            "header_name": cfg.auth.header_name,
            "token_prefix": cfg.auth.token_prefix,
        },
        "timeout_seconds": cfg.timeout_seconds,
        "streams": [],
    }
    if cfg.auth.token:
        payload["auth"]["token"] = cfg.auth.token
    if cfg.auth.env_var:
        payload["auth"]["env_var"] = cfg.auth.env_var
    if cfg.openapi_url:
        payload["openapi_url"] = cfg.openapi_url
    for st in cfg.streams:
        stream_payload: dict[str, Any] = {
            "name": st.name,
            "path": st.path,
            "method": st.method,
            "pagination": {
                "type": st.pagination.type,
                "limit_param": st.pagination.limit_param,
                "offset_param": st.pagination.offset_param,
                "limit": st.pagination.limit,
                "max_pages": st.pagination.max_pages,
            },
        }
        if st.records_json_path:
            stream_payload["records_json_path"] = st.records_json_path
        if st.body:
            stream_payload["body"] = st.body
        payload["streams"].append(stream_payload)
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def probe_rest_builder_stream(
    cfg: RestConnectorYaml,
    *,
    stream_index: int = 0,
    sample_limit: int = 5,
) -> dict[str, Any]:
    if not cfg.streams:
        return {"ok": False, "status_code": None, "message": "Нет streams", "sample_records": [], "record_count": 0}
    if stream_index < 0 or stream_index >= len(cfg.streams):
        return {
            "ok": False,
            "status_code": None,
            "message": f"stream_index {stream_index} вне диапазона",
            "sample_records": [],
            "record_count": 0,
        }
    st = cfg.streams[stream_index]
    headers = _auth_headers(cfg.auth)
    url = cfg.base_url.rstrip("/") + "/" + st.path.lstrip("/")
    try:
        with httpx.Client(timeout=cfg.timeout_seconds) as client:
            if st.method == "GET":
                params: dict[str, Any] = {}
                if st.pagination.type == "offset":
                    params[st.pagination.limit_param] = min(st.pagination.limit, 20)
                    params[st.pagination.offset_param] = 0
                resp = client.request(st.method, url, headers=headers, params=params or None)
            else:
                resp = client.request(st.method, url, headers=headers, json=st.body or {})
        ok = resp.status_code < 500
        records: list[dict[str, Any]] = []
        schema_hint: dict[str, Any] = {}
        if resp.status_code < 400:
            try:
                body = resp.json()
                records = _extract_records(body, st.records_json_path)
                schema_hint = records_to_json_schema(records[:sample_limit])
            except Exception:
                records = []
        sample = records[:sample_limit]
        return {
            "ok": ok and resp.status_code < 400,
            "status_code": resp.status_code,
            "message": f"HTTP {resp.status_code} для stream «{st.name}»",
            "sample_records": sample,
            "record_count": len(records),
            "schema_hint": schema_hint,
            "stream": st.name,
            "url": url,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "message": str(exc),
            "sample_records": [],
            "record_count": 0,
            "schema_hint": {},
            "stream": st.name,
            "url": url,
        }


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


def openapi_to_ingest_json_schema(schema_node: dict[str, Any] | None) -> dict[str, Any]:
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

    def discover(self) -> IngestCatalog:
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
                        json_schema = openapi_to_ingest_json_schema(js)  # type: ignore[assignment]

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
                    self.ingest_stream(
                        st.name,
                        json_schema,
                        sync_modes=(SyncMode.full_refresh, SyncMode.incremental),
                        default_cursor_field=None,
                        source_defined_cursor=False,
                    )
                )
        return IngestCatalog(streams=streams_out)

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
