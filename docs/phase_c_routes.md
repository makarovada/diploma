# Web UI маршруты (`/app/*`)

Справочник маршрутов пользовательского веб-интерфейса DataNorma (FastAPI + Jinja2) для приемки, скриншотов и регрессионных проверок.

## 1. Контекст

- UI использует терминологию, близкую к Airbyte: `Sources`, `Destinations`, `Connections`, `Syncs`.
- Оркестрация вынесена в Dagster; из UI доступна ссылка-переход.
- Доступ к страницам контролируется RBAC-матрицей.

## 2. Основные маршруты

| Маршрут | Назначение |
|---------|------------|
| `GET /app/login` | Страница входа |
| `POST /app/login` | Аутентификация, установка cookie/JWT |
| `GET /app/logout` | Выход и очистка сессии |
| `GET /app/dashboard` | Главная страница с операционными метриками |
| `GET /app/about` | О системе, контекст и FAQ |
| `GET /app/external/dagster` | Переход в Dagster UI |

## 3. Build-раздел

| Маршрут | Назначение |
|---------|------------|
| `GET /app/sources` | Список источников |
| `GET /app/sources/new` | Форма проверки/обнаружения нового source |
| `GET /app/sources/{code}` | Карточка источника |
| `GET /app/destinations` | Назначения (destinations) |
| `GET /app/connections` | Список connections |
| `POST /app/connections` | Изменение конфигурации connection |
| `GET /app/connections/sample/{code}` | Просмотр sample-данных источника |
| `GET /app/mappings` | Профили маппинга |
| `GET /app/mappings/editor` | Редактор маппинга (preview) |
| `POST /app/mappings/editor` | Валидация/предпросмотр маппинга |

## 4. Monitor-раздел

| Маршрут | Назначение |
|---------|------------|
| `GET /app/runs` | История запусков |
| `GET /app/runs/{id}` | Детали конкретного запуска |
| `GET /app/pipeline/graph` | Схема pipeline и переход к Dagster |
| `GET /app/monitoring/normalization` | Журнал нормализации |
| `GET /app/samples/preview` | Предпросмотр sample-данных |
| `GET /app/warehouse/sales` | Просмотр витрины |
| `GET /app/warehouse/export` | Экран экспорта данных |
| `GET /app/warehouse/download.csv` | Скачивание CSV из витрины |

## 5. Settings и администрирование

| Маршрут | Назначение |
|---------|------------|
| `GET /app/integrations/secrets` | Просмотр конфигурации интеграций |
| `POST /app/integrations/secrets` | Обновление секретов/параметров |
| `GET /app/settings/schedule` | Просмотр расписания |
| `POST /app/settings/schedule` | Обновление cron-настроек |
| `GET /app/account/password` | Форма смены пароля |
| `POST /app/account/password` | Смена пароля |
| `GET /app/admin/users` | Пользователи |
| `GET /app/admin/user-roles` | Матрица ролей пользователей |
| `POST /app/admin/user-roles` | Назначение/снятие ролей |
| `GET /app/workspaces` | Просмотр workspaces |
| `GET /app/ref/source-systems` | Справочник источников |
| `GET /app/ref/currencies` | Справочник валют |

## 6. Дополнительные маршруты

- Legacy SPA интерфейс: `/ui/`
- REST API: `/api/*` и `/api/v1/*`

## 7. Примечания для приемки

- Не все POST-маршруты имеют одинаковую глубину персистентности (часть форм MVP-уровня).
- Редактор маппингов предназначен для preview/валидации и не сохраняет YAML в файлы репозитория.
- Для ролевой приемки используйте матрицу операций из `/api/rbac/matrix`.

## 8. Связанные документы

- Карта проекта и runbook: `README.md`
- Ручное тестирование: `docs/manual_testing_guide.md`
- RBAC для ВКР: `docs/vkr_rbac_text.md`
