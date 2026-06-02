# Архитектура DataNorma

## Контекст

DataNorma использует Airbyte-like слоистую архитектуру:
коннекторы пишут в raw-слой, нормализатор приводит данные к типизированному виду в normalized-слое,
а dbt-модели формируют бизнес-витрины в semantic-слое.

Единая глобальная каноническая модель не является дальнейшим целевым направлением:
вместо этого каждая предметная область получает набор своих dbt-моделей и витрин.

## Основной поток

1. `extract` - чтение из source connector.
2. `staging_raw` - запись сырого payload и ingest-метаданных.
3. `normalize` - структурная нормализация полей и форматов.
4. `dbt_run` - построение бизнес-витрин в `semantic.*`.
5. `validate/complete` - проверка и завершение синхронизации.

## Компоненты

- Orchestration: Dagster (`datanorma/definitions.py`, assets в `datanorma/assets/`).
- API и UI: FastAPI (`datanorma/web/`), React SPA (`client/`), раздача собранного фронта под `/ui/`.
- Хранилище: PostgreSQL + Alembic миграции.
- Семантический слой: dbt-проект в `dbt/`.

## Текущий статус

Проект работает в целевой схеме `raw -> normalized -> semantic`:
- `canonical_*` слой удалён из runtime-контура и миграций;
- нормализация выполняется по per-stream правилам (`StreamRules`/`ColumnRule`);
- бизнес-агрегации выполняются только в `dbt` моделях.

## Мастер подключения (UX)

Пользователь настраивает **колонки и типы**, а не «потоки» Airbyte:

- **flat**-источники (Google Sheets, Ozon, 1C): одна схема, таблица полей без выбора сущности.
- **entities**-источники (Wildberries, amoCRM, …): чекбоксы сущностей + колонка «Сущность» в маппинге.
- `sync_mode` / `cursor_field` задаются автоматически из `connector_schema_meta` и не показываются в мастере.
- Правила сохраняются в `connection.wizard_meta`, `connection_stream_rules`, `connection_column_rule`; синк применяет `cast_row` при наличии правил.

Внутренний контракт коннекторов (`discover` / `read` по `stream_name`) сохранён для совместимости.
