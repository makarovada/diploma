"""Централизованные настройки и константы (Pydantic Settings + значения по умолчанию).

Переменные окружения читаются из процесса и при наличии — из файла `.env` в рабочей директории.
См. также `.env.example`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- константы (не из env) ---

OZON_API_BASE: Final[str] = "https://api-seller.ozon.ru"

DEFAULT_DATABASE_URL: Final[str] = (
    "postgresql+psycopg://datanorma:datanorma@127.0.0.1:5433/datanorma"
)


class Settings(BaseSettings):
    """Все пути и флаги из окружения в одном месте."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = Field(default=DEFAULT_DATABASE_URL, description="SQLAlchemy URL PostgreSQL")

    datanorma_repo_root: str = ""
    datanorma_source_mappings_path: str = ""
    datanorma_warehouse_table: str = "normalized"
    datanorma_typed_table: str = "normalized"
    datanorma_auto_create_tables: str = ""
    datanorma_jwt_secret: str = ""
    datanorma_jwt_expire_hours: int = 24
    # development | production — в production обязательны DATANORMA_JWT_SECRET и DATANORMA_CORS_ORIGINS
    datanorma_environment: str = "development"
    # Список origin через запятую (нельзя * при credentials=True)
    datanorma_cors_origins: str = ""
    datanorma_dagster_ui_url: str = "http://127.0.0.1:3000"
    datanorma_sms_webhook_url: str = ""
    datanorma_sms_webhook_token: str = ""

    ozon_client_id: str = ""
    ozon_api_key: str = ""
    ozon_fetch_limit: int = 100

    # --- новые коннекторы (offline demo через fixtures) ---
    wildberries_api_token: str = Field(default="", validation_alias="DATANORMA_WB_API_TOKEN")
    bitrix24_webhook_url: str = Field(default="", validation_alias="DATANORMA_BITRIX24_WEBHOOK_URL")
    amocrm_base_url: str = Field(default="", validation_alias="DATANORMA_AMOCRM_BASE_URL")
    amocrm_token: str = Field(default="", validation_alias="DATANORMA_AMOCRM_TOKEN")
    moysklad_token: str = Field(default="", validation_alias="DATANORMA_MOYSKLAD_TOKEN")

    gspread_service_account_file: str = ""
    gspread_spreadsheet_id: str = ""
    gspread_worksheet: str = "0"

    # Google OAuth (UI): путь к client_secret JSON и redirect URI в Google Cloud Console
    datanorma_google_oauth_client_file: str = Field(
        default="",
        validation_alias="DATANORMA_GOOGLE_OAUTH_CLIENT_FILE",
    )
    datanorma_google_oauth_redirect_uri: str = Field(
        default="",
        validation_alias="DATANORMA_GOOGLE_OAUTH_REDIRECT_URI",
    )
    datanorma_google_oauth_frontend_return_url: str = Field(
        default="",
        validation_alias="DATANORMA_GOOGLE_OAUTH_FRONTEND_RETURN_URL",
    )

    datanorma_1c_export_path: str = ""

    yandex_metrika_oauth_token: str = ""
    yandex_metrika_counter_id: str = ""

    def warehouse_auto_ddl_enabled(self) -> bool:
        v = self.datanorma_auto_create_tables.strip().lower()
        return v in ("1", "true", "yes")

    def resolved_source_mappings_path(self) -> Path:
        p = self.datanorma_source_mappings_path.strip()
        if p:
            return Path(p)
        return Path(__file__).resolve().parent / "schemas" / "source_mappings.yaml"

    def resolved_repo_root(self) -> Path:
        env = self.datanorma_repo_root.strip()
        if env:
            return Path(env)
        return Path(__file__).resolve().parent.parent

    def samples_dir(self) -> Path:
        return self.resolved_repo_root() / "data" / "samples"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Сброс кэша (для тестов)."""
    get_settings.cache_clear()
