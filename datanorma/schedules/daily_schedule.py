import dagster as dg

daily_job = dg.define_asset_job(
    "daily_refresh",
    description="Ежедневная материализация всех assets",
    selection=dg.AssetSelection.all(),
)

daily_schedule = dg.ScheduleDefinition(
    name="daily_moscow",
    job=daily_job,
    cron_schedule="0 5 * * *",
    execution_timezone="Europe/Moscow",
)
