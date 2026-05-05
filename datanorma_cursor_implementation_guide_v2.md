# DataNorma: обновлённый implementation guide для Cursor

> **Ключевое архитектурное изменение по сравнению с предыдущей версией гайда:**
> Проект отказывается от концепции единой канонической модели (`canonical_sales`, `canonical_marketing_events` и т.п. как жёстко зашитых ORM-сущностей в основном backend).
> Вместо этого принимается **Airbyte-like слоистая архитектура**:
>
> | Слой | Ответственность | Где живёт |
> |---|---|---|
> | **Ingestion (Extract + Load)** | Коннекторы забирают данные из источников и пишут raw-записи в staging | `datanorma/sources/`, Dagster |
> | **Raw layer** | Хранение исходных записей без преобразований, с метаданными `_airbyte_*` | PostgreSQL schema `raw` |
> | **Typed / Normalized layer** | Типизация, дедупликация, базовая структурная нормализация (даты, телефоны, ИНН) | PostgreSQL schema `normalized`, Dagster |
> | **Semantic / Business layer** | Доменные метрики, бизнес-определения, витрины под конкретные сценарии | `dbt/` models, semantic layer |
>
> **Каноническая модель в коде бэкенда больше не является жёстко зашитым ORM-объектом.**
> Она выражается через dbt-модели в `dbt/` и может отличаться для разных бизнесов: один видит рекламную витрину, другой — сквозную воронку, третий — складской учёт.

---

## Как использовать этот документ

Дать Cursor как основной implementation guide для репозитория `https://github.com/makarovada/diploma`, ветка `base_1`.

Cursor не должен пытаться сделать весь проект за один проход. Работать нужно фазами. Каждая фаза должна заканчиваться проверкой сборки, тестов и коротким отчётом: что изменено, какие файлы затронуты, что не успели сделать.

---

## Главная цель

Превратить DataNorma из MVP с жёсткой канонической моделью в Airbyte-like платформу интеграции данных для МСП:

- универсальный слой извлечения (коннекторы) и загрузки (destinations);
- raw-слой с хранением исходных данных рядом с типизированным;
- нормализация как структурный слой, а не бизнес-смысл;
- dbt-модели как место для доменной семантики и бизнес-витрин;
- UI, в котором пользователь сам конфигурирует, что нормализовать и какие поля маппить, без жёстко зашитых "canonical" таблиц в ORM.

---

## Текущее состояние, которое Cursor должен учитывать

### Что уже есть

- Python backend на FastAPI.
- Dagster ELT pipeline.
- PostgreSQL + SQLAlchemy + Alembic.
- Jinja2 UI, который в основном работает.
- React/Vite SPA в `client/`, реализованный как каркас.
- RBAC-матрица.
- Mapping profiles с версиями.
- Sync runs через Dagster GraphQL.
- Нормализация дат, валют, телефонов, email, ФИО, статусов, единиц измерения.
- Коннекторы Ozon, 1C CSV/XLSX, Google Sheets, REST Builder.
- dbt/ директория уже есть в репозитории.
- 58 backend тестов.

### Что критично сломано

- React UI не собирается: отсутствует `client/src/lib`.
- `.gitignore` содержит правило `lib/`.
- React UI не подключён к реальному API.
- Login в React фиктивный.

### Главные архитектурные долги, которые меняем этим гайдом

- `canonical_sales` как жёстко зашитая ORM-сущность — заменяем на dbt-модель.
- Нет разделения raw / normalized / semantic schema в PostgreSQL.
- Одна основная каноническая сущность вместо гибкого слоя.
- Нет описания того, что raw-данные хранятся отдельно.

---

## Общие правила для Cursor

### Не переписывать проект с нуля

Нельзя удалять существующий backend, Dagster pipeline, миграции, RBAC, Jinja UI или тесты без явной причины.

### Работать маленькими проверяемыми шагами

Одна задача — одно изменение:
- починить React build;
- добавить raw schema в PostgreSQL;
- убрать ORM-модель `canonical_sales`, заменить на dbt-model;
- добавить API клиент;
- добавить Яндекс Метрику.

