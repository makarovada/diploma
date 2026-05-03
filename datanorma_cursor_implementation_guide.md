# DataNorma: подробный гайд для Cursor по доработке проекта до полноценной версии

## Как использовать этот документ

Этот документ нужно дать Cursor как основной implementation guide для репозитория `https://github.com/makarovada/diploma`.

Важно: Cursor не должен пытаться сделать весь проект за один проход. Работать нужно фазами. Каждая фаза должна заканчиваться проверкой сборки, тестов и коротким отчетом: что изменено, какие файлы затронуты, какие команды запускались, что не успели сделать.

Фактическая реализация находится в ветке `base_1`. Ветка `main` почти пустая. Перед началом работы Cursor должен перейти на `base_1` или создать рабочую ветку от `base_1`.

Актуальное продуктовое требование: **Яндекс Метрика** — source-коннектор с потоками `summary`, `visits`, `hits`, `goals_reaches` (каталог UI, бэкенд, документация, тесты). **Unisender** в актуальных списках коннекторов не используется (см. историю в конце чеклиста документации).

## Главная цель

Превратить текущий проект DataNorma из сильного, но фрагментированного MVP в цельный полноценный дипломный проект: Airbyte-like платформу интеграции и нормализации данных для МСП с российским фокусом, рабочим React UI, FastAPI backend, Dagster ELT, полноценными сущностями source/destination/connection, нормализацией, логами, ролями, рабочими пространствами и расширяемым каталогом коннекторов.

## Текущее состояние, которое Cursor должен учитывать

### Что уже есть

- Python backend на FastAPI.
- Dagster ELT pipeline.
- PostgreSQL + SQLAlchemy + Alembic.
- Jinja2 UI, который в основном работает.
- React/Vite SPA в `client/`, реализованный как каркас по фронтенд-ТЗ.
- RBAC-матрица.
- Mapping profiles с версиями.
- Sync runs через Dagster GraphQL.
- Нормализация дат, валют, телефонов, email, ФИО, статусов, единиц измерения.
- Коннекторы Ozon, 1C CSV/XLSX, Google Sheets, REST Builder.
- 58 backend тестов.

### Что критично сломано

- React UI не собирается, если в репозитории нет `client/src/lib` (или локально удалены файлы).
- `.gitignore` не должен содержать голое правило `lib/` — оно игнорирует любой каталог `lib/` в дереве, включая `client/src/lib`. Используйте `/lib/` только у корня репозитория.
- React UI пока не подключен к реальному API.
- Login в React фиктивный.
- Есть две UI-ветки: Jinja и React, без явной стратегии.

### Главные архитектурные долги

- `Connection` фактически сведена к `sync_state`.
- Нет полноценной модели `Source`.
- Нет полноценной модели `Destination`.
- Нет связи `Connection -> Streams -> Mapping -> Normalization -> Schedule`.
- Один реальный destination: PostgreSQL warehouse.
- Одна основная каноническая сущность: `canonical_sales`.
- Multi-tenancy частично заложен, но не enforced во всех запросах.
- Секреты интеграций хранятся plain-text.
- Пароли хешируются SHA-256 без соли.
- CORS небезопасен.
- Нет CI/CD.
- Нет тестов React.

## Общие правила для Cursor

### Не переписывать проект с нуля

Нельзя удалять существующий backend, Dagster pipeline, миграции, RBAC, Jinja UI или тесты без явной причины. Текущая бэкенд-база ценная. Нужно расширять и стабилизировать, а не “начать заново”.

### Работать маленькими PR-подобными шагами

Одна задача должна быть небольшой и проверяемой:

- починить React build;
- подключить login;
- добавить API client;
- добавить таблицу `source`;
- добавить Яндекс Метрику;
- добавить тесты.

Не нужно в одном изменении одновременно трогать frontend, backend, миграции, security, коннекторы и Helm.

### Сначала стабилизация, потом новые функции

Порядок обязателен:

1. Сборка React.
2. Security P0.
3. API-клиент и auth.
4. Реальная модель source/destination/connection.
5. Wizard.
6. Яндекс Метрика.
7. Остальные коннекторы.
8. Observability, deploy, docs.

### Jinja UI не удалять на ранних этапах

Jinja UI пока является рабочим fallback. До тех пор пока React UI не закрывает основные сценарии, Jinja нужно сохранить. Можно постепенно переводить функциональность в React.

### Каталог коннекторов: Яндекс Метрика

В актуальных списках и UI используется **Яндекс Метрика** (потоки выше). Для поиска остаточных `Unisender` / `unisender` / `UniSender` вне исторических примечаний — см. Фазу 6.

### Все новые API должны быть workspace-aware

Если добавляется новая таблица или endpoint, нужно учитывать `workspace_id`. Даже если старый код еще не полностью workspace-aware, новый код не должен увеличивать долг.

### Все новые секреты должны храниться безопасно

Нельзя добавлять новые plain-text секреты. Для новых integration credentials нужно проектировать шифрование или хотя бы интерфейс, совместимый с будущим encrypted storage.

