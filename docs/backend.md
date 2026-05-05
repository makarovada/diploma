# Backend

## Состав

- FastAPI-приложение: `datanorma/web/`
- Dagster assets: `datanorma/assets/`
- Коннекторы: `datanorma/sources/`
- Нормализация: `datanorma/normalization/`
- Загрузка/хранилище: `datanorma/warehouse/`

## Роли backend

- API для UI и интеграционных операций.
- Оркестрация sync-пайплайнов.
- Запись данных в слои `raw/normalized` и запуск `dbt_run`.
- RBAC-контроль и эксплуатационные endpoint-ы.
