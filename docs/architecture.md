# Архитектура DataNorma

## Контекст

DataNorma — платформа интеграции и нормализации данных для МСП. Продуктовый контур построен по модели **ELT** (Airbyte-like):

- **источник** (`source`) — внешняя система или файл;
- **приёмник** (`destination`) — куда пишутся данные после извлечения и нормализации;
- **подключение** (`connection`) — связка source → destination с правилами колонок, расписанием и состоянием синка.

Нормализация выполняется per-stream правилами (`StreamRules` / `ColumnRule`) на этапе синка; бизнес-смысл задаётся маппингом колонок в мастере подключения.

## Структура кода (модульный монолит)

Один репозиторий, один Python-пакет `datanorma`, один Docker-образ. Разделение по модулям, не по микросервисам:

| Модуль | Назначение |
|--------|------------|
| `datanorma/web/` | FastAPI: REST API, JWT/RBAC, workspaces, UI (`/ui/`) |
| `datanorma/sources/` | Коннекторы источников (`check` / `discover` / `read`) |
| `datanorma/destinations/` | Приёмники (`check` / `write`) |
| `datanorma/elt/` | Прогон connection: source → destination, sync_state |
| `datanorma/normalization/` | Правила колонок, `cast_row`, issues |
| `datanorma/warehouse/` | Состояние синка (`sync_state`), служебные репозитории |
| `datanorma/schedules/` | Cron по подключениям, scheduler в FastAPI |
| `client/` | React/Vite SPA |
| `alembic/` | Миграции метаданных приложения |

## Источники (внешние)

Контракт каждого source connector: `check` → `discover` → `read(stream_name, sync_mode, cursor…)`.

| Код | Система | Layout в мастере | Примечание |
|-----|---------|------------------|------------|
| `google_sheet` | Google Sheets | **flat** | одна таблица полей |
| `bitrix24` | Bitrix24 CRM | **entities** | сделки, контакты, лиды, … |
| `moysklad` | МойСклад | **entities** | заказы, товары, остатки, … |
| `amocrm` | amoCRM | **entities** | сделки, контакты, компании, … |
| `yandex_metrika` | Яндекс Метрика | **entities** | визиты, hits, цели, … |

Реализации: `datanorma/sources/`. Фикстуры для тестов — `data/fixtures/<connector>/`.

Коннекторы **Ozon**, **1C** и **Wildberries** в каталоге и мастере создания source **не предлагаются**: нет тестового стенда для проверки соединения (`check`).

## Приёмники (destinations)

Приёмник — целевая система записи данных connection. Контракт: `check(config)` и `write(stream, records, schema, mode, config)`.

| Код | Тип | Назначение |
|-----|-----|------------|
| `postgres` | **Внешняя PostgreSQL** | основной сценарий: БД заказчика / аналитическое хранилище |
| `clickhouse` | ClickHouse (HTTP) | колоночное хранилище |
| `csv` | CSV-файл | выгрузка на диск (path в config) |
| `xlsx` | Excel-файл | выгрузка на диск |

Реализации: `datanorma/destinations/`.

### Две роли PostgreSQL

1. **Внутренняя БД приложения** (`DATABASE_URL`) — метаданные: users, workspaces, sources, destinations, connections, sync_runs, normalization_issue, sync_state.
2. **Внешний приёмник `postgres`** — отдельный инстанс; URL задаётся в config destination (`url`, `schema`, `table`, `primary_key`). Синк connection пишет туда через `PostgresDestination`.

Для продуктового использования **рекомендуется явно указывать внешний URL** приёмника, а не полагаться на fallback к `DATABASE_URL`.

## Основной поток (ELT connection)

1. **extract** — `source.read` для каждого включённого stream connection.
2. **normalize** — `cast_row` по `connection_column_rule` / stream rules (типы, телефон, email, ИНН, даты МСК и т.д.); ошибки → `normalization_issue`.
3. **load** — `destination_write` в выбранный приёмник (append, upsert, full_refresh, replace_table).
4. **state** — обновление `sync_state` / cursor per connection+stream.
5. **complete** — статус `sync_run`, audit, issues в UI.

