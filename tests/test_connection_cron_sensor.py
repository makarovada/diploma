"""Unit tests for connection_cron_sensor cron matching."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

pytest.importorskip("croniter")
from datanorma.schedules.connection_cron_runner import (
    cron_fires_at_local_minute as _cron_fires_at_local_minute,
    next_scheduled_run_utc,
)

pytestmark = pytest.mark.unit


def test_cron_every_five_minutes_utc() -> None:
    ref = datetime(2026, 5, 10, 12, 5, tzinfo=timezone.utc)
    assert _cron_fires_at_local_minute("*/5 * * * *", "UTC", ref) is True
    ref2 = datetime(2026, 5, 10, 12, 3, tzinfo=timezone.utc)
    assert _cron_fires_at_local_minute("*/5 * * * *", "UTC", ref2) is False


def test_empty_schedule_never_fires() -> None:
    ref = datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc)
    assert _cron_fires_at_local_minute("", "UTC", ref) is False
    assert _cron_fires_at_local_minute("   ", "UTC", ref) is False


def test_next_scheduled_run_utc_after_now() -> None:
    now = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    nxt = next_scheduled_run_utc("0 8 * * *", "UTC", now_utc=now)
    assert nxt is not None
    assert nxt > now
    assert nxt.hour == 8
