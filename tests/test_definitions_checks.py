"""Smoke: Definitions содержит asset checks."""

from __future__ import annotations

import pytest
from datanorma.definitions import defs

pytestmark = pytest.mark.unit


def test_definitions_loads_asset_checks() -> None:
    checks = list(defs.asset_checks or [])
    assert len(checks) >= 2
