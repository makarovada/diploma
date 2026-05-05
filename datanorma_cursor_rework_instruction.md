# DataNorma — инструкция по доработке проекта (для Cursor)

> Репозиторий: `github.com/makarovada/diploma`, ветка `base_1`.
> Стек: Python 3.11+, FastAPI, Dagster, SQLAlchemy + Alembic + PostgreSQL, dbt, React 19 + Vite + TanStack Query + Tailwind, Jinja fallback.
> Цель доработки: убрать каноническую модель, перейти на per-stream нормализацию по правилам колонок (Airbyte-подобный подход), реализовать недостающие коннекторы, упростить мастер создания подключения и заменить все mock-data/заглушки реальными данными из API.

---

## 0. Контекст и текущее состояние (что уже есть в `base_1`)

Реализовано:

- Серверная часть (`datanorma/`): источники `ozon`, `1c`, `google_sheet`, `yandex_metrika`, `rest_builder`; приёмники `postgres`, `clickhouse`, `csv`, `xlsx`; нормализация (даты MSK, валюты ЦБ, ФИО, контакты, единицы, статусы, типизация).
- Каноническая модель: `datanorma/schemas/canonical_sales.yaml` + `canonical_marketing_events.yaml` + `source_mappings.yaml`. Используется в `datanorma/normalization/to_canonical.py` и `datanorma/normalization/typing.py` (таблица `typed_canonical_sales`). Это ровно то, от чего нужно избавиться.
- React SPA (`client/src/`): мастер подключения `connection-wizard/` (12 шагов), страницы Sources/Destinations/Connections/Runs/Mappings/Normalization, RBAC.
- Тесты: `tests/test_business_normalization.py`, `test_normalization.py`, `test_typing_phase3.py`, `test_marketing_events_mapping.py` — все привязаны к канонической модели.
- Каталог коннекторов в UI (`client/src/lib/mock-data.ts`) показывает Wildberries, Bitrix24, amoCRM, МойСклад как источники, **но в `datanorma/sources/registry.py` они НЕ реализованы**. UI вводит пользователя в заблуждение.

Главные проблемы, которые мы исправим:

1. Жёсткая каноническая модель `canonical_sales_v1` и `canonical_marketing_events_v1` — несовместима со множеством доменов (МСП работает не только с продажами).
2. Нормализация задаётся одним глобальным YAML и фуззи-маппингом колонок в каноническую таблицу. Нужно: per-connection + per-stream + per-column правила (тип `number`/`date`/`currency`/`phone`/`email`/`enum`/`string` с параметрами).
3. UI каталог ссылается на коннекторы, которых нет (Wildberries, Bitrix24, amoCRM, МойСклад).
4. Мастер создания подключения — 12 шагов, с открытым JSON-полем для секретов и YAML — слишком длинный и технический.
5. Половина React-страниц (`workspaces`, `users`, `sources`, `destinations`, `connectors`, `connector-detail`, `source-new`, `source-detail`, `destinations`, `destination-detail`, `connection-mapping`, `connection-normalization`, `normalization`, `normalization-rules`, `normalization-dictionaries`, `dictionaries`, `schedules`, `queue`, `activity`, `issues`, `issue-detail`, `semantic-layer`, `settings`, `help`, `api-docs`) импортируют `@/lib/mock-data` и не ходят в API.

---

## 1. Глобальные правила работы

- Все изменения делаем атомарными PR-блоками; после каждого блока — `pytest -q`, `cd client && npm run typecheck && npm run test`, `alembic upgrade head` (если миграции).
- Не ломать совместимость API `/v1/*` — добавлять новые поля/эндпоинты, старые помечать `deprecated=True` в OpenAPI и ставить ToDo на удаление в следующем релизе.
- В Python — типизация (mypy/pyright не настроен, но придерживаемся PEP 484) и docstring на русском.
- В TS — `strict: true` уже стоит, не добавлять `any` без `// eslint-disable-next-line` и комментария почему.
- Все новые таблицы создаются Alembic-миграцией; каждое изменение схемы БД даёт upgrade + downgrade.
- Все user-facing строки — на русском, технические идентификаторы — на английском snake_case.

---

## 2. Блок A. Удаление канонической модели и переход к per-stream правилам нормализации

### A.1. Что выпиливаем

Файлы и сущности, которые удаляются или сильно перерабатываются:

- `datanorma/schemas/canonical_sales.yaml` — удалить.
- `datanorma/schemas/canonical_marketing_events.yaml` — удалить.
- `datanorma/schemas/source_mappings.yaml` — удалить (заменим на per-connection правила, лежащие в БД).
- `datanorma/normalization/to_canonical.py` — удалить.
- `datanorma/normalization/marketing_events.py` — удалить.
- `datanorma/normalization/typing.py` — переписать (см. A.4).
- `datanorma/normalization/enrich.py` — оставить, но изолировать как набор pure-функций обогащения (CBR rate, dim_status_map). Эти функции теперь вызываются только если в правилах колонки указано `enrich: cbr_rate` или `enrich: status_map`.
- `dbt/models/marts/canonical_sales_business.sql` — удалить.
- `datanorma/web/mapping_profiles.py` — упростить: больше не работает с каноническими полями, а хранит profile = набор column_rules per stream.
- Таблица `typed_canonical_sales` — удалить миграцией; вместо неё создаются типизированные таблицы под каждый stream подключения (см. A.3).
- Все тесты, явно тестирующие каноническую модель: `test_business_normalization.py`, `test_marketing_events_mapping.py`, частично `test_normalization.py`, `test_typing_phase3.py`, `test_mapping_profiles_*.py` — переписать под новую модель.
- Страница `client/src/pages/canonical-model.tsx` — удалить, маршрут убрать из `routes.tsx`.

