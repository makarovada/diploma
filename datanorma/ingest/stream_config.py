"""Утилиты конфигурации stream/sync_mode/cursor_field."""

from __future__ import annotations

from typing import Any, Literal

SyncModeLiteral = Literal["full_refresh", "incremental"]

DEFAULT_STREAMS: dict[str, str] = {
    "google_sheet": "orders",
    "bitrix24": "crm_deals",
}


def stream_name_for_source(source_key: str, src_cfg: dict[str, Any] | None) -> str:
    if src_cfg and src_cfg.get("stream"):
        return str(src_cfg["stream"]).strip() or DEFAULT_STREAMS.get(source_key, "default")
    return DEFAULT_STREAMS.get(source_key, "default")


def sync_mode_for_source(source_key: str, src_cfg: dict[str, Any] | None) -> SyncModeLiteral:
    raw = (src_cfg or {}).get("sync_mode") or "full_refresh"
    s = str(raw).strip().lower()
    if s == "incremental":
        return "incremental"
    return "full_refresh"


def cursor_field_for_source(source_key: str, src_cfg: dict[str, Any] | None) -> str | None:
    v = (src_cfg or {}).get("cursor_field")
    if v is None or str(v).strip() == "":
        return None
    return str(v).strip()


def staging_table_physical_name(integration_code: str, stream: str) -> str:
    """Имя таблицы raw_<source>_<stream>_staging (google_sheet → raw_google_sheet_...)."""
    safe = stream.replace("-", "_")
    return f"raw_{integration_code}_{safe}_staging"


def integration_code_from_yaml_key(key: str) -> str:
    return str(key).strip()


def parse_all_stream_configs(mappings: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Собирает базовую конфигурацию потоков по integration_code."""
    sources = (mappings or {}).get("sources") or {}
    out: dict[str, dict[str, Any]] = {}
    for key, cfg in sources.items():
        if not isinstance(cfg, dict):
            continue
        code = integration_code_from_yaml_key(str(key))
        stream = stream_name_for_source(code, cfg)
        out[code] = {
            "yaml_key": str(key),
            "stream": stream,
            "sync_mode": sync_mode_for_source(code, cfg),
            "cursor_field": cursor_field_for_source(code, cfg),
            "table": staging_table_physical_name(code, stream),
        }
    for code in DEFAULT_STREAMS:
        if code not in out:
            stream = DEFAULT_STREAMS.get(code, "default")
            cursor_field = "DATE_MODIFY" if code == "bitrix24" else None
            out[code] = {
                "yaml_key": code,
                "stream": stream,
                "sync_mode": "incremental" if code == "bitrix24" else "full_refresh",
                "cursor_field": cursor_field,
                "table": staging_table_physical_name(code, stream),
            }
    return out
