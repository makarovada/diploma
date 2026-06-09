# Коннектор Яндекс Метрика

## Назначение

Источник `yandex_metrika` (`datanorma/sources/yandex_metrika.py`) реализует `check`, `discover`, `read` для потоков:

- `summary`
- `visits`
- `hits`
- `goals_reaches`

Layout в мастере подключения: **entities** (чекбоксы сущностей).

## Режимы работы

| Режим | Условие | Поведение |
|-------|---------|-----------|
| OAuth | `YANDEX_METRIKA_OAUTH_TOKEN` + `YANDEX_METRIKA_COUNTER_ID` в env или config source | `check` через Management API |
| Fixture | OAuth не задан | чтение из `data/samples/yandex_metrika_*.json` |

Config source (JSON): `oauth_token`, `counter_id`.

## Поток данных

Продуктовый контур — connection sync:

1. `source.read(stream)` — извлечение визитов, hits и т.д.
2. `cast_row(StreamRules)` — типизация по правилам connection.
3. `destination.write` — запись в выбранный приёмник (`postgres`, `csv`, …).

При destination `postgres` данные попадают в `schema.table` из config приёмника.

## dbt-интеграция

Модели в репозитории (читают из `normalized.*` после warehouse-загрузки):

- `dbt/models/marketing/yandex_metrika_visits.sql`
- `dbt/models/marketing/yandex_metrika_goal_reaches.sql`

Просмотр через API: `GET /api/v1/dbt/models`.

dbt запускается отдельно (`dbt run` или Dagster asset `dbt_run`), не в inline sync.

## Smoke-сценарий

См. [testing.md](testing.md) — раздел «Smoke: Яндекс Метрика → PostgreSQL + cron».