### A.2. Новая модель данных: ColumnRule + StreamRules

Идея — Airbyte-подобная: коннектор отдаёт «сырое» ведро записей в `raw.*`, после чего пользователь в UI задаёт *правила колонок* (тип, формат, постобработка) на уровне `connection × stream × column`. Слой `normalized.*` строится из этих правил.

Создать модуль `datanorma/normalization/rules.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

ColumnType = Literal[
    "string", "integer", "number", "boolean",
    "date", "datetime", "currency_amount", "currency_code",
    "phone", "email", "inn", "kpp", "ogrn",
    "enum", "json"
]

@dataclass(slots=True)
class ColumnRule:
    """Правило нормализации одной колонки в одном stream одного подключения."""
    source_field: str                      # имя поля в raw (как пришло из коннектора)
    target_field: str                      # имя поля после нормализации (snake_case)
    type: ColumnType
    nullable: bool = True
    required: bool = False                 # если True — пустые строки роняются в issues
    # type-specific параметры:
    date_formats: list[str] = field(default_factory=list)   # для date/datetime
    timezone: str | None = None                              # для datetime: "Europe/Moscow"
    decimal_separator: str | None = None                     # для number/currency_amount: "," или "."
    thousands_separator: str | None = None
    currency_code: str | None = None                         # фиксированный ISO-код, если currency_code не приходит из источника
    convert_to_currency: str | None = None                   # если задан — пересчитать в эту валюту через CBR
    enum_map: dict[str, str] = field(default_factory=dict)   # для enum: raw → canonical
    enum_default: str | None = None
    phone_default_country: str = "RU"                        # для phone: для парсинга phonenumbers
    trim: bool = True
    lowercase: bool = False
    uppercase: bool = False
    # extra:
    on_error: Literal["null", "raise", "keep_raw"] = "null"
    description: str | None = None

@dataclass(slots=True)
class StreamRules:
    """Набор правил для одного stream."""
    stream_name: str
    primary_key: list[str] = field(default_factory=list)     # имена target_field, формирующие PK
    cursor_field: str | None = None                          # target_field, по которому идёт incremental
    sync_mode: Literal["full_refresh", "incremental"] = "full_refresh"
    columns: list[ColumnRule] = field(default_factory=list)
    drop_unknown_columns: bool = False                       # True — выкидывать поля, для которых нет правил
    deduplicate: bool = True                                 # True — дедуп по primary_key
```

Создать модуль `datanorma/normalization/apply.py`:

```python
"""Применение правил к одной записи / батчу.

Контракт:
- apply_rules_to_row(rule_set, row) -> tuple[normalized_row, issues]
- apply_rules_to_batch(rule_set, rows) -> tuple[list[normalized], list[Issue], NormStats]
- Issue хранится с source_record_id, field, raw_value, error_code, error_text.
"""
```

Реализовать функции типизации (выделить из старого `typing.py`):

- `cast_string`, `cast_integer`, `cast_number(decimal/thousands sep)`, `cast_boolean`, `cast_date`, `cast_datetime` (с TZ), `cast_currency_amount` (число + опционально пересчёт в `convert_to_currency` через `cbr_rates.py`), `cast_phone` (через `phonenumbers`), `cast_email`, `cast_inn` (длина 10/12 + контрольная сумма), `cast_enum`. Каждая возвращает `tuple[value, error | None]`.

### A.3. Хранение правил в БД и динамические таблицы normalized

Создать миграцию `alembic/versions/<NN>_drop_canonical_add_rules.py`:

```sql
-- 1) DROP старого
DROP TABLE IF EXISTS typed_canonical_sales;
DROP TABLE IF EXISTS canonical_marketing_events;  -- если существует

-- 2) Правила на уровне connection (а не глобально)
CREATE TABLE connection_stream_rules (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL REFERENCES connection(id) ON DELETE CASCADE,
    stream_name TEXT NOT NULL,
    sync_mode TEXT NOT NULL DEFAULT 'full_refresh',
    cursor_field TEXT,
    primary_key JSONB NOT NULL DEFAULT '[]'::jsonb,
    drop_unknown_columns BOOLEAN NOT NULL DEFAULT FALSE,
    deduplicate BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (connection_id, stream_name)
);

CREATE TABLE connection_column_rule (
    id BIGSERIAL PRIMARY KEY,
    stream_rules_id BIGINT NOT NULL REFERENCES connection_stream_rules(id) ON DELETE CASCADE,
    source_field TEXT NOT NULL,
    target_field TEXT NOT NULL,
    type TEXT NOT NULL,
    nullable BOOLEAN NOT NULL DEFAULT TRUE,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    params JSONB NOT NULL DEFAULT '{}'::jsonb,  -- date_formats, decimal_separator, enum_map, ...
    on_error TEXT NOT NULL DEFAULT 'null',
    sort_order INT NOT NULL DEFAULT 0,
    description TEXT,
    UNIQUE (stream_rules_id, target_field)
);

CREATE TABLE normalization_issue (
    id BIGSERIAL PRIMARY KEY,
    sync_run_id BIGINT NOT NULL REFERENCES sync_run(id) ON DELETE CASCADE,
    connection_id BIGINT NOT NULL,
    stream_name TEXT NOT NULL,
    source_record_id TEXT,
    target_field TEXT,
    error_code TEXT NOT NULL,        -- 'cast_error' | 'required_missing' | 'enum_unknown' | ...
    error_text TEXT,
    raw_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_normalization_issue_run ON normalization_issue(sync_run_id);
```

