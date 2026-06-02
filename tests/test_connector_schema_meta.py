"""Unit tests for connector schema metadata."""

from __future__ import annotations

import pytest

from datanorma.web.connector_schema_meta import connector_schema_layout, connector_schema_meta

pytestmark = pytest.mark.unit


def test_flat_connectors() -> None:
    assert connector_schema_layout("google_sheet") == "flat"
    assert connector_schema_layout("ozon") == "flat"
    meta = connector_schema_meta("google_sheet")
    assert meta["layout"] == "flat"
    assert len(meta["stream_defaults"]) == 1


def test_entity_connectors() -> None:
    meta = connector_schema_meta("wildberries")
    assert meta["layout"] == "entities"
    assert "orders" in meta["entity_labels"]
    assert len(meta["stream_defaults"]) == 3


def test_single_discovered_stream_is_flat() -> None:
    assert connector_schema_layout("rest_builder", discovered_stream_count=1) == "flat"
