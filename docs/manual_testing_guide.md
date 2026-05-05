# DataNorma: руководство по ручному тестированию

Документ описывает единый набор ручных проверок для MVP-платформы DataNorma (аналог Ingest для SMB в РФ).

## 1. Цель документа

- Зафиксировать полный функциональный охват ручного тестирования.
- Дать воспроизводимый сценарий smoke/regression проверки после изменений.
- Синхронизировать терминологию с `README.md` и `docs/comparison_ingest.md`.

## 2. Контекст и границы MVP

DataNorma в текущей версии:
- поддерживает интеграции из `Ozon`, `1C`, `Google Sheets`, `Яндекс Метрика` и `REST Builder`;
- ведет пайплайн `sync_catalog -> raw -> staging -> normalized -> typed -> warehouse -> dbt`;
- использует PostgreSQL как основной destination;
- предоставляет web UI (`/app/*`) и REST API (`/api/*`, `/api/v1/*`);
- использует ролевую модель доступа (RBAC) и JWT.

Ограничения текущего этапа:
- `POST /api/v1/syncs/trigger` запускает реальный run и возвращает `run_id`; для актуального статуса используйте polling `GET /api/v1/syncs/{run_id}/status`;
- редактор маппингов в UI сохраняет версии правил в БД (draft/published/active), YAML используется как fallback/import;
- основной сценарий загрузки ориентирован на PostgreSQL.

## 3. Предварительные условия

1. Установлены зависимости:
   - `pip install -e .`
   - для тестов: `pip install -e ".[dev]"`
2. Поднят PostgreSQL:
   - `docker compose up -d`
3. Применены миграции и seed:
   - `alembic upgrade head`
   - `python scripts/seed_database.py`
4. Запущены сервисы:
   - `python -m datanorma.web`
   - `dagster dev -m datanorma.definitions`

Демо-учетки:
- `seed_admin / AdminDemo2026`
- `seed_integrator / IntegratorDemo2026`
- `seed_analyst / AnalystDemo2026`

## 4. Покрытие по функциональным блокам

### 4.1 Коннекторы и источники

- `OzonSource`: `check/discover/read`, API-режим и fallback на sample.
- `OneCSource`: CSV/XLSX, support `DATANORMA_1C_EXPORT_PATH`.
- `GoogleSheetsSource`: `gspread` + fallback на sample.
- `YandexMetrikaSource`: `check/discover/read`, OAuth + Management API или полный набор `data/samples/yandex_metrika_*.json`.
- `rest_builder`: динамический source по YAML-схеме.
- **Приёмники (Фаза 7):** `datanorma/destinations/*` — `check` и `write` с режимами `append`, `full_refresh`, `upsert`, `replace_table` для `postgres`, `csv`, `xlsx`, `clickhouse`; API `POST /api/v1/destinations/{id}/check` и `POST /api/v1/destinations/{id}/write`.

### 4.2 Оркестрация и pipeline (Dagster)

- `sync_catalog`
- `raw_ozon_postings`
- `raw_1c_orders`
- `raw_google_sheet_orders`
- `staging_raw_postgres`
- `normalized_orders`
- `typed_canonical_sales`
- `warehouse_sales`
- `dbt_run`

### 4.3 Слой хранения и данные

- Raw staging таблицы:
  - `raw_ozon_postings_staging`
  - `raw_1c_orders_staging`
  - `raw_google_sheet_orders_staging`
- Таблица состояния синхронизации: `sync_state`
- Типизированный слой: `typed_canonical_sales`
- Витрина: `canonical_sales`
- Маркетинг / веб-события: `canonical_marketing_events` (Яндекс Метрика и др., см. `docs/yandex_metrika_connector.md`)

### 4.4 Веб и API

- Web UI: `GET/POST /app/*`
- REST API:
  - auth: `/api/auth/*`
  - data/admin/meta/rbac: `/api/*`
  - product-shaped API: `/api/v1/*`

### 4.5 Контроль качества и наблюдаемость

- asset checks:
  - `staging_raw_has_rows`
  - `normalized_orders_has_rows`
  - `warehouse_has_rows`
- расписание: `daily_schedule`
- сенсор: `failed_sync_alert_sensor`

## 5. Основной чеклист ручного тестирования

## 5.1 Готовность платформы

Шаги:
1. Поднять БД, применить миграции и seed.
2. Запустить web и Dagster.
3. Открыть `/app/login`.

Ожидаемо:
- приложения стартуют без критических ошибок;
- страница логина доступна;
- демо-учетки проходят аутентификацию.

