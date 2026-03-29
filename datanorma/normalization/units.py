"""Минимальная нормализация единиц измерения (строка → канонический код)."""

from __future__ import annotations

_UNIT_ALIASES: dict[str, str] = {
    "шт": "pcs",
    "штук": "pcs",
    "штука": "pcs",
    "уп": "pack",
    "упак": "pack",
    "кг": "kg",
    "г": "g",
    "гр": "g",
    "л": "l",
    "литр": "l",
    "м": "m",
    "м2": "m2",
    "м3": "m3",
    "час": "hour",
    "ч": "hour",
    "усл. ед": "unit",
    "усл.ед.": "unit",
}


def normalize_unit_label(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower().replace("ё", "е")
    if not s:
        return None
    return _UNIT_ALIASES.get(s, s)
