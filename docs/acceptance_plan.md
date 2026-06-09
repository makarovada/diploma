# План приемочных испытаний (ПМИ)

## Сценарии

1. Login в UI и проверка workspace-прав (`seed_admin`, `seed_integrator`, `seed_analyst`).
2. Создание source (`yandex_metrika` или `google_sheet`).
3. Создание destination (`postgres`).
4. Создание connection через мастер (discover → колонки и типы).
5. Ручной запуск sync (`POST /api/v1/connections/{id}/trigger`).
6. Просмотр run logs и run detail (`/runs`).
7. Обработка normalization issue (resolve/ignore).
8. Проверка RBAC: запрет операций без права → `403`.
9. Яндекс Метрика: потоки `summary`, `visits`, `hits`, `goals_reaches`.
10. Cron-расписание connection и автоматический запуск (FastAPI scheduler).
11. Коннекторы CRM/учёта: smoke на `bitrix24` / `amocrm` / `moysklad` (фикстуры).

## Критерии приемки

- Документация в `docs/` соответствует коду (ELT connection, `StreamRules`, без устаревших терминов).
- Воспроизводимый запуск: `docker compose`, `alembic upgrade head`, `seed_database.py`, `python -m datanorma.web`.
- Ключевые сценарии выполняются end-to-end.
- `pytest tests/ -q` и `npm run build` в `client/` проходят без ошибок.

## Связанные документы

- [testing.md](testing.md) — smoke и Allure
- [user_guide.md](user_guide.md) — роли