### Все новые React-элементы должны иметь data-testid

Особенно:

- кнопки;
- inputs;
- selects;
- links;
- таблицы;
- строки таблиц;
- status badges;
- dynamic values;
- dialogs.

Формат:

```tsx
data-testid="button-create-connection"
data-testid="input-source-token"
data-testid="row-run-${run.id}"
data-testid="badge-connection-status-${connection.id}"
```

## Рекомендуемый рабочий процесс в Cursor

### Перед каждой фазой

Cursor должен:

1. Проверить текущую ветку.
2. Изучить релевантные файлы.
3. Составить короткий локальный план.
4. Выполнить изменения.
5. Запустить релевантные проверки.
6. Исправить ошибки.
7. Дать отчет.

### Минимальный отчет после каждой фазы

Cursor должен вернуть:

```text
Что сделано:
- ...

Измененные файлы:
- ...

Проверки:
- команда: результат
- команда: результат

Оставшиеся риски:
- ...

Следующий рекомендуемый шаг:
- ...
```

### Команды, которые нужно уточнить по репозиторию

Cursor должен сам проверить фактические scripts в `package.json`, `pyproject.toml`, `Makefile`, `README`.

Ожидаемые команды:

```bash
pytest
npm install
npm run build
npm run dev
alembic upgrade head
docker compose up
```

Если команды отличаются, использовать фактические команды из репозитория.

## Фаза 0. Стабилизация React-сборки

### Цель

Сделать React/Vite SPA собираемым и запускаемым. Без этого нельзя развивать фронтенд.

### Контекст

Сейчас 40+ React-страниц импортируют модули из `@/lib/...`, но `client/src/lib` отсутствует. Вероятная причина: `.gitignore` содержит `lib/`.

### Задачи

#### Задача 0.1. Исправить `.gitignore`

Найти правило:

```gitignore
lib/
```

Добавить исключение:

```gitignore
!client/src/lib/
!client/src/lib/**
```

Если в репозитории есть другие правила, которые исключают frontend lib, адаптировать исключение.

#### Задача 0.2. Восстановить `client/src/lib`

Создать папку:

```text
client/src/lib/
```

Минимально нужны файлы:

```text
client/src/lib/api-client.ts
client/src/lib/types.ts
client/src/lib/utils.ts
client/src/lib/mock-data.ts
client/src/lib/nav-config.ts
client/src/lib/route-utils.ts
```

Если какие-то импорты требуют другие файлы, добавить их.

#### Задача 0.3. Реализовать `utils.ts`

Нужна функция `cn`:

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Если `clsx` или `tailwind-merge` отсутствуют, проверить package.json и установить или заменить на простую реализацию.

#### Задача 0.4. Реализовать `types.ts`

Минимальные типы:

```ts
export type UserRole = "platform_admin" | "data_integrator" | "analyst" | "viewer";

export type User = {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  workspaceId?: string;
};

export type ConnectorType = "source" | "destination" | "both";

export type Connector = {
  id: string;
  code: string;
  name: string;
  type: ConnectorType;
  category: string;
  region?: "ru" | "global";
  status: "available" | "preview" | "planned";
  description: string;
  streams?: string[];
};

export type Source = {
  id: string;
  name: string;
  connectorCode: string;
  status: "connected" | "warning" | "failed" | "unchecked";
  workspaceId?: string;
  updatedAt?: string;
};

export type Destination = {
  id: string;
  name: string;
  connectorCode: string;
  status: "connected" | "warning" | "failed" | "unchecked";
  workspaceId?: string;
  updatedAt?: string;
};

export type ConnectionStatus =
  | "draft"
  | "ready"
  | "running"
  | "success"
  | "partial"
  | "failed"
  | "paused"
  | "disabled";

export type Connection = {
  id: string;
  name: string;
  description?: string;
  sourceId: string;
  destinationId: string;
  status: ConnectionStatus;
  syncMode: "full_refresh" | "incremental" | "append" | "upsert";
  schedule?: string;
  streams: string[];
  mappingCoverage?: number;
  normalizationEnabled?: boolean;
  lastRunId?: string;
  workspaceId?: string;
  updatedAt?: string;
};

export type SyncRunStatus = "queued" | "running" | "success" | "partial" | "failed" | "cancelled";

export type SyncRun = {
  id: string;
  connectionId: string;
  status: SyncRunStatus;
  stage?: "extract" | "staging" | "normalize" | "validate" | "load" | "complete";
  startedAt: string;
  finishedAt?: string;
  durationSeconds?: number;
  recordsExtracted?: number;
  recordsNormalized?: number;
  recordsLoaded?: number;
  issuesCount?: number;
  triggeredBy?: string;
};

export type NormalizationIssue = {
  id: string;
  connectionId?: string;
  runId?: string;
  severity: "info" | "warning" | "error";
  type: string;
  stream?: string;
  field?: string;
  originalValue?: string;
  suggestedValue?: string;
  status: "open" | "resolved" | "ignored";
  createdAt: string;
};
```

