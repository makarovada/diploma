"""Универсальные коннекторы (фаза 2): BaseSource + встроенные источники + REST YAML builder."""

from datanorma.sources.base import BaseSource, SourceCheckResult
from datanorma.sources.builder import RestBuilderSource, RestConnectorYaml, load_rest_connector_yaml
from datanorma.sources.onec import OneCSource
from datanorma.sources.ozon import OzonSource
from datanorma.sources.registry import SOURCE_KINDS, create_source
from datanorma.sources.sheets import GoogleSheetsSource

__all__ = [
    "SOURCE_KINDS",
    "BaseSource",
    "GoogleSheetsSource",
    "OneCSource",
    "OzonSource",
    "RestBuilderSource",
    "RestConnectorYaml",
    "SourceCheckResult",
    "create_source",
    "load_rest_connector_yaml",
]
