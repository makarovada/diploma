# Deployment

## Локальный контур (продуктовый)

1. PostgreSQL: `docker compose up -d`
2. Миграции: `alembic upgrade head`
3. Demo-данные: `python scripts/seed_database.py`
4. Backend + UI: `python -m datanorma.web`

- Web/API: `http://127.0.0.1:8080` (SPA: `/ui/`)
- Cron-синки: фоновый scheduler в FastAPI (вкл. по умолчанию; `DATANORMA_CONNECTION_SCHEDULER=0` — отключить)

## Frontend (разработка)

```bash
cd client
npm install
npm run dev
```

Dev-сервер: `http://127.0.0.1:5173` (прокси API на backend).

Production-like: `npm run build` — статика подхватывается FastAPI (`DATANORMA_UI_STATIC_DIR`).

## Dagster (опционально)

Для demo assets и `dbt_run`:

```bash
dagster dev -m datanorma.definitions
```

Dagster UI: обычно `http://127.0.0.1:3000` (`DATANORMA_DAGSTER_UI_URL`).

Для продуктового ELT достаточно FastAPI; Dagster не обязателен.

## Production (базово)

- `DATANORMA_ENVIRONMENT=production`
- Безопасный `DATANORMA_JWT_SECRET`
- Явные `DATANORMA_CORS_ORIGINS` (не `*` с credentials)
- Секреты коннекторов — в env / secret manager, не в git
- Внешний URL приёмника `postgres` в `destination.config`, не fallback на `DATABASE_URL`

## Связанные документы

- [security.md](security.md)
- [README.md](../README.md)
