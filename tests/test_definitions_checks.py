"""Smoke: Definitions содержит asset checks."""

from __future__ import annotations

from datanorma.definitions import defs


def test_definitions_loads_asset_checks() -> None:
    checks = list(defs.asset_checks or [])
    assert len(checks) >= 2
