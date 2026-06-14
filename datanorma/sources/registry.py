"""Фабрика коннекторов по типу (UI / тесты / будущий generic asset)."""

from __future__ import annotations

from typing import Any

from datanorma.resources.paths import DataPathsResource
from datanorma.sources.base import BaseSource
from datanorma.sources.builder import RestBuilderSource, rest_builder_config_from_source
from datanorma.sources.amocrm import AmoCRMSource
from datanorma.sources.bitrix24 import Bitrix24Source
from datanorma.sources.moysklad import MoysKladSource
from datanorma.sources.sheets import GoogleSheetsSource
from datanorma.sources.yandex_metrika import YandexMetrikaSource

SOURCE_KINDS: tuple[str, ...] = (
    "google_sheet",
    "bitrix24",
    "amocrm",
    "moysklad",
    "rest_builder",
    "yandex_metrika",
)


def create_source(
    kind: str,
    *,
    paths: DataPathsResource | None = None,
    yaml_text: str | None = None,
    source_config: dict[str, Any] | None = None,
) -> BaseSource:
    k = kind.strip().lower().replace("-", "_")
    if k in ("bitrix24", "bx24"):
        if paths is None:
            raise ValueError("Для bitrix24 нужен paths: DataPathsResource")
        return Bitrix24Source(paths, source_config=source_config)
    if k in ("amocrm",):
        if paths is None:
            raise ValueError("Для amocrm нужен paths: DataPathsResource")
        return AmoCRMSource(paths, source_config=source_config)
    if k in ("moysklad",):
        if paths is None:
            raise ValueError("Для moysklad нужен paths: DataPathsResource")
        return MoysKladSource(paths, source_config=source_config)
    if k in ("google_sheet", "sheets", "google_sheets", "sheet"):
        if paths is None:
            raise ValueError("Для google_sheet нужен paths: DataPathsResource")
        return GoogleSheetsSource(paths, source_config=source_config)
    if k in ("rest", "rest_builder", "builder", "yaml_rest"):
        cfg = rest_builder_config_from_source(source_config or {}, yaml_text)
        return RestBuilderSource(cfg)
    if k in ("yandex_metrika", "yandexmetrika", "metrika", "ya_metrika"):
        if paths is None:
            raise ValueError("Для yandex_metrika нужен paths: DataPathsResource")
        return YandexMetrikaSource(paths, source_config=source_config)
    raise ValueError(f"Неизвестный тип источника: {kind!r}. Допустимо: {SOURCE_KINDS}")
