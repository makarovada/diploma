# Тестирование

## Основные проверки

- Backend tests: `pytest tests/ -q`
- Frontend build: `npm run build` в `client/`

## Что проверяется

- API и RBAC-ограничения.
- Коннекторы и чтение потоков.
- Нормализация и обработка issues.
- Pipeline stages и post-load dbt run.

## Smoke для фазы 14

1. Войти в UI под demo-пользователями.
2. Проверить создание source/destination/connection.
3. Запустить sync и открыть run history.
4. Проверить страницу `semantic-layer` и наличие dbt-источников данных.
