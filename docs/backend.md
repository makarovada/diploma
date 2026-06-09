# Backend

## Состав

| Модуль | Назначение |
|--------|------------|
| `datanorma/web/` | FastAPI: REST API, JWT/RBAC, workspaces, раздача SPA (`/ui/`) |
| `datanorma/sources/` | Коннекторы источников (`check` / `discover` / `read`) |
| `datanorma/destinations/` | Приёмники (`check` / `write`) |
| `datanorma/elt/` | Прогон connection: source → normalize → destination |
| `datanorma/normalization/` | `ColumnRule`, `StreamRules`, `cast_row`, issues |
| `datanorma/warehouse/` | `sync_state`, динамические normalized-таблицы |
| `datanorma/schedules/` | Cron по подключениям (`connection_cron_runner`) |
| `datanorma/assets/` | Dagster assets (демо-контур, dbt) |

## Роли backend

- **API** для React UI и интеграционных операций (`/api/v1/*`).
- **Оркестрация синков** inline в процессе FastAPI: `run_connection_sync` + фоновый планировщик `connection_scheduler` (вкл. по умолчанию, откл. `DATANORMA_CONNECTION_SCHEDULER=0`).
- **Нормализация** при синке: `cast_row` по правилам из `connection_stream_rules` / `connection_column_rule`; ошибки → `normalization_issue`.
- **RBAC** по workspace: `workspace_member_permission`, `resource_grant`.
- **Метаданные** в PostgreSQL (`DATABASE_URL`); бизнес-данные — в выбранном destination.

## Продуктовый поток (ELT connection)

1. `POST /api/v1/connections/{id}/trigger` или cron → создаётся `sync_run`.
2. Для каждого включённого stream: `source.read` → `cast_row` → `destination.write`.
3. Обновляется `sync_state` (cursor per connection+stream).
4. Статус и логи — в `sync_run` / `sync_run_log`; issues — в UI `/issues`.

Inline-синк **не** запускает dbt автоматически. Слой `semantic.*` строится отдельно (`dbt run` или Dagster asset `dbt_run`).

## Dagster (опционально)

`dagster dev -m datanorma.definitions` — демо-контур для материализации assets, sensor `connection_cron_sensor` (дублирует cron при отсутствии FastAPI scheduler) и `dbt_run`. Для продуктовой эксплуатации достаточно `python -m datanorma.web`.

## Связанные документы

- [`architecture.md`](architecture.md) — схема метаданных и поток данных.
- [`api.md`](api.md) — карта endpoints.
- [`normalization_rules.md`](normalization_rules.md) — правила колонок.
