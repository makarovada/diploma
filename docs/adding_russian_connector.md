# Добавление российского коннектора (пример)

Этот гайд показывает путь от идеи до рабочего коннектора для российских сервисов (СБИС, МойСклад, Wildberries и т.д.).

## 1) Выберите подход

- **Low-code REST Builder**: опишите API в `datanorma/schemas/connector_builder.yaml`.
- **Python class source**: добавьте класс в `datanorma/sources/` с `check()/discover()/read()`.

## 2) Добавьте stream-конфиг

Обновите `datanorma/schemas/source_mappings.yaml`:

- `handler`
- `stream`
- `sync_mode`
- `cursor_field` (для incremental)
- `fields` (column map в canonical поля)

## 3) Проверьте discovery

- UI: `/app/sources/new` (check + discover).
- API: `/api/v1/connections` для регистрации stream/sync режима.

## 4) Прогоните pipeline

1. `alembic upgrade head`
2. `dagster dev -m datanorma.definitions`
3. Materialize: `sync_catalog` -> raw -> staging -> normalized -> typed -> warehouse -> dbt_run

## 5) Мультитенантность

Назначьте workspace через `/api/v1/workspaces`, чтобы пользователь видел коннектор в нужной организации.

## 6) Quality checklist

- incremental курсор обновляется в `sync_state`
- плохие строки не валят батч (`row_errors` в output staging)
- schema discover не пустой
- есть smoke tests под новый source