## 5.2 Аутентификация и сессия

Шаги:
1. Логин с валидными данными.
2. Выход из системы.
3. Логин с неверным паролем.
4. Проверка `POST /api/auth/login` и `GET /api/auth/me`.

Ожидаемо:
- при валидном логине создается сессия;
- logout очищает сессию;
- неверный пароль дает `401`;
- `/api/auth/me` возвращает пользователя и роли.

## 5.3 Проверка коннектора Ozon

Шаги:
1. В `/app/sources/new` выбрать `ozon`, выполнить check/discover.
2. Запустить raw + staging этапы.
3. Проверить `/app/connections/sample/ozon`.

Ожидаемо:
- check/discover успешны (в API-режиме или fallback);
- в `raw_ozon_postings_staging` есть записи;
- sample-данные отображаются в UI.

## 5.4 Проверка коннектора 1C

Шаги:
1. Проверить режим sample (без `DATANORMA_1C_EXPORT_PATH`).
2. При необходимости указать кастомный файл и перезапустить.
3. Выполнить check/discover.

Ожидаемо:
- источник читается;
- discover возвращает колонки;
- `raw_1c_orders_staging` содержит записи.

## 5.5 Проверка коннектора Google Sheets

Шаги:
1. Проверить fallback без `GSPREAD_*`.
2. (Опционально) проверить режим с сервисным аккаунтом.
3. Выполнить check/discover.

Ожидаемо:
- fallback работает;
- при валидных учетных данных gspread-режим работает;
- `raw_google_sheet_orders_staging` содержит записи.

## 5.6 Проверка REST Builder

Шаги:
1. В `/app/sources/new` выбрать `rest_builder`.
2. Отправить корректный YAML.
3. Отправить некорректный YAML.

Ожидаемо:
- корректный YAML проходит check/discover;
- некорректный YAML дает понятную ошибку.

## 5.7 Проверка incremental/state

Шаги:
1. В `/app/connections` настроить stream:
   - `sync_mode=incremental`
   - `cursor_field`
2. Перезапустить raw/staging.
3. Проверить `/api/data/sync-state`.

Ожидаемо:
- в `sync_state` есть запись с mode/cursor;
- курсор учитывается в следующих запусках;
- `updated_at` обновляется после синка.

## 5.8 Проверка staging persistence

Шаги:
1. Материализовать `staging_raw_postgres`.
2. Проверить staging-таблицы и `sync_state`.
3. Проверить `/api/data/staging-counts`.

Ожидаемо:
- staging-таблицы заполнены;
- `sync_state` содержит метаданные stream;
- API возвращает корректные count-значения.

## 5.9 Проверка нормализации

Шаги:
1. Материализовать `normalized_orders`.
2. Проверить metadata в Dagster.
3. Проверить:
   - MSK-нормализацию дат;
   - поля конвертации валюты;
   - дедуп по source-ключу;
   - нормализацию единиц.

Ожидаемо:
- строки соответствуют канонической форме;
- статистика этапа заполнена;
- отсутствуют аварийные падения на опциональных полях.

## 5.10 Проверка typed слоя

Шаги:
1. Материализовать `typed_canonical_sales`.
2. Проверить статистику типизации и count строк.

Ожидаемо:
- данные приводятся к ожидаемым типам;
- таблица typed слоя заполнена.

## 5.11 Проверка warehouse UPSERT

Шаги:
1. Материализовать `warehouse_sales`.
2. Проверить `/app/warehouse/sales` и `/app/warehouse/export`.
3. Скачать `/app/warehouse/download.csv`.

Ожидаемо:
- `canonical_sales` обновляется через UPSERT;
- данные отображаются в UI;
- CSV выгружается корректно.

## 5.12 Проверка dbt этапа

Шаги:
1. Убедиться, что dbt-проект доступен и зависимости установлены.
2. Материализовать `dbt_run`.

Ожидаемо:
- при успехе статус `ok`;
- при ошибке - `failed` с диагностикой в логах.

## 5.13 Проверка API по ролям

Шаги:
1. Выполнить auth и получить токен.
2. Проверить `api/data`, `api/admin`, `api/v1` для каждой роли.

Ожидаемо:
- разрешенные операции возвращают `2xx`;
- запрещенные операции возвращают `403`;
- невалидная аутентификация возвращает `401`.

## 5.14 Проверка web-страниц по ролям

