# DataNorma

DataNorma - сервис интеграции и нормализации данных для малого и среднего бизнеса, ориентированный на российскую аудиторию.  
По продуктовой идее это аналог Airbyte: готовые коннекторы, управляемые синхронизации, единая каноническая модель данных и операционная консоль.

Текущая реализация сочетает:
- оркестрацию в Dagster;
- коннекторы к популярным источникам (Ozon, 1C, Google Sheets);
- нормализацию в Python/YAML;
- загрузку в PostgreSQL (staging + warehouse);
- веб-интерфейс и REST API на FastAPI + Jinja2 с RBAC.

## 1) Что умеет проект сейчас

- Подключает данные из готовых источников и в fallback-режиме работает на sample-файлах.
- Поддерживает режимы full refresh и incremental по курсору.
- Пишет raw-слой в PostgreSQL (`raw_*_staging`) с Airbyte-style метаданными.
- Приводит данные к канонической модели продаж (`canonical_sales`).
- Выполняет enrichment: даты в `Europe/Moscow`, конвертация валют через ЦБ РФ, нормализация единиц.
- Типизирует канонический слой по YAML-схеме.
- Загружает витрину в warehouse через UPSERT.
- Даёт UI для операционных и аналитических сценариев + API и матрицу ролей.

## 2) Архитектура (в терминах потока)

Основной pipeline:

1. `sync_catalog` - готовит конфиг потоков и resume state.
2. `raw_ozon` / `raw_1c` / `raw_google_sheet` - читают источники.
3. `staging_raw_postgres` - сохраняет сырой слой в PostgreSQL.
4. `normalized_orders` - канонизация, дедупликация, enrichment.
5. `typed_canonical_sales` - типизация колонок по схеме.
6. `warehouse_sales` - UPSERT в витрину `canonical_sales`.
7. `dbt_run` - пост-трансформации в dbt.

Точка сборки всех assets: `datanorma/definitions.py`.

## 3) Полная карта проекта

### Корневые директории

- `datanorma/` - основное приложение.
- `alembic/` - миграции БД.
- `dbt/` - dbt-проект (marts и источники).
- `docs/` - документация и manual testing.
- `tests/` - unit/smoke тесты.
- `data/samples/` - демо-данные для запуска без секретов.
- `scripts/` - утилиты, включая seed данных.
- `helm/` - deployment-скелет для Kubernetes.

### Внутри `datanorma/`

- `assets/` - Dagster assets по этапам конвейера.
- `sources/` - коннекторы и source factory (`check/discover/read`).
- `normalization/` - mapping, fuzzy, даты/валюта/units, typing.
- `warehouse/` - запись в staging и warehouse, sync state.
- `web/` - FastAPI API + Jinja2 UI + auth/RBAC/static/templates.
- `resources/` - ресурсы Dagster (Postgres, paths).
- `schemas/` - YAML-схемы и маппинги.
- `checks/` - проверки качества данных (Dagster asset checks).
- `schedules/` - расписания и sensor-оповещения.
- `core/` - базовые типы и протоколы.
- `ingest/` - stream config и cursor filtering.

## 4) Технологический стек

- Python 3.11+
- Dagster, dagster-webserver, dagster-dbt
- FastAPI, Uvicorn, Jinja2, PyJWT
- SQLAlchemy 2.x, psycopg3, Alembic, PostgreSQL
- dbt-core + dbt-postgres
- httpx
- pandas, openpyxl
- gspread, google-auth
- RapidFuzz
- pydantic-settings

Файл зависимостей: `pyproject.toml`.

## 5) Быстрый старт (локальная разработка)

### 5.1 Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Для тестов:

```bash
pip install -e ".[dev]"
```

### 5.2 Поднять PostgreSQL

```bash
docker compose up -d
```

По умолчанию контейнер доступен на `127.0.0.1:5433`  
(внутри контейнера `5432`, снаружи специально `5433`).

### 5.3 Накатить схему и сиды

```bash
alembic upgrade head
python scripts/seed_database.py
```

### 5.4 Запустить платформу

Dagster UI (оркестрация):

```bash
dagster dev -m datanorma.definitions
```

Web/API:

```bash
python -m datanorma.web
```

По умолчанию веб-приложение поднимается на `http://127.0.0.1:8080`.

## 6) Конфигурация и переменные окружения

Основной файл примеров: `.env.example`  
Централизация настроек: `datanorma/config.py`

Ключевые переменные:

- `DATABASE_URL` - строка подключения к PostgreSQL.
- `DATANORMA_SOURCE_MAPPINGS_PATH` - путь к кастомному YAML-маппингу.
- `DATANORMA_REPO_ROOT` - корень репозитория (важно для sample-данных вне editable-режима).
- `DATANORMA_WAREHOUSE_TABLE` - имя целевой витрины (по умолчанию `canonical_sales`).
- `DATANORMA_JWT_SECRET`, `DATANORMA_JWT_EXPIRE_HOURS` - аутентификация веба/API.
- `DATANORMA_DAGSTER_UI_URL` - ссылка на внешний Dagster UI из веба.
- `OZON_CLIENT_ID`, `OZON_API_KEY`, `OZON_FETCH_LIMIT` - Ozon API.
- `DATANORMA_1C_EXPORT_PATH` - путь к 1C CSV/XLSX.
- `GSPREAD_SERVICE_ACCOUNT_FILE`, `GSPREAD_SPREADSHEET_ID`, `GSPREAD_WORKSHEET` - Google Sheets.

## 7) Источники данных (connectors)

### Встроенные коннекторы

- **Ozon** (`datanorma/sources/ozon.py`)  
  Читает postings через Ozon Seller API; при отсутствии ключей использует sample JSON.