В `datanorma/warehouse/tables.py` добавить функцию `ensure_normalized_table(engine, *, schema='normalized', stream_rules: StreamRules) -> Table`, которая:

1. Имя таблицы: `normalized.{connector_code}__{stream_name}` (например `normalized.ozon__postings`).
2. Колонки строятся из `stream_rules.columns`:
   - `string` → `Text`,
   - `integer` → `BigInteger`,
   - `number`, `currency_amount` → `Numeric(38, 9)`,
   - `currency_code` → `String(8)`,
   - `boolean` → `Boolean`,
   - `date` → `Date`,
   - `datetime` → `DateTime(timezone=True)`,
   - `phone` → `String(32)` (E.164),
   - `email` → `String(320)`,
   - `inn` → `String(12)`, `kpp` → `String(9)`, `ogrn` → `String(15)`,
   - `enum` → `String(128)`,
   - `json` → `JSONB`.
3. Технические поля (всегда): `_ingest_run_id BIGINT`, `_ingest_extracted_at TIMESTAMPTZ`, `_ingest_loaded_at TIMESTAMPTZ DEFAULT NOW()`, `_source_record_id TEXT`, `_raw JSONB` (опционально, если в connection.settings включена опция `keep_raw_payload`).
4. Если `primary_key` не пуст — `PrimaryKeyConstraint(*primary_key)`. Иначе — суррогатный `id BIGSERIAL`.
5. Используется `checkfirst=True`; при изменении набора колонок — `ALTER TABLE` через миграцию `auto-evolve` (см. A.5).

### A.4. Переписанный `typing.py` (только утилиты)

`datanorma/normalization/typing.py` оставляем как тонкий слой утилит-кастов. Удаляем `typed_canonical_table`, `cast_rows_to_typed`, `upsert_typed_rows` в их текущем виде; переименовываем в:

- `cast_value(rule: ColumnRule, raw: Any) -> tuple[Any, Issue | None]`
- `cast_row(rules: StreamRules, raw_row: dict) -> tuple[dict, list[Issue]]`
- `upsert_rows(engine, table, rows, *, primary_key, chunk_size=500) -> dict` — общий upsert по PK, не привязанный к канонической схеме.

### A.5. Эволюция схемы normalized.* при изменении правил

Когда пользователь добавляет/удаляет колонку или меняет тип:

- Добавление колонки → автоматический `ALTER TABLE ADD COLUMN ... NULL` в начале sync-run.
- Удаление колонки → не дропаем автоматически (риск потери данных). Помечаем колонку как `_dropped` в JSONB-метаданных таблицы `normalized_table_meta` и перестаём заполнять. Кнопка «Удалить колонку из БД физически» в UI настроек подключения.
- Изменение типа → запретить online; требуем `Recreate stream` действие, которое: backup таблицы → drop → create заново → reingest.

Создать таблицу `normalized_table_meta` (миграция):

```sql
CREATE TABLE normalized_table_meta (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT NOT NULL,
    stream_name TEXT NOT NULL,
    schema_name TEXT NOT NULL DEFAULT 'normalized',
    table_name TEXT NOT NULL,
    columns JSONB NOT NULL,           -- [{target_field, type, dropped: bool}]
    last_evolved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (connection_id, stream_name)
);
```

### A.6. Обновлённый Dagster-pipeline

В `datanorma/assets/normalized.py` (заменить старую логику):

```python
@asset
def normalized_stream(context, raw_stream_records, stream_rules: StreamRules) -> NormalizedOutput:
    typed_rows, issues = apply_rules_to_batch(stream_rules, raw_stream_records)
    table = ensure_normalized_table(engine, stream_rules=stream_rules)
    upsert_rows(engine, table, typed_rows, primary_key=stream_rules.primary_key)
    write_issues_bulk(engine, run_id=context.run_id, issues=issues)
    return NormalizedOutput(rows_in=len(raw_stream_records), rows_out=len(typed_rows), issues=len(issues))
```

Удалить `datanorma/assets/typed.py` и `datanorma/assets/warehouse.py` если они привязаны к `canonical_sales`. Все ссылки в `datanorma/definitions.py` обновить.

### A.7. Дефолтные пресеты правил для известных коннекторов

Чтобы пользователь не задавал правила вручную каждый раз, для каждого коннектора в `datanorma/sources/<connector>.py` добавить метод:

```python
def default_stream_rules(self, stream_name: str, json_schema: dict) -> StreamRules:
    """Возвращает StreamRules с разумными дефолтами для типов. Пользователь может переопределить в UI."""
```

Алгоритм по умолчанию:

1. Берём `json_schema.properties`.
2. Для каждого свойства определяем тип:
   - `format: date-time` → `datetime`, `format: date` → `date`, `format: email` → `email`.
   - имя поля содержит `phone|телефон` → `phone` с `phone_default_country='RU'`.
   - имя поля содержит `inn|ИНН` → `inn`; `kpp` → `kpp`.
   - имя поля содержит `email|e_mail|почта` → `email`.
   - имя `currency|валюта` → `currency_code`; `amount|сумма|price|цена|выручка` → `currency_amount` с `decimal_separator=','` и `thousands_separator=' '`.
   - `type: number` → `number`, `type: integer` → `integer`, `type: boolean` → `boolean`, иначе → `string`.
