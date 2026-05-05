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

## 2. Опишите stream-конфиг и правила нормализации

Используйте `default_stream_rules()` в source-классе и/или сохранение правил через API:
- `PUT /api/v1/connections/{connection_id}/streams/{stream_name}/rules`
- `POST /api/v1/connections/preview-rules`

Минимальный набор на stream:
- `sync_mode`
- `cursor_field` (для incremental)
- `primary_key`
- `columns[]` (`source_field`, `target_field`, `type`, `required`, `nullable`)

Важно: в актуальном контуре маппинг должен обеспечивать корректный путь
`raw.* -> normalized.* -> semantic.*` и не обходить слои напрямую.

## 3. Проверьте source в UI и API

Минимальные проверки:
- UI: `/app/sources/new` (check + discover);
- API: потоки `sync_state` через `/api/v1/sync-streams`; доменные connections — `/api/v1/connections`.

Ожидаемо:
- `check` подтверждает доступность интеграции;
- `discover` возвращает непустую схему;
- stream корректно появляется в конфигурации связей.

## 4. Прогоните pipeline end-to-end

1. `alembic upgrade head`
2. `dagster dev -m datanorma.definitions`
3. Материализуйте:
   - `sync_catalog`
   - соответствующий `extract/raw` asset
   - `staging_raw_postgres`
   - `normalize`-слой (`normalized_*`)
   - `dbt_run`
   - проверка данных в `semantic.*`

Проверьте:
- записи в `raw_*_staging`;
- обновление `sync_state`;
- появление данных в `normalized.*` и затем в `semantic.*`.

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
- Нормализуйте поля источника как можно ближе к структурной схеме `normalized`-слоя, а бизнес-логику выносите в dbt.
- Для нестабильных API заранее закладывайте стратегию ретраев и идемпотентности чтения.

## 7. Связанные документы

- Карта проекта и runbook: `README.md`
- Сравнение с Ingest: `docs/comparison_ingest.md`
- Ручное тестирование: `docs/manual_testing_guide.md`