Типы можно расширить по фактическим props компонентов.

#### Задача 0.5. Реализовать `mock-data.ts`

Mock data нужны только для временной сборки и демонстрации, пока API не подключен. Данные должны быть реалистичными и русскоязычными.

В mock connector catalog обязательна **Яндекс Метрика** с потоками `summary`, `visits`, `hits`, `goals_reaches`; **Unisender** не включать.

Минимальный каталог:

- Ozon;
- 1C;
- Google Sheets;
- REST API Builder;
- Яндекс Метрика;
- Wildberries;
- Битрикс24;
- amoCRM;
- PostgreSQL;
- CSV;
- XLSX;
- ClickHouse.

Пример:

```ts
export const connectors = [
  {
    id: "conn-yandex-metrika",
    code: "yandex_metrika",
    name: "Яндекс Метрика",
    type: "source",
    category: "analytics",
    region: "ru",
    status: "planned",
    description: "Источник веб-аналитики: визиты, хиты, цели, UTM-метки и источники трафика.",
    streams: ["summary", "visits", "hits", "goals_reaches"],
  },
];
```

#### Задача 0.6. Реализовать `nav-config.ts`

Навигация должна соответствовать фронтенд-ТЗ:

- Дашборд;
- Активность;
- Подключения;
- Источники;
- Приемники;
- Каталог коннекторов;
- Запуски;
- Расписания;
- Очередь;
- Нормализация;
- Каноническая модель;
- Проблемные записи;
- Предпросмотр данных;
- Пользователи и роли;
- Рабочие пространства;
- Справочники;
- Настройки;
- Аудит;
- Помощь;
- API docs.

#### Задача 0.7. Реализовать `route-utils.ts`

Минимально:

- helpers для активного route;
- breadcrumbs;
- route labels.

#### Задача 0.8. Проверить сборку

Запустить:

```bash
cd client
npm install
npm run build
```

Если package scripts другие, использовать фактические.

### Acceptance criteria

- `client/src/lib` существует.
- `npm run build` проходит.
- React dev server запускается.
- В актуальном каталоге нет Unisender; есть Яндекс Метрика с потоками summary, visits, hits, goals_reaches.
- Яндекс Метрика есть в mock connector catalog.
- Не сломаны backend тесты.

## Фаза 1. Security P0

### Цель

Закрыть самые грубые security-проблемы, которые нельзя оставлять даже в дипломном проекте.

### Задачи

#### Задача 1.1. Заменить SHA-256 пароли

Найти файл:

```text
datanorma/web/passwords.py
```

Заменить `hashlib.sha256` на `passlib[bcrypt]` или `argon2-cffi`.

Рекомендуемый вариант:

```py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
```

Если в БД уже есть SHA-256 demo hashes, добавить временную миграционную совместимость:

- если hash выглядит как старый SHA-256, проверить старым способом;
- при успешном входе перехешировать bcrypt;
- для seed users сразу создавать bcrypt hashes.

#### Задача 1.2. JWT secret

Найти конфиг:

```text
datanorma/web/config.py
```

Правило:

- в dev можно использовать дефолт только если `ENV=development`;
- в production при отсутствии `DATANORMA_JWT_SECRET` приложение должно падать при старте.

#### Задача 1.3. CORS

Заменить `allow_origins=["*"]` при `allow_credentials=True` на env allow-list:

```text
DATANORMA_CORS_ORIGINS=http://localhost:5173,http://localhost:8000
```

#### Задача 1.4. Тесты

Добавить или обновить тесты:

- verify bcrypt hash;
- старый SHA fallback, если реализован;
- production без JWT secret падает;
- CORS origins берутся из env.

### Acceptance criteria

- Пароли больше не SHA-256 без соли.
- Production не стартует с `dev-insecure-change-me`.
- CORS не `*` вместе с credentials.
- Тесты проходят.

## Фаза 2. Стратегия UI: React как основной интерфейс

### Цель

Закрепить React как основной продуктовый UI, Jinja как временный fallback/admin.

### Задачи

#### Задача 2.1. Обновить документацию

В README или `docs/frontend.md` указать:

- React SPA — целевой интерфейс;
- Jinja UI — legacy/fallback на период миграции;
- новые product-facing страницы делать в React;
- backend admin/debug страницы можно временно оставлять в Jinja.

#### Задача 2.2. Раздача React через FastAPI

После `npm run build` FastAPI должен уметь отдавать SPA:

- либо через `StaticFiles`;
- либо через отдельный nginx в compose;
- для диплома проще через FastAPI static.

Нужно не сломать существующий Jinja `/app/*`.

Вариант маршрутов:

- `/` → React SPA;
- `/app/*` → Jinja legacy UI;
- `/api/*` → API;
- `/docs` или `/api-docs` → API docs.

#### Задача 2.3. React protected routes

Добавить auth provider:

- при загрузке вызывает `/api/auth/me`;
- хранит user;
- показывает loading;
- redirect на `/login` при 401;
- показывает forbidden state при 403.

### Acceptance criteria

