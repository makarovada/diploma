# dbt модели в DataNorma

## Где находятся модели

- Каталог: `dbt/models/`
- Текущие доменные примеры:
  - `dbt/models/marketing/yandex_metrika_visits.sql`
  - `dbt/models/marketing/yandex_metrika_goal_reaches.sql`

## Как добавить новую витрину

1. Определить источник в `normalized.*`, который уже заполняется pipeline.
2. Создать SQL-модель в нужном домене (`marketing`, `ecommerce`, `crm` и т.д.).
3. Использовать `source('normalized', '<table_name>')`.
4. Добавить описание модели и колонок (в `schema.yml`, если используется в проекте).
5. Запустить `dbt run` и проверить результат в `semantic.*`.

## Пример шаблона

```sql
select
  *
from {{ source('normalized', 'your_table') }}
```

## Проверка

- Локально: `dbt run --project-dir dbt`
- Через пайплайн: asset `dbt_run` в Dagster.

## Практика проекта

В новых изменениях бизнес-смысл добавляется через dbt-модели, а не через новые `Canonical*` ORM-сущности.
