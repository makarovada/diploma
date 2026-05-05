# Безопасность

## Аутентификация и доступ

- JWT используется для API и React UI.
- RBAC-матрица определяет операции по ролям (`Platform Admin`, `Data Integrator`, `Analyst`).
- Legacy Jinja-flow использует тот же auth-контур и ограничения операций.

## Конфигурация

- `DATANORMA_JWT_SECRET` обязателен в production.
- `DATANORMA_ENVIRONMENT=production` включает stricter проверки окружения.
- `DATANORMA_CORS_ORIGINS` должен быть явно задан в production.

## Практики

- Не хранить секреты в репозитории.
- Использовать `.env`/секрет-хранилище и ротацию ключей.
- Проверять, что `allow_origins=*` не используется вместе с credentialed requests.
