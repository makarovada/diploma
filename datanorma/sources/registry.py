"""Фабрика коннекторов по типу (UI / тесты / будущий generic asset)."""

from __future__ import annotations

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource
from datanorma.sources.builder import RestBuilderSource, load_rest_connector_yaml
from datanorma.sources.onec import OneCSource
from datanorma.sources.ozon import OzonSource
from datanorma.sources.sheets import GoogleSheetsSource

SOURCE_KINDS: tuple[str, ...] = ("ozon", "1c", "google_sheet", "rest_builder")


def create_source(
    kind: str,
    *,
    paths: DataPathsResource | None = None,
    yaml_text: str | None = None,
) -> BaseSource:
    k = kind.strip().lower().replace("-", "_")
    if k in ("ozon",):
        if paths is None:
            raise ValueError("Для ozon нужен paths: DataPathsResource")
        return OzonSource(paths)
    if k in ("1c", "onec", "1с"):
        if paths is None:
            raise ValueError("Для 1c нужен paths: DataPathsResource")
        return OneCSource(paths)
    if k in ("google_sheet", "sheets", "google_sheets", "sheet"):
        if paths is None:
            raise ValueError("Для google_sheet нужен paths: DataPathsResource")
        return GoogleSheetsSource(paths)
    if k in ("rest", "rest_builder", "builder", "yaml_rest"):
        if not (yaml_text and yaml_text.strip()):
            raise ValueError("Для rest_builder нужен yaml_text (Connector Builder YAML)")
        cfg = load_rest_connector_yaml(yaml_text)
        return RestBuilderSource(cfg)
    raise ValueError(f"Неизвестный тип источника: {kind!r}. Допустимо: {SOURCE_KINDS}")
