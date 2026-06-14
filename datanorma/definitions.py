"""Dagster Definitions: assets, checks, schedules, sensors."""

import dagster as dg

from datanorma.assets import (
    dbt_asset,
    normalized,
    raw_bitrix24,
    raw_google_sheet,
    staging_postgres,
    sync_catalog,
    warehouse,
)
from datanorma.checks import data_quality
from datanorma.resources.database import PostgresResource
from datanorma.resources.paths import DataPathsResource
from datanorma.schedules.alerts import failed_sync_alert_sensor
from datanorma.schedules.connection_cron_sensor import connection_cron_sensor
from datanorma.schedules.daily_schedule import daily_job, daily_schedule

all_assets = dg.load_assets_from_modules(
    [sync_catalog, raw_google_sheet, raw_bitrix24, staging_postgres, normalized, warehouse, dbt_asset]
)
all_asset_checks = dg.load_asset_checks_from_modules([data_quality])

defs = dg.Definitions(
    assets=all_assets,
    asset_checks=all_asset_checks,
    resources={
        "postgres": PostgresResource(),
        "paths": DataPathsResource(),
    },
    jobs=[daily_job],
    schedules=[daily_schedule],
    sensors=[failed_sync_alert_sensor, connection_cron_sensor],
)