- React UI открывается как основной интерфейс.
- Jinja `/app/*` продолжает работать.
- Login route работает в React.
- Protected pages не открываются без auth.

## Фаза 3. Реальный API client для React

### Цель

Заменить mock-запросы на единый API layer.

### Файлы

Создать/обновить:

```text
client/src/lib/api-client.ts
client/src/lib/api-types.ts
client/src/lib/query-keys.ts
client/src/lib/auth.ts
```

### API client

Нужна единая функция:

```ts
export async function apiRequest<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(path, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (res.status === 401) {
    throw new ApiError(401, "Unauthorized");
  }

  if (res.status === 403) {
    throw new ApiError(403, "Forbidden");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }

  return res.json();
}
```

Если backend возвращает не JSON для некоторых endpoints, добавить `apiDownload` или `apiText`.

### Подключить страницы

Приоритет:

1. Login.
2. `/api/auth/me`.
3. Dashboard.
4. Connections list.
5. Runs list.
6. Run detail.
7. Issues list.
8. Sources.
9. Destinations.
10. Users/workspaces.

### Правила TanStack Query

- Использовать object form:

```ts
useQuery({
  queryKey: ["connections"],
  queryFn: () => apiRequest<Connection[]>("/api/v1/connections"),
});
```

- После mutation делать invalidate:

```ts
queryClient.invalidateQueries({ queryKey: ["connections"] });
```

### Acceptance criteria

- Login в React реально вызывает backend.
- Dashboard берет реальные данные, если endpoint есть.
- Connections/Runs/Issues не завязаны на mock-data.
- Mock-data остается только для fallback/story/demo.

## Фаза 4. Полноценная модель Source, Destination, Connection

### Цель

Перейти от MVP-модели `sync_state` к нормальной Airbyte-like доменной модели.

### Новые доменные сущности

#### Source

Источник данных.

Поля:

- id;
- workspace_id;
- name;
- connector_code;
- config_encrypted;
- status;
- created_by;
- created_at;
- updated_at;
- last_checked_at.

#### Destination

Приемник данных.

Поля:

- id;
- workspace_id;
- name;
- connector_code;
- config_encrypted;
- status;
- created_by;
- created_at;
- updated_at;
- last_checked_at.

#### Connection

Сценарий интеграции.

Поля:

- id;
- workspace_id;
- name;
- description;
- source_id;
- destination_id;
- status;
- schedule_cron;
- timezone;
- is_active;
- created_by;
- created_at;
- updated_at.

#### ConnectionStream

Поток внутри connection.

Поля:

- id;
- connection_id;
- stream_name;
- sync_mode;
- cursor_field;
- primary_key;
- is_enabled;
- cursor_value;
- mapping_profile_id.

### Миграция

Создать новую Alembic migration.

Требования:

- не ломать старые таблицы;
- сделать backfill из `sync_state`;
- старый `sync_state` оставить как state/cache;
- новые таблицы должны иметь workspace_id.

### API endpoints

Добавить:

```text
GET    /api/v1/sources
POST   /api/v1/sources
GET    /api/v1/sources/{source_id}
PATCH  /api/v1/sources/{source_id}
DELETE /api/v1/sources/{source_id}
POST   /api/v1/sources/{source_id}/check
POST   /api/v1/sources/{source_id}/discover

GET    /api/v1/destinations
POST   /api/v1/destinations
GET    /api/v1/destinations/{destination_id}
PATCH  /api/v1/destinations/{destination_id}
DELETE /api/v1/destinations/{destination_id}
POST   /api/v1/destinations/{destination_id}/check

GET    /api/v1/connections
POST   /api/v1/connections
GET    /api/v1/connections/{connection_id}
PATCH  /api/v1/connections/{connection_id}
DELETE /api/v1/connections/{connection_id}
POST   /api/v1/connections/{connection_id}/trigger
POST   /api/v1/connections/{connection_id}/pause
POST   /api/v1/connections/{connection_id}/resume
```

### Acceptance criteria

- Source, Destination и Connection существуют как отдельные таблицы.
- Connection ссылается на source и destination.
- SyncRun ссылается на connection.
- Один source может использоваться в нескольких connections.
- Один destination может использоваться в нескольких connections.
- API покрыт тестами.

## Фаза 5. Connection Wizard в React

### Цель

Сделать главный пользовательский сценарий продукта: создание интеграции без ручного YAML.

### Шаги

1. Название.
2. Выбор источника.
3. Доступ к источнику.
4. Проверка источника.
5. Discover streams.
6. Выбор приемника.
7. Проверка приемника.
8. Mapping.
9. Normalization.
10. Schedule.
11. Review.
12. Save and run.

### Компоненты

Создать или доработать:

```text
client/src/components/connection-wizard/connection-wizard-shell.tsx
client/src/components/connection-wizard/step-name.tsx
client/src/components/connection-wizard/step-source.tsx
client/src/components/connection-wizard/step-source-credentials.tsx
client/src/components/connection-wizard/step-streams.tsx
client/src/components/connection-wizard/step-destination.tsx
client/src/components/connection-wizard/step-mapping.tsx
client/src/components/connection-wizard/step-normalization.tsx
client/src/components/connection-wizard/step-schedule.tsx
client/src/components/connection-wizard/step-review.tsx
```