### Правило про canonical_*

**Нельзя добавлять новые ORM-классы с именами `Canonical*`.**
Если нужна каноническая структура — она описывается в `dbt/models/` как dbt-модель.
Если нужен mapping из источника в целевые поля — он описывается через MappingProfile, а не через фиксированную схему в Python.

### Jinja UI не удалять на ранних этапах

Jinja UI — рабочий fallback. Сохраняем до тех пор, пока React не закрывает основные сценарии.

### Unisender заменить на Яндекс Метрику

Cursor должен найти и заменить `Unisender`, `unisender`, `UniSender` во всех актуальных местах (каталог, mock-data, docs, README).
Исключение: история изменения требований.

### Все новые API — workspace-aware

Если добавляется новая таблица или endpoint, учитывать `workspace_id`.

### Все новые секреты — безопасно

Нельзя добавлять новые plain-text секреты.

### Все новые React-элементы — data-testid

```tsx
data-testid="button-create-connection"
data-testid="input-source-token"
data-testid="row-run-${run.id}"
data-testid="badge-connection-status-${connection.id}"
```

---

## Архитектурная модель данных (Airbyte-like)

### Схемы PostgreSQL

После рефакторинга в базе данных должны быть три отдельные схемы:

```
raw          -- исходные данные, близкие к source API
normalized   -- типизированные и структурированно нормализованные данные
public       -- платформенные таблицы (users, workspaces, connections, runs...)
```

Это не требует полного переноса существующих таблиц сразу. Новые потоки данных должны писаться по этой схеме.

### Raw-таблицы

Каждый stream коннектора пишет в таблицу вида `raw.<connector_code>__<stream_name>`.

Обязательные системные поля:

```sql
_raw_id          TEXT    -- уникальный id записи в raw-слое (UUID)
_extracted_at    TIMESTAMPTZ  -- когда извлечена из источника
_loaded_at       TIMESTAMPTZ  -- когда загружена в raw-слой
_stream_name     TEXT    -- имя потока
_source_id       UUID    -- id source в платформе
_connection_id   UUID    -- id connection
_workspace_id    UUID    -- id workspace
_data            JSONB   -- исходная запись целиком
```

Пример: `raw.yandex_metrika__visits`, `raw.ozon__orders`.

### Normalized-таблицы

После прохода через normalizer данные типизируются и пишутся в `normalized.<connector_code>__<stream_name>`.

Поля: все поля из `_data` + типизация + результат нормализации + дополнительное поле `_normalized_at`.

Пример: `normalized.yandex_metrika__visits`, `normalized.ozon__orders`.

### Semantic / dbt layer

Бизнес-витрины описываются в `dbt/models/` как SQL-модели поверх normalized-слоя.

Примеры:
```
dbt/models/marketing/visits_with_utm.sql    -- веб-аналитика
dbt/models/ecommerce/order_items.sql        -- продажи
dbt/models/crm/leads_funnel.sql             -- воронка лидов
```

**Это и есть замена "единой канонической модели"**: вместо одного Python ORM-класса `CanonicalSales` — набор dbt-моделей, каждая из которых понятна конкретному типу бизнеса.

---

## Что нужно изменить в существующем коде

### Шаг A. Переименовать / переместить canonical ORM-модели в dbt

Найти все ORM-классы или таблицы с именем `canonical_*`:

```bash
grep -Rni "canonical_" datanorma/ alembic/ --include="*.py"
```

Для каждой найденной сущности:

1. Если это SQLAlchemy ORM-модель типа `CanonicalSales` — создать соответствующий dbt-файл в `dbt/models/` вместо неё.
2. Убрать зависимость Dagster/pipeline от прямой записи в `canonical_*` таблицу.
3. Добавить dbt-run как финальный шаг pipeline вместо прямого маппинга в canonical.

Пример dbt-модели, которая заменяет `canonical_sales`:

