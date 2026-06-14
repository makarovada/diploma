# Слои данных: raw, normalized, semantic

## Назначение слоёв

| Слой | Назначение |
|------|------------|
| `raw` | Неизменённые записи из источника + ingest-метаданные (`_ingest_*`, `_source_record_id`) |
| `normalized` | Структурно нормализованные таблицы: типы, даты, телефон/email/ИНН, дедупликация |
| `semantic` | Прикладные витрины для аналитики, строятся dbt-моделями |

## Продуктовый контур (connection sync)

Основной путь записи — **напрямую в destination** connection:

```
source.read → cast_row(StreamRules) → destination.write
```

- Приёмник `postgres` — схема и таблица из `destination.config` (`schema`, `table`, `primary_key`).
- Приёмники `csv` / `xlsx` — путь к файлу в config.
- Режим записи определяется `destination_sync_mode` (`refresh_overwrite`, `append`, `append_dedup`, …) — см. [`architecture.md`](architecture.md).
- Слои `raw.*` / `normalized.*` **не обязательны** на этом пути: данные попадают в целевое хранилище уже после `cast_row`.

Если destination — внутренний warehouse PostgreSQL, таблицы могут создаваться динамически как `normalized.<connector_code>__<stream_name>` (`datanorma/warehouse/tables.py`). Реестр эволюции колонок — `normalized_table_meta`.

## Warehouse-контур (опционально, Dagster)

Для демо и batch-обработки в Dagster assets:

```
sync_catalog → raw_*_staging → normalized.<connector>__<stream> → dbt → semantic.*
```

### Raw staging

Таблицы `raw_<integration_code>_<stream_name>_staging` (например `raw_google_sheet_orders_staging`, `raw_bitrix24_crm_deals_staging`):

- колонки: `ingest_batch_id`, `row_json` (JSONB), `_ingest_extracted_at`, `_ingest_meta`, …;
- создание: миграция Phase 1 (`002_phase1_ingest`) или `ensure_raw_staging_table` (`datanorma/warehouse/raw_staging.py`).

Активные потоки warehouse-контура (`datanorma/ingest/dagster_streams.py`):

| integration_code | stream_name |
|------------------|-------------|
| `google_sheet` | `orders` |
| `bitrix24` | `crm_deals` |

### Normalized asset

Asset `normalized_orders` (`datanorma/assets/normalized.py`) читает raw payloads, применяет `apply_rules_to_batch` / `default_stream_rules` и upsert в `normalized.<connector>__<stream>`.

Интроспекция слоёв через API: `GET /api/v1/layers/raw`, `GET /api/v1/layers/normalized`.

## Пример цепочки (Яндекс Метрика)

При загрузке во внешний PostgreSQL:

1. `source.read("visits")` — извлечение из API или фикстуры.
2. `cast_row` — типизация полей по правилам connection.
3. `destination.write` с `destination_sync_mode=append_dedup` — upsert в `destination.config.schema` / `destination.config.table`.

При warehouse-контуре:

- `normalized.yandex_metrika__visits`
- `semantic.marketing_yandex_metrika_visits` (dbt, `dbt/models/marketing/yandex_metrika_visits.sql`)

## sync_state

Состояние инкрементальной синхронизации хранится в таблице `sync_state`:

- **продуктовый путь** — одна строка на `connection_stream_id` (миграция 015);
- **legacy Dagster** — строки по (`integration_code`, `stream_name`) без привязки к connection;
- курсор — в `ingest_state.stream.cursor` (Ingest-style) или legacy `cursor_value`;
- при удалении `connection_stream` связанный `sync_state` удаляется каскадно (миграция 018).

## Принципы

1. Коннектор не пишет напрямую в бизнес-витрину.
2. Нормализация (`cast_row`) не кодирует KPI и доменные отчёты.
3. Бизнес-агрегации живут в dbt-моделях `semantic.*`.
4. Каждая таблица `normalized.*` детерминирована относительно правил stream connection.

## Связанные документы

- [`dbt_models.md`](dbt_models.md) — добавление витрин.
- [`normalization_rules.md`](normalization_rules.md) — `ColumnRule` / `StreamRules`.
- [`architecture.md`](architecture.md) — режимы репликации и ER-диаграмма.
