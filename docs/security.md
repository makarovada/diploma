# Безопасность

## Аутентификация и доступ

- JWT (Bearer) для API и React SPA.
- Изоляция данных по **рабочим пространствам** (`workspace`): пользователь видит только те пространства, куда добавлен в `user_workspace`.
- **Глобальных ролей** (`platform_admin` / `data_integrator` / `analyst`) в логике доступа больше нет; таблицы `role` / `user_role` могут оставаться для совместимости сидов.
- Внутри пространства:
  - **Администратор пространства** (`user_workspace.is_admin`) — полный доступ.
  - **Участник** — набор прав из `workspace_member_permission` (например `source.read`, `connection.sync.run`).
  - **Делегирование на объект** — `resource_grant` (уровни `view` / `edit` / `manage`) для `source`, `destination`, `connection`; выдаёт создатель объекта или администратор.

## API

- Заголовок `X-Workspace-Id` — активное пространство (дублируется в JWT).
- Каталог прав: `GET /api/v1/permissions/catalog`.
- Участники и права: `GET/POST /api/v1/workspaces/{id}/members`, `PUT .../permissions`.
- Доступ к объекту: `GET/POST/DELETE /api/v1/{sources|destinations|connections}/{id}/grants`.
- Эффективные права в UI: `GET /api/auth/me` → `permissions`, `is_workspace_admin`.

## Конфигурация

- `DATANORMA_JWT_SECRET` обязателен в production.
- `DATANORMA_ENVIRONMENT=production` — строгие проверки при старте.
- `DATANORMA_CORS_ORIGINS` — явный список origin (не `*` с credentials).

## Практики

- Не хранить секреты коннекторов в репозитории; `config_encrypted` в БД — пока JSON без шифрования (см. дорожную карту).
- OAuth client secret — `config/secrets/google_oauth_client.json` (в `.gitignore`).
- При смене прав клиент вызывает `refreshMe()` после переключения workspace.