```sql
-- dbt/models/ecommerce/orders_normalized.sql
{{ config(materialized='table', schema='semantic') }}

SELECT
    o._raw_id                      AS record_id,
    o._connection_id               AS connection_id,
    o._workspace_id                AS workspace_id,
    o._extracted_at                AS extracted_at,
    (o._data->>'order_id')::text   AS order_id,
    (o._data->>'created_at')::timestamptz AS order_date,
    (o._data->>'total_price')::numeric    AS total_amount,
    (o._data->>'currency')::text          AS currency,
    (o._data->>'status')::text            AS status
FROM {{ source('normalized', 'ozon__orders') }} o
```

### Шаг B. Нормализатор — только структурная нормализация

Существующий нормализатор (даты, валюты, телефоны, email, ФИО, статусы) **оставить как есть** — это правильно.

Изменить только одно: нормализатор должен писать результаты в `normalized.*` схему, а не в `canonical_*` таблицу.

Dagster pipeline:
```
extract → raw.* → normalizer → normalized.* → dbt run → semantic.*
```

### Шаг C. Navigation — убрать "Каноническая модель" как отдельную страницу

В `client/src/lib/nav-config.ts` заменить:
- `"Каноническая модель"` → `"Семантический слой"` (ссылка на dbt models explorer или статическая страница с описанием dbt-моделей)

В UI страница `Semantic layer` должна показывать:
- список dbt-моделей;
- для каждой: схема, поля, источники данных;
- не жёстко зашитую ORM-структуру, а конфигурацию из dbt.

---

## Фаза 0. Стабилизация React-сборки

### Цель

Сделать React/Vite SPA собираемым. Без этого нельзя развивать фронтенд.

### Задачи

#### Задача 0.1. Исправить `.gitignore`

Найти правило `lib/` и добавить исключение:

```gitignore
!client/src/lib/
!client/src/lib/**
```

#### Задача 0.2. Восстановить `client/src/lib`

Минимально нужны файлы:

```
client/src/lib/api-client.ts
client/src/lib/types.ts
client/src/lib/utils.ts
client/src/lib/mock-data.ts
client/src/lib/nav-config.ts
client/src/lib/route-utils.ts
```

#### Задача 0.3. Реализовать `utils.ts`

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

#### Задача 0.4. Реализовать `types.ts`

Полный набор типов: `User`, `Connector`, `Source`, `Destination`, `Connection`, `ConnectionStream`, `SyncRun`, `NormalizationIssue`.

**Важно: убрать тип `CanonicalEntity` как жёсткую сущность.**
Вместо этого добавить:

```ts
export type DbtModel = {
  id: string;
  name: string;
  schema: "semantic" | "normalized" | "raw";
  description?: string;
  columns: DbtColumn[];
  sources: string[];  // normalized tables this model reads from
  materializedAs: "table" | "view" | "incremental";
};

export type DbtColumn = {
  name: string;
  dataType: string;
  description?: string;
  isPrimaryKey?: boolean;
};

export type StreamSchema = {
  streamName: string;
  fields: StreamField[];
};

export type StreamField = {
  name: string;
  dataType: string;
  nullable: boolean;
  description?: string;
};
```

#### Задача 0.5. Реализовать `mock-data.ts`

Mock-данные должны отражать трёхслойную архитектуру.

Connector catalog (Unisender → Яндекс Метрика):

```ts
export const connectors = [
  {
    id: "conn-yandex-metrika",
    code: "yandex_metrika",
    name: "Яндекс Метрика",
    type: "source",
    category: "Веб-аналитика",
    region: "ru",
    status: "planned",
    description: "Источник веб-аналитики: визиты, хиты, цели, UTM-метки и источники трафика.",
    streams: ["summary", "visits", "hits", "goals_reaches"],
  },
  // Ozon, 1C, Google Sheets, REST API Builder, Wildberries,
  // Битрикс24, amoCRM, PostgreSQL, CSV, XLSX, ClickHouse
];
```

Mock dbt-модели вместо canonical entities:

