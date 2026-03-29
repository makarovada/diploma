import os
from pathlib import Path

from dagster import ConfigurableResource
from pydantic import Field


def _default_repo_root() -> str:
    env = os.environ.get("DATANORMA_REPO_ROOT", "").strip()
    if env:
        return env
    # datanorma/resources/paths.py -> parents[2] = корень репозитория при editable install
    return str(Path(__file__).resolve().parents[2])


class DataPathsResource(ConfigurableResource):
    """Пути к каталогам данных внутри репозитория (samples, при необходимости raw)."""

    repo_root: str = Field(default_factory=_default_repo_root)

    @property
    def samples_dir(self) -> Path:
        return Path(self.repo_root) / "data" / "samples"

    def sample_file(self, *parts: str) -> Path:
        return self.samples_dir.joinpath(*parts)