3. `primary_key` берём из `default_cursor_field` если он явно задан (например, для Ozon — `posting_number`).

---

## 3. Блок B. Реализация недостающих коннекторов

В UI каталоге заявлены: Wildberries, Bitrix24, amoCRM, МойСклад, но в `datanorma/sources/registry.py` их нет. Реализуем их (минимально-рабочее ядро + sample-фикстуры для оффлайн-демо).

Общие требования:

- Каждый коннектор лежит в `datanorma/sources/<name>.py`, наследуется от `BaseSource`.
- В `data/samples/<name>_*.json` или `.csv` лежит фикстура (≥10 записей), которая используется когда нет API-ключей. Это требование демо-режима.
- В `datanorma/config.py` — settings-поля для credentials (env-переменные с префиксом `DATANORMA_`).
- В `datanorma/sources/registry.py` — регистрация по тем же `connector_code`, что в UI: `wildberries`, `bitrix24`, `amocrm`, `moysklad`.
- Каждый коннектор реализует `check / discover / read / default_stream_rules`.
- Обязательные тесты: `tests/test_<name>_connector.py` с тремя сценариями: (1) check без ключей читает фикстуру, (2) discover отдаёт корректный JSON Schema, (3) read возвращает > 0 записей в фикстурном режиме.

### B.1. Wildberries (`datanorma/sources/wildberries.py`)

- Базовый URL: `https://statistics-api.wildberries.ru` (Statistics API), `https://suppliers-api.wildberries.ru` (Supplier API).
- Авторизация: header `Authorization: <token>` (env `DATANORMA_WB_API_TOKEN`).
- Streams:
  - `orders` — `GET /api/v1/supplier/orders?dateFrom=YYYY-MM-DDTHH:MM:SS` (Statistics).
  - `sales` — `GET /api/v1/supplier/sales?dateFrom=...`.
  - `stocks` — `GET /api/v1/supplier/stocks?dateFrom=...`.
- Cursor: `lastChangeDate` (incremental).
- Default rules: `lastChangeDate` → datetime, `priceWithDisc`, `totalPrice` → `currency_amount` (RUB), `nmId` → `integer`, `supplierArticle` → `string`.
- Sample: `data/samples/wildberries_orders.json`, `wildberries_sales.json`, `wildberries_stocks.json`.

### B.2. Bitrix24 (`datanorma/sources/bitrix24.py`)

- Webhook-режим (проще для демо): URL вида `https://<portal>.bitrix24.ru/rest/<user_id>/<webhook_token>/`.
- Env: `DATANORMA_BITRIX24_WEBHOOK_URL`.
- Streams:
  - `crm_deals` — `crm.deal.list` (пагинация `start=0,50,100`).
  - `crm_contacts` — `crm.contact.list`.
  - `crm_leads` — `crm.lead.list`.
  - `crm_companies` — `crm.company.list`.
- Cursor: `DATE_MODIFY` (incremental).
- Default rules: `OPPORTUNITY` → `currency_amount`, `CURRENCY_ID` → `currency_code`, `DATE_CREATE`/`DATE_MODIFY` → `datetime`, `PHONE`/`EMAIL` → выгружаются как массивы, нужно их разворачивать в первое значение → `phone`/`email`.
- Sample: `data/samples/bitrix24_deals.json`, `bitrix24_contacts.json`, `bitrix24_leads.json`.

### B.3. amoCRM (`datanorma/sources/amocrm.py`)

- Long-lived token аутентификация: header `Authorization: Bearer <token>`. Env: `DATANORMA_AMOCRM_BASE_URL` (вида `https://<account>.amocrm.ru`), `DATANORMA_AMOCRM_TOKEN`.
- Streams:
  - `leads` — `GET /api/v4/leads?with=contacts&limit=250&page=N`.
  - `contacts` — `GET /api/v4/contacts?limit=250`.
  - `companies` — `GET /api/v4/companies?limit=250`.
- Pagination: `_links.next.href` → следующий курсор.
- Cursor: `updated_at` (incremental).
- Default rules: `price` → `currency_amount`, `created_at`/`updated_at` → `datetime` (UNIX timestamp → конвертировать в ISO в коде).
- Sample: `data/samples/amocrm_leads.json`, `amocrm_contacts.json`.

### B.4. МойСклад (`datanorma/sources/moysklad.py`)

- Базовый URL: `https://api.moysklad.ru/api/remap/1.2`. Bearer/Basic аутентификация. Env: `DATANORMA_MOYSKLAD_TOKEN` (или login/password).
- Streams:
  - `demand` — `GET /entity/demand?limit=100&offset=N&order=updated,asc`.
  - `customerorder` — `GET /entity/customerorder`.
  - `product` — `GET /entity/product`.
  - `counterparty` — `GET /entity/counterparty`.
- Cursor: `updated` (incremental).
- Default rules: `sum` → `currency_amount` (учитывать что МойСклад отдаёт суммы в копейках — `params.scale_factor=0.01`), `created`/`updated` → `datetime`.
- Sample: `data/samples/moysklad_demand.json`, `moysklad_customerorder.json`.

### B.5. Регистрация и UI

- Обновить `datanorma/sources/registry.py`: добавить `bitrix24`, `amocrm`, `wildberries`, `moysklad` в `SOURCE_KINDS` и в `create_source`.
- Обновить `client/src/lib/mock-data.ts` → удалить (см. блок D), а каталог коннекторов отдавать из нового API `GET /v1/connectors/catalog` (см. D.1).
- Обновить `docs/connectors.md` — описать новые коннекторы и их env.

