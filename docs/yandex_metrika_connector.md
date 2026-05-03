# Коннектор «Яндекс Метрика»

## Назначение

Источник `yandex_metrika` в `datanorma/sources/yandex_metrika.py` реализует контракт `check` / `discover` / `read` для потоков:

- `summary` — агрегированные показатели по дням (демо: `data/samples/yandex_metrika_summary.json`);
- `visits` — визиты;
- `hits` — просмотры страниц;
- `goals_reaches` — достижения целей.

## Подключение

- **Без секретов:** при наличии всех четырёх sample-файлов в `data/samples/` коннектор проходит `check` и отдаёт данные из фикстур.
- **С OAuth:** задайте переменные окружения `YANDEX_METRIKA_OAUTH_TOKEN` и `YANDEX_METRIKA_COUNTER_ID`. Метод `check` вызывает Management API (`GET /management/v1/counter/{id}`). Чтение в текущей версии по-прежнему ориентировано на sample-файлы (отчёты Statistics API можно добавить отдельно).

## Каноническая модель

Маппинг описан в `datanorma/schemas/source_mappings.yaml` (блок `marketing`) и в логической схеме `datanorma/schemas/canonical_marketing_events.yaml`. Программный сборщик строк: `datanorma.normalization.marketing_events.build_canonical_marketing_event_rows`.

Таблица PostgreSQL: `canonical_marketing_events` (миграция `009_phase6_canonical_marketing_events`).

## UI

В демо-каталоге React (`client/src/lib/mock-data.ts`) коннектор отображается как «Яндекс Метрика» с потоками `summary`, `visits`, `hits`, `goals_reaches`.

## История требований

Изначально в продуктовых чеклистах фигурировал Unisender; актуальное требование для веб-аналитики — Яндекс Метрика с перечисленными потоками.
