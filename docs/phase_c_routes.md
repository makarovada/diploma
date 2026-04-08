# Фаза C: маршруты веб-клиента (`/app/...`)

Уникальные пути (для приложения к ВКР и подсчёта «экранов»). Часть маршрутов — POST (формы).

Переменные окружения и пути для веб-слоя и пайплайна — **`datanorma/config.py`** (`Settings`). Сравнение с Airbyte — **[comparison_airbyte.md](comparison_airbyte.md)**.

**Терминология UI** в духе [Airbyte](https://airbyte.com): **Sources**, **Destinations**, **Connections**, sync history, secrets, replication schedule; оркестрация вынесена в **Dagster** (`/app/external/dagster`).

| Маршрут | Назначение |
|---------|------------|
| `GET /app/login` | Вход |
| `POST /app/login` | Проверка логина, cookie JWT |
| `GET /app/logout` | Выход, сброс cookie |
| `GET /app/dashboard` | Home / дашборд (карточки connections, витрина) |
| `GET /app/connections` | Connections: логические source→destination, недавние sync jobs |
| `GET /app/destinations` | Destinations: PostgreSQL (staging + витрина) |
| `GET /app/external/dagster` | Редирект на Dagster UI (оркестрация) |
| `GET/POST /app/account/password` | Смена пароля |
| `GET /app/sources` | Список источников + sync |
| `GET /app/sources/{code}` | Карточка источника |
| `GET/POST /app/integrations/secrets` | Конфиги (маскирование), добавление (админ) |
| `GET /app/mappings` | Список профилей маппинга |
| `GET/POST /app/mappings/editor` | Редактор YAML (без записи на диск) |
| `GET /app/samples/preview` | Предпросмотр sample |
| `GET /app/runs` | Список запусков |
| `GET /app/runs/{id}` | Детали run |
| `GET /app/pipeline/graph` | Статическая схема + Dagster |
| `GET /app/warehouse/sales` | Витрина, фильтр `source_system` |
| `GET /app/warehouse/export` | Экран экспорта |
| `GET /app/warehouse/download.csv` | Скачивание CSV |
| `GET /app/ref/currencies` | Справочник валют |
| `GET /app/ref/source-systems` | Справочник источников (dim) |
| `GET /app/admin/users` | Пользователи |
| `GET/POST /app/admin/user-roles` | Назначение / снятие ролей |
| `GET /app/monitoring/normalization` | Журнал normalization_issue |
| `GET/POST /app/settings/schedule` | Cron-текст в `integration_config` |
| `GET /app/about` | О системе и FAQ |

Дополнительно: одностраничный клиент на **`/ui/`** (фаза B), REST **`/api/*`**.
