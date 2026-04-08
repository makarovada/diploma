"""Вывод JSON Schema из образцов записей (REST / pandas / dict)."""

from __future__ import annotations

from typing import Any


def _schema_for_scalar(v: Any) -> dict[str, Any]:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "boolean"}
    if isinstance(v, int) and not isinstance(v, bool):
        return {"type": "integer"}
    if isinstance(v, float):
        return {"type": "number"}
    if isinstance(v, str):
        return {"type": "string"}
    return {"type": "string"}


def _merge_types(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    if a == b:
        return a
    ta, tb = a.get("type"), b.get("type")
    if ta == tb and ta == "object":
        ap, bp = a.get("properties") or {}, b.get("properties") or {}
        keys = set(ap) | set(bp)
        props = {k: _merge_types(ap.get(k, {"type": "null"}), bp.get(k, {"type": "null"})) for k in keys}
        return {"type": "object", "properties": props}
    if ta == tb and ta == "array":
        ai = a.get("items") or {"type": "string"}
        bi = b.get("items") or {"type": "string"}
        return {"type": "array", "items": _merge_types(ai, bi)}
    opts = []
    for x in (a, b):
        if x not in opts:
            opts.append(x)
    return {"anyOf": opts}


def value_to_json_schema(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        if not v:
            return {"type": "object", "additionalProperties": True}
        return {"type": "object", "properties": {k: value_to_json_schema(v[k]) for k in sorted(v)}}
    if isinstance(v, list):
        if not v:
            return {"type": "array", "items": {}}
        merged: dict[str, Any] | None = None
        for item in v[:50]:
            s = value_to_json_schema(item)
            merged = s if merged is None else _merge_types(merged, s)
        return {"type": "array", "items": merged or {}}
    return _schema_for_scalar(v)


def records_to_json_schema(records: list[dict[str, Any]], sample_size: int = 50) -> dict[str, Any]:
    if not records:
        return {"type": "object", "properties": {}}
    merged: dict[str, Any] | None = None
    for row in records[:sample_size]:
        s = value_to_json_schema(row)
        merged = s if merged is None else _merge_types(merged, s)
    return merged or {"type": "object", "properties": {}}