Шаги:
1. Войти под каждой ролью.
2. Открыть все доступные `/app/*`.
3. Проверить POST-формы:
   - `/app/account/password`
   - `/app/connections`
   - `/app/integrations/secrets`
   - `/app/settings/schedule`
   - `/app/admin/user-roles`
   - `/app/mappings/editor`

Ожидаемо:
- разрешенные страницы открываются корректно;
- недоступные сценарии блокируются (`403`);
- формы меняют состояние там, где предусмотрена персистентность.

## 5.15 Проверка RBAC-матрицы

Шаги:
1. Сверить реальное поведение ролей с `/api/rbac/matrix`.
2. Проверить несколько типовых операций для каждой роли.

Ожидаемо:
- фактический доступ совпадает с матрицей;
- нет повышения привилегий между ролями.

## 5.16 Проверка workspaces (phase 3)

Шаги:
1. Выполнить `POST /api/v1/workspaces` от admin/integrator.
2. Проверить `/app/workspaces` и `/api/v1/workspaces`.
3. Проверить read-only поведение analyst.

Ожидаемо:
- workspace создается/обновляется;
- пользователь привязывается к workspace;
- analyst не получает прав управления.

## 5.17 Проверка мониторинга

Шаги:
1. Выполнить полный pipeline.
2. Проверить asset checks в Dagster.
3. Открыть `/app/runs` и `/app/monitoring/normalization`.

Ожидаемо:
- проверки видны и интерпретируемы;
- история запусков отображается;
- журнал нормализации доступен без ошибок;
- на `/app/monitoring/normalization` видна вторая секция — агрегаты исправлений typed-слоя (`action` / `field` из `_ingest_meta.changes`);
- `GET /api/data/normalization-fix-stats?limit=50` возвращает JSON с полем `rows` (после материализации `typed_canonical_sales` возможны ненулевые счётчики).

## 6. Рекомендуемый smoke-набор после изменений

1. Логин под `seed_admin`.
2. В `/app/sources/new` выполнить check/discover для `ozon`, `1c`, `google_sheet`, `rest_builder`.
3. В Dagster последовательно материализовать:
   - `sync_catalog`
   - raw assets
   - `staging_raw_postgres`
   - `normalized_orders`
   - `typed_canonical_sales`
   - `warehouse_sales`
   - `dbt_run` (если используется)
4. Проверить:
   - `/api/data/staging-counts`
   - `/api/data/sales-summary`
   - `/api/data/normalization-fix-stats`
   - `/app/warehouse/sales`
   - `/app/warehouse/download.csv`
   - `/app/monitoring/normalization` (issues + агрегаты fixes)
5. Проверить RBAC:
   - integrator не имеет admin-доступа;
   - analyst не может изменять конфигурации.

Критерии успешности:
- нет необработанных ошибок в web/API/pipeline;
- staging и warehouse содержат данные;
- RBAC работает согласно матрице;
- экспорт и preview доступны.

## 7. Связанные документы

- Карта проекта и runbook: `README.md`
- Сравнение с Ingest: `docs/comparison_ingest.md`
- Маршруты web UI: `docs/phase_c_routes.md`
- Текст для ВКР по RBAC: `docs/vkr_rbac_text.md`
# DataNorma: manual testing guide and full functionality list

Business context (aligned with `README.md`):
- DataNorma is an Ingest-like data integration and normalization service for SMB teams in Russia.
- The current version is an MVP with production-style building blocks: connectors, staged ingestion, canonical modeling, warehouse load, web/API layer, and RBAC.

This document contains:
- full current functionality list;
- step-by-step manual test instructions for each functional block;
- integration-focused checks and expected results.

## 1) Scope and assumptions

The guide covers:
- ingestion integrations (`Ozon`, `1C`, `Google Sheets`, `REST Connector Builder`);
- ETL/ELT pipeline stages in Dagster (`sync_catalog -> raw -> staging -> normalized -> typed -> warehouse -> dbt`);
- PostgreSQL persistence layers (`raw_*_staging`, `sync_state`, `typed_canonical_sales`, `canonical_sales`);
- web UI (`/app/*`) and REST API (`/api/*`, `/api/v1/*`);
- RBAC behavior for all three roles;
- optional dbt post-load transformation.

Environment assumptions:
- Python environment is installed (`pip install -e ".[dev]"`);
- PostgreSQL container is up (`docker compose up -d`);
- migrations and seed are applied:
  - `alembic upgrade head`
  - `python scripts/seed_database.py`
- app server is running (`python -m datanorma.web`);
- Dagster is running (`dagster dev -m datanorma.definitions`).

