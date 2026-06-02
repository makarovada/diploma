"""Чтение полей из сохранённого JSON-конфига источника (мастер подключений).

Значения из UI имеют приоритет над переменными окружения / дефолтами процесса."""

from __future__ import annotations

from typing import Any


def cfg_str(cfg: dict[str, Any] | None, key: str, fallback: str = "") -> str:
    if not cfg:
        return fallback
    v = cfg.get(key)
    if v is None:
        return fallback
    s = str(v).strip()
    return s if s else fallback


def cfg_int(cfg: dict[str, Any] | None, key: str, fallback: int) -> int:
    if not cfg:
        return fallback
    v = cfg.get(key)
    if v is None:
        return fallback
    if isinstance(v, bool):
        return fallback
    try:
        return int(v)
    except (TypeError, ValueError):
        return fallback
