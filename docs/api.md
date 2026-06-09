# API DataNorma

Базовый префикс: `/api`. Продуктовые ELT-операции — `/api/v1/*`.

Все `/api/v1` endpoints (кроме OAuth callback) требуют:
- заголовок `Authorization: Bearer <JWT>`;
- заголовок `X-Workspace-Id` — активное рабочее пространство.

## Auth

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/api/auth/login` | Получение JWT |
| POST | `/api/auth/register` | Регистрация |
| GET | `/api/auth/me` | Текущий пользователь, workspace, `permissions` |

## Workspaces и права

| Метод | Путь |
|-------|------|
| GET | `/api/v1/permissions/catalog` |
| GET/POST | `/api/v1/workspaces` |
| GET/POST/DELETE | `/api/v1/workspaces/{id}/members` |
| GET/PUT | `/api/v1/workspaces/{id}/members/{user_id}/permissions` |
| GET/POST/DELETE | `/api/v1/{sources\|destinations\|connections}/{id}/grants` |

## Каталог и справочники

| Метод | Путь |
|-------|------|
| GET | `/api/v1/connectors/catalog` |
| GET | `/api/v1/connectors/catalog/{code}` |
| GET | `/api/v1/dictionaries` |
| GET | `/api/v1/dictionaries/{code}` |

## Sources

| Метод | Путь |
|-------|------|
| GET/POST | `/api/v1/sources` |
| GET/PATCH/DELETE | `/api/v1/sources/{id}` |
| POST | `/api/v1/sources/{id}/check` |
| POST | `/api/v1/sources/{id}/discover` |

## Destinations

| Метод | Путь |
|-------|------|
| GET/POST | `/api/v1/destinations` |
| GET/PATCH/DELETE | `/api/v1/destinations/{id}` |
| POST | `/api/v1/destinations/{id}/check` |
| POST | `/api/v1/destinations/{id}/write` |

## Connections

| Метод | Путь |
|-------|------|
| GET/POST | `/api/v1/connections` |
| GET/PATCH/DELETE | `/api/v1/connections/{id}` |
| POST | `/api/v1/connections/{id}/trigger` |
| POST | `/api/v1/connections/{id}/pause` |
| POST | `/api/v1/connections/{id}/resume` |
| GET | `/api/v1/connections/{id}/streams` |
| POST | `/api/v1/connections/preview-rules` |
| PUT | `/api/v1/connections/{id}/streams/{stream}/rules` |

## Sync runs

| Метод | Путь |
|-------|------|
| GET/POST | `/api/v1/sync-streams` |
| GET/POST | `/api/v1/syncs` |
| POST | `/api/v1/syncs/trigger` |
| GET | `/api/v1/syncs/{id}` |
| GET | `/api/v1/syncs/{id}/status` |
| GET | `/api/v1/syncs/{id}/logs` |
| GET | `/api/v1/syncs/{id}/issues` |
| POST | `/api/v1/syncs/{id}/retry` |

## Issues, очередь, расписания

| Метод | Путь |
|-------|------|
| GET | `/api/v1/issues` |
| GET | `/api/v1/issues/export` |
| GET | `/api/v1/issues/{id}` |
| POST | `/api/v1/issues/{id}/resolve` |
| POST | `/api/v1/issues/{id}/ignore` |
| GET | `/api/v1/queue` |
| GET | `/api/v1/activity` |
| GET/POST/PUT/DELETE | `/api/v1/schedules`, `/api/v1/schedules/{id}` |

## Слои данных и dbt

| Метод | Путь |
|-------|------|
| GET | `/api/v1/layers/raw` |
| GET | `/api/v1/layers/normalized` |
| GET | `/api/v1/dbt/models` |
| GET | `/api/v1/dbt/models/{name}/preview` |

## Google OAuth (Sheets)

| Метод | Путь |
|-------|------|
| GET | `/api/v1/integrations/google/oauth/start` |
| GET | `/api/v1/integrations/google/oauth/callback` |
| GET | `/api/v1/integrations/google/oauth/complete` |

## Аудит

| Метод | Путь |
|-------|------|
| GET | `/api/v1/audit-log` |

## Legacy endpoints (`/api/data/*`, `/api/admin/*`)

Сохранены для совместимости демо-дашборда и старых экранов. Для новых интеграций используйте `/api/v1`:

- `/api/data/sales-summary`, `/api/data/sales-rows` — демо-агрегаты
- `/api/data/pipeline-runs`, `/api/data/staging-*` — Dagster/demo staging
- `/api/data/mapping-profiles/*` — версионированные профили (параллельный путь к stream rules)
- `/api/admin/users`, `/api/admin/roles`, `/api/admin/integration-config`

## Принципы

- Авторизация — workspace ACL (`workspace_member_permission` + `resource_grant`).
- Для новых сценариев предпочтителен `/api/v1`.
- Секреты коннекторов — в `source.config` / `destination.config` (поле `config_encrypted` в БД).
