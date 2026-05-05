# Deployment

## Локальный контур

1. Поднять PostgreSQL: `docker compose up -d`.
2. Применить миграции: `alembic upgrade head`.
3. Заполнить demo-данные: `python scripts/seed_database.py`.
4. Запустить backend/UI: `python -m datanorma.web`.
5. Запустить оркестрацию: `dagster dev -m datanorma.definitions`.

## Frontend

- Для dev: в `client/` выполнить `npm install` и `npm run dev`.
- Для production-like: `npm run build` и публикация собранного UI через FastAPI static.

## Production базово

- Выставить `DATANORMA_ENVIRONMENT=production`.
- Задать безопасные значения `DATANORMA_JWT_SECRET` и CORS origins.
- Хранить секреты вне git (env/secret manager).
