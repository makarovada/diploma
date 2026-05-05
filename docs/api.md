# API DataNorma

## Базовые префиксы

- `/api` - основной API.
- `/api/v1` - ELT-эндпоинты (sources, destinations, connections, runs и related actions).

## Auth

- `POST /api/auth/login` - получение токена.
- `GET /api/auth/me` - текущий пользователь и роли.
- RBAC-матрица: `GET /api/rbac/matrix`.

## Core data endpoints

- `GET /api/data/sales-summary`
- `GET /api/data/sales-rows`
- `GET /api/data/pipeline-runs`
- `GET /api/data/normalization-issues`
- `GET /api/data/sync-state`

## ELT v1 endpoints

- `GET/POST/PATCH/DELETE /api/v1/sources`
- `POST /api/v1/sources/{id}/check`
- `POST /api/v1/sources/{id}/discover`
- `GET/POST/PATCH/DELETE /api/v1/destinations`
- `POST /api/v1/destinations/{id}/check`
- `GET/POST/PATCH/DELETE /api/v1/connections`
- `POST /api/v1/connections/{id}/trigger`
- `POST /api/v1/connections/{id}/pause`
- `POST /api/v1/connections/{id}/resume`

## Принципы

- Все защищенные операции используют JWT и RBAC-операции.
- Для новых сценариев предпочтителен `/api/v1`.