### B.6. Тесты для каждого нового коннектора

`tests/test_wildberries_connector.py`, `test_bitrix24_connector.py`, `test_amocrm_connector.py`, `test_moysklad_connector.py` — структура одинаковая:

```python
def test_check_without_credentials_uses_fixture(tmp_path, monkeypatch):
    monkeypatch.delenv("DATANORMA_WB_API_TOKEN", raising=False)
    src = WildberriesSource(paths=DataPathsResource())
    res = src.check()
    assert res.ok and res.details["mode"] == "fixture"

def test_discover_returns_streams():
    src = WildberriesSource(paths=DataPathsResource())
    catalog = src.discover()
    assert {s.name for s in catalog.streams} >= {"orders", "sales", "stocks"}

def test_read_orders_yields_records():
    src = WildberriesSource(paths=DataPathsResource())
    rows = list(src.read("orders"))
    assert len(rows) >= 1
```

---

## 4. Блок C. Упрощение формы создания подключения

Сегодня мастер — 12 шагов (`WIZARD_STEP_LABELS`), включая сырой JSON-редактор для секретов и YAML для rest_builder. Заменим на 4 логических шага с динамической формой.

### C.1. Целевая структура — 4 шага

```ts
export const WIZARD_STEP_LABELS = [
  "Источник",         // Шаг 1: выбор коннектора + одна форма по динамической JSON-Schema (имя, описание, креды)
  "Поток и колонки",  // Шаг 2: выбор stream + редактор правил колонок
  "Приёмник",         // Шаг 3: куда грузим (postgres/csv/xlsx/clickhouse) + проверка
  "Расписание",       // Шаг 4: cron + режим (full/incremental) + старт/сохранение
] as const;
```

Шаги объединяются так:
- старые `Название`, `Источник`, `Доступ к источнику`, `Проверка источника` → один шаг **«Источник»** с inline-проверкой по кнопке «Проверить подключение».
- старые `Потоки данных`, `Маппинг`, `Нормализация` → один шаг **«Поток и колонки»** с компактным редактором.
- старые `Приёмник`, `Проверка приёмника` → один шаг **«Приёмник»**.
- старые `Расписание`, `Обзор`, `Сохранение` → один шаг **«Расписание»** с inline-обзором справа.

### C.2. Динамические формы вместо JSON-textarea

Создать `client/src/components/connection-wizard/connector-config-form.tsx`. Форма генерируется по схеме конфигурации, которую отдаёт API `GET /v1/connectors/catalog/{code}` (см. D.1). Каждый коннектор объявляет свою JSON-Schema, например для Ozon:

```json
{
  "code": "ozon",
  "title": "Ozon",
  "config_schema": {
    "type": "object",
    "required": ["client_id", "api_key"],
    "properties": {
      "client_id": {"type": "string", "title": "Client-Id", "x-format": "secret"},
      "api_key":   {"type": "string", "title": "API Key",  "x-format": "secret"},
      "fetch_limit": {"type": "integer", "title": "Лимит выборки", "default": 500, "minimum": 1, "maximum": 1000}
    }
  }
}
```

Поведение формы:
- `x-format: secret` → `<input type="password">` с маской и кнопкой показать/скрыть.
- `enum` → `<select>`.
- `format: uri` → `<input type="url">`.
- `type: integer/number` → числовое поле с min/max.
- Подсказка под полем = `description` из схемы.
- Удалить `step-source-credentials.tsx` (большой JSON-textarea) и `wizard-validation.credentialsJsonError`.
- YAML для rest_builder остаётся, но прячется под Disclosure «Расширенный режим: YAML коннектор-билдер».

### C.3. Шаг «Поток и колонки»

Заменяет 3 старых. Сверху список streams (toggle on/off), под ним для активного stream — таблица правил колонок с колонками: `source_field` (readonly из discover), `target_field` (input, с auto-suggest snake_case), `type` (select из ColumnType), `params` (контекстная мини-форма по типу), `required`, `nullable`, `on_error`, кнопка «🗑» удалить.

Кнопка `Авто-заполнить из source_schema` вызывает `POST /v1/connections/preview-rules` (см. D.2) и подтягивает дефолты.

### C.4. Inline-проверки

- На шаге «Источник» — кнопка `Проверить подключение`. Дёргает `POST /v1/sources/{id}/check`. Без перехода на отдельный шаг — статус выводится зелёной/красной плашкой под формой.
- На шаге «Приёмник» — аналогично.
- Глобальный preflight (старая `triggerEltConnection` с `dry_run=true`) — выполняется автоматически при попытке нажать «Сохранить и запустить» на шаге «Расписание». В обзоре показываем чек-лист (✅/❌) для: source ok / destination ok / streams ≥ 1 / rules valid / cron valid.

### C.5. Файлы под изменения

- Перепиcать: `client/src/components/connection-wizard/connection-wizard-shell.tsx` (с 672 строк до ~250), `wizard-constants.ts`, `wizard-types.ts`, `wizard-validation.ts`.
- Удалить: `step-check-source.tsx`, `step-check-destination.tsx`, `step-discover-streams.tsx`, `step-mapping.tsx`, `step-name.tsx`, `step-normalization.tsx`, `step-review.tsx`, `step-save-run.tsx`, `step-source-credentials.tsx`.
- Создать: `step-source.tsx` (новый, объединённый), `step-streams-and-columns.tsx`, `step-destination.tsx` (объединённый), `step-schedule.tsx` (новый, со встроенным обзором), `connector-config-form.tsx`, `column-rules-editor.tsx`.
- Сохранить URL `/connections/new`.
- Тесты: `connection-wizard.smoke.test.tsx` обновить под новую структуру; добавить `column-rules-editor.test.tsx` (Vitest + React Testing Library).

