# dbt-модели в DataNorma

## Где находятся модели

- Каталог: `dbt/models/`
- Профиль: `dbt/profiles.yml` (переменная `DBT_DATABASE_URL` для override)
- Текущие модели:
  - `dbt/models/marts/normalized_orders_business.sql` — демо-витрина заказов
  - `dbt/models/marketing/yandex_metrika_visits.sql`
  - `dbt/models/marketing/yandex_metrika_goal_reaches.sql`

Источники объявлены в `dbt/models/sources.yml` (схема `normalized`, таблица `seed_demo__orders` для демо).

## Как добавить новую витрину

1. Убедиться, что в `normalized.*` есть таблица, заполняемая pipeline (destination postgres или warehouse).
2. Добавить таблицу в `dbt/models/sources.yml` под source `normalized`.
3. Создать SQL-модель в доменной папке (`marketing`, `crm`, `ecommerce` и т.д.).
4. Использовать `{{ source('normalized', '<table_name>') }}`.
5. Запустить `dbt run --project-dir dbt` и проверить результат в `semantic.*`.

## Пример шаблона

```sql
{{ config(materialized='table', schema='semantic') }}

select
    *
from {{ source('normalized', 'your_table') }}
```

## Запуск

| Способ | Команда / триггер |
|--------|-------------------|
| Локально | `dbt run --project-dir dbt` |
| Dagster | asset `dbt_run` в `datanorma/definitions.py` |
| API (просмотр) | `GET /api/v1/dbt/models`, `GET /api/v1/dbt/models/{name}/preview` |

Inline connection sync **не** вызывает dbt. Витрины пересобираются отдельным шагом.

## Практика проекта

Бизнес-смысл добавляется через dbt-модели в `semantic.*`, а не через жёстко зашитые ORM-сущности в Python. Структурная подготовка данных — в `cast_row` по `StreamRules` на этапе синка.
