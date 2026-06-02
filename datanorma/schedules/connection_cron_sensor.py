"""Периодический запуск доменных connection по полю schedule_cron (Dagster sensor)."""

from __future__ import annotations

import json
import logging

import dagster as dg
from sqlalchemy import create_engine

from datanorma.config import get_settings
from datanorma.schedules.connection_cron_runner import run_due_scheduled_syncs

_log = logging.getLogger(__name__)


@dg.sensor(
    name="connection_cron_sensor",
    minimum_interval_seconds=60,
    default_status=dg.DefaultSensorStatus.RUNNING,
)
def connection_cron_sensor(context: dg.SensorEvaluationContext):
    settings = get_settings()

    cursor_raw = context.cursor or ""
    try:
        fired: dict[str, str] = json.loads(cursor_raw) if cursor_raw.strip() else {}
    except json.JSONDecodeError:
        fired = {}

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    count, errors, fired = run_due_scheduled_syncs(engine, fired=fired)

    if count:
        context.update_cursor(json.dumps(fired, ensure_ascii=False))

    if not count and not errors:
        return dg.SkipReason("No connection cron slots due for this minute")

    if errors:
        return dg.SkipReason("Scheduled runs completed with errors: " + "; ".join(errors[:5]))

    return dg.SkipReason(f"Scheduled ELT sync for {count} connection(s)")
