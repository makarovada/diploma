# Коннекторы DataNorma

## Общий контракт

Каждый source connector реализует:

- `check` — проверка доступности источника и конфигурации;
- `discover` — описание доступных stream и их JSON-схемы;
- `read` — чтение данных потока (`full_refresh` или `incremental`).

Реализации: `datanorma/sources/`. Регистрация: `datanorma/sources/registry.py`. Каталог в UI и API: `GET /api/v1/connectors/catalog`.

## Источники в продуктовом каталоге

В UI (`/connectors`) и мастере создания source предлагаются коннекторы с рабочим `check` на фикстурах или тестовых стендах:

| Код | Система | Layout в мастере | Потоки (примеры) |
|-----|---------|------------------|------------------|
| `google_sheet` | Google Sheets | **flat** | одна таблица |
| `bitrix24` | Bitrix24 CRM | **entities** | сделки, контакты, лиды |
| `moysklad` | МойСклад | **entities** | заказы, товары, остатки |
| `amocrm` | amoCRM | **entities** | сделки, контакты, компании |
| `yandex_metrika` | Яндекс Метрика | **entities** | summary, visits, hits, goals_reaches |
| `rest_builder` | REST API Builder | **flat** | потоки из формы или YAML |

Фикстуры для офлайн-режима: `data/samples/` и `data/fixtures/<connector>/`.

### REST API Builder (`rest_builder`)

В UI (`/sources/new`) доступна форма с полями:

- `base_url`, `auth_type`, `auth_token`, `openapi_url`, `timeout_seconds`;
- список `streams` (name, path, method, pagination, `records_json_path`);
- переключатель **Форма / YAML**;
- кнопка **Проверить запрос** → `POST /api/v1/connectors/rest-builder/probe`.

Конфиг сохраняется как structured JSON + `yaml_body` (для обратной совместимости). Альтернатива — только `yaml_body` / `connector_builder_yaml`.

Пример YAML: `datanorma/schemas/connector_builder.yaml`.

### Переменные окружения (источники)

| Коннектор | Переменные | Fallback |
|-----------|------------|----------|
| `google_sheet` | `GSPREAD_SERVICE_ACCOUNT_FILE`, `GSPREAD_SPREADSHEET_ID`, `GSPREAD_WORKSHEET` | `data/samples/google_sheet_export.csv` |
| `bitrix24` | `DATANORMA_BITRIX24_WEBHOOK_URL` | фикстуры в `data/fixtures/bitrix24/` |
| `moysklad` | `DATANORMA_MOYSKLAD_TOKEN` | фикстуры в `data/fixtures/moysklad/` |
| `amocrm` | `DATANORMA_AMOCRM_BASE_URL`, `DATANORMA_AMOCRM_TOKEN` | фикстуры в `data/fixtures/amocrm/` |
| `yandex_metrika` | `YANDEX_METRIKA_OAUTH_TOKEN`, `YANDEX_METRIKA_COUNTER_ID` | `data/samples/yandex_metrika_*.json` |
| `rest_builder` | `auth_token` в config или `env_var` в YAML | live REST API |

Для Google Sheets в UI доступен OAuth: `GET /api/v1/integrations/google/oauth/start`.

Подробнее по Яндекс Метрике: [`yandex_metrika_connector.md`](yandex_metrika_connector.md).

## Приёмники

| Код | Назначение |
|-----|------------|
| `postgres` | внешняя PostgreSQL (основной сценарий) |
| `clickhouse` | ClickHouse по HTTP |
| `csv` | выгрузка в CSV-файл |
| `xlsx` | выгрузка в Excel |

Реализации: `datanorma/destinations/`. Контракт: `check(config)` и `write(stream, records, schema, mode, config)`.

## Поток данных

Продуктовый контур — **connection sync** (`datanorma/elt/run_connection_sync.py`):

```
source.read(stream) → cast_row(StreamRules) → destination.write → sync_state
```

Коннектор **не формирует бизнес-витрины**. Структурная нормализация — per-stream правила (`ColumnRule` / `StreamRules`); бизнес-смысл — в dbt-моделях слоя `semantic.*` (опционально, после загрузки в warehouse).

## Добавление коннектора

См. [`adding_russian_connector.md`](adding_russian_connector.md).