```ts
export const dbtModels = [
  {
    id: "model-visits",
    name: "visits_with_utm",
    schema: "semantic",
    description: "Визиты из Яндекс Метрики с UTM-разметкой и источниками трафика.",
    sources: ["normalized.yandex_metrika__visits"],
    materializedAs: "table",
    columns: [
      { name: "visit_id", dataType: "text", isPrimaryKey: true },
      { name: "session_date", dataType: "date" },
      { name: "utm_source", dataType: "text" },
      { name: "utm_medium", dataType: "text" },
      { name: "utm_campaign", dataType: "text" },
      { name: "device_type", dataType: "text" },
      { name: "region", dataType: "text" },
      { name: "goal_count", dataType: "integer" },
    ],
  },
  {
    id: "model-orders",
    name: "order_items",
    schema: "semantic",
    description: "Заказы из Ozon с товарами и статусами.",
    sources: ["normalized.ozon__orders", "normalized.ozon__order_items"],
    materializedAs: "table",
    columns: [
      { name: "order_id", dataType: "text", isPrimaryKey: true },
      { name: "order_date", dataType: "timestamptz" },
      { name: "total_amount", dataType: "numeric" },
      { name: "currency", dataType: "text" },
      { name: "status", dataType: "text" },
    ],
  },
];
```

#### Задача 0.6. Реализовать `nav-config.ts`

Навигация должна отражать новую архитектуру:

```ts
export const navItems = [
  { label: "Дашборд", path: "/dashboard" },
  { label: "Активность", path: "/activity" },
  { label: "Подключения", path: "/connections" },
  { label: "Источники", path: "/sources" },
  { label: "Приёмники", path: "/destinations" },
  { label: "Каталог коннекторов", path: "/connectors" },
  { label: "Запуски", path: "/runs" },
  { label: "Расписания", path: "/schedules" },
  { label: "Очередь", path: "/queue" },
  // ИЗМЕНЕНО: вместо "Каноническая модель"
  { label: "Семантический слой", path: "/semantic-layer" },
  { label: "Нормализация", path: "/normalization" },
  { label: "Проблемные записи", path: "/issues" },
  { label: "Предпросмотр данных", path: "/preview" },
  { label: "Пользователи и роли", path: "/users" },
  { label: "Рабочие пространства", path: "/workspaces" },
  { label: "Справочники", path: "/dictionaries" },
  { label: "Настройки", path: "/settings" },
  { label: "Аудит", path: "/audit" },
  { label: "Помощь", path: "/help" },
  { label: "API docs", path: "/api-docs" },
];
```

#### Задача 0.7. Проверить сборку

```bash
cd client
npm install
npm run build
```

### Acceptance criteria

- `npm run build` проходит.
- React dev server запускается.
- Unisender не отображается в каталоге.
- Яндекс Метрика есть в mock connector catalog.
- "Каноническая модель" заменена на "Семантический слой" в навигации.
- Backend тесты не сломаны.

---

## Фаза 1. Security P0

(Без изменений относительно предыдущей версии.)

### Задачи

- Заменить SHA-256 на bcrypt/argon2 (`datanorma/web/passwords.py`).
- JWT secret: в production падать при старте без `DATANORMA_JWT_SECRET`.
- CORS: убрать `allow_origins=["*"]` вместе с `allow_credentials=True`.

### Acceptance criteria

- Пароли не SHA-256 без соли.
- Production не стартует без JWT secret.
- CORS безопасен.
- Тесты проходят.

---

## Фаза 2. Стратегия UI: React как основной интерфейс

(Без изменений.)

- React SPA — целевой интерфейс.
- Jinja UI — legacy/fallback.
- Настроить protected routes, auth provider.

---

## Фаза 3. Реальный API client для React

(Без изменений в механике, но добавляются новые endpoints для слоёв.)

Новые endpoints для работы с данными слоёв:

```
GET /api/v1/layers/raw?connection_id=&stream=&limit=
GET /api/v1/layers/normalized?connection_id=&stream=&limit=
GET /api/v1/dbt/models
GET /api/v1/dbt/models/{model_name}/preview
```

---

