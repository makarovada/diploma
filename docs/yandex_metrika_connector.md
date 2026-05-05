# Коннектор Яндекс Метрика

## Назначение

Источник `yandex_metrika` (`datanorma/sources/yandex_metrika.py`) реализует `check`, `discover`, `read`
для потоков:

- `summary`
- `visits`
- `hits`
- `goals_reaches`

## Режимы работы

- OAuth mode: используются `YANDEX_METRIKA_OAUTH_TOKEN` и `YANDEX_METRIKA_COUNTER_ID` для проверки счетчика.
- Fixture mode: при отсутствии OAuth коннектор работает на sample JSON в `data/samples/`.

## Слои данных

Для актуальной архитектуры поток должен проходить через слои:

1. `raw.yandex_metrika__<stream>`
2. `normalized.yandex_metrika__<stream>`
3. `semantic.*` через dbt-модели маркетингового домена.

Существующие legacy-таблицы и канонические сущности могут оставаться временно для обратной совместимости,
но новые изменения ориентируются на `raw/normalized/semantic`.

## dbt интеграция

Текущие модели в репозитории:

- `dbt/models/marketing/yandex_metrika_visits.sql`
- `dbt/models/marketing/yandex_metrika_goal_reaches.sql`

Модели читают из `normalized`-источников и формируют аналитический слой.

## Изменение требований

Для веб-аналитики в актуальном каталоге используется Яндекс Метрика.
Unisender в актуальных сценариях не является обязательным источником.
