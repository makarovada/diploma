import os

from dagster import ConfigurableResource
from pydantic import Field
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_DEFAULT_LOCAL_URL = (
    "postgresql+psycopg://datanorma:datanorma@127.0.0.1:5433/datanorma"
)


def _connection_url_default() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_LOCAL_URL)


class PostgresResource(ConfigurableResource):
    """Целевая БД (PostgreSQL). Переопределение: переменная окружения DATABASE_URL."""

    connection_url: str = Field(
        default_factory=_connection_url_default,
        description="SQLAlchemy URL, например postgresql+psycopg://user:pass@host:5432/db",
    )

    def get_engine(self) -> Engine:
        return create_engine(self.connection_url, pool_pre_ping=True)
