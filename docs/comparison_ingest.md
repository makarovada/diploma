# Сравнение DataNorma и Ingest

Документ фиксирует позиционирование DataNorma как MVP-платформы интеграции данных для МСП в РФ.
По смыслу DataNorma следует продуктовой модели Ingest: `sources → connections → sync → destination`, реализованной на FastAPI + PostgreSQL + React.

## Краткое сравнение

| Аспект | Ingest | DataNorma (текущее состояние) |
|--------|---------|-------------------------------|
| **Назначение** | Универсальная EL(T)-платформа, большой ecosystem | Вертикально сфокусированный MVP под SMB РФ |
| **Sources** | Большой каталог + marketplace | `google_sheet`, `bitrix24`, `moysklad`, `amocrm`, `yandex_metrika`, `rest_builder` |
| **Destinations** | Много хранилищ и БД | `postgres`, `clickhouse`, `csv`, `xlsx` |
| **Connections** | Богатая модель связей в UI | Полный CRUD + мастер колонок/типов/репликации, cron, pause/resume |
| **Incremental state** | Нативный state-протокол | `sync_state` per `connection_stream`, `ingest_state` (Ingest-style), CASCADE при удалении потока |
| **Destination sync mode** | `destination_sync_mode` per stream | `refresh_overwrite`, `append`, `append_dedup`, … → `WriteMode` приёмника |
| **Нормализация** | Typing/Dedup + dbt | `ColumnRule` / `StreamRules`, `cast_row` при синке; dbt для `semantic.*` |
| **Оркестрация** | Собственный runtime | Inline sync в FastAPI + опционально Dagster (demo/dbt) |
| **UI/API** | Зрелая product-консоль | FastAPI + React SPA (`/ui/`) + `/api/v1/*` |
| **RBAC** | Enterprise IAM | Workspace ACL + `resource_grant` |
| **Расширяемость** | CDK/коннекторы | Python source framework + REST Builder (YAML) |

## Что уже близко к Ingest

- Единая терминология `sources` / `destinations` / `connections` / `syncs`.
- Парные режимы `sync_mode` + `destination_sync_mode` (как в Ingest Protocol).
- Инкрементальный контур со state в БД (`ingest_state`).
- Мастер настройки колонок, типов и репликации per stream.
- API/UI для операционной работы интегратора.
- Нормализация на этапе load, issues в UI.

## Что остаётся развить

- Расширить библиотеку готовых российских коннекторов.
- Автоматический `dbt run` после успешного sync.
- Усилить production-контур (шифрование `config_encrypted`, observability).
- Расширить no-code UX для REST Builder.

## Связанные документы

- [README.md](../README.md)
- [acceptance_plan.md](acceptance_plan.md)
- [frontend.md](frontend.md) — маршруты UI
