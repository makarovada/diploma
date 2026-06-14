# Веб-интерфейс DataNorma

Продуктовый UI — React/Vite SPA в каталоге `client/`. Сборка раздаётся FastAPI под `/ui/` (корень `/` → redirect на `/ui/`).

| Параметр | Значение |
|----------|----------|
| Роутинг | hash (`/#/...`), библиотека [wouter](https://github.com/molefrog/wouter) |
| API | `/api/...`, Bearer JWT + заголовок `X-Workspace-Id` |
| Состояние | TanStack Query, контекст auth/workspace |
| Стили | Tailwind CSS, shadcn/ui, семантические токены в `client/src/index.css` |

Запуск: корневой [README.md](../README.md), [deploy.md](deploy.md).

## Структура кода

| Каталог / файл | Назначение |
|----------------|------------|
| `client/src/pages/` | Страницы (экраны) |
| `client/src/components/` | Переиспользуемые UI-блоки, мастер подключения |
| `client/src/lib/` | API-клиент, типы, утилиты (cron, OAuth, sync mode) |
| `client/src/app/` | Роутер, auth, authenticated shell |
| `client/src/lib/nav-config.ts` | Пункты бокового меню |
| `client/src/app/authenticated-shell.tsx` | Таблица маршрутов |

Новые экраны добавляются в `client/src/pages/...` с `data-testid` на ключевых элементах.

## Навигация

Конфиг меню: `client/src/lib/nav-config.ts`. Роутер: `client/src/app/authenticated-shell.tsx`.

### Карта маршрутов

| Раздел меню | Маршруты |
|-------------|----------|
| Обзор | `/`, `/activity` |
| Интеграции | `/connections/*`, `/sources/*`, `/destinations/*`, `/connectors/*` |
| Синхронизация | `/runs/*`, `/schedules`, `/queue` |
| Данные | `/issues/*`, `/connections/:id/streams` |
| Администрирование | `/users`, `/workspaces/*`, `/dictionaries`, `/audit` |
| Auth | `/login`, `/forbidden` |

Список dbt-моделей доступен через API (`GET /api/v1/dbt/models`); отдельной страницы semantic layer в UI нет.

---

## Экраны и функционал

Ниже — базовое описание каждого экрана: что видит пользователь и какие действия доступны.

### Аутентификация

#### `/login` — Вход и регистрация

- Форма входа по логину и паролю; после успеха — redirect на сохранённый путь или дашборд.
- Режим регистрации: создание workspace или ожидание приглашения.
- Обработка OAuth-callback Google Sheets (восстановление сессии мастера подключения).

#### `/forbidden` — Нет доступа

- Сообщение о недостаточных правах; ссылка назад в приложение.

---

### Обзор

#### `/` — Дашборд

Сводка состояния интеграций в текущем workspace.

- **KPI:** активные подключения, успешные/неуспешные запуски за 24 ч, открытые проблемы нормализации, среднее время sync, оценка качества нормализации.
- **График** запусков за 7 дней (успех / частичный / ошибка / в процессе).
- **Блоки:** последние запуски, последние проблемные записи, здоровье коннекторов.
- **Пустое состояние:** при отсутствии подключений — CTA «Создать подключение» и «Открыть каталог коннекторов».

#### `/activity` — Активность

- Лента событий по подключениям, запускам и настройкам (audit-like feed из API).
- Только просмотр; фильтрации нет.

---

### Интеграции — Подключения

Подключение (`connection`) — связка **источник → приёмник** с правилами колонок, расписанием и синком.

#### `/connections` — Список подключений

- Таблица: название, источник, приёмник, статус, режим, cron-расписание, счётчик проблем.
- Действия: открыть карточку, удалить (с подтверждением).
- Кнопка **«Создать подключение»** → мастер `/connections/new`.

#### `/connections/new` — Мастер создания подключения

Пошаговый wizard (`ConnectionWizardShell`). Шаги (индикатор в UI):

| Шаг | Название | Функционал |
|-----|----------|------------|
| 1 | Источник | Выбор существующего source или создание нового; проверка (`check`); `discover` → схема потоков |
| 2 | Колонки и типы | Выбор сущностей (layout `entities`) или одной таблицы (`flat`); маппинг полей; типы нормализации; **режим репликации** (`sync_mode` + `destination_sync_mode`, cursor, primary key) |
| 3 | Приёмник | Выбор или создание destination; проверка подключения |
| 4 | Расписание | Cron и часовой пояс (опционально) |
| — | Обзор и сохранение | Итоговая сводка; `POST /api/v1/connections`; опциональный первый запуск |

Внутри шага «Источник» также задаются имя подключения и конфиг коннектора (формы Google Sheets, Bitrix24, REST Builder и др.).

**Layout источника:**

- **flat** (Google Sheets, REST Builder с одним потоком) — одна таблица полей.
- **entities** (Bitrix24, amoCRM, МойСклад, Яндекс Метрика, REST Builder с несколькими потоками) — чекбоксы сущностей + колонка «Сущность» в маппинге.

#### Карточка подключения — вкладки (`ConnectionSubNav`)

Общая навигация для `/connections/:id/*`:

| Вкладка | Маршрут | Функционал |
|---------|---------|------------|
| Обзор | `/connections/:id` | Pipeline source→destination; таблица потоков (статус, cursor, последний sync, issues); последний запуск; **«Запустить»** / **«Отменить»**; панель доступа (RBAC) |
| Редактирование | `/connections/:id/edit` | Имя, описание; удаление подключения |
| Потоки | `/connections/:id/streams` | Вкл/выкл потоков; sync одного потока; health по потокам; ссылка на редактирование правил |
| Запуски | `/connections/:id/runs` | История sync_run только этого connection |
| Логи | `/connections/:id/logs` | Агрегированные логи последних 5 запусков |
| Проблемы | `/connections/:id/issues` | Фильтр normalization_issue по connection |
| Настройки | `/connections/:id/settings` | Cron, timezone; вкл/выкл расписания; удаление connection |

#### `/connections/:id/streams/edit` — Редактирование потоков и правил

- Повторный `discover` источника.
- Редактор режима репликации (`StreamReplicationModeEditor`) per stream.
- Редактор правил колонок (`ColumnRulesEditor`): source/target field, тип (`phone`, `email`, `inn`, `datetime`, …), required.
- Сохранение через `PATCH` connection (streams + column_rules).

---

### Интеграции — Источники

#### `/sources` — Список источников

- Таблица ELT-источников workspace: название, коннектор, статус проверки, дата последней проверки.
- Поиск по названию; удаление; переход в карточку.
- **«Добавить источник»** → `/sources/new`.

#### `/sources/new` — Создание источника

- Выбор коннектора из каталога.
- Форма конфигурации (Google Sheets + OAuth, Bitrix24 webhook, REST Builder, JSON по schema).
- Проверка и сохранение без привязки к connection (можно использовать в мастере позже).

#### `/sources/:sourceId` — Карточка источника

- Метаданные, статус, дата проверки.
- **«Проверить подключение»** (`POST .../check`).
- Редактирование, удаление; панель точечного доступа (`ResourceAccessPanel`).

#### `/sources/:sourceId/edit` — Редактирование источника

- Изменение имени и config; повторная проверка.

---

### Интеграции — Приёмники

#### `/destinations` — Список приёмников

- Таблица: название, тип, коннектор, статус, схема/БД, последнее использование, число подключений.
- **«Добавить приёмник»** → `/destinations/new`.

#### `/destinations/new` — Создание приёмника

- Тип: `postgres`, `clickhouse`, `csv`, `xlsx`.
- Форма параметров (`DestinationConfigForm`): URL, schema, table, primary_key или путь к файлу.
- Проверка (`check`) перед/после создания.

#### `/destinations/:destinationId` — Карточка приёмника

- Обзор config (маскирование секретов), связанные connections.
- Проверка, редактирование, удаление; панель доступа.

#### `/destinations/:destinationId/edit` — Редактирование приёмника

- Имя и config; валидация по типу коннектора.

---

### Интеграции — Каталог коннекторов

#### `/connectors` — Каталог

- Справочник доступных source/destination коннекторов из API.
- Поиск, фильтр по роли (source / destination / both) и региону.
- Карточки с кратким описанием и списком потоков.

#### `/connectors/:connectorId` — Карточка коннектора

- Детали: категория, регион, список streams, тип авторизации.
- CTA «Создать источник» / «Создать приёмник» (переход к формам создания).

Фильтрация скрытых коннекторов: `client/src/lib/connector-catalog.ts`.

---

### Синхронизация

#### `/runs` — Запуски (глобально)

- Таблица всех `sync_run`: ID, подключение, статус, stage, время, длительность, issues.
- Переход в детальную карточку запуска.

#### `/runs/:id` — Детали запуска

- Статус, timeline этапов (`StageTimeline`).
- Логи прогона (`LogViewer`); issues этого run.
- **«Повторить»** (retry) и **«Отменить»** для running/queued.
- Авто-обновление каждые 3 с, пока статус `running` / `queued`.

#### `/runs/:runId/logs` — Логи запуска

- Полноэкранный просмотр логов одного run.

#### `/schedules` — Расписания

- Таблица cron по подключениям: человекочитаемое описание, timezone, следующий/последний запуск, статус, владелец.
- Переход в настройки connection; пауза/возобновление (если поддерживается API).

#### `/queue` — Очередь

- Только просмотр: job ID, connection, stage, приоритет, время постановки/старта, worker, статус.

---

### Данные

#### `/issues` — Проблемные записи

Центр качества данных (`normalization_issue`).

- Таблица: severity, тип ошибки, connection, stream, field, исходное/предложенное значение, статус.
- Быстрые действия: **«Разрешить»**, **«Игнорировать»**, открыть детали.

#### `/issues/:issueId` — Детали проблемы

- Полное описание ошибки `cast_row`, контекст записи.
- Resolve / ignore; опционально **отключить поток** connection (если ошибки системные).

#### Потоки connection (раздел «Данные» в меню)

Маршрут `/connections/:id/streams` описан выше — управление потоками и per-stream sync.

---

### Администрирование

#### `/users` — Пользователи и роли

- Список пользователей platform: имя, email, глобальная роль, workspace, статус.
- Кнопка «Пригласить пользователя» (UI; интеграция с backend по мере готовности).

#### `/workspaces` — Рабочие пространства

- Список workspace пользователя; переключение активного (через `X-Workspace-Id`).
- **«Создать пространство»** — форма code + name.

#### `/workspaces/:workspaceId/settings` — Настройки workspace

- Участники: добавление по username, удаление.
- Матрица прав (`workspace_member_permission`) — чекбоксы по каталогу permissions.
- Требует `workspace.members.manage` или роль admin workspace.

#### `/dictionaries` — Справочники

- Сводка справочников нормализации: валюты, единицы измерения, статусы (количество строк из API).
- Кнопки «Открыть» / «Добавить» — заготовки UI.

#### `/audit` — Аудит

- Журнал `audit_log` с фильтрами: actor, action, resource_type, result, период.
- Доступен при праве `audit.read` / роли `platform_admin`.
- Детальный просмотр выбранной записи.

---

### Прочие экраны

#### 404 — Страница не найдена

- Fallback для неизвестных hash-маршрутов в authenticated shell.

---

## Мастер подключения (техническая справка)

Последовательность API при создании:

1. `POST /api/v1/sources/{id}/discover` → `layout`, `entity_labels`, `stream_defaults`.
2. Настройка **режима передачи данных** — пресеты репликации (`StreamReplicationModeEditor`): `sync_mode` + `destination_sync_mode`, `cursor_field`, `primary_key`.
3. **Колонки и типы** — маппинг с типами нормализации.
4. `POST /api/v1/connections` с `streams`, `column_rules`, `wizard_meta`.

После создания:

- правила колонок: `GET /api/v1/connections/{id}` → `column_rules`;
- управление потоками: `/connections/:id/streams` и `/connections/:id/streams/edit`.

Пресеты репликации и маппинг в backend: `client/src/lib/destination-sync-mode.ts`, `datanorma/elt/sync_mode_policy.py`.

## Цвета и дальтонизм

Семантические токены в `client/src/index.css` (палитра [Paul Tol](https://sronpersonalpages.nl/~pault/)): успех — синий, ошибка — вермилион, предупреждение — жёлто-оранжевый, выполняется — сине-фиолетовый. Бейджи (`StatusBadge`) различаются иконкой и рамкой.

Проверка: Chrome DevTools → Rendering → Emulate vision deficiencies; или [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/).

После правок: `npm run build` в `client/` или `docker compose build fastapi`.

## Тесты UI

- Unit: `npm run test` (Vitest) в `client/`
- E2E: `npm run test:e2e` (Playwright)

См. [testing.md](testing.md).

## Связанные документы

- [architecture.md](architecture.md) — ELT-поток и мастер подключения (backend-контекст)
- [api.md](api.md) — REST API, используемый экранами
- [security.md](security.md) — JWT, workspace ACL, RBAC
- [user_guide.md](user_guide.md) — роли и пользовательские сценарии
