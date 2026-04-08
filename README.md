# DataNorma

Конфигурируемый прототип интеграции и нормализации данных для МСБ (оркестрация: **Dagster**).

## Сравнение с Airbyte

Веб-консоль и смысловые блоки (Sources, Destinations, Connections, sync history и т.д.) сознательно согласованы с продуктовой логикой **[Airbyte](https://airbyte.com)** (open-source EL/ELT), но оркестрация и нормализация реализованы на **Dagster** и собственном Python/YAML-слое. Развёрнутая таблица соответствий и отличий: **[docs/comparison_airbyte.md](docs/comparison_airbyte.md)**.

- Централизованные пути и переменные окружения: **`datanorma/config.py`** (`pydantic-settings`, при необходимости читает `.env`).
- Базовые типы **Airbyte Protocol** (Record, State, Catalog, Stream …): **`datanorma/core/airbyte_protocol.py`**.
- Dev-зависимости: `pip install -e ".[dev]"` (в т.ч. `dbt-postgres`). Пакет **Airbyte CDK** при необходимости: `pip install -e ".[dev-airbyte]"`.

## Для кого и что это

Сервис **не привязан к одной гипотетической компании**: смысл в том, что данные **вашей** организации (или песочные примеры) проходят через одни и те же коннекторы, а различия в колонках и форматах задаются **конфигом маппинга** (`datanorma/schemas/source_mappings.yaml` или `DATANORMA_SOURCE_MAPPINGS_PATH`). Логическая цель — единая **каноническая модель** продаж (`datanorma/schemas/canonical_sales.yaml`), с которой удобно работать аналитику в SQL/BI после загрузки в warehouse.

**Сейчас в дипломном прототипе:** просмотр и запуск пайплайна — через **Dagster UI** (граф, материализации, логи). Отдельного «личного кабинета аналитика» с логином и мультитенантностью нет: это следующий уровень продукта (SaaS), за рамками текущего объёма. Зато пайплайн изначально рассчитан на **любого заказчика**, который подставляет свои файлы, ключи API и YAML маппинга.

## Этап 1: запуск локально

1. Python 3.11+, виртуальное окружение:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   ```

2. PostgreSQL (целевая БД):

   ```bash
   docker compose up -d
   ```

3. UI и пайплайны:

   ```bash
   dagster dev -m datanorma.definitions
   ```

   Альтернатива в новых версиях Dagster: `dg dev` (см. предупреждение *SupersessionWarning* в консоли — старая команда пока поддерживается).

   Откройте адрес из вывода команды (обычно http://127.0.0.1:3000). В разделе **Assets** виден граф: **raw** → **`staging_raw_postgres`** (запись в `raw_*_staging` + `sync_state`) → **`normalized_orders`** → **`warehouse_sales`**. Расписание **daily_moscow** (05:00 Europe/Moscow) в **Automation**.

## Этап 2: raw-источники

Без секретов пайплайн читает файлы из `data/samples/` (Ozon — JSON, 1С — CSV, Google Sheets — CSV как экспорт). Реальные интеграции задаются переменными окружения (см. `.env.example`):

- **Ozon** — `OZON_CLIENT_ID`, `OZON_API_KEY`; запрос к `POST /v3/posting/fbs/list`, при ошибке или отсутствии ключей — фикстура.
- **1С** — `DATANORMA_1C_EXPORT_PATH` на ваш CSV/XLSX; иначе sample `1c_export.csv`.
- **Google Sheets** — `GSPREAD_SERVICE_ACCOUNT_FILE`, `GSPREAD_SPREADSHEET_ID`, опционально `GSPREAD_WORKSHEET`; иначе sample CSV.

При установке пакета не из исходников укажите `DATANORMA_REPO_ROOT` на каталог, где лежит `data/samples`.

## Каноническая модель и маппинг (любая компания)

- Описание полей витрины: `datanorma/schemas/canonical_sales.yaml` (документация для аналитики и разработки коннекторов).
- Соответствие колонок ваших выгрузок этим полям: `datanorma/schemas/source_mappings.yaml`. Для другой структуры CSV/листа скопируйте файл, измените `fields` и задайте `DATANORMA_SOURCE_MAPPINGS_PATH`.
- Asset `normalized_orders` строит список строк в этой канонической форме и выполняет простую дедупликацию по паре `(source_system, source_record_id)`.

## Этап 3: нормализация (даты, ЦБ, fuzzy, единицы)

- **Даты:** поле `event_datetime` приводится к ISO с часовым поясом **Europe/Moscow** (см. `datanorma/normalization/dates_msk.py`).
- **Валюта → RUB:** для каждой строки берётся дата события (или сегодня по MSK), запрашивается дневной XML ЦБ РФ (`cbr_rates.py`, кэш `lru_cache` по дате). Поля **`amount_rub`**, **`cbr_rate_date`**. Нет сети или валюты в справочнике — `amount_rub` может быть `None`.
- **Fuzzy маппинг колонок:** RapidFuzz, порог задаётся в `source_mappings.yaml` (`fuzzy_column_threshold` в `options` или у конкретного источника; у sample для **1С** включено 85).
- **Единицы:** справочник-алиасы в `units.py`; в строке появляется `line_unit_normalized`, если задан `line_unit_raw` (при необходимости добавьте поле в YAML маппинга).

Тесты: `pytest tests/ -q` (нужен `pip install -e ".[dev]"`).

## Фаза А: схема БД (Alembic) и сиды

Целевая схема (≥10 таблиц: справочники, staging raw, витрина, роли/пользователи, конфиги, аудит) задаётся миграциями в `alembic/versions/`. После `docker compose up -d`:

```bash
alembic upgrade head
python scripts/seed_database.py
```

Сиды добавляют демо-данные (в т.ч. **520+** строк в `canonical_sales` с префиксом `seed_*`) и вспомогательные строки в других таблицах; повторный запуск скрипта очищает только «сидовые» ключи и перезаполняет их.

Переменная **`DATABASE_URL`** — как у Dagster (см. `.env.example`).

Если при материализации **`sync_catalog`** в Dagster ошибка **`column "stream_name" does not exist`**: схема БД старая, не накатили Phase 1. В каталоге проекта выполните **`alembic upgrade head`** с **тем же** `DATABASE_URL`, что видит Dagster (часто сбой из‑за порта **5432** локального Postgres вместо **5433** из `docker-compose`). Проверка: `alembic current` должно показывать ревизию **`002_phase1_airbyte`**.

## Фаза B: raw в PostgreSQL (staging)

После фазы А пайплайн фиксирует сырой слой в БД до нормализации (аналог **landing / raw** в medallion или буфера в ELT):

- Asset **`sync_catalog`** читает **`sync_state`** и YAML до raw-слоя; raw-ассеты поддерживают **`full_refresh`** / **`incremental`** (поля `sync_mode`, `cursor_field` в `source_mappings.yaml`).
- Asset **`staging_raw_postgres`** пишет в **`raw_ozon_postings_staging`**, **`raw_1c_orders_staging`**, **`raw_google_sheet_orders_staging`** с мета-колонками **`_airbyte_raw_id`**, **`_airbyte_extracted_at`**, **`_airbyte_meta`**; общий **`ingest_batch_id`** (UUID).
- **`sync_state`**: строка на пару `(integration_code, stream_name)` + **`airbyte_state`** (JSON), **`cursor_field`**, режим синхронизации.
- Витрина: колонка **`_airbyte_loaded_at`**, UPSERT обновляет строку только если новое значение не старее (инкрементальная логика по времени загрузки).
- **`normalized_orders`** зависит от `staging_raw_postgres`, поэтому порядок материализации: raw → staging → каноника → warehouse.

Логика вставок: `datanorma/warehouse/raw_staging.py`. Нужны применённые миграции Alembic (таблицы staging).

### Веб-UI и API: три роли (JWT + матрица доступа)

Для методички (свои экраны, матрица «роль × операция», скриншоты под разными учётками):

1. Поднять БД, миграции и сиды (`alembic upgrade head`, `python scripts/seed_database.py`) — в `app_user` / `role` / `user_role` появятся демо-пользователи.
2. Запуск UI и REST: **`python -m datanorma.web`** → корень **`/`** ведёт на **`/app/login`** (веб-клиент Jinja2). REST: префикс **`/api`**. Классический одностраничный интерфейс сохранён на **`/ui/`**.
3. Демо-пароли (см. также экран входа): **`seed_admin` / AdminDemo2026**, **`seed_integrator` / IntegratorDemo2026**, **`seed_analyst` / AnalystDemo2026**.
4. Каждый защищённый маршрут API сопоставлен с **операцией** в `datanorma/web/rbac_matrix.py`; JWT содержит **claims `roles`**; при запрете — **403** с указанием операции.
5. **Dagster** остаётся операционной консолью; для ВКР основной акцент — на **веб-клиенте** (фаза C) и матрице доступа.
6. Готовый текст для главы диплома: **`docs/vkr_rbac_text.md`**.

Переменные: **`DATANORMA_JWT_SECRET`**, **`DATANORMA_DAGSTER_UI_URL`** (см. `.env.example`).

## Фаза C: веб-клиент (≥20 экранов, Jinja2)

Реализовано **FastAPI + Jinja2** (альтернатива Streamlit — быстрее набрать экраны, но здесь единый стек с API и **явные URL** для скриншотов). Уточните у кафедры, засчитывают ли такие страницы как «экранные формы»; при необходимости сравнение с Streamlit можно описать в ВКР.

- **Вход:** форма на **`/app/login`** (POST), сессия через **httpOnly cookie** + тот же JWT, что и для API.
- **≥20 уникальных маршрутов** под шаблоны в `datanorma/web/templates/`; роутинг и данные — `datanorma/web/pages_jinja.py`. Навигация в `base.html` дублирует список из кода (подпись, URL, операция RBAC).
- **UI в духе Airbyte:** светлая консоль (`datanorma/web/static/theme-airbyte.css`), секции **Sources**, **Destinations**, **Connections**, sync history / settings / secrets; оркестрация вынесена в **Dagster** (`/app/external/dagster`). Подробнее о сходстве и отличиях — **`/app/about`**.
- Примеры экранов: смена пароля, дашборд (Home), **connections** и **destinations**, источники и карточка, ключи/env с маскированием, маппинги и редактор YAML (отправка без записи на диск), предпросмотр sample, запуски и детали run, **статическая схема** пайплайна + ссылка на Dagster, витрина с фильтром, страница экспорта и **`/app/warehouse/download.csv`**, справочники, админ-пользователи, назначение ролей, журнал нормализации, cron в настройках, «о системе и FAQ».
- На каждой странице проверка **операции** из `rbac_matrix.py` (как и для REST); при отсутствии прав — страница **403** (`forbidden.html`).
- Перечень путей для приложения к ВКР: **`docs/phase_c_routes.md`**.

## Этап 4: warehouse (PostgreSQL)

- Таблица **`canonical_sales`** (и остальные объекты фазы А) создаётся миграциями Alembic. Asset **`warehouse_sales`** выполняет **UPSERT** по ключу `(source_system, source_record_id)` из `normalized_orders["rows"]` (имя таблицы: `DATANORMA_WAREHOUSE_TABLE`, по умолчанию `canonical_sales`).
- Если миграции пока не применялись, можно включить устаревшее автосоздание только витрины: `DATANORMA_AUTO_CREATE_TABLES=1` (не рекомендуется для согласованной схемы).
- Строки без `source_record_id` в warehouse **не пишутся** (нет стабильного ключа).
- Проверка для аналитика после materialize:

  ```sql
  SELECT * FROM canonical_sales ORDER BY loaded_at DESC LIMIT 20;
  ```

## Этап 5: качество и наблюдаемость

- **Unit-тесты:** каталог `tests/` — нормализация, ЦБ (в т.ч. `Nominal`), fuzzy, enrich с моком, warehouse, **дедуп и склейка трёх источников** (`test_pipeline_stage5.py`). Запуск: `pytest tests/ -q` (нужен `pip install -e ".[dev]"`).
- **Asset checks (Dagster):** модуль `datanorma/checks/data_quality.py` — проверки staging (хотя бы одна запись raw в БД), непустой `normalized_orders` и запись в warehouse. Статус WARN при пустых данных (удобно для демо без Postgres или без материализации).

## Этап 6 (опционально): мультитенантность и deployment polish

- Базовая модель **organization/workspace** + привязка пользователей (`organization`, `workspace`, `user_workspace`), миграция `004_phase3_multitenancy`.
- API для workspaces: `GET/POST /api/v1/workspaces`.
- Личный кабинет аналитика: `/app/analyst/cabinet`.
- Контейнеризация: `Dockerfile` в корне.
- Kubernetes-скелет: `helm/` (Chart, values, deployment/service templates).
- Гайд по подключению российского коннектора: `docs/adding_russian_connector.md`.

Переопределение URL БД: переменная окружения `DATABASE_URL` (см. `.env.example`).

### Если падает `warehouse_sales` (PostgreSQL)

Чаще всего на Windows порт **5432** уже занят **локальным** PostgreSQL: приложение подключается не к Docker, и пользователь `datanorma` «не существует» или пароль не подходит (в логе Dagster это видно как кракозябры — русское сообщение сервера).

В проекте контейнер проброшен на порт **5433** (`docker-compose.yml`). После `docker compose up -d` строка подключения по умолчанию: `127.0.0.1:5433`, пользователь/пароль/БД `datanorma`. Проверка из PowerShell:

```powershell
docker compose -f c:\dev\diploma\diploma\docker-compose.yml up -d
docker compose -f c:\dev\diploma\diploma\docker-compose.yml exec postgres psql -U datanorma -d datanorma -c "SELECT 1"
```

Если в `.env` или в системе задан старый `DATABASE_URL` с портом `5432`, удалите его или поправьте на `5433`. Если пароль контейнера когда-то меняли и том не сбрасывали: `docker compose down -v` (удалит данные в volume) и снова `up -d`.

### Что значат сообщения в консоли

- **Временный каталог для storage** — по умолчанию Dagster кладёт служебные данные в temp-папку и удаляет её после выхода. Чтобы сохранять историю и настройки между запусками, задайте каталог, например: `set DAGSTER_HOME=c:\dev\diploma\diploma\.dagster_home` (PowerShell: `$env:DAGSTER_HOME="..."`), и при необходимости создайте в нём `dagster.yaml`.
- **Telemetry** — сбор анонимной статистики; отключение: в `%DAGSTER_HOME%\dagster.yaml` добавить `telemetry: { enabled: false }`.
- **Compute log capture is disabled (Windows)** — логи выполнения шагов в UI могут быть пустыми. Чтобы включить захват, перед запуском задайте `PYTHONLEGACYWINDOWSSTDIO=1` (в PowerShell: `$env:PYTHONLEGACYWINDOWSSTDIO="1"`).
- Строка про **daemons** и **Serving dagster-webserver on http://127.0.0.1:3000** означает, что всё поднялось успешно.

### Сравнение с Airbyte
|Категория|Что есть в Airbyte|Что есть у тебя|Что не хватает (приоритет для диплома)|
|---------|------------------|---------------|--------------------------------------|
|Коннекторы|600+ любых|3 специфических (Ozon/1C/Google Sheets)|"Универсальный механизм коннекторов + Connector Builder / CDK. Сейчас всё ""вшито"" в Dagster assets."|
|Схема и discovery|Автоматический discover() + JSON Schema|Жёсткие YAML-маппинги|Автоматическое обнаружение схемы источников (чтобы не писать маппинг вручную каждый раз)|
|Режимы синхронизации|Full / Incremental / CDC + state|Только full (судя по коду и сэмплам)|Incremental + state management (чтобы не переливать всё каждый день)|
|Нормализация|Typing + Deduping (TyD) + dbt (generic + typed columns)|"Кастомная бизнес-нормализация (валюты, даты, fuzzy, units)"|1) Генерация typed columns по схеме (как TyD). 2) Поддержка dbt / SQL-трансформаций после загрузки. 3) Raw-таблицы + _airbyte_meta для ошибок.|
|Назначения|Много (warehouse + lakes + DB)|Только один Postgres-warehouse + фиксированная canonical_sales|Несколько destinations + выбор (или хотя бы абстракция).|
|UI / UX|Полноценный no-code builder соединений|"20+ экранов FastAPI+Jinja (хорошо, но проще)"|Визуальный конструктор Connections (drag-and-drop streams/fields).|
|Оркестрация|Собственный движок + Temporal + Workloads|Dagster (отлично!)|— (Dagster даже лучше для сложных пайплайнов)|
|Мониторинг / Надёжность|"Retries, resumability, per-row errors, alerts"|Dagster logs + asset checks|"Автоматические retries, resumable syncs, обработка schema changes."
|API / Extensibility|Полный REST API + protocol|Внутренний FastAPI + RBAC|Публичный API для внешних систем + возможность добавлять коннекторы без изменения кода.|
|Мультитенантность|Workspaces + Organizations|Однотенант (по README)|Хотя бы базовая мультитенантность (компании/проекты)|
|Дополнительно|"File syncing, breaking change protection, unstructured data"|—|"Поддержка файлов (не только таблицы), защита от breaking changes."|
