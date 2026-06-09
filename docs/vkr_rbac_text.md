# Текст для ВКР: роли, доступ и UI-контур

Материал для раздела ВКР о разграничении доступа и пользовательском контуре платформы DataNorma.

## 1. Модель доступа (workspace ACL)

Единица изоляции — **рабочее пространство** (`workspace`). Пользователь видит только пространства из `user_workspace`.

- **Администратор пространства** (`user_workspace.is_admin`) — полный доступ, приглашение участников, выдача прав.
- **Участник** — набор строк в `workspace_member_permission` (например `source.create`, `connection.sync.run`).
- **Делегирование на объект** — таблица `resource_grant` (уровни `view` / `edit` / `manage`); выдаёт создатель ресурса или администратор.

Каталог прав: `GET /api/v1/permissions/catalog`. Глобальные роли (`role`, `user_role`) в проверках ELT API не участвуют.

## 2. Аутентификация и авторизация

- Веб-приложение: `python -m datanorma.web`.
- JWT (Bearer); активное пространство — `X-Workspace-Id` и `allowed_workspace_ids` в claims.
- `GET /api/auth/me` → `permissions`, `is_workspace_admin`.
- При отсутствии прав — `403 Forbidden`.

## 3. Пользовательский и операционный контуры

- **Пользовательский контур** — React SPA (`/ui/`): подключения, источники, приёмники, запуски, issues. Синки запускаются через API (`run_connection_sync` inline в FastAPI).
- **Операционный контур** — опционально Dagster: demo assets, `dbt_run`, sensor cron (дублирует FastAPI scheduler).

Разделение позволяет интеграторам работать в продуктовом UI, а разработчикам — диагностировать pipeline в Dagster при необходимости.

## 4. Аргументация для приемки

Для подтверждения RBAC в ВКР рекомендуется показать:

- таблицу «право × операция» на основе `GET /api/v1/permissions/catalog`;
- скриншоты разделов под разными учётками;
- примеры `2xx` и `403`;
- соответствие меню (`client/src/lib/nav-config.ts`) и API-доступов.

Демо-учётки:

- `seed_admin` / `AdminDemo2026`
- `seed_integrator` / `IntegratorDemo2026`
- `seed_analyst` / `AnalystDemo2026`

## 5. Ограничения MVP

- `config_encrypted` в БД — JSON без шифрования at-rest (дорожная карта).
- Inline sync не запускает dbt автоматически.
- Часть `/api/data/*` — legacy demo endpoints.

## 6. Связанные документы

- [README.md](../README.md)
- [security.md](security.md)
- [frontend.md](frontend.md)
- [comparison_ingest.md](comparison_ingest.md)
