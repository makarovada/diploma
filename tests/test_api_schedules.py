from __future__ import annotations

from datetime import datetime, timezone

from fastapi.routing import APIRoute

from datanorma.schedules.connection_cron_runner import next_scheduled_run_utc
from datanorma.web import api_v1_catalog as catalog_mod
from datanorma.web.main import create_app

import pytest

pytestmark = pytest.mark.unit


def test_schedules_routes_registered() -> None:
    app = create_app()
    paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    assert "/api/v1/schedules" in paths


def test_next_scheduled_run_utc_daily() -> None:
    pytest.importorskip("croniter")
    now = datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc)
    nxt = next_scheduled_run_utc("0 8 * * *", "UTC", now_utc=now)
    assert nxt is not None
    assert nxt.hour == 8
    assert nxt.minute == 0


def test_list_connection_schedules_imported() -> None:
    assert hasattr(catalog_mod, "list_connection_schedules")

