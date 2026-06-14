# DataNorma

DataNorma - дипломная платформа интеграции и нормализации данных для МСП.
Текущий контур сочетает FastAPI, Dagster, PostgreSQL, dbt и React/Vite UI.

## Что важно сейчас

- Интерфейс: React SPA под `/ui/` (сборка из `client/`).
- Продуктовый контур: **connection sync** — `source.read → cast_row(StreamRules) → destination.write` (режим записи: `destination_sync_mode`).
- Нормализация per-stream: `ColumnRule` / `StreamRules` в мастере подключения.
- Источники в каталоге: `google_sheet`, `bitrix24`, `moysklad`, `amocrm`, `yandex_metrika`, `rest_builder`.
- Приёмники: `postgres`, `clickhouse`, `csv`, `xlsx`.
- Бизнес-витрины — dbt-модели в `semantic.*` (опционально, после загрузки в warehouse).

## Быстрый запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
docker compose up -d
alembic upgrade head
python scripts/seed_database.py
```

Запуск (продуктовый контур):

```bash
python -m datanorma.web
```

- Web/API: `http://127.0.0.1:8080`

Опционально Dagster (demo assets, dbt): `dagster dev -m datanorma.definitions` → UI обычно `http://127.0.0.1:3000`

## Demo users

- `seed_admin` / `AdminDemo2026`
- `seed_integrator` / `IntegratorDemo2026`
- `seed_analyst` / `AnalystDemo2026`

## Документация

- `docs/architecture.md` - архитектура и поток данных.
- `docs/data_layers.md` - схемы `raw/normalized/semantic`.
- `docs/dbt_models.md` - как добавлять новые dbt-витрины.
- `docs/connectors.md` - источники и контракт коннекторов.
- `docs/yandex_metrika_connector.md` - коннектор Яндекс Метрики.
- `docs/normalization_rules.md` - структурная нормализация.
- `docs/frontend.md` - React SPA, маршруты, мастер подключения.
- `docs/api.md` - API и основные endpoints.
- `docs/security.md` - auth, RBAC, CORS, секреты.
- `docs/deploy.md` - локальный и базовый production deployment.
- `docs/testing.md` - тесты и проверки.
- `docs/user_guide.md` - руководство по ролям.
- `docs/acceptance_plan.md` - ПМИ/сценарии приемки.
