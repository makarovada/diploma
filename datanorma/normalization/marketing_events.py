"""Маппинг потоков Яндекс Метрики (и родственных источников) в canonical_marketing_events_v1."""

from __future__ import annotations

from typing import Any

from datanorma.normalization.to_canonical import _coerce_amount, _parse_datetime, load_source_mappings


def load_marketing_section(mappings: dict[str, Any] | None = None) -> dict[str, Any]:
    m = mappings or load_source_mappings(with_db_override=False)
    sec = m.get("marketing")
    return sec if isinstance(sec, dict) else {}


def _record_id_from_spec(spec: Any, row: dict[str, Any], counter_id: str) -> str:
    if not isinstance(spec, list):
        return ""
    parts: list[str] = []
    for item in spec:
        if not isinstance(item, str):
            continue
        if item.startswith("literal:"):
            parts.append(item[len("literal:") :])
        elif item == "counter_id":
            parts.append(str(counter_id or ""))
        else:
            parts.append(str(row.get(item, "") or ""))
    return "|".join(parts)


def _apply_field_map(row: dict[str, Any], field_map: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(field_map, dict):
        return out
    for raw_key, canon_key in field_map.items():
        if not isinstance(canon_key, str):
            continue
        val = row.get(raw_key)
        if val is None or val == "":
            out[canon_key] = None
            continue
        if canon_key == "event_datetime":
            out[canon_key] = _parse_datetime(val)
        elif canon_key == "revenue":
            out[canon_key] = _coerce_amount(val)
        elif canon_key == "currency":
            out[canon_key] = str(val).strip().upper()
        else:
            out[canon_key] = val
    return out


def _copy_to_meta(row: dict[str, Any], spec: dict[str, Any] | None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if not isinstance(spec, dict):
        return meta
    for raw_key, meta_key in spec.items():
        if raw_key in row and row[raw_key] is not None:
            mk = meta_key if isinstance(meta_key, str) else raw_key
            meta[mk] = row[raw_key]
    return meta


def build_canonical_marketing_event_rows(
    raw_by_stream: dict[str, list[dict[str, Any]]],
    *,
    counter_id: str,
    source_key: str = "yandex_metrika",
    mappings: dict[str, Any] | None = None,
    batch_loaded_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Собирает плоский список канонических строк по YAML `marketing.sources`."""
    bundle = load_marketing_section(mappings)
    sources = bundle.get("sources") or {}
    src_cfg = sources.get(source_key) or {}
    if not isinstance(src_cfg, dict):
        src_cfg = {}
    streams_cfg = src_cfg.get("streams") or {}
    source_system = str(src_cfg.get("source_system") or source_key)

    out_rows: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "canonical": bundle.get("canonical"),
        "source": source_key,
        "per_stream": {},
    }

    for stream_name, rows in raw_by_stream.items():
        cfg = streams_cfg.get(stream_name)
        if not isinstance(cfg, dict):
            stats["per_stream"][stream_name] = {"skipped": True, "reason": "no_yaml_stream"}
            continue
        if not rows:
            stats["per_stream"][stream_name] = {"rows": 0}
            continue
        event_type = str(cfg.get("event_type") or stream_name)
        rid_spec = cfg.get("source_record_id")
        field_map = cfg.get("field_map") or {}
        meta_spec = cfg.get("copy_to_meta") or {}

        for row in rows:
            base = _apply_field_map(row, field_map)
            meta = _copy_to_meta(row, meta_spec if isinstance(meta_spec, dict) else {})
            rec_id = _record_id_from_spec(rid_spec, row, counter_id)
            canon: dict[str, Any] = {
                "source_system": source_system,
                "source_record_id": rec_id,
                "counter_id": str(counter_id) if counter_id else None,
                "event_type": event_type,
                "event_datetime": base.get("event_datetime"),
                "client_id": base.get("client_id"),
                "visit_id": base.get("visit_id"),
                "traffic_source": base.get("traffic_source"),
                "utm_source": base.get("utm_source"),
                "utm_medium": base.get("utm_medium"),
                "utm_campaign": base.get("utm_campaign"),
                "device": base.get("device"),
                "browser": base.get("browser"),
                "region": base.get("region"),
                "goal_id": None if base.get("goal_id") is None else str(base.get("goal_id")),
                "goal_name": base.get("goal_name"),
                "revenue": base.get("revenue"),
                "currency": base.get("currency"),
                "_ingest_loaded_at": batch_loaded_at,
                "_ingest_meta": meta,
            }
            out_rows.append(canon)
        stats["per_stream"][stream_name] = {"rows": len(rows)}

    stats["rows_out"] = len(out_rows)
    return out_rows, stats
