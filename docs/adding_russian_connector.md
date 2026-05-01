# Добавление нового российского коннектора

Гайд описывает единый путь добавления источника данных в DataNorma для российского рынка (например, СБИС, МойСклад, Wildberries, Яндекс Маркет и др.).

## 1. Выберите способ реализации

## 1.1 Low-code через REST Builder

Используйте, если источник имеет HTTP API и достаточно декларативной конфигурации:
- файл: `datanorma/schemas/connector_builder.yaml`;
- реализация: `datanorma/sources/builder.py`.

Подходит для быстрых интеграций без отдельного Python-класса.

## 1.2 Полноценный Python source

Используйте, если нужны:
- сложная авторизация;
- нестандартная пагинация;
- специальные правила трансформации на уровне чтения.

Шаги:
1. Добавьте новый модуль в `datanorma/sources/`.
2. Реализуйте контракт `check()/discover()/read()`.
3. Зарегистрируйте источник в factory/registry (`datanorma/sources/registry.py`).

## 2. Опишите stream-конфиг и маппинг

Обновите `datanorma/schemas/source_mappings.yaml`:
- `stream`
- `handler`
- `sync_mode`
- `cursor_field` (для incremental)
- `fields` (соответствие полей источника канонической модели)
- при необходимости `options` (например, fuzzy-порог)

Важно: маппинг должен приводить данные к канонической схеме `datanorma/schemas/canonical_sales.yaml`.

## 3. Проверьте source в UI и API

Минимальные проверки:
- UI: `/app/sources/new` (check + discover);
- API: создание/обновление связи через `/api/v1/connections`.

Ожидаемо:
- `check` подтверждает доступность интеграции;
- `discover` возвращает непустую схему;
- stream корректно появляется в конфигурации связей.

## 4. Прогоните pipeline end-to-end

1. `alembic upgrade head`
2. `dagster dev -m datanorma.definitions`
3. Материализуйте:
   - `sync_catalog`
   - соответствующий raw asset
   - `staging_raw_postgres`
   - `normalized_orders`
   - `typed_canonical_sales`
   - `warehouse_sales`
   - `dbt_run` (если используется)

Проверьте:
- записи в `raw_*_staging`;
- обновление `sync_state`;
- появление данных в `canonical_sales`.

## 5. Проверка качества для нового коннектора

Чеклист:
- incremental-курсор обновляется в `sync_state`;
- ошибки отдельных строк не валят весь batch;
- `discover` стабилен и не пуст;
- есть минимум один smoke-тест для нового source;
- в UI/API нет регрессий по RBAC.

## 6. Рекомендации по production-ready развитию

- Добавляйте тестовые фикстуры в `data/samples/` для fallback-режима.
- Явно документируйте обязательные env-переменные.
- Нормализуйте поля источника как можно ближе к канонической модели, чтобы упростить downstream-логику.
- Для нестабильных API заранее закладывайте стратегию ретраев и идемпотентности чтения.

## 7. Связанные документы

- Карта проекта и runbook: `README.md`
- Сравнение с Airbyte: `docs/comparison_airbyte.md`
- Ручное тестирование: `docs/manual_testing_guide.md`