Оркестрация: `run_connection_sync` в процессе FastAPI. Расписания — `connection_cron_runner` + scheduler в FastAPI.

## Компоненты инфраструктуры

- **API и UI:** FastAPI (`datanorma/web/`), React SPA (`client/`), раздача сборки под `/ui/`.
- **Метаданные:** PostgreSQL + Alembic.
- **Деплой:** Docker / docker-compose / Helm.

## Мастер подключения (UX)

Пользователь настраивает **колонки и типы**, а не «потоки» Airbyte:

- **flat**-источники (Google Sheets): одна схема, таблица полей без выбора сущности.
- **entities**-источники (Bitrix24, amoCRM, МойСклад, Яндекс Метрика): чекбоксы сущностей + колонка «Сущность» в маппинге.
- `sync_mode` / `cursor_field` задаются автоматически из `connector_schema_meta` и не показываются в мастере.
- Правила сохраняются в `connection.wizard_meta`, `connection_stream_rules`, `connection_column_rule`; синк применяет `cast_row` при наличии правил.

Внутренний контракт коннекторов (`discover` / `read` по `stream_name`) сохранён для совместимости.

## Схема метаданных (внутренняя PostgreSQL)

Актуальная логическая модель после миграций Alembic (`017_normalization_issue_status`). Описаны только таблицы, которые использует продуктовый ELT-контур. **Не включены** устаревшие артефакты Phase A: `canonical_sales`, `typed_canonical_sales`, `canonical_marketing_events`, фиксированные `raw_*_staging`, старая форма `normalization_issue` (batch/source_system), `integration_config`, `pipeline_run_summary`, справочники `dim_*`.

Миграции: `alembic/versions/`. Динамические таблицы данных (слои `raw` / `normalized` / `semantic`) — в [`docs/data_layers.md`](data_layers.md).

### ER-диаграмма (метаданные)

```mermaid
erDiagram
    organization ||--o{ workspace : contains
    app_user ||--o{ user_workspace : member
    workspace ||--o{ user_workspace : has
    app_user ||--o{ workspace_member_permission : grants
    workspace ||--o{ workspace_member_permission : scopes
    permission ||--o{ workspace_member_permission : defines
    workspace ||--o{ resource_grant : scopes
    app_user ||--o{ resource_grant : grantee

    workspace ||--o{ source : owns
    workspace ||--o{ destination : owns
    workspace ||--o{ connection : owns
    source ||--o{ connection : feeds
    destination ||--o{ connection : receives

    connection ||--o{ connection_stream : configures
    connection ||--o{ connection_stream_rules : rules
    connection_stream_rules ||--o{ connection_column_rule : columns
    connection_stream ||--|| sync_state : state
    connection ||--o{ sync_run : runs
    sync_run ||--o{ sync_run_log : logs
    sync_run ||--o{ normalization_issue : issues

    workspace ||--o{ mapping_profile : owns
    mapping_profile ||--o{ mapping_profile_version : versions
    mapping_profile_version o|--o| mapping_profile : active_version

    workspace ||--o{ audit_log : audits
    app_user ||--o{ audit_log : actor
```

### Тенант и доступ

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `organization` | Организация-владелец | `id`, `code` (UK), `name` |
| `workspace` | Изолированное пространство данных | `id`, `organization_id` → `organization`, `code` (глобально UK), `name`, `created_by_user_id` → `app_user` |
| `app_user` | Учётная запись | `id`, `username` (UK), `password_hash`, `email`, `is_active`, `created_at` |
| `user_workspace` | Членство пользователя в workspace | PK (`user_id`, `workspace_id`), `is_admin` |
| `permission` | Каталог прав (seed) | `code` (PK), `description_ru`, `category` |
| `workspace_member_permission` | Права участника в workspace | PK (`workspace_id`, `user_id`, `permission_code`) |
| `resource_grant` | Точечный доступ к source/destination/connection | `workspace_id`, `resource_type`, `resource_id`, `grantee_user_id`, `level` (`read` / `manage`) |

