"""Маппинг сырых статусов источников в канонические коды через dim_status_map."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from datanorma.normalization.references import load_dim_status_map


def resolve_status(
    engine: Engine | None,
    dimension: str,
    source_system: str,
    raw_status: str | None,
    *,
    cache: dict[tuple[str, str, str], str] | None = None,
) -> str | None:
    if raw_status is None:
        return None
    key = (dimension, str(source_system).strip(), str(raw_status).strip().lower())
    if cache is not None:
        return cache.get(key)
    if engine is None:
        return None
    return load_dim_status_map(engine).get(key)