Demo users:
- `seed_admin / AdminDemo2026`
- `seed_integrator / IntegratorDemo2026`
- `seed_analyst / AnalystDemo2026`

## 2) Full functionality inventory

### 2.1 Integrations and source connectors

1. `OzonSource`
- `check()` validates API mode (when keys exist) or fixture fallback mode.
- `discover()` builds stream schema from API or fixture records.
- `read()` reads postings with full/incremental filtering.

2. `OneCSource`
- reads CSV/XLSX export;
- supports env override path (`DATANORMA_1C_EXPORT_PATH`);
- supports full/incremental filtering.

3. `GoogleSheetsSource`
- reads via `gspread` using service account, with fixture fallback;
- supports stream discover and full/incremental filtering.

4. Dynamic source creation
- source factory supports `ozon`, `1c`, `google_sheet`, `rest_builder`;
- `rest_builder` uses YAML from `connector_builder.yaml`.

### 2.2 Pipeline and orchestration (Dagster)

1. `sync_catalog`
- loads stream configs from YAML mapping;
- merges with database sync state;
- resolves cursor resume behavior.

2. Raw assets
- `raw_ozon_postings`
- `raw_1c_orders`
- `raw_google_sheet_orders`

3. Staging persistence
- `staging_raw_postgres` writes to:
  - `raw_ozon_postings_staging`
  - `raw_1c_orders_staging`
  - `raw_google_sheet_orders_staging`
- updates `sync_state`.

4. Normalization and canonical model
- `normalized_orders` applies mapping and canonicalization;
- date normalization to Moscow TZ;
- currency conversion via CBR;
- unit aliases normalization;
- dedup by source key.

5. Typed layer
- `typed_canonical_sales` casts canonical rows into strict typed structure;
- stores typing metadata.

6. Warehouse layer
- `warehouse_sales` UPSERT into `canonical_sales`.

7. dbt layer
- `dbt_run` executes dbt models from `dbt/`.

8. Monitoring and quality
- `staging_raw_has_rows` asset check;
- `normalized_orders_has_rows` asset check;
- `warehouse_has_rows` asset check;
- schedule `daily_schedule`;
- sensor `failed_sync_alert_sensor`.

### 2.3 REST API functionality

1. Auth
- `POST /api/auth/login`
- `GET /api/auth/me`

2. Access matrix and meta
- `GET /api/rbac/matrix`
- `GET /api/meta/dagster-url`

3. Data views
- `GET /api/data/sales-summary`
- `GET /api/data/sales-rows`
- `GET /api/data/staging-counts`
- `GET /api/data/staging-ozon-sample`
- `GET /api/data/staging-1c-sample`
- `GET /api/data/staging-sheet-sample`
- `GET /api/data/sync-state`
- `GET /api/data/normalization-issues`
- `GET /api/data/normalization-fix-stats`
- `GET /api/data/mapping-profiles`
- `POST /api/data/mapping-profiles/draft`
- `POST /api/data/mapping-profiles/publish`
- `POST /api/data/mapping-profiles/activate`
- `POST /api/data/mapping-profiles/rollback`
- `GET /api/data/dim-sources`
- `GET /api/data/dim-currencies`
- `GET /api/data/pipeline-runs`
- `GET /api/data/export-sales-csv`

4. Admin
- `GET /api/admin/users`
- `GET /api/admin/roles`
- `GET /api/admin/integration-config`
- `POST /api/admin/integration-config`

5. API v1 orchestration surface
- `GET /api/v1/sync-streams` / `POST /api/v1/sync-streams` (каталог `sync_state` / курсоры)
- `GET|POST /api/v1/sources`, `GET|PATCH|DELETE /api/v1/sources/{id}`, `POST .../check`, `POST .../discover`
- `GET|POST /api/v1/destinations`, `GET|PATCH|DELETE /api/v1/destinations/{id}`, `POST .../check`
- `GET|POST /api/v1/connections`, `GET|PATCH|DELETE /api/v1/connections/{id}`, `POST .../trigger`, `POST .../pause`, `POST .../resume`
- `GET /api/v1/syncs`
- `POST /api/v1/syncs/trigger` (creates `sync_run` and launches Dagster run)
- `GET /api/v1/syncs/{run_id}`
- `GET /api/v1/syncs/{run_id}/status`
- `GET /api/v1/workspaces`
- `POST /api/v1/workspaces`

### 2.4 Web UI functionality (`/app/*`)

1. Authentication and session
- `/app/login` (GET/POST), `/app/logout`.

