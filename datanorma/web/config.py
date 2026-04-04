"""Настройки веб-слоя."""

from __future__ import annotations

import os

from datanorma.resources.database import _DEFAULT_LOCAL_URL  # noqa: SLF001


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip() or _DEFAULT_LOCAL_URL


def jwt_secret() -> str:
    s = os.environ.get("DATANORMA_JWT_SECRET", "").strip()
    if not s:
        return "dev-insecure-change-me"
    return s


def jwt_expire_hours() -> int:
    return int(os.environ.get("DATANORMA_JWT_EXPIRE_HOURS", "24"))


def dagster_console_url() -> str:
    return os.environ.get("DATANORMA_DAGSTER_UI_URL", "http://127.0.0.1:3000").strip()
