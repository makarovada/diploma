# Backend

## Состав

| Модуль | Назначение |
|--------|------------|
| `datanorma/web/` | FastAPI: REST API, JWT/RBAC, workspaces, раздача SPA (`/ui/`) |
| `datanorma/sources/` | Коннекторы источников (`check` / `discover` / `read`) |
| `datanorma/destinations/` | Приёмники (`check` / `write`) |
| `datanorma/elt/` | Прогон connection: source → normalize → destination; `sync_mode_policy` |
| `datanorma/normalization/` | `ColumnRule`, `StreamRules`, `cast_row`, issues |
| `datanorma/warehouse/` | `sync_state`, raw staging, динамические normalized-таблицы |
| `datanorma/ingest/` | Конфиг потоков, cursor filter, список Dagster warehouse streams |
| `datanorma/core/` | Модели Ingest Protocol (`SyncMode`, `DestinationSyncMode`, …) |
| `datanorma/http/` | HTTP-клиент для REST-коннекторов (Bitrix24, REST Builder, …) |
| `datanorma/integrations/` | Google OAuth для Sheets |
| `datanorma/resources/` | Dagster resources (`PostgresResource`, `DataPathsResource`) |
| `datanorma/schedules/` | Cron по подключениям (`connection_cron_runner`, `connection_scheduler`) |
| `datanorma/assets/` | Dagster assets (raw → normalized → dbt) |
| `datanorma/checks/` | Dagster asset checks (data quality) |

Ключевые файлы web-слоя:

| Файл | Назначение |
|------|------------|
| `api_router.py` | Auth, sync runs, issues, layers, dbt, legacy `/api/data/*` |
| `api_elt.py` | CRUD sources / destinations / connections, inline trigger |
| `api_v1_catalog.py` | Каталог коннекторов, issues, schedules, preview-rules |
| `elt_repo.py` | Репозиторий ELT-сущностей, сохранение stream rules |
| `connector_schema_meta.py` | Layout мастера, дефолты `sync_mode` / `destination_sync_mode` |
| `sync_launch.py` | Inline sync vs Dagster launch |
| `sync_runs.py` | Жизненный цикл `sync_run`, cancel, retry |
| `connection_scheduler.py` | Фоновый cron в процессе FastAPI |

## Роли backend

- **API** для React UI и интеграционных операций (`/api/v1/*`).
- **Оркестрация синков** inline в процессе FastAPI: `run_connection_sync` + фоновый планировщик `connection_scheduler` (вкл. по умолчанию, откл. `DATANORMA_CONNECTION_SCHEDULER=0`).
- **Нормализация** при синке: `cast_row` по правилам из `connection_stream_rules` / `connection_column_rule`; ошибки → `normalization_issue`.
- **Режимы репликации**: пара `sync_mode` + `destination_sync_mode` в `connection_stream` → `resolve_write_mode` → `destination.write`.
- **RBAC** по workspace: `workspace_member_permission`, `resource_grant` (`view` / `edit` / `manage`).
- **Метаданные** в PostgreSQL (`DATABASE_URL`); бизнес-данные — в выбранном destination.

## Продуктовый поток (ELT connection)

1. `POST /api/v1/connections/{id}/trigger` или cron → создаётся `sync_run`.
2. Для каждого включённого stream: `source.read` → `cast_row` → `destination.write` (режим из `destination_sync_mode`).
3. Обновляется `sync_state` per `connection_stream` (курсор в `ingest_state`).
4. Статус и логи — в `sync_run` / `sync_run_log`; issues — в UI `/issues`.
5. Между потоками поддерживается отмена: `POST /api/v1/syncs/{id}/cancel`.

Inline-синк **не** запускает dbt автоматически. Слой `semantic.*` строится отдельно (`dbt run` или Dagster asset `dbt_run`).

## Dagster (опционально)

`dagster dev -m datanorma.definitions` — демо-контур: assets `sync_catalog`, `raw_google_sheet_orders`, `raw_bitrix24_crm_deals`, `staging_postgres`, `normalized_orders`, `dbt_run`; sensor `connection_cron_sensor` (дублирует cron при отсутствии FastAPI scheduler) и `failed_sync_alert_sensor`. Для продуктовой эксплуатации достаточно `python -m datanorma.web`.

## Связанные документы

- [`architecture.md`](architecture.md) — схема метаданных и поток данных.
- [`api.md`](api.md) — карта endpoints.
- [`normalization_rules.md`](normalization_rules.md) — правила колонок.