2. Home and analytics
- `/app/dashboard`
- `/app/analyst/cabinet`

3. Build section
- `/app/sources`
- `/app/sources/new` (connector check/discover UI)
- `/app/sources/{code}`
- `/app/destinations`
- `/app/connections` (GET/POST)
- `/app/connections/sample/{code}`
- `/app/mappings`
- `/app/mappings/editor` (GET/POST, persisted draft/publish flow)

4. Monitor section
- `/app/runs`
- `/app/runs/{run_id}`
- `/app/monitoring/normalization`
- `/app/warehouse/sales`
- `/app/warehouse/export`
- `/app/warehouse/download.csv`
- `/app/samples/preview`
- `/app/pipeline/graph`

5. Settings and support
- `/app/integrations/secrets` (GET/POST)
- `/app/settings/schedule` (GET/POST)
- `/app/about`
- `/app/external/dagster` redirect

6. Access and references
- `/app/admin/users`
- `/app/admin/user-roles` (GET/POST)
- `/app/workspaces`
- `/app/account/password` (GET/POST)
- `/app/ref/source-systems`
- `/app/ref/currencies`

### 2.5 RBAC model

Roles:
- `platform_admin`
- `data_integrator`
- `analyst`

Access control:
- every API and web page checks operation-level permission;
- forbidden actions return HTTP `403`;
- operation matrix available via `GET /api/rbac/matrix`.

## 3) Manual test scenarios per function

Use this as a runnable checklist.

### 3.1 Platform readiness

Steps:
1. Start PostgreSQL, run migrations and seed.
2. Start web app and Dagster.
3. Open web login page.

Expected:
- no startup errors;
- login page opens;
- seed users can authenticate.

### 3.2 Auth and session

Steps:
1. Log in with valid credentials.
2. Log out.
3. Try wrong password.
4. Call `/api/auth/login` and then `/api/auth/me` with bearer token.

Expected:
- valid login creates session and redirects to dashboard;
- logout removes session;
- wrong password returns `401`;
- `auth/me` returns username and roles.

### 3.3 Ozon integration

Steps:
1. In `/app/sources/new`, select `ozon` and run check/discover.
2. Run pipeline materialization for raw/staging.
3. Open `/app/connections/sample/ozon`.

Expected:
- check is OK either in API mode or fixture mode;
- discover returns stream schema;
- sample rows are visible in UI;
- `raw_ozon_postings_staging` row count > 0.

### 3.4 1C integration

Steps:
1. Test default sample mode (no env path).
2. Optional: set `DATANORMA_1C_EXPORT_PATH` to custom file and restart.
3. Run check/discover from `/app/sources/new`.

Expected:
- file is detected and readable;
- stream discover returns columns from file;
- staging table `raw_1c_orders_staging` gets rows.

### 3.5 Google Sheets integration

Steps:
1. Test sample mode without `GSPREAD_*` vars.
2. Optional: configure service account vars and retry.
3. Run check/discover from `/app/sources/new`.

Expected:
- fallback mode works with sample CSV;
- gspread mode works if credentials are valid;
- data lands in `raw_google_sheet_orders_staging`.

### 3.6 REST builder source function

Steps:
1. In `/app/sources/new`, select `rest_builder`.
2. Keep default YAML and submit.
3. Try malformed YAML.

Expected:
- valid YAML: check/discover output shown;
- invalid YAML: error shown in UI.

### 3.7 Sync catalog and incremental behavior

Steps:
1. Open `/app/connections`, edit one connection:
   - set `sync_mode=incremental`
   - set `cursor_field`.
2. Re-run raw/staging assets.
3. Open `/api/data/sync-state`.

Expected:
- state entry exists and reflects selected mode/cursor;
- subsequent runs use cursor logic;
- `sync_state.updated_at` changes after edit.

### 3.8 Staging persistence function

Steps:
1. Materialize `staging_raw_postgres`.
2. Query staging tables and `sync_state`.
3. Open `/api/data/staging-counts`.

Expected:
- rows inserted into all configured raw staging tables;
- `sync_state` contains stream state and metadata;
- API returns correct table counts.

### 3.9 Normalization function

Steps:
1. Materialize `normalized_orders`.
2. Inspect returned rows in Dagster metadata.
3. Verify:
   - date converted to MSK;
   - currency conversion fields are present;
   - source dedup works;
   - units normalization appears when unit fields exist.

Expected:
- rows are in canonical shape;
- stats block is populated;
- no crash on missing optional values.

### 3.10 Typed layer function