## Фаза 4. Полноценная модель Source, Destination, Connection

(Аналогично предыдущей версии, но с изменением в `ConnectionStream`.)

### ConnectionStream — добавить поля слоёв

```python
class ConnectionStream(Base):
    __tablename__ = "connection_stream"
    # ... базовые поля ...
    raw_table_name: str          # raw.<connector>__<stream>
    normalized_table_name: str   # normalized.<connector>__<stream>
    normalization_enabled: bool  # применять ли structural normalizer
    dbt_model_ref: str | None    # опциональная ссылка на dbt-модель
```

### Acceptance criteria

- Source, Destination, Connection существуют как отдельные таблицы.
- ConnectionStream знает, в какую raw/normalized таблицу писать.
- API покрыт тестами.

---

## Фаза 5. Connection Wizard в React

Шаги wizard — аналогично предыдущей версии, но шаг "Mapping" переформулируется.

### Шаг mapping (обновлённый)

Вместо "маппинг в каноническую сущность":

- показать discovered schema источника;
- дать возможность включить/отключить поля;
- дать возможность переименовать поля для normalized-слоя;
- опционально: показать список dbt-моделей, которые могут использовать этот stream, и предложить выбрать "шаблон бизнес-витрины".

### Шаг normalization

- toggle: включить structural normalization;
- показать список активных правил: типизация дат, телефонов, email, ИНН, статусов;
- показать preview: before / after для sample record.

### WizardState

```ts
type WizardState = {
  name: string;
  description?: string;
  sourceId?: string;
  sourceConnectorCode?: string;
  sourceConfig: Record<string, unknown>;
  discoveredStreams: DiscoveredStream[];
  selectedStreams: SelectedStream[];
  destinationId?: string;
  destinationConnectorCode?: string;
  destinationConfig: Record<string, unknown>;
  fieldMapping: FieldMapping[];          // field rename/include/exclude
  normalizationEnabled: boolean;
  normalizationRules: NormalizationRule[];
  dbtModelTemplate?: string;            // опциональный шаблон витрины
  schedule?: ScheduleConfig;
};
```

---

## Фаза 6. Яндекс Метрика вместо Unisender

### Где заменить Unisender

```bash
grep -Rni "unisender\|UniSender\|Unisender" .
```

Заменить во всех актуальных местах.

### Backend connector

```python
# datanorma/sources/yandex_metrika.py

class YandexMetrikaSource:
    integration_code = "yandex_metrika"

    def check(self) -> CheckResult: ...
    def discover(self) -> Catalog: ...
    def read(self, stream: str, state: State | None = None) -> Iterator[Record]: ...
```

Параметры: OAuth/API token, `counter_id`, `date_from`, `date_to`, metrics, dimensions.

Streams: `summary`, `visits`, `hits`, `goals_reaches`.

### Raw таблицы коннектора

Коннектор должен писать в:
- `raw.yandex_metrika__summary`
- `raw.yandex_metrika__visits`
- `raw.yandex_metrika__hits`
- `raw.yandex_metrika__goals_reaches`

**Не нужно маппить в canonical_marketing_events как ORM-сущность.**
Вместо этого создать dbt-модель:

```sql
-- dbt/models/marketing/yandex_metrika_visits.sql
{{ config(materialized='table', schema='semantic') }}

SELECT
    v._raw_id            AS record_id,
    v._workspace_id      AS workspace_id,
    v._connection_id     AS connection_id,
    (v._data->>'visitId')::text            AS visit_id,
    (v._data->>'dateTime')::timestamptz    AS visit_datetime,
    (v._data->>'clientId')::text           AS client_id,
    (v._data->>'trafficSource')::text      AS traffic_source,
    (v._data->>'utmSource')::text          AS utm_source,
    (v._data->>'utmMedium')::text          AS utm_medium,
    (v._data->>'utmCampaign')::text        AS utm_campaign,
    (v._data->>'deviceCategory')::text     AS device,
    (v._data->>'regionName')::text         AS region,
    (v._data->>'goalReachesCount')::int    AS goal_count
FROM {{ source('normalized', 'yandex_metrika__visits') }} v
```