Если текущая структура другая, не обязательно создавать именно эти файлы, но логика должна быть разделена.

### State management

Использовать React state или reducer. Не использовать localStorage/sessionStorage как основной state.

Пример:

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
  mapping: MappingRule[];
  normalizationRules: NormalizationRule[];
  schedule?: ScheduleConfig;
};
```

### Validation

Каждый шаг должен иметь:

- required fields;
- inline error;
- disabled next при blockers;
- preflight на финальном шаге.

### Acceptance criteria

- Пользователь может создать connection через UI.
- Можно выбрать source и destination.
- Можно проверить source/destination.
- Можно выбрать streams.
- Можно сохранить mapping.
- Можно сохранить normalization rules.
- Можно сохранить schedule.
- Можно запустить sync из финального шага.

## Фаза 6. Коннектор «Яндекс Метрика»

### Цель

Добавить реальный source connector и убрать устаревшие упоминания Unisender из актуальных артефактов.

### Где искать остаточные упоминания Unisender

Cursor должен выполнить поиск:

```bash
grep -Rni "unisender\\|UniSender\\|Unisender" .
```

Заменить в:

- connector catalog;
- mock data;
- docs;
- README;
- frontend labels;
- acceptance scenarios;
- тестовых фикстурах, если они обозначают список обязательных коннекторов.

Не нужно заменять только там, где явно описана история изменения требований. Там можно написать: “Изначально рассматривался Unisender, затем требование заменено на Яндекс Метрику”.

### Backend connector

Создать:

```text
datanorma/sources/yandex_metrika.py
```

Интерфейс должен соответствовать существующим source-коннекторам.

Минимальные методы:

```py
class YandexMetrikaSource:
    integration_code = "yandex_metrika"

    def check(self) -> CheckResult:
        ...

    def discover(self) -> Catalog:
        ...

    def read(self, stream: str, state: State | None = None) -> Iterator[Record]:
        ...
```

Адаптировать под фактические базовые классы проекта.

### Параметры подключения

- OAuth token или API token;
- `counter_id`;
- `date_from`;
- `date_to`;
- список metrics;
- список dimensions.

### Streams

Минимум:

- `summary`;
- `visits`;
- `hits`;
- `goals_reaches`.

### Режимы sync

- `full_refresh`;
- `incremental` по дате события/визита.

### Sample fixtures

Добавить:

```text
data/samples/yandex_metrika_summary.json
data/samples/yandex_metrika_visits.json
data/samples/yandex_metrika_hits.json
data/samples/yandex_metrika_goals_reaches.json
```

Если структура sample data в проекте другая, использовать существующую.

### Canonical mapping

Добавить сущность:

```text
canonical_marketing_events
```

или:

```text
canonical_web_visits
```

Предпочтительно `canonical_marketing_events`, потому что она шире и подойдет для VK Рекламы/Яндекс Метрики.

Минимальные поля:

- `source_system`;
- `source_record_id`;
- `counter_id`;
- `event_type`;
- `event_datetime`;
- `client_id`;
- `visit_id`;
- `traffic_source`;
- `utm_source`;
- `utm_medium`;
- `utm_campaign`;
- `device`;
- `browser`;
- `region`;
- `goal_id`;
- `goal_name`;
- `revenue`;
- `currency`;
- `_ingest_loaded_at`;
- `_ingest_meta`.

### Frontend

В connector catalog:

- название: `Яндекс Метрика`;
- категория: `Веб-аналитика`;
- тип: `Источник`;
- статус: сначала `Preview`, после backend готовности `Available`;
- streams: `summary`, `visits`, `hits`, `goals_reaches`.

В wizard:

- показывать форму токена и counter_id;
- показывать кнопку `Проверить подключение`;
- показывать discover streams.

### Тесты

Добавить:

- unit test check config validation;
- discover returns streams;
- read returns normalized records from fixtures;
- mapping to canonical_marketing_events;
- frontend catalog contains Yandex Metrika with streams summary, visits, hits, goals_reaches;
- frontend catalog has no Unisender in active connector lists.

### Acceptance criteria

- Яндекс Метрика фигурирует как актуальный source-коннектор; Unisender не используется в актуальном каталоге.
- Яндекс Метрика есть в backend registry.
- Яндекс Метрика есть в React connector catalog.
- Есть sample data.
- Есть тесты.
- Можно создать source в UI.

## Фаза 7. Destinations

### Цель

Сделать DataNorma не просто загрузчиком в один PostgreSQL, а платформой с разными приемниками.

### Backend

Создать:

```text
datanorma/destinations/base.py
datanorma/destinations/postgres.py
datanorma/destinations/csv_file.py
datanorma/destinations/xlsx_file.py
datanorma/destinations/clickhouse.py
datanorma/destinations/registry.py
```

Адаптировать под текущую архитектуру.

### Base interface

```py
class BaseDestination(Protocol):
    code: str

    def check(self, config: dict) -> CheckResult:
        ...

    def write(
        self,
        stream_name: str,
        records: Iterable[dict],
        schema: dict,
        mode: WriteMode,
    ) -> WriteResult:
        ...