Steps:
1. Materialize `typed_canonical_sales`.
2. Check typing stats and resulting table row count.

Expected:
- rows cast to typed representation;
- typing stats present;
- typed table receives data.

### 3.11 Warehouse upsert function

Steps:
1. Materialize `warehouse_sales`.
2. Open `/app/warehouse/sales` and `/app/warehouse/export`.
3. Download `/app/warehouse/download.csv`.

Expected:
- `canonical_sales` updated with UPSERT behavior;
- warehouse rows visible in UI;
- CSV download succeeds with expected columns.

### 3.12 dbt function

Steps:
1. Ensure `dbt/` project exists and dbt deps installed.
2. Materialize `dbt_run`.

Expected:
- status `ok` when dbt succeeds;
- in failure case: status `failed` with stdout/stderr tails.

### 3.13 API functional verification

Steps:
1. Authenticate and keep bearer token.
2. Call each `/api/data/*`, `/api/admin/*`, `/api/v1/*` endpoint according to role.
3. Validate response schema and status codes.

Expected:
- successful endpoints return JSON payloads as defined;
- forbidden operations return `403`;
- invalid auth returns `401`.

### 3.14 Web pages functional verification

Steps:
1. Log in as each role.
2. Open every `/app/*` page from navigation.
3. For form pages, execute one positive and one negative case:
   - `/app/account/password`
   - `/app/connections` POST
   - `/app/integrations/secrets` POST
   - `/app/settings/schedule` POST
   - `/app/admin/user-roles` POST
   - `/app/mappings/editor` POST

Expected:
- allowed pages render successfully;
- forbidden pages show access denied (`403`);
- form changes are applied where persistence is intended;
- mapping editor creates new draft versions and supports publish/activate.

### 3.15 RBAC matrix verification

Steps:
1. For each role (admin/integrator/analyst), test representative API and UI operations.
2. Compare observed behavior with `/api/rbac/matrix`.

Expected:
- access control strictly matches operation matrix;
- no privilege escalation between roles.

### 3.16 Workspaces (phase 3) function

Steps:
1. Call `POST /api/v1/workspaces` as admin/integrator.
2. Open `/app/workspaces` and `/api/v1/workspaces`.
3. Log in as analyst and verify read-only behavior.

Expected:
- organization/workspace entries are created or updated;
- current user is linked to workspace on create;
- analysts can view but cannot manage.

### 3.17 Monitoring and checks

Steps:
1. Run full pipeline.
2. Verify asset checks in Dagster:
   - staging rows check
   - normalized rows check
   - warehouse rows check
3. Open `/app/runs`, `/app/monitoring/normalization`.

Expected:
- checks are visible and meaningful;
- run history is visible;
- normalization issues page shows data (or empty list without errors);
- the same page lists typed-layer fix aggregates (`action` / `field` from `_ingest_meta.changes`) when data exists;
- `GET /api/data/normalization-fix-stats` returns `rows` (may be empty before typed layer is loaded).

## 4) Integration-focused regression pack (recommended smoke run)

Run this compact sequence after any important change:
1. Login as `seed_admin`.
2. `/app/sources/new`: run check/discover for all four source kinds.
3. Materialize in Dagster:
   - `sync_catalog`
   - all raw assets
   - `staging_raw_postgres`
   - `normalized_orders`
   - `typed_canonical_sales`
   - `warehouse_sales`
   - `dbt_run` (if enabled)
4. Trigger orchestration from UI/API:
   - `/app/runs` form `Запустить синхронизацию`;
   - or `POST /api/v1/syncs/trigger`.
5. Verify:
   - `/api/data/staging-counts`
   - `/api/data/sales-summary`
   - `/api/data/normalization-fix-stats`
   - `/api/v1/syncs/{run_id}/status`
   - `/app/warehouse/sales`
   - `/app/warehouse/download.csv`
   - `/app/monitoring/normalization`
6. Verify RBAC:
   - `seed_integrator` can edit connections but cannot open admin users;
   - `seed_analyst` can view warehouse but cannot modify connections/config.

Pass criteria:
- no unhandled errors in web/API/pipeline;
- staging and warehouse contain rows;
- RBAC restrictions are correct;
- export and preview pages are operational.

## 5) Notes on MVP boundaries

- Primary destination is PostgreSQL at this stage.
- Mapping editor page persists mapping versions in DB (draft/published/active); YAML file remains fallback/import.
- Some product-shaped API routes are intentionally lightweight in MVP and should be validated as such during acceptance.