- **1C** (`datanorma/sources/onec.py`)  
  Читает выгрузку CSV/XLSX (через pandas/openpyxl), fallback на sample CSV.

- **Google Sheets** (`datanorma/sources/sheets.py`)  
  Работает через service account (`gspread`), fallback на sample CSV.

### Коннектор-конструктор (low-code)

- `datanorma/sources/builder.py`
- схема: `datanorma/schemas/connector_builder.yaml`

Поддерживаются декларативные REST-коннекторы (auth/pagination/discover/read), включая сценарий генерации из OpenAPI.

## 8) Нормализация и каноническая модель

### Каноника

- Схема: `datanorma/schemas/canonical_sales.yaml`
- Маппинг источников: `datanorma/schemas/source_mappings.yaml`

### Что делает слой нормализации

- Сопоставляет поля источников с каноническими полями.
- Может применять fuzzy matching названий колонок.
- Обрабатывает source-specific особенности (включая Ozon handler).
- Дедуплицирует записи по `(source_system, source_record_id)`.
- Нормализует даты в московскую таймзону.
- Считает `amount_rub` по курсу ЦБ РФ.
- Нормализует единицы измерения.

Ключевые модули:

- `datanorma/normalization/to_canonical.py`
- `datanorma/normalization/enrich.py`
- `datanorma/normalization/dates_msk.py`
- `datanorma/normalization/cbr_rates.py`
- `datanorma/normalization/units.py`
- `datanorma/normalization/typing.py`

## 9) База данных и хранение

- Миграции: `alembic/versions/`
- Сырой слой: `raw_ozon_postings_staging`, `raw_1c_orders_staging`, `raw_google_sheet_orders_staging`
- Состояние синхронизации: `sync_state`
- Витрина: `canonical_sales` (или имя из `DATANORMA_WAREHOUSE_TABLE`)

В raw-слое используются техполя в стиле Airbyte:
- `_airbyte_raw_id`
- `_airbyte_extracted_at`
- `_airbyte_meta`

## 10) Web UI и API

- Приложение: `datanorma/web/main.py`
- Запуск: `python -m datanorma.web`
- UI-маршруты (Jinja2): `datanorma/web/pages_jinja.py`
- API-роутер: `datanorma/web/api_router.py`
- RBAC-матрица: `datanorma/web/rbac_matrix.py`

Реализованы:
- аутентификация (JWT + cookie для web flow),
- роли и проверка операций,
- страницы по источникам/коннекциям/синкам/витрине/админке,
- REST API под `/api`.

Каталог маршрутов для тестирования: `docs/phase_c_routes.md`.

## 11) Тестирование и качество

Запуск:

```bash
pytest tests/ -q
```

Что покрыто тестами:
- нормализация и enrich;
- курсоры incremental;
- staging и warehouse;
- Airbyte protocol layer;
- API-маршруты и RBAC;
- Dagster definitions/checks.

Проверки качества в Dagster:
- `datanorma/checks/data_quality.py`

## 12) Документация в репозитории

- `docs/README.md` - индекс документации и единый стандарт.
- `docs/manual_testing_guide.md` - детальные ручные сценарии.
- `docs/comparison_airbyte.md` - сравнение с Airbyte.
- `docs/adding_russian_connector.md` - как добавить новый российский коннектор.
- `docs/phase_c_routes.md` - список web-маршрутов.
- `docs/vkr_rbac_text.md` - текстовый материал по RBAC для ВКР.

## 13) Ограничения текущей версии

- Основной destination сейчас один: PostgreSQL.
- Часть возможностей Airbyte реализована частично или в упрощенном виде (особенно вокруг универсальности коннекторов и UX-конструктора).
- Есть API-эндпоинты в формате продукта, но не все из них запускают полный продакшен-оркестрационный цикл.
- Проект ориентирован на дипломный MVP и развитие в сторону полноценного SaaS.

## 14) Roadmap (куда развивать дальше)

- Расширить набор готовых коннекторов для российского SMB.
- Улучшить incremental/state и обработку schema changes.
- Добавить больше destination-адаптеров кроме PostgreSQL.
- Укрепить CI/CD и автопроверки.
- Развить мультитенантный контур (organization/workspace) до production-ready состояния.
- Расширить no-code/low-code UX для управления коннекциями.

## 15) Позиционирование относительно Airbyte

DataNorma уже закрывает базовый сценарий "подключить источник -> нормализовать -> загрузить в warehouse" в российском контексте и с акцентом на бизнес-данные МСБ.

Ключевое отличие на текущем этапе:
- Airbyte - зрелая универсальная платформа с большим ecosystem;
- DataNorma - целевой продуктовый MVP, фокусированный на локальных интеграциях, кастомной нормализации и прозрачном Python/Dagster-контуре.

Подробное сравнение: `docs/comparison_airbyte.md`.
# DataNorma

Конфигурируемый прототип интеграции и нормализации данных для МСБ (оркестрация: **Dagster**).

## Сравнение с Airbyte

Веб-консоль и смысловые блоки (Sources, Destinations, Connections, sync history и т.д.) сознательно согласованы с продуктовой логикой **[Airbyte](https://airbyte.com)** (open-source EL/ELT), но оркестрация и нормализация реализованы на **Dagster** и собственном Python/YAML-слое. Развёрнутая таблица соответствий и отличий: **[docs/comparison_airbyte.md](docs/comparison_airbyte.md)**.

- Полный перечень текущего функционала и пошаговое ручное тестирование (включая интеграции): **[docs/manual_testing_guide.md](docs/manual_testing_guide.md)**.

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
