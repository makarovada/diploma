# Веб-интерфейс DataNorma

- **Продуктовый UI** — React/Vite SPA (`client/`), раздаётся FastAPI под `/ui/` (корень `/` → redirect на `/ui/`).
- Маршрутизация — hash (`/#/...`); API — `/api/...` с Bearer JWT и `X-Workspace-Id`.
- Новые экраны — в `client/src/pages/...`, с `data-testid` на ключевых элементах.

Запуск: корневой [README.md](../README.md), [deploy.md](deploy.md).

## Навигация (актуальные маршруты)

Конфиг: `client/src/lib/nav-config.ts`. Роутер: `client/src/app/authenticated-shell.tsx`.

| Раздел | Маршруты |
|--------|----------|
| Обзор | `/`, `/activity` |
| Интеграции | `/connections/*`, `/sources/*`, `/destinations/*`, `/connectors/*` |
| Синхронизация | `/runs/*`, `/schedules`, `/queue` |
| Данные | `/issues/*` |
| Администрирование | `/users`, `/workspaces/*`, `/dictionaries`, `/audit` |
| Auth | `/login`, `/forbidden` |

Список dbt-моделей доступен через API (`GET /api/v1/dbt/models`); отдельной страницы semantic layer в UI нет.

## Мастер подключения

Шаг **«Колонки и типы»** (`connection-wizard`):

1. `POST /api/v1/sources/{id}/discover` → `layout` (`flat` / `entities`), `entity_labels`.
2. Маппинг полей с типами нормализации (`phone`, `email`, `inn`, `datetime`, …).
3. `POST /api/v1/connections` с `column_rules` и `wizard_meta`.

Страница правил колонок: `GET /api/v1/connections/{id}` → `column_rules`.

- **flat**-источники (Google Sheets, REST Builder): одна таблица полей.
- **entities**-источники (Bitrix24, amoCRM, МойСклад, Яндекс Метрика): чекбоксы сущностей + колонка «Сущность».

## Цвета и дальтонизм

Семантические токены в `client/src/index.css` (палитра [Paul Tol](https://sronpersonalpages.nl/~pault/)): успех — синий, ошибка — вермилион, предупреждение — жёлто-оранжевый, выполняется — сине-фиолетовый. Бейджи (`StatusBadge`) различаются иконкой и рамкой.

Проверка: Chrome DevTools → Rendering → Emulate vision deficiencies; или [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/).

После правок: `npm run build` в `client/` или `docker compose build fastapi`.

## Тесты UI

- Unit: `npm run test` (Vitest) в `client/`
- E2E: `npm run test:e2e` (Playwright)

См. [testing.md](testing.md).
