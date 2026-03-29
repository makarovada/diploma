# DataNorma

Конфигурируемый прототип интеграции и нормализации данных для МСБ (оркестрация: **Dagster**).

## Для кого и что это

Сервис **не привязан к одной гипотетической компании**: смысл в том, что данные **вашей** организации (или песочные примеры) проходят через одни и те же коннекторы, а различия в колонках и форматах задаются **конфигом маппинга** (`datanorma/schemas/source_mappings.yaml` или `DATANORMA_SOURCE_MAPPINGS_PATH`). Логическая цель — единая **каноническая модель** продаж (`datanorma/schemas/canonical_sales.yaml`), с которой удобно работать аналитику в SQL/BI после загрузки в warehouse.

**Сейчас в дипломном прототипе:** просмотр и запуск пайплайна — через **Dagster UI** (граф, материализации, логи). Отдельного «личного кабинета аналитика» с логином и мультитенантностью нет: это следующий уровень продукта (SaaS), за рамками текущего объёма. Зато пайплайн изначально рассчитан на **любого заказчика**, который подставляет свои файлы, ключи API и YAML маппинга.

## Этап 1: запуск локально

1. Python 3.11+, виртуальное окружение:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e .
   ```

2. PostgreSQL (целевая БД):

   ```bash
   docker compose up -d
   ```

3. UI и пайплайны:

   ```bash
   dagster dev -m datanorma.definitions
   ```

   Альтернатива в новых версиях Dagster: `dg dev` (см. предупреждение *SupersessionWarning* в консоли — старая команда пока поддерживается).

   Откройте адрес из вывода команды (обычно http://127.0.0.1:3000). В разделе **Assets** виден граф: **raw** (`raw_ozon_postings`, `raw_1c_orders`, `raw_google_sheet_orders`) → `normalized_orders` → `warehouse_sales`. Расписание **daily_moscow** (05:00 Europe/Moscow) в **Automation**.

## Этап 2: raw-источники

Без секретов пайплайн читает файлы из `data/samples/` (Ozon — JSON, 1С — CSV, Google Sheets — CSV как экспорт). Реальные интеграции задаются переменными окружения (см. `.env.example`):

- **Ozon** — `OZON_CLIENT_ID`, `OZON_API_KEY`; запрос к `POST /v3/posting/fbs/list`, при ошибке или отсутствии ключей — фикстура.
- **1С** — `DATANORMA_1C_EXPORT_PATH` на ваш CSV/XLSX; иначе sample `1c_export.csv`.
- **Google Sheets** — `GSPREAD_SERVICE_ACCOUNT_FILE`, `GSPREAD_SPREADSHEET_ID`, опционально `GSPREAD_WORKSHEET`; иначе sample CSV.

При установке пакета не из исходников укажите `DATANORMA_REPO_ROOT` на каталог, где лежит `data/samples`.

## Каноническая модель и маппинг (любая компания)

- Описание полей витрины: `datanorma/schemas/canonical_sales.yaml` (документация для аналитики и разработки коннекторов).
- Соответствие колонок ваших выгрузок этим полям: `datanorma/schemas/source_mappings.yaml`. Для другой структуры CSV/листа скопируйте файл, измените `fields` и задайте `DATANORMA_SOURCE_MAPPINGS_PATH`.
- Asset `normalized_orders` строит список строк в этой канонической форме и выполняет простую дедупликацию по паре `(source_system, source_record_id)`.

Переопределение URL БД: переменная окружения `DATABASE_URL` (см. `.env.example`).

### Если падает `warehouse_sales` (PostgreSQL)

Чаще всего на Windows порт **5432** уже занят **локальным** PostgreSQL: приложение подключается не к Docker, и пользователь `datanorma` «не существует» или пароль не подходит (в логе Dagster это видно как кракозябры — русское сообщение сервера).

В проекте контейнер проброшен на порт **5433** (`docker-compose.yml`). После `docker compose up -d` строка подключения по умолчанию: `127.0.0.1:5433`, пользователь/пароль/БД `datanorma`. Проверка из PowerShell:

```powershell
docker compose -f c:\dev\diploma\diploma\docker-compose.yml up -d
docker compose -f c:\dev\diploma\diploma\docker-compose.yml exec postgres psql -U datanorma -d datanorma -c "SELECT 1"
```

Если в `.env` или в системе задан старый `DATABASE_URL` с портом `5432`, удалите его или поправьте на `5433`. Если пароль контейнера когда-то меняли и том не сбрасывали: `docker compose down -v` (удалит данные в volume) и снова `up -d`.

### Что значат сообщения в консоли

- **Временный каталог для storage** — по умолчанию Dagster кладёт служебные данные в temp-папку и удаляет её после выхода. Чтобы сохранять историю и настройки между запусками, задайте каталог, например: `set DAGSTER_HOME=c:\dev\diploma\diploma\.dagster_home` (PowerShell: `$env:DAGSTER_HOME="..."`), и при необходимости создайте в нём `dagster.yaml`.
- **Telemetry** — сбор анонимной статистики; отключение: в `%DAGSTER_HOME%\dagster.yaml` добавить `telemetry: { enabled: false }`.
- **Compute log capture is disabled (Windows)** — логи выполнения шагов в UI могут быть пустыми. Чтобы включить захват, перед запуском задайте `PYTHONLEGACYWINDOWSSTDIO=1` (в PowerShell: `$env:PYTHONLEGACYWINDOWSSTDIO="1"`).
- Строка про **daemons** и **Serving dagster-webserver on http://127.0.0.1:3000** означает, что всё поднялось успешно.