```

### Write modes

- append;
- full_refresh;
- upsert;
- replace_table.

### Frontend

Destination pages должны показывать:

- список destinations;
- статус проверки;
- connector;
- где используется;
- last used;
- actions.

Wizard должен позволять выбрать destination и проверить доступ.

### Acceptance criteria

- Есть минимум PostgreSQL + CSV/XLSX destination.
- Желательно ClickHouse destination.
- Destination создается через UI.
- Connection использует выбранный destination.
- Run detail показывает load result для destination.

## Фаза 8. Каноническая модель и нормализация

### Цель

Расширить продукт за пределы продаж.

### Добавить canonical entities

Минимум:

- `canonical_marketing_events`;
- `canonical_customers`;

Желательно:

- `canonical_orders`;
- `canonical_products`;
- `canonical_inventory`.

### Нормализация

Добавить или усилить:

- ИНН;
- КПП;
- ОГРН;
- адреса;
- JSON flattening;
- UTM normalization;
- дедупликация клиентов.

### UI

Страница `Canonical model` должна:

- показывать список сущностей;
- показывать поля;
- показывать обязательность;
- показывать типы;
- показывать source aliases;
- показывать examples.

Страница `Normalization` должна:

- показывать группы правил;
- давать тестировать правило на sample input;
- показывать before/after.

### Acceptance criteria

- Яндекс Метрика маппится не в `canonical_sales`, а в marketing/web entity.
- Пользователь видит новую canonical entity в UI.
- Issues ссылаются на конкретную entity/field.

## Фаза 9. Runs, logs, issues

### Цель

Сделать мониторинг синхронизаций полноценным.

### Backend

Добавить таблицу:

```text
sync_run_log
```

Поля:

- id;
- sync_run_id;
- stage;
- level;
- message;
- technical_details;
- record_ref;
- created_at.

### API

Добавить:

```text
GET /api/v1/syncs/{id}/logs
GET /api/v1/syncs/{id}/issues
POST /api/v1/syncs/{id}/retry
POST /api/v1/issues/{id}/resolve
POST /api/v1/issues/{id}/ignore
```

### Frontend

Run detail должен показывать:

- StageTimeline;
- summary cards;
- logs;
- issues;
- retry button;
- link to connection.

Issues page должна показывать:

- severity;
- type;
- connection;
- stream;
- field;
- original value;
- suggested value;
- status;
- actions.

### Acceptance criteria

- Пользователь может открыть run и понять, где ошибка.
- Логи доступны внутри DataNorma, не только через Dagster.
- Issues можно resolve/ignore.

## Фаза 10. Multi-tenancy

### Цель

Сделать систему безопасной для нескольких компаний/workspaces.

### Backend

Добавить `workspace_id` во все новые сущности и постепенно в старые:

- source;
- destination;
- connection;
- connection_stream;
- sync_run;
- sync_run_log;
- sync_state;
- integration_config;
- mapping_profile;
- normalization_issue;
- audit_log.

### Auth

JWT должен содержать:

- user_id;
- active_workspace_id;
- role или roles;
- allowed_workspaces.

### API

Все endpoints должны фильтровать по текущему workspace.

### Frontend

Добавить workspace switcher в sidebar/topbar.

### Acceptance criteria

- Пользователь не видит данные чужого workspace.
- При переключении workspace меняются connections/runs/issues.
- Role может отличаться по workspace.

## Фаза 11. Audit log

### Цель

Все важные действия должны быть отслеживаемыми.

### Таблица

```text
audit_log
```

Поля:

- id;
- workspace_id;
- actor_user_id;
- action;
- resource_type;
- resource_id;
- result;
- payload_json;
- ip_address;
- user_agent;
- created_at.

### Логировать действия

- login success/failure;
- create source;
- update source;
- delete source;
- create destination;
- update destination;
- create connection;
- update connection;
- trigger sync;
- pause/resume connection;
- publish mapping;
- change role;
- invite user.

### UI

React page `/audit`:

- filters by actor/action/resource/date/result;
- table;
- details drawer.

### Acceptance criteria

- Mutating action создает audit record.
- Admin видит audit page.
- Analyst не видит audit page.

## Фаза 12. Tests and CI

### Цель

Сделать проект проверяемым.

### Backend tests

Добавить маркеры:

```ini
[pytest]
markers =
    unit: fast unit tests
    integration: tests requiring database or external services
    e2e: full-stack tests
