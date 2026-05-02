"""Загрузка справочников из PostgreSQL (кэш на URL движка)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

_status_map_cache: dict[str, dict[tuple[str, str, str], str]] = {}
_country_codes_cache: dict[str, set[str]] = {}
_unit_codes_cache: dict[str, set[str]] = {}
_currency_codes_cache: dict[str, set[str]] = {}


def _cache_key(engine: Engine) -> str:
    return str(engine.url)


def load_dim_status_map(engine: Engine) -> dict[tuple[str, str, str], str]:
    """Ключ: (dimension, source_system, raw_status_lower) -> canonical_code."""
    key = _cache_key(engine)
    if key in _status_map_cache:
        return _status_map_cache[key]
    out: dict[tuple[str, str, str], str] = {}
    with engine.connect() as conn:
        try:
            rows = conn.execute(
                text(
                    "SELECT dimension, source_system, raw_status, canonical_code FROM dim_status_map"
                )
            ).mappings().all()
        except Exception:
            _status_map_cache[key] = out
            return out
        for r in rows:
            raw = str(r["raw_status"] or "").strip().lower()
            out[(str(r["dimension"]), str(r["source_system"]), raw)] = str(r["canonical_code"])
    _status_map_cache[key] = out
    return out


def load_country_codes(engine: Engine) -> set[str]:
    key = _cache_key(engine)
    if key in _country_codes_cache:
        return _country_codes_cache[key]
    codes: set[str] = set()
    with engine.connect() as conn:
        try:
            for (c,) in conn.execute(text("SELECT code FROM dim_country")):
                codes.add(str(c).upper())
        except Exception:
            pass
    _country_codes_cache[key] = codes
    return codes


def load_unit_codes(engine: Engine) -> set[str]:
    key = _cache_key(engine)
    if key in _unit_codes_cache:
        return _unit_codes_cache[key]
    codes: set[str] = set()
    with engine.connect() as conn:
        try:
            for (c,) in conn.execute(text("SELECT code FROM dim_unit")):
                codes.add(str(c).lower())
        except Exception:
            pass
    _unit_codes_cache[key] = codes
    return codes


def load_currency_codes(engine: Engine) -> set[str]:
    key = _cache_key(engine)
    if key in _currency_codes_cache:
        return _currency_codes_cache[key]
    codes: set[str] = set()
    with engine.connect() as conn:
        try:
            for (c,) in conn.execute(text("SELECT code FROM dim_currency")):
                codes.add(str(c).upper())
        except Exception:
            pass
    _currency_codes_cache[key] = codes
    return codes


def normalize_country_code(raw: str | None, valid: set[str]) -> tuple[str | None, dict[str, Any] | None]:
    if raw is None or str(raw).strip() == "":
        return None, None
    code = str(raw).strip().upper()[:2]
    if code in valid:
        return code, {"field": "country_code", "action": "country_normalized", "from": raw, "to": code}
    return None, {"field": "country_code", "action": "country_unknown", "from": raw, "to": None}
