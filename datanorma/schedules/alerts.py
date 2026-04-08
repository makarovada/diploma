"""Dagster sensors: failed-run alerting via SMS webhook."""

from __future__ import annotations

from datetime import datetime, timezone

import dagster as dg
import httpx
from sqlalchemy import create_engine, text

from datanorma.config import get_settings


@dg.sensor(name="failed_sync_alert_sensor", minimum_interval_seconds=60)
def failed_sync_alert_sensor(context: dg.SensorEvaluationContext):
    settings = get_settings()
    webhook = settings.datanorma_sms_webhook_url.strip()
    token = settings.datanorma_sms_webhook_token.strip()
    if not webhook:
        return dg.SkipReason("DATANORMA_SMS_WEBHOOK_URL is not set")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, job_name, status, started_at, finished_at FROM pipeline_run_summary "
                "WHERE status = 'failed' ORDER BY id DESC LIMIT 1"
            )
        ).mappings().first()
    if row is None:
        return dg.SkipReason("No failed runs")

    last_id = int(context.cursor) if (context.cursor or "").isdigit() else 0
    if int(row["id"]) <= last_id:
        return dg.SkipReason("No new failed runs")

    payload = {
        "text": (
            f"[DataNorma] sync failed: id={row['id']}, job={row.get('job_name')}, "
            f"started={row.get('started_at')}, finished={row.get('finished_at')}"
        ),
        "source": "datanorma",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(webhook, json=payload, headers=headers).raise_for_status()
    except Exception as exc:
        return dg.SkipReason(f"Webhook send failed: {exc}")

    context.update_cursor(str(row["id"]))
    return dg.SkipReason(f"Alert sent for failed run id={row['id']}")
