"""Точка входа Dagster: assets, resources, jobs, schedules."""

import dagster as dg

from datanorma.assets import (
    normalized,
    raw_1c,
    raw_google_sheet,
    raw_ozon,
    warehouse,
)
from datanorma.resources.database import PostgresResource
from datanorma.resources.paths import DataPathsResource
from datanorma.schedules.daily_schedule import daily_job, daily_schedule

all_assets = dg.load_assets_from_modules(
    [raw_ozon, raw_1c, raw_google_sheet, normalized, warehouse]
)

defs = dg.Definitions(
    assets=all_assets,
    resources={
        "postgres": PostgresResource(),
        "paths": DataPathsResource(),
    },
    jobs=[daily_job],
    schedules=[daily_schedule],
)
