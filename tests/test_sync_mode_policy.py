"""Режимы синхронизации: Airbyte-подобное сопоставление с WriteMode."""

from __future__ import annotations

import pytest

from datanorma.destinations.base import WriteMode
from datanorma.elt.sync_mode_policy import (
    destination_sync_mode_for_legacy,
    effective_source_sync_mode,
    parse_primary_key_field,
    resolve_write_mode,
    validate_stream_sync_config,
)

pytestmark = pytest.mark.unit


def test_legacy_incremental_maps_to_append() -> None:
    assert destination_sync_mode_for_legacy("incremental") == "append"
    assert resolve_write_mode(sync_mode="incremental", destination_sync_mode=None) == WriteMode.append


def test_legacy_full_refresh_overwrite() -> None:
    assert destination_sync_mode_for_legacy("full_refresh") == "refresh_overwrite"
    assert resolve_write_mode(sync_mode="full_refresh", destination_sync_mode=None) == WriteMode.full_refresh


@pytest.mark.parametrize(
    ("dsm", "expected"),
    [
        ("refresh_overwrite", WriteMode.full_refresh),
        ("refresh_append", WriteMode.append),
        ("append", WriteMode.append),
        ("append_dedup", WriteMode.upsert),
        ("overwrite", WriteMode.replace_table),
    ],
)
def test_resolve_write_mode(dsm: str, expected: WriteMode) -> None:
    assert resolve_write_mode(sync_mode="incremental", destination_sync_mode=dsm) == expected


def test_refresh_modes_force_full_refresh_source() -> None:
    assert (
        effective_source_sync_mode(sync_mode="incremental", destination_sync_mode="refresh_overwrite")
        == "full_refresh"
    )


def test_append_dedup_requires_pk() -> None:
    errs = validate_stream_sync_config(
        sync_mode="incremental",
        destination_sync_mode="append_dedup",
        cursor_field="updated_at",
        primary_key=None,
    )
    assert any("первичный ключ" in e.lower() for e in errs)


def test_parse_primary_key_variants() -> None:
    assert parse_primary_key_field("order_id") == ["order_id"]
    assert parse_primary_key_field('["a","b"]') == ["a", "b"]
    assert parse_primary_key_field("a,b") == ["a", "b"]