```

Команды:

```bash
pytest -m unit
pytest -m integration
pytest --cov=datanorma --cov-fail-under=70
```

### Frontend tests

Добавить:

- Vitest;
- React Testing Library;
- Playwright.

Тесты:

- StatusBadge;
- ConnectorCard;
- MappingTable;
- StageTimeline;
- LogViewer;
- LoginPage;
- ConnectionWizard smoke.

### GitHub Actions

Создать:

```text
.github/workflows/ci.yml
```

Jobs:

- backend-lint;
- backend-tests;
- frontend-install;
- frontend-typecheck;
- frontend-tests;
- frontend-build;
- docker-build;
- helm-lint.

### Acceptance criteria

- CI запускается на PR.
- Нельзя слить сломанный React build.
- Нельзя слить падающие backend tests.

## Фаза 13. Deployment

### Цель

Сделать проект запускаемым целиком.

### Docker compose

Должен поднимать:

- postgres;
- dagster-webserver;
- dagster-daemon;
- fastapi;
- react static/nginx или FastAPI static.

### Dockerfile

Multi-stage:

1. Python builder.
2. Node frontend builder.
3. Runtime.

Перед стартом:

- alembic upgrade head;
- запуск app.

### Helm

Добавить:

- Secret;
- ConfigMap;
- Ingress;
- TLS values;
- migration job/init container;
- ServiceAccount;
- HPA;
- NetworkPolicy.

### Acceptance criteria

- `docker compose up` поднимает полный стек.
- После старта можно открыть React UI.
- API работает.
- Dagster доступен.
- Миграции применяются автоматически.

## Фаза 14. Документация для диплома

### Цель

Сделать проект понятным для научного руководителя, комиссии и будущего разработчика.

### Документы

Создать или обновить:

```text
README.md
docs/architecture.md
docs/frontend.md
docs/backend.md
docs/connectors.md
docs/yandex_metrika_connector.md
docs/normalization_rules.md
docs/api.md
docs/security.md
docs/deploy.md
docs/testing.md
docs/user_guide.md
docs/acceptance_plan.md
docs/adr/
```

### README

README должен быть коротким:

- что такое DataNorma;
- какие возможности;
- как запустить;
- demo users;
- ссылки на docs.

### User guide

По ролям:

- Platform Admin;
- Data Integrator;
- Analyst.

### Acceptance plan

Сценарии:

1. Login.
2. Создание source.
3. Создание destination.
4. Создание connection.
5. Mapping.
6. Normalization.
7. Запуск sync.
8. Просмотр run logs.
9. Исправление issue.
10. Проверка RBAC.
11. Яндекс Метрика flow.

### Acceptance criteria

- Документы не противоречат текущему коду.
- Яндекс Метрика отражена в документации и каталоге; Unisender убран из актуальных разделов.
- Есть инструкция запуска.
- Есть ПМИ.

## Главный супер-промпт для Cursor

Используй этот промпт в начале работы:

```text
Ты работаешь в репозитории DataNorma: https://github.com/makarovada/diploma. Фактическая реализация находится в ветке base_1. Цель — доработать проект из сильного MVP до полноценной дипломной платформы интеграции и нормализации данных для МСП. Не переписывай проект с нуля: сохрани текущий FastAPI + Dagster + PostgreSQL + Alembic + Jinja fallback + React/Vite SPA. Работай фазами, маленькими проверяемыми изменениями.

Важное изменение требований: Unisender больше не является обязательным коннектором. Везде в актуальном каталоге и документации замени его на Яндекс Метрику. Яндекс Метрика должна стать source connector для summary, visits, hits, goals_reaches.

Первый приоритет: починить React build. Сейчас отсутствует client/src/lib, вероятно из-за правила lib/ в .gitignore. Восстанови client/src/lib с api-client.ts, types.ts, utils.ts, mock-data.ts, nav-config.ts, route-utils.ts, исправь .gitignore и добейся npm run build.

