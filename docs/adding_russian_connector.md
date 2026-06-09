# Добавление нового российского коннектора

Гайд для источников российского рынка (СБИС, Яндекс Маркет и др.) в актуальном ELT-контуре DataNorma.

## 1. Способ реализации

### 1.1 REST Builder (low-code)

Если источник имеет HTTP API и достаточно декларативной конфигурации:

- схема: `datanorma/schemas/connector_builder.yaml`;
- реализация: `datanorma/sources/builder.py` (`RestBuilderSource`);
- код в каталоге: `rest_builder`.

### 1.2 Python source

Если нужны сложная авторизация, нестандартная пагинация или трансформации при чтении:

1. Модуль в `datanorma/sources/<name>.py`.
2. Контракт `check()` / `discover()` / `read()`.
3. Регистрация в `datanorma/sources/registry.py` (`SOURCE_KINDS`, `create_source`).
4. Фикстуры в `data/fixtures/<connector>/` для офлайн-тестов.
5. Добавить коннектор в UI-каталог (если не скрыт): метаданные в `discover` / catalog API.

## 2. Stream rules и нормализация

Правила задаются per-connection, не глобальным YAML:

- `default_stream_rules()` в source-классе — авто-вывод из JSON Schema;
- сохранение через API:
  - `PUT /api/v1/connections/{id}/streams/{stream}/rules`
  - `POST /api/v1/connections/preview-rules`

Минимум на stream: `sync_mode`, `cursor_field` (для incremental), `primary_key`, `columns[]` (`source_field`, `target_field`, `type`, `required`, `nullable`).

Нормализация применяется в `cast_row` на этапе sync, не в отдельном batch-job.

## 3. Проверка в UI и API

| Шаг | Действие |
|-----|----------|
| check | `POST /api/v1/sources/{id}/check` |
| discover | `POST /api/v1/sources/{id}/discover` — непустые streams |
| connection | Мастер `/connections/new` → колонки и типы |
| sync | `POST /api/v1/connections/{id}/trigger` |
| state | `GET /api/v1/sync-streams` — обновление cursor |

## 4. End-to-end через connection sync

1. `alembic upgrade head`
2. `python scripts/seed_database.py` (опционально)
3. `python -m datanorma.web`
4. Создать source → destination → connection в UI.
5. Запустить sync, проверить `/runs` и данные в destination.
6. При ошибках типизации — `/issues`.

Dagster (`dagster dev -m datanorma.definitions`) — опционально для demo assets и `dbt_run`.

## 5. Чеклист качества

- incremental-курсор обновляется в `sync_state`;
- ошибки отдельных строк не валят весь batch (`on_error: null`);
- `discover` стабилен на фикстурах;
- тест `tests/test_<connector>_connector.py`;
- RBAC: операции требуют workspace-права.

## 6. Рекомендации

- Фикстуры в `data/fixtures/` и `data/samples/`.
- Документировать env-переменные в `.env.example` и `docs/connectors.md`.
- Структурную нормализацию — в `ColumnRule`; бизнес-логику — в dbt `semantic.*`.
- Для нестабильных API — ретраи и идемпотентность в `read`.

## 7. Связанные документы

- [connectors.md](connectors.md)
- [comparison_ingest.md](comparison_ingest.md)
- [testing.md](testing.md)