```sql
-- dbt/models/marketing/yandex_metrika_goal_reaches.sql
{{ config(materialized='table', schema='semantic') }}

SELECT
    g._raw_id            AS record_id,
    g._workspace_id      AS workspace_id,
    (g._data->>'goalId')::text             AS goal_id,
    (g._data->>'goalName')::text           AS goal_name,
    (g._data->>'dateTime')::timestamptz    AS reached_at,
    (g._data->>'revenue')::numeric         AS revenue,
    (g._data->>'currency')::text           AS currency
FROM {{ source('normalized', 'yandex_metrika__goals_reaches') }} g
```

### Sample fixtures

```
data/samples/yandex_metrika_summary.json
data/samples/yandex_metrika_visits.json
data/samples/yandex_metrika_hits.json
data/samples/yandex_metrika_goals_reaches.json
```

### Тесты

- unit test: check config validation;
- discover returns streams;
- read returns records from fixtures;
- records write into `raw.yandex_metrika__visits` (not into `canonical_*`);
- dbt-модель `yandex_metrika_visits` читает из правильного source;
- frontend catalog содержит Яндекс Метрику;
- frontend catalog не показывает Unisender.

### Acceptance criteria

- Unisender не фигурирует как актуальный коннектор.
- Яндекс Метрика пишет в raw-таблицы, не в canonical ORM.
- dbt-модели для маркетинга есть в `dbt/models/marketing/`.
- Есть sample data и тесты.

---

## Фаза 7. Destinations

(Аналогично предыдущей версии.)

BaseDestination, PostgreSQL + CSV/XLSX + ClickHouse, write modes.

**Дополнение:** destination должен уметь писать как в `normalized.*`, так и принимать результаты dbt-run из `semantic.*`.

---

## Фаза 8. Semantic Layer UI (вместо фазы "Каноническая модель")

### Цель

Показать пользователю бизнес-витрины, которые доступны поверх его данных, без жёстко зашитых ORM-сущностей.

### Backend

Добавить API:

```
GET /api/v1/dbt/models                    -- список dbt-моделей
GET /api/v1/dbt/models/{name}             -- детали модели
GET /api/v1/dbt/models/{name}/preview     -- sample rows из semantic.*
POST /api/v1/dbt/run                      -- запустить dbt run
GET /api/v1/dbt/runs                      -- история dbt runs
GET /api/v1/dbt/runs/{run_id}/logs        -- логи dbt run
```

Для чтения списка моделей можно парсить `dbt/models/**/*.sql` или `dbt/target/manifest.json` (если dbt compile уже запускался).

### React страница `/semantic-layer`

Заменяет `/canonical-model`.

Должна показывать:

- список dbt-моделей с группировкой по домену (marketing, ecommerce, crm, operations);
- для каждой модели: схема, источники, список колонок, описание;
- кнопку "Preview" — показать sample из `semantic.*`;
- кнопку "Run dbt" — запустить обновление витрин;
- статус последнего dbt run.

Пример структуры:

```
Семантический слой
├── Marketing
│   ├── yandex_metrika_visits
│   └── yandex_metrika_goal_reaches
├── Ecommerce
│   ├── order_items
│   └── products
└── CRM
    └── leads_funnel
```

### dbt/models структура

Если в репозитории уже есть `dbt/`, добавить:

```
dbt/
├── dbt_project.yml
├── profiles.yml.example
├── sources.yml                     -- описание raw/normalized sources
├── models/
│   ├── marketing/
│   │   ├── yandex_metrika_visits.sql
│   │   └── yandex_metrika_goal_reaches.sql
│   ├── ecommerce/
│   │   └── order_items.sql
│   └── crm/
│       └── leads_funnel.sql
└── tests/
```

### Нормализация UI

Страница `/normalization` остаётся, но фокус — на structural rules, не на канонической схеме:

- группы правил: даты, телефоны, email, ИНН/КПП, статусы, единицы измерения;
- тест правила: input → output;
- before/after для sample record из normalized-слоя.