---

## 5. Блок D. Удаление заглушек и mock-data из UI

Все страницы, помеченные как «MVP-заглушка» или импортирующие `@/lib/mock-data`, заменяются реальными API-вызовами через TanStack Query. Если соответствующего API ещё нет — он создаётся.

### D.1. Новые backend endpoints

Добавить в `datanorma/web/api_router.py` (или новый файл `api_catalog.py`, регистрируется в `v1`):

| Метод | Path | Назначение |
|---|---|---|
| GET | `/v1/connectors/catalog` | Список всех зарегистрированных коннекторов (источников и приёмников) с метаданными (название, категория, регион, поддерживаемые streams, JSON-Schema конфига). Источник истины — `datanorma/sources/registry.py` + `datanorma/destinations/registry.py`, без БД. |
| GET | `/v1/connectors/catalog/{code}` | Детали одного коннектора (включая `config_schema`). |
| GET | `/v1/dictionaries` | Список справочников: статусы, валюты, единицы измерения. Источник — `datanorma/normalization/references.py` (БД-таблицы `dim_currency`, `dim_unit`, `dim_status_map`). |
| GET | `/v1/dictionaries/{code}` | Содержимое одного справочника (постранично). |
| GET | `/v1/issues` | Список проблемных записей (фильтры: `connection_id`, `stream_name`, `error_code`, `from`, `to`, пагинация). Источник — таблица `normalization_issue`. |
| GET | `/v1/issues/{id}` | Детали одной проблемы (включая raw_value JSON). |
| GET | `/v1/queue` | Текущие/недавние Dagster-ранрайнеры: статус, прогресс. Источник — `sync_run` + Dagster GraphQL. |
| GET | `/v1/activity` | Лента событий аудита (расширение существующего `/v1/audit`). |
| GET | `/v1/schedules` | Список расписаний. Источник — `sync_schedule` (создать таблицу, если нет). |
| POST | `/v1/schedules`, PUT, DELETE | CRUD расписаний. |
| GET | `/v1/dbt/models` | Список dbt-моделей с описанием и колонками. Источник — `dbt ls --output json` (выполняется при старте и кешируется в БД-таблице `dbt_model_meta`). |
| POST | `/v1/connections/preview-rules` | Body: `{source_id, stream_name}`. Возвращает `StreamRules` с дефолтами по `default_stream_rules()` коннектора. |
| GET | `/v1/connections/{id}/streams` | Список streams и их `StreamRules` для подключения. |
| PUT | `/v1/connections/{id}/streams/{name}/rules` | Сохранить/обновить `StreamRules`. |

Все endpoints используют существующий `require_operation` для RBAC.

### D.2. Frontend: убрать импорты из mock-data

Файлы, в которых нужно заменить `@/lib/mock-data` на реальные `useQuery(...)`:

- `client/src/pages/workspaces.tsx` → `GET /v1/workspaces` (есть).
- `client/src/pages/users.tsx` → `GET /v1/admin/users` (есть).
- `client/src/pages/sources.tsx` → `fetchEltSources()` (есть).
- `client/src/pages/source-new.tsx` → `GET /v1/connectors/catalog?role=source`.
- `client/src/pages/source-detail.tsx` → `fetchEltSource(id)`.
- `client/src/pages/destinations.tsx` → `fetchEltDestinations()`.
- `client/src/pages/destination-detail.tsx` → `fetchEltDestination(id)`.
- `client/src/pages/destination-new.tsx` → `GET /v1/connectors/catalog?role=destination`.
- `client/src/pages/connectors.tsx` → `GET /v1/connectors/catalog`.
- `client/src/pages/connector-detail.tsx` → `GET /v1/connectors/catalog/{code}`.
- `client/src/pages/connection-mapping.tsx` → `GET /v1/connections/{id}/streams` (правила колонок вместо `mappingRows`).
- `client/src/pages/connection-normalization.tsx` → удалить (правила теперь живут на странице маппинга/streams; маршрут `/connections/:id/normalization` редиректит на `/connections/:id/mapping`).
- `client/src/pages/normalization.tsx` → переписать как «Глобальные справочники нормализации»: словари статусов/валют/единиц через `GET /v1/dictionaries`. Удалить `data-testid="normalization-history-stub"` блок и текст про «MVP заглушка».
- `client/src/pages/normalization-rules.tsx` → удалить страницу (правила теперь per-connection); маршрут редиректит на `/connections`.
- `client/src/pages/normalization-dictionaries.tsx` → `GET /v1/dictionaries`.
- `client/src/pages/dictionaries.tsx` → `GET /v1/dictionaries`.
- `client/src/pages/schedules.tsx` → `GET /v1/schedules`.
- `client/src/pages/queue.tsx` → `GET /v1/queue`.
- `client/src/pages/activity.tsx` → `GET /v1/activity`.
- `client/src/pages/issues.tsx` → `GET /v1/issues`.
- `client/src/pages/issue-detail.tsx` → `GET /v1/issues/{id}`.
- `client/src/pages/semantic-layer.tsx` → удалить ветку `mockAsDto()`/`source: "mock"`; всегда использовать `GET /v1/dbt/models`. Если API недоступен — показать `<DemoFallbackBanner>` с явной ошибкой, а не подменять данные.
- `client/src/pages/settings.tsx` → удалить блок-заглушку `«заглушка MVP (данные появятся позже)»`. Каждая вкладка получает реальные данные:
  - «Профиль» → `GET /v1/me`,
  - «Безопасность» → `GET /v1/me/sessions` + смена пароля,
  - «Уведомления» → `GET /v1/me/notifications` (создать таблицу `user_notification_pref`),
  - «Workspace» → `GET /v1/workspaces/{code}` (есть).
