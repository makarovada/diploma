from dagster import ConfigurableResource
from pydantic import Field
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from datanorma.config import DEFAULT_DATABASE_URL, get_settings


def _connection_url_default() -> str:
    return get_settings().database_url


# Обратная совместимость для скриптов/тестов, импортирующих константу.
_DEFAULT_LOCAL_URL = DEFAULT_DATABASE_URL


class PostgresResource(ConfigurableResource):
    """Целевая БД (PostgreSQL). Переопределение: переменная окружения DATABASE_URL."""

    connection_url: str = Field(
        default_factory=_connection_url_default,
        description="SQLAlchemy URL, например postgresql+psycopg://user:pass@host:5432/db",
    )

    def get_engine(self) -> Engine:
        return create_engine(self.connection_url, pool_pre_ping=True)
