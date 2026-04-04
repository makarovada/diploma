"""Точка входа Dagster: assets, resources, jobs, schedules."""

import dagster as dg

from datanorma.assets import (
    normalized,
    raw_1c,
    raw_google_sheet,
    raw_ozon,
    staging_postgres,
    warehouse,
)
from datanorma.checks import data_quality
from datanorma.resources.database import PostgresResource
from datanorma.resources.paths import DataPathsResource
from datanorma.schedules.daily_schedule import daily_job, daily_schedule

all_assets = dg.load_assets_from_modules(
    [raw_ozon, raw_1c, raw_google_sheet, staging_postgres, normalized, warehouse]
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
)