- `client/src/pages/help.tsx` → загружать markdown из `/docs` репозитория через статический сервинг, а не хардкод текста.
- `client/src/pages/api-docs.tsx` → встроить Swagger UI/Redoc, ссылающийся на `/v1/openapi.json`. Удалить надпись `«REST API v1 (мок)»`.
- `client/src/pages/canonical-model.tsx` → удалить вместе с маршрутом.
- `client/src/components/command-palette.tsx` → объединить результаты из реальных запросов: `useQuery(connectors)`, `useQuery(connections)`, `useQuery(issues)`, `useQuery(runs)`. Без mock-data.
- `client/src/components/connection-wizard/step-normalization.tsx` → удалить (см. блок C).

### D.3. Удаление файла `mock-data.ts`

После того как все импорты заменены, удалить файл `client/src/lib/mock-data.ts` целиком и убрать ссылку из `tsconfig`/`vite` если есть. Запустить `npm run typecheck` — должен пройти без ошибок. Удалить `client/src/components/demo-fallback-banner.tsx` — он используется только как индикатор fallback на mock; после удаления mock баннер не нужен.

### D.4. Заглушки в backend

В `datanorma/web/deps.py` есть `from unittest.mock import MagicMock` — это используется в каких-то ветвях. Найти все места и заменить на реальные зависимости (если используется в production-коде; в тестах — оставить через `monkeypatch`).

В `datanorma/web/config.py` строка `«В production нельзя использовать значение-заглушку для DATANORMA_JWT_SECRET»` — это валидатор, оставляем как есть (это правильное поведение, не заглушка).

### D.5. Footer / общие надписи

- `client/src/components/page-footer.tsx` → заменить «`DataNorma MVP · API v1 · Europe/Moscow`» на «`DataNorma · API v1 · Europe/Moscow`». Слово «MVP» удалить также из `sidebar-content.tsx`.
- В `help.tsx` фразу «`в внутренней документации MVP`» переписать → «в документации в `docs/user_guide.md`».

---

## 6. Блок E. Дополнительные доработки и приведение в порядок

### E.1. Документация

- Переписать `docs/architecture.md` — убрать упоминания canonical_*; описать новый поток `raw → rules → normalized → semantic`.
- Переписать `docs/normalization_rules.md` — описать ColumnRule/StreamRules, типы, параметры, on_error.
- Удалить `docs/data_layers.md` старое содержимое и заменить на описание динамических таблиц `normalized.{connector}__{stream}`.
- В `docs/connectors.md` — добавить разделы по WB/Bitrix24/amoCRM/МойСклад, env-переменные, sample-фикстуры.
- Обновить `README.md`: убрать упоминание `canonical_*`; убрать «Unisender в актуальном контуре не используется» (это shadow-history, переносится в раздел `## История` если нужно сохранить).

### E.2. Seed-данные

`scripts/seed_database.py` — почистить: больше не сидим `dim_status_map` под канонические поля, а только справочники валют, единиц, статусов общего назначения. Добавить пример подключения «Ozon → CSV» с готовыми `StreamRules` для демонстрации.

### E.3. dbt

- Удалить `dbt/models/marts/canonical_sales_business.sql`.
- Оставить `dbt/models/marketing/yandex_metrika_visits.sql` и `yandex_metrika_goal_reaches.sql`, но переподключить их sources на новые имена `normalized.yandex_metrika__visits`, `normalized.yandex_metrika__goals_reaches` (через `dbt/models/sources.yml`).
- В `dbt_project.yml` — model paths без изменений.

### E.4. .env.example

Добавить новые переменные: `DATANORMA_WB_API_TOKEN`, `DATANORMA_BITRIX24_WEBHOOK_URL`, `DATANORMA_AMOCRM_BASE_URL`, `DATANORMA_AMOCRM_TOKEN`, `DATANORMA_MOYSKLAD_TOKEN`. Удалить переменные, которые больше не используются (если есть `DATANORMA_TYPED_TABLE` — удалить).

### E.5. Тесты

После всех изменений:

1. Удалить устаревшие тесты канонической модели.
2. Добавить:
   - `tests/test_column_rules.py` — юнит-тесты `cast_value` для каждого `ColumnType`.
   - `tests/test_apply_rules.py` — `apply_rules_to_batch` с типичными сценариями (хороший row, row с required=null, enum_unknown, cast_error → попадают в issues).
   - `tests/test_normalized_table_evolution.py` — добавление колонки → ALTER TABLE; смена типа → ошибка «нужен Recreate stream».
   - `tests/test_<wb|bitrix24|amocrm|moysklad>_connector.py` — см. B.6.
   - `tests/test_api_catalog.py` — `GET /v1/connectors/catalog` отдаёт все коннекторы и валидную JSON-Schema.
   - `tests/test_api_dictionaries.py`, `test_api_issues.py`, `test_api_queue.py`, `test_api_schedules.py`.