### Acceptance criteria

- Страница `/canonical-model` переименована в `/semantic-layer`.
- UI показывает dbt-модели, а не ORM-сущности.
- Есть dbt-модели для Яндекс Метрики.
- API для dbt models работает.
- Preview из semantic.* работает.

---

## Фаза 9. Runs, logs, issues

(Аналогично предыдущей версии + добавление dbt run в pipeline.)

### Dagster pipeline stages

После рефакторинга pipeline должен иметь явные стадии:

```
extract → staging_raw → normalize → dbt_run → validate → complete
```

- `staging_raw`: запись в `raw.*` таблицы;
- `normalize`: structural normalizer → запись в `normalized.*`;
- `dbt_run`: запуск dbt моделей → запись в `semantic.*`.

Лог должен отражать эти стадии в UI.

---

## Фазы 10–14

Аналогично предыдущей версии:

- Фаза 10: Multi-tenancy.
- Фаза 11: Audit log.
- Фаза 12: Tests and CI.
- Фаза 13: Deployment.
- Фаза 14: Документация.

**Изменение в Фазе 14 (Документация):**

Добавить или обновить:

```
docs/architecture.md                -- обновить: описать три слоя (raw/normalized/semantic)
docs/data_layers.md                 -- НОВЫЙ: описание raw/normalized/semantic схем
docs/dbt_models.md                  -- НОВЫЙ: как добавить новую бизнес-витрину
docs/normalization_rules.md         -- обновить: structural normalization, не canonical mapping
docs/connectors.md                  -- обновить: коннекторы пишут в raw.*, не в canonical_*
docs/yandex_metrika_connector.md    -- обновить: raw tables + dbt models
```

В `docs/architecture.md` явно написать:

> DataNorma использует Airbyte-like слоистую архитектуру:
> коннекторы пишут в raw-слой, нормализатор приводит данные к типизированному виду в normalized-слое,
> а dbt-модели формируют бизнес-витрины в semantic-слое.
> Единая глобальная каноническая модель не используется:
> каждый тип бизнеса получает свои витрины через набор dbt-моделей,
> что позволяет одному пользователю видеть только рекламные метрики,
> другому — воронку продаж, третьему — складской учёт.

---

## Главный промпт для Cursor

```
Ты работаешь в репозитории DataNorma: https://github.com/makarovada/diploma, ветка base_1.

АРХИТЕКТУРНОЕ ИЗМЕНЕНИЕ: проект переходит от единой канонической модели к Airbyte-like слоистой архитектуре.
Больше нельзя добавлять ORM-классы с именем Canonical* или писать данные напрямую в canonical_* таблицы из pipeline.
Вместо этого:
- Коннекторы пишут в raw.* (schema raw в PostgreSQL).
- Normalizer трансформирует в normalized.* (schema normalized).
- dbt-модели в dbt/models/ формируют бизнес-витрины в semantic.* schema.

Сохрани текущий FastAPI + Dagster + PostgreSQL + Alembic + Jinja fallback + React/Vite SPA.
Не переписывай с нуля. Работай фазами.

Важное изменение требований: Unisender → Яндекс Метрика. Заменить везде в актуальном каталоге.

Яндекс Метрика должна писать в raw.yandex_metrika__visits, raw.yandex_metrika__hits и т.д., а dbt-модели в dbt/models/marketing/ обеспечивают бизнес-смысл.

Первый приоритет: починить React build. Отсутствует client/src/lib. Исправить .gitignore, восстановить lib, убрать "Каноническая модель" из навигации, добавить "Семантический слой".

После каждого этапа — отчёт: что сделано, какие файлы изменены, что осталось.
```

---

## Промпт для Фазы 0

