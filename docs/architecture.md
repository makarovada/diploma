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
- API и UI: FastAPI (`datanorma/web/`), React SPA (`client/`), Jinja fallback (`/app/*`).
- Хранилище: PostgreSQL + Alembic миграции.
- Семантический слой: dbt-проект в `dbt/`.

## Текущий переходный статус

В кодовой базе еще встречаются legacy-артефакты с `canonical_*`.
Для новых изменений используется слой `raw/normalized/semantic`; legacy-части сохраняются
для совместимости и поэтапного рефакторинга.