3. Обновить `conftest.py`: фикстура `default_stream_rules` для тестов.
4. Покрытие — не ниже текущего (70%+); прогон `pytest --cov=datanorma`.

### E.6. Чеклист для приёмки (что демонстрирует студент)

1. Войти под `seed_admin`/`AdminDemo2026`.
2. Создать source «Ozon» через 4-шаговый мастер (новый): credentials по форме, не JSON.
3. Discover показывает stream `postings`. Авто-правила колонок подгружаются (suma → currency_amount RUB, in_process_at → datetime MSK).
4. Создать destination «Postgres» (локальная БД).
5. Запустить sync.
6. Проверить, что в БД появилась таблица `normalized.ozon__postings` с типизированными колонками (Numeric для amount, timestamptz для in_process_at).
7. Открыть `/issues` — увидеть 0 ошибок (или несколько, если в фикстуре есть кривые записи).
8. Создать source «Wildberries» в фикстурном режиме, повторить пункты 4–6 — должна появиться `normalized.wildberries__orders`.
9. Поменять правило колонки `priceWithDisc` с RUB на USD с `convert_to_currency: RUB` → пересчёт через CBR должен работать.
10. Все страницы открываются без `Demo / mock` плашек.

---

## 7. Порядок выполнения (для Cursor)

Делаем **строго последовательно**, по одному PR на блок, между блоками — зелёные тесты:

1. **PR 1 — Блок A.1–A.5**: новые модели `ColumnRule/StreamRules`, миграция, новый normalize-pipeline, удаление canonical*. Тесты `test_column_rules.py`, `test_apply_rules.py`, `test_normalized_table_evolution.py`.
2. **PR 2 — Блок A.6–A.7**: дефолтные правила по коннекторам + Dagster assets. Прогнать end-to-end на Ozon/1c/sheets/yandex_metrika.
3. **PR 3 — Блок B**: 4 новых коннектора (WB, Bitrix24, amoCRM, МойСклад) + sample-фикстуры + тесты + регистрация.
4. **PR 4 — Блок D.1**: backend API endpoints (catalog, dictionaries, issues, queue, schedules, dbt, preview-rules, streams/rules CRUD) + тесты.
5. **PR 5 — Блок C**: новый 4-шаговый мастер; удаление старых wizard-step файлов; тесты wizard.
6. **PR 6 — Блок D.2–D.5**: замена всех импортов из `mock-data` в страницах SPA на реальные API; удаление `mock-data.ts`, `connection-normalization.tsx`, `normalization-rules.tsx`, `canonical-model.tsx`, `demo-fallback-banner.tsx`; правка footer/sidebar.
7. **PR 7 — Блок E**: документация, dbt, .env.example, seed, README, чеклист приёмки.

После каждого PR:

```bash
pytest -q
cd client && npm run typecheck && npm run test && npm run build
alembic upgrade head
```

В каждом PR — описание: список файлов, миграции (если есть), команды для проверки, скриншоты UI (для frontend-блоков).

---

## 8. Критерии завершения работы

- [ ] В коде нет файлов `canonical_*.yaml`, `to_canonical.py`, `marketing_events.py`; нет таблицы `typed_canonical_sales`.
- [ ] Все 9 коннекторов из UI каталога (`ozon`, `1c`, `google_sheets`, `yandex_metrika`, `wildberries`, `bitrix24`, `amocrm`, `moysklad`, `rest-builder`) реализованы и зарегистрированы; для каждого есть оффлайн-фикстура.
- [ ] Мастер создания подключения — 4 шага, без сырого JSON-textarea, динамические формы по `config_schema`.
- [ ] `grep -r "@/lib/mock-data" client/src` ничего не находит (кроме тестов, где явный mock на компонент).
- [ ] `grep -r "MVP" client/src` находит только в исторических местах документации, не в footer/sidebar/настройках/api-docs.
- [ ] `grep -r "заглушк" client/src datanorma` — пусто (кроме валидатора JWT в `config.py`).
- [ ] `pytest -q` зелёный, покрытие ≥ 70%.
- [ ] `npm run typecheck`, `npm run test`, `npm run build` зелёные.
- [ ] Чеклист приёмки из §E.6 выполняется.

---

## 9. Сноски и важные нюансы

- **Совместимость**: запросы старого API `/v1/sources`, `/v1/destinations`, `/v1/connections` сохраняем; добавляем новые поля (`config_schema`, `streams_with_rules`). Поле `description` подключения, в которое сейчас зашит `__DATANORMA_WIZARD__:{...}` метаданными мастера, → перевести в отдельное JSONB-поле `wizard_meta` таблицы `connection`. Миграция переноса данных обязательна.
- **Безопасность секретов**: при генерации динамической формы поля с `x-format: secret` на frontend никогда не отображают существующее значение — только маска `••••` с кнопкой «Изменить» (после клика — пустое поле).
- **i18n**: все новые user-facing строки — на русском; коды/енумы — на английском.
- **Производительность**: при `discover()` коннектор не должен качать > 200 записей; используется только для построения JSON-Schema.
- **Issues UI**: страница `/issues` обязана уметь экспорт CSV выбранных проблем (кнопка «Экспорт») — реализовать через `GET /v1/issues/export?ids=...`.

---

Готовая инструкция загружается в Cursor и выполняется по PR-ам последовательно. Если возникнут вопросы по конкретному PR — задавать в issue с тегом `[PR-N]`.
