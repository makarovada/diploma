from pathlib import Path

from dagster import ConfigurableResource
from pydantic import Field

from datanorma.config import get_settings


def _default_repo_root() -> str:
    return str(get_settings().resolved_repo_root())


class DataPathsResource(ConfigurableResource):
    """Пути к каталогам данных внутри репозитория (samples, при необходимости raw)."""

    repo_root: str = Field(default_factory=_default_repo_root)

    @property
    def samples_dir(self) -> Path:
        return Path(self.repo_root) / "data" / "samples"

    def sample_file(self, *parts: str) -> Path:
        return self.samples_dir.joinpath(*parts)
