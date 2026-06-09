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
- Слои `raw.*` / `normalized.*` **не обязательны** на этом пути: данные попадают в целевое хранилище уже после `cast_row`.

Если destination — внутренний warehouse PostgreSQL, таблицы могут создаваться динамически как `normalized.<connector_code>__<stream_name>` (`datanorma/warehouse/tables.py`).

## Warehouse-контур (опционально)

Для демо и batch-обработки в Dagster assets:

```
extract → raw_*_staging → normalized.<connector>__<stream> → dbt → semantic.*
```

Интроспекция слоёв через API: `GET /api/v1/layers/raw`, `GET /api/v1/layers/normalized`.

## Пример цепочки (Яндекс Метрика)

При загрузке во внешний PostgreSQL:

1. `source.read("visits")` — извлечение из API или фикстуры.
2. `cast_row` — типизация полей по правилам connection.
3. Запись в `destination.config.schema` / `destination.config.table`.

При warehouse-контуре:

- `normalized.yandex_metrika__visits`
- `semantic.marketing_yandex_metrika_visits` (dbt, `dbt/models/marketing/yandex_metrika_visits.sql`)

## Принципы

1. Коннектор не пишет напрямую в бизнес-витрину.
2. Нормализация (`cast_row`) не кодирует KPI и доменные отчёты.
3. Бизнес-агрегации живут в dbt-моделях `semantic.*`.
4. Каждая таблица `normalized.*` детерминирована относительно правил stream connection.

## Связанные документы

- [`dbt_models.md`](dbt_models.md) — добавление витрин.
- [`normalization_rules.md`](normalization_rules.md) — `ColumnRule` / `StreamRules`.
