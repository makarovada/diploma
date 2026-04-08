"""Настройки веб-слоя."""

from __future__ import annotations

from datanorma.config import get_settings


def database_url() -> str:
    return get_settings().database_url


def jwt_secret() -> str:
    s = get_settings().datanorma_jwt_secret.strip()
    return s or "dev-insecure-change-me"


def jwt_expire_hours() -> int:
    return get_settings().datanorma_jwt_expire_hours


def dagster_console_url() -> str:
    return get_settings().datanorma_dagster_ui_url.strip()