После каждого этапа запускай релевантные проверки и возвращай отчет: что сделано, какие файлы изменены, какие команды запускались, что осталось.
```

## Промпт для Фазы 0

```text
Начни с Фазы 0: стабилизация React-сборки. Перейди на ветку base_1 или создай ветку от base_1. Найди все импорты из @/lib в client/src. Восстанови отсутствующую папку client/src/lib, исправь .gitignore так, чтобы client/src/lib попадала в git, реализуй минимально необходимые файлы utils.ts, types.ts, mock-data.ts, nav-config.ts, route-utils.ts и api-client.ts. В mock-data обязательно используй Яндекс Метрику вместо Unisender. После изменений запусти npm install и npm run build в client. Исправь все ошибки сборки. Не трогай backend без необходимости. В конце дай отчет.
```

## Промпт для Фазы 1

```text
Выполни Фазу 1: security P0. Найди текущую реализацию хеширования паролей и замени SHA-256 без соли на bcrypt или argon2. Обеспечь совместимость с существующими demo users или обнови сиды. Убери небезопасный production JWT secret: приложение не должно стартовать в production без DATANORMA_JWT_SECRET. Исправь CORS: нельзя использовать allow_origins=[\"*\"] вместе с allow_credentials=True. Добавь или обнови тесты. Запусти pytest. В конце дай отчет.
```

## Промпт для Фазы 2

```text
Выполни Фазу 2: закрепи React как основной UI, Jinja как fallback. Не удаляй Jinja. Настрой auth provider в React, реальный login через /api/auth/login, загрузку пользователя через /api/auth/me, protected routes, redirect на /login при 401 и forbidden state при 403. Обнови документацию, что React — целевой интерфейс, Jinja — legacy/fallback. Проверь сборку React и backend тесты.
```

## Промпт для Фазы 3

```text
Выполни Фазу 3: подключи React к реальному API. Реализуй единый api-client.ts, query keys и DTO. Замени mock-запросы на реальные API там, где endpoints уже существуют: login, auth me, dashboard, connections, runs, run detail, issues, sources, destinations, users/workspaces. Добавь loading, empty, error states. Mock-data оставь только как fallback/demo. Проверь npm run build.
```

## Промпт для Фазы 4

```text
Выполни Фазу 4: полноценная модель Source/Destination/Connection. Добавь Alembic migration с таблицами source, destination, connection, connection_stream. Не ломай существующий sync_state, используй его как cursor/cache. Сделай backfill из sync_state. Добавь API CRUD для sources, destinations, connections, check/discover и trigger. Все новые сущности должны иметь workspace_id. Добавь тесты API.
```

## Промпт для Фазы 5

```text
Выполни Фазу 5: полноценный React Connection Wizard. Реализуй шаги: название, source, source credentials, check source, discover streams, destination, check destination, mapping, normalization, schedule, review, save and run. Используй реальные API из предыдущей фазы. Добавь validation, disabled next при ошибках, preflight checks и data-testid. Проверь npm run build и добавь базовые frontend tests, если тестовый стек уже подключен.
```

## Промпт для Фазы 6

```text
Выполни Фазу 6: Яндекс Метрика вместо Unisender. Найди все актуальные упоминания Unisender и замени на Яндекс Метрику, кроме исторических пояснений об изменении требований. Добавь backend source connector datanorma/sources/yandex_metrika.py с check/discover/read. Потоки: summary, visits, hits, goals_reaches. Добавь sample fixtures, mapping в canonical_marketing_events или canonical_web_visits, обнови catalog UI и docs. Добавь tests для connector discovery/read и frontend catalog. Проверь pytest и npm run build.
```

## Промпт для Фазы 7

```text
Выполни Фазу 7: destinations. Создай абстракцию BaseDestination и registry. Реализуй минимум PostgreSQL и CSV/XLSX destination, желательно ClickHouse. Добавь destination check, write modes append/full_refresh/upsert/replace_table, API и UI. Connection должен использовать выбранный destination. Добавь тесты.
```

## Чеклист перед финальной сдачей

### Продуктовый flow

- [ ] Пользователь входит в React UI.
- [ ] Пользователь выбирает workspace.
- [ ] Пользователь создает source.
- [ ] Пользователь создает destination.
- [ ] Пользователь создает connection.
- [ ] Пользователь выбирает streams.
- [ ] Пользователь настраивает mapping.
- [ ] Пользователь включает normalization.
- [ ] Пользователь запускает sync.
- [ ] Пользователь видит run detail.
- [ ] Пользователь видит logs.
- [ ] Пользователь видит issues.
- [ ] Пользователь может retry/resync.
- [ ] Analyst не видит admin actions.
- [ ] Platform admin видит users/audit/settings.

### Яндекс Метрика

- [ ] Есть в connector catalog.
- [ ] В актуальном каталоге нет Unisender; для веб-аналитики используется Яндекс Метрика.
- [ ] Есть backend connector.
- [ ] Есть sample fixtures.
- [ ] Есть streams summary/visits/hits/goals_reaches.
- [ ] Есть mapping в marketing canonical entity.
- [ ] Есть tests.
- [ ] Есть docs.

### Техническая готовность

- [ ] `npm run build` проходит.
- [ ] `pytest` проходит.
- [ ] Есть CI.
- [ ] Есть Docker compose полного стека.
- [ ] Есть миграции.
- [ ] Секреты не plain-text.
- [ ] Пароли не SHA-256.
- [ ] CORS безопасен.
- [ ] Есть audit log.
- [ ] Есть workspace scoping.

### Документация

- [ ] README не дублируется.
- [ ] Есть architecture docs.
- [ ] Есть connector docs.
- [ ] Есть Yandex Metrika docs.
- [ ] Есть normalization rules.
- [ ] Есть API docs.
- [ ] Есть user guide.
- [ ] Есть acceptance plan.
- [ ] Есть описание изменения требований Unisender → Яндекс Метрика.

## Короткая стратегия, если времени мало

Если до сдачи мало времени, не реализовывать все российские коннекторы. Лучше сделать меньше, но глубже:

1. Починить React.
2. Подключить React к API.
3. Закрыть security P0.
4. Сделать полноценную модель Source/Destination/Connection.
5. Сделать Яндекс Метрику.
6. Сделать одну новую canonical entity для маркетинга.
7. Сделать CSV/XLSX destination.
8. Сделать e2e flow и документацию.

Это будет выглядеть сильнее, чем большой каталог карточек без реальной реализации.

