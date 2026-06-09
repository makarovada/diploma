# Правила структурной нормализации

## Цель

Слой нормализации приводит данные к консистентному техническому виду **на этапе connection sync** (`cast_row`), до записи в destination. Это структурная подготовка, а не доменная аналитическая модель.

Модели: `datanorma/normalization/rules.py`. Применение: `datanorma/normalization/typing.py`, `datanorma/normalization/apply.py`.

## StreamRules и ColumnRule

Правила хранятся в БД (`connection_stream_rules`, `connection_column_rule`) и настраиваются в мастере подключения или через API:

- `POST /api/v1/connections/preview-rules`
- `PUT /api/v1/connections/{id}/streams/{stream}/rules`

### StreamRules (на поток)

| Поле | Назначение |
|------|------------|
| `stream_name` | Имя потока из `discover` |
| `primary_key` | Ключи дедупликации |
| `cursor_field` | Поле для incremental |
| `sync_mode` | `full_refresh` / `incremental` |
| `drop_unknown_columns` | Удалять колонки без правила |
| `deduplicate` | Дедупликация по `primary_key` |

### ColumnRule (на колонку)

| Поле | Назначение |
|------|------------|
| `source_field` / `target_field` | Маппинг имён |
| `type` | См. типы ниже |
| `nullable`, `required` | Ограничения |
| `on_error` | `null` / `raise` / `keep_raw` |
| `enum_map`, `date_formats`, `timezone` | Параметры типизации |

### Поддерживаемые типы (`ColumnType`)

`string`, `integer`, `number`, `boolean`, `date`, `datetime`, `currency_amount`, `currency_code`, `phone`, `email`, `inn`, `kpp`, `ogrn`, `enum`, `json`.

Авто-вывод правил из JSON Schema: `datanorma/normalization/default_stream_rules.py`.

## Что нормализуем

- даты и время (единый формат, таймзона);
- e-mail, телефоны, ИНН/КПП/ОГРН;
- числовые типы и nullable-поля;
- enum-маппинг сырых значений;
- дедупликацию по `primary_key`.

## Что не делаем в этом слое

- не формируем финальные KPI-витрины;
- не шьём бизнес-логику конкретного отчёта;
- не заменяем dbt-модели.

## Ошибки нормализации

При `on_error: null` или `keep_raw` проблемные значения фиксируются в `normalization_issue` (привязка к `sync_run`, `connection_id`, `stream_name`, `target_field`). UI: `/issues`.

## Граница ответственности

| Слой | Ответственность |
|------|-----------------|
| extract (`source.read`) | Чтение без изменения смысла |
| normalize (`cast_row`) | Структурная чистка и типы |
| load (`destination.write`) | Запись в приёмник |
| `semantic.*` (dbt) | Бизнес-правила и аналитика |

## Связанные документы

- [`architecture.md`](architecture.md) — таблицы правил в метаданных.
- [`frontend.md`](frontend.md) — мастер «Колонки и типы».