```
Фаза 0: стабилизация React-сборки. Перейди на ветку base_1.
Найди все импорты из @/lib в client/src. Восстанови client/src/lib:
utils.ts, types.ts, mock-data.ts, nav-config.ts, route-utils.ts, api-client.ts.

ВАЖНО:
- В mock-data: Unisender → Яндекс Метрика. Добавить mock dbtModels вместо canonicalEntities.
- В types.ts: добавить DbtModel, DbtColumn, StreamSchema, StreamField. Не добавлять тип CanonicalEntity.
- В nav-config.ts: "Каноническая модель" → "Семантический слой" (path: /semantic-layer).

Запустить npm install и npm run build в client. Исправить все ошибки. В конце отчёт.
```

---

## Промпт для Фазы 6 (Яндекс Метрика)

```
Фаза 6: Яндекс Метрика вместо Unisender.
Найди все упоминания Unisender в актуальном каталоге и замени.

Backend: datanorma/sources/yandex_metrika.py — check/discover/read.
Streams: summary, visits, hits, goals_reaches.
Данные должны идти в raw.yandex_metrika__<stream>, НЕ в canonical_marketing_events ORM.

dbt-модели: создай dbt/models/marketing/yandex_metrika_visits.sql и yandex_metrika_goal_reaches.sql,
читающие из source('normalized', 'yandex_metrika__visits') и т.д.

Sample fixtures в data/samples/.
Тесты: connector пишет в raw.*, dbt-модель читает из normalized.*.
Проверить pytest и npm run build.
```

---

## Промпт для Фазы 8 (Semantic Layer UI)

```
Фаза 8: Semantic Layer UI.

Backend: добавить endpoints GET /api/v1/dbt/models, GET /api/v1/dbt/models/{name}/preview.
Читать список моделей из dbt/models/**/*.sql или dbt/target/manifest.json.

Frontend: переименовать страницу /canonical-model → /semantic-layer.
Показывать список dbt-моделей, сгруппированных по домену (marketing, ecommerce, crm).
Для каждой: название, описание, список колонок, источники.
Кнопка Preview показывает sample rows из semantic.* schema.

Страница /normalization: показывать structural rules (даты, телефоны, email, ИНН), before/after preview.
Нормализация — это структурный слой, не бизнес-каноническая схема.
```

---

## Чеклист перед финальной сдачей

### Архитектурный чеклист (новый)

- [ ] Нет ORM-классов с именем `Canonical*` в новом коде.
- [ ] Коннекторы пишут в `raw.*`, не в `canonical_*`.
- [ ] Есть schema `raw` и `normalized` в PostgreSQL.
- [ ] dbt/models/ содержит как минимум 2 рабочих модели.
- [ ] Dagster pipeline имеет стадии: extract → raw → normalize → dbt_run.
- [ ] Навигация содержит "Семантический слой", не "Каноническая модель".
- [ ] UI `/semantic-layer` показывает dbt-модели.

### Продуктовый flow

- [ ] Пользователь входит в React UI.
- [ ] Создаёт source → destination → connection.
- [ ] Выбирает streams, настраивает field mapping и normalization.
- [ ] Запускает sync: данные попадают в raw.*, normalized.*, semantic.*.
- [ ] Видит run detail с этапами extract / normalize / dbt_run.
- [ ] Открывает /semantic-layer, видит dbt-модели и preview данных.
- [ ] Analyst не видит admin actions.

### Яндекс Метрика

- [ ] Есть в connector catalog.
- [ ] Нет Unisender как актуального обязательного connector.
- [ ] Backend connector пишет в raw.yandex_metrika__*.
- [ ] Есть dbt-модели в dbt/models/marketing/.
- [ ] Есть sample fixtures и тесты.
- [ ] Есть документация.

### Техническая готовность

- [ ] `npm run build` проходит.
- [ ] `pytest` проходит.
- [ ] Есть CI.
- [ ] Есть Docker compose полного стека.
- [ ] Секреты не plain-text.
- [ ] CORS безопасен.

### Документация

- [ ] docs/architecture.md описывает три слоя (raw/normalized/semantic).
- [ ] docs/data_layers.md описывает схемы PostgreSQL.
- [ ] docs/dbt_models.md объясняет, как добавить витрину.
- [ ] Явно написано, почему единая каноническая модель заменена на dbt-слой.