Глобальные роли `role` / `user_role` в БД могут оставаться для `platform_admin`, но **авторизация ELT-ресурсов** опирается на `workspace_member_permission` и `resource_grant`.

### ELT-контур

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `source` | Подключённый источник | `workspace_id`, `connector_code`, `config_encrypted` (JSON), `status`, `created_by_user_id`, `last_checked_at` |
| `destination` | Приёмник записи | те же поля, что у `source` |
| `connection` | Связка source → destination | `source_id`, `destination_id`, `schedule_cron`, `timezone`, `is_active`, `wizard_meta` (JSONB), `created_by_user_id` |
| `connection_stream` | Включённый поток в подключении | UK (`connection_id`, `stream_name`); `sync_mode`, `destination_sync_mode`, `cursor_field`, `primary_key`, `is_enabled`, `cursor_value`, `mapping_profile_id` |

### Правила нормализации (мастер подключения)

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `connection_stream_rules` | Правила потока для `cast_row` | UK (`connection_id`, `stream_name`); `sync_mode`, `cursor_field`, `primary_key` (JSONB), `drop_unknown_columns`, `deduplicate`, `enabled` |
| `connection_column_rule` | Правило колонки | UK (`stream_rules_id`, `target_field`); `source_field`, `type`, `nullable`, `required`, `params`, `on_error`, `sort_order` |
| `normalized_table_meta` | Реестр эволюции normalized-таблиц | UK (`connection_id`, `stream_name`); `schema_name`, `table_name`, `columns` (JSONB), `last_evolved_at` |

### Синхронизация и состояние

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `sync_state` | Курсор и ingest-state **на поток** | UK по `connection_stream_id` (актуальный путь); `integration_code`, `stream_name`, `sync_mode`, `cursor_field`, `cursor_value`, `ingest_state` (JSONB), `workspace_id`, `last_success_at` |
| `sync_run` | Запуск синка connection | `domain_connection_id` → `connection`, `workspace_id`, `status` (`queued` / `running` / `success` / `failed` / `cancelled`), `dagster_run_id`, `triggered_by`, `meta` (JSONB) |
| `sync_run_log` | Пошаговые логи прогона | `sync_run_id`, `stage`, `level`, `message`, `technical_details`, `record_ref` |
| `normalization_issue` | Ошибки `cast_row` за прогон | `sync_run_id`, `connection_id`, `stream_name`, `target_field`, `error_code`, `error_text`, `raw_value`; `status` (`open` / `resolved` / `ignored`), `resolved_at`, `resolved_by`, `resolution_note` |

### Профили маппинга (опционально)

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `mapping_profile` | Именованный профиль правил | UK (`workspace_id`, `source_type`, `stream_name`, `profile_name`); `active_version_id`, `is_active` |
| `mapping_profile_version` | Версия профиля | UK (`profile_id`, `version`); `status` (`draft` / `published` / `archived`), `rules_json` |

`connection_stream.mapping_profile_id` ссылается на профиль; в мастере подключения основной путь — `connection_stream_rules` + `connection_column_rule`.

### Аудит

| Таблица | Назначение |
|---------|------------|
| `audit_log` | Действия с security-следом: `workspace_id`, `actor_user_id`, `action`, `resource_type`, `resource_id`, `result`, `payload_json`, `ip_address`, `created_at` |

### Данные синка (вне метаданных)

Сами строки бизнес-данных **не хранятся** в таблицах выше. Запись идёт в выбранный приёмник:

- **Внешний `postgres` / `clickhouse`** — схема и таблица из `destination.config` (`schema`, `table`, `primary_key`).
- **Файлы `csv` / `xlsx`** — путь из config.

При использовании внутреннего warehouse-контура таблицы создаются динамически: `normalized.<connector_code>__<stream_name>` (колонки из `connection_column_rule` + технические `_ingest_*`, `_source_record_id`, опционально `_raw`). См. `datanorma/warehouse/tables.py`.

## Связанные документы

- `docs/connectors.md` — контракт коннекторов и каталог.
- `docs/backend.md` — модули backend.
- `docs/frontend.md` — UI и мастер подключения.
