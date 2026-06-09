# Руководство пользователя

## Администратор пространства

- Управление участниками workspace: `/workspaces` → участники, права (`workspace_member_permission`).
- Выдача точечного доступа к объектам: `resource_grant` на source/destination/connection.
- Просмотр аудита: `/audit` (право `audit.read`).
- Управление пользователями: `/users`.

Демо-учётка: `seed_admin` / `AdminDemo2026`.

## Интегратор данных

Основной сценарий — настройка ELT-подключений:

1. **Источники** (`/sources`) — создать source, выполнить `check` и `discover`.
2. **Приёмники** (`/destinations`) — настроить `postgres` / `clickhouse` / файл.
3. **Подключения** (`/connections`) — мастер: выбор source/destination → колонки и типы → расписание.
4. **Запуски** (`/runs`) — история sync, логи, retry.
5. **Проблемные записи** (`/issues`) — ошибки `cast_row`, resolve/ignore.
6. **Расписания** (`/schedules`), **Очередь** (`/queue`) — мониторинг cron-синков.

Каталог коннекторов: `/connectors` — `google_sheet`, `bitrix24`, `moysklad`, `amocrm`, `yandex_metrika`, `rest_builder`.

Демо-учётка: `seed_integrator` / `IntegratorDemo2026`.

## Аналитик

- Просмотр активности: `/activity`, дашборд `/`.
- Мониторинг загрузок: `/runs`, статусы connection.
- Данные в приёмнике — во внешней БД или файле (не в UI DataNorma).
- dbt-витрины `semantic.*` — через warehouse и `dbt run`; список моделей: API `GET /api/v1/dbt/models`.

Права ограничены `workspace_member_permission` (без `source.create`, `connection.sync.run` и т.д., если не выданы).

Демо-учётка: `seed_analyst` / `AnalystDemo2026`.

## Переключение workspace

В UI выберите рабочее пространство; API получает `X-Workspace-Id`. После смены прав — обновление через повторный login или `GET /api/auth/me`.

## Связанные документы

- [acceptance_plan.md](acceptance_plan.md)
- [security.md](security.md)
- [testing.md](testing.md)
