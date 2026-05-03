"""Настройки веб-слоя."""

from __future__ import annotations

from datanorma.config import get_settings

_DEV_JWT_PLACEHOLDER = "dev-insecure-change-me"


def database_url() -> str:
    return get_settings().database_url


def is_production() -> bool:
    env = get_settings().datanorma_environment.strip().lower()
    return env in ("production", "prod")


def jwt_secret() -> str:
    s = get_settings().datanorma_jwt_secret.strip()
    if is_production():
        return s
    return s or _DEV_JWT_PLACEHOLDER


def jwt_expire_hours() -> int:
    return get_settings().datanorma_jwt_expire_hours


def dagster_console_url() -> str:
    return get_settings().datanorma_dagster_ui_url.strip()


def cors_allow_origins() -> list[str]:
    raw = get_settings().datanorma_cors_origins.strip()
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    if is_production():
        raise RuntimeError(
            "В production задайте DATANORMA_CORS_ORIGINS (список origin через запятую). "
            "Сочетание allow_origins=['*'] и allow_credentials=True запрещено."
        )
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]


def validate_security_at_startup() -> None:
    """Вызывать при создании FastAPI: в production — секрет JWT и явные CORS origin."""
    if not is_production():
        return
    secret = get_settings().datanorma_jwt_secret.strip()
    if not secret:
        raise RuntimeError(
            "В production задайте непустой DATANORMA_JWT_SECRET (переменная окружения)."
        )
    if secret == _DEV_JWT_PLACEHOLDER:
        raise RuntimeError(
            "В production нельзя использовать значение-заглушку для DATANORMA_JWT_SECRET."
        )
    cors_allow_origins()
