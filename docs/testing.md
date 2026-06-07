# Тестирование

## Основные проверки

- Backend tests: `pytest tests/ -q`
- Frontend build: `npm run build` в `client/`

## Отчёты Allure (графики и история прогонов)

Нужны: `pip install -e ".[dev]"` и [Allure Commandline](https://github.com/allure-framework/allure2/releases) (требуется Java), либо Docker (см. ниже).

### Ручная установка Allure Commandline (Windows)

Пакет `allure-pytest` из pip **не** добавляет команду `allure` в терминал. Её даёт только **Allure CLI** (zip с GitHub) при наличии **Java**.

1. **Установите JDK** (например [Eclipse Temurin 17 LTS](https://adoptium.net/) или Oracle/OpenJDK). В PowerShell проверка:

   ```powershell
   java -version
   ```

   Если команды нет — сначала поставьте JDK и при необходимости перезапустите терминал.

2. **Скачайте архив Allure 2** со страницы [релизов Allure](https://github.com/allure-framework/allure2/releases). Для Windows обычно берут файл вида `allure-2.x.x.zip` (не исходники).

3. **Распакуйте** в постоянный каталог без пробелов в пути, например:

   `C:\tools\allure-2.34.1`

   Внутри должен быть подкаталог `bin` с файлом `allure.bat`.

4. **Добавьте `bin` в PATH** (один из способов):

   - **Через интерфейс:** «Параметры» → «О системе» → «Дополнительные параметры системы» → «Переменные среды» → в переменной **Path** пользователя или системы → «Создать» → вставьте полный путь, например `C:\tools\allure-2.34.1\bin` → ОК везде.
   - **Через PowerShell (только текущий пользователь, сессия PATH обновится для новых окон):**

     ```powershell
     [Environment]::SetEnvironmentVariable(
       "Path",
       $env:Path + ";C:\allure-2.40.0\bin",
       "User"
     )
     ```

     Замените путь на свой. Закройте и снова откройте PowerShell или Cursor.

5. **Проверка:**

   ```powershell
   allure --version
   ```

   Должна вывестись версия Allure. Если снова «не распознано» — убедитесь, что в PATH именно каталог **`bin`**, а не корень распаковки.

6. **Запуск отчёта** из корня репозитория (после `pytest --alluredir=allure-results`):

   ```powershell
   allure serve allure-results
   ```

**Замечание:** `python -m pip install allure-pytest` ставит только интеграцию с pytest; без шагов 1–5 команда `allure` в PowerShell не появится.

### Цикл работы с отчётом

1. Собрать сырые результаты:

```bash
python -m pytest tests/ --alluredir=allure-results --clean-alluredir
```

(Если активировано виртуальное окружение и `pytest` в `PATH`, можно вызывать `pytest` вместо `python -m pytest`.)

2. Открыть интерактивный отчёт в браузере:

```bash
allure serve allure-results
```

Либо сгенерировать статический HTML и открыть `allure-report/index.html`:

```bash
allure generate allure-results --clean -o allure-report
allure open allure-report
```

На Windows можно вызвать `scripts/run_tests_allure.ps1` из корня репозитория (после установки Allure в `PATH`). На Linux/macOS — `scripts/run_tests_allure.sh`.

Только сгенерировать HTML без `serve` (например, если `allure-results` уже есть):

```powershell
scripts/generate_allure_report.ps1
```

### CI

В GitHub Actions job `backend-tests` после прогона тестов собирается артефакт **`allure-report`** (HTML). Скачайте его на странице workflow run → Artifacts и откройте `index.html` локально.

**Без локальной Java** можно поднять отчёт в Docker — см. [fescobar/allure-docker-service](https://github.com/fescobar/allure-docker-service): смонтируйте каталог `allure-results` и откройте UI по адресу из логов контейнера (по умолчанию порт 5050).

Дополнительные метки в коде: декораторы из `allure` (`@allure.feature`, `@allure.story`, `@allure.title`) — см. [документацию allure-python](https://docs.qameta.io/allure-report/frameworks/python/pytest/).

## Нагрузочное тестирование (Locust)

Сценарии имитируют интегратора: логин и чтение каталога, источников, приёмников, подключений, очереди и run history.

**Требования:** запущенный API (`docker compose up -d` или `python -m datanorma.web`), сиды (`python scripts/seed_database.py`).

1. Установить зависимости:

```bash
pip install -e ".[load]"
```

2. **Интерактивный режим** (веб-UI Locust на http://127.0.0.1:8089):

```bash
locust -f loadtests/locustfile.py --host http://127.0.0.1:8080
```

3. **Headless** (HTML + CSV в `loadtest-results/`):

```powershell
.\scripts\run_load_tests.ps1
```

Параметры через переменные окружения:

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `LOAD_TEST_HOST` | `http://127.0.0.1:8080` | Базовый URL API |
| `LOAD_TEST_USER` | `seed_integrator` | Логин |
| `LOAD_TEST_PASSWORD` | `IntegratorDemo2026` | Пароль |
| `LOAD_TEST_WORKSPACE` | `1` | Заголовок `X-Workspace-Id` |
| `LOAD_TEST_USERS` | `10` | Виртуальных пользователей |
| `LOAD_TEST_SPAWN_RATE` | `2` | Пользователей/сек при разгоне |
| `LOAD_TEST_DURATION` | `1m` | Длительность прогона |

Пример более жёсткого прогона:

```powershell
$env:LOAD_TEST_USERS = "50"
$env:LOAD_TEST_DURATION = "3m"
.\scripts\run_load_tests.ps1
```

Откройте `loadtest-results/report.html` — там RPS, latency (median/p95/p99) и доля ошибок по каждому endpoint.

**Замечание:** нагрузочные тесты не входят в обычный CI (нужен живой сервер); запускайте вручную перед приёмкой или на staging.

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

## Smoke: Яндекс Метрика → PostgreSQL + cron

1. В UI открыть `Источники` → `Новый источник`.
2. Выбрать `yandex_metrika`, сохранить источник с JSON-конфигом:
   - `oauth_token`
   - `counter_id`
3. В UI открыть `Приёмники` → `Новый приёмник`, выбрать `postgres`, задать `url`, `schema`, `table`.
4. В мастере подключения связать созданные source/destination и сохранить connection.
5. В `Настройки подключения` задать cron `*/5 * * * *` и timezone (например `Europe/Moscow`), сохранить.
6. Проверить ручной запуск с карточки подключения (`Запустить`) и появление записи в run history.
7. Убедиться, что в окружении Dagster включён sensor `connection_cron_sensor` (иначе расписание не исполняется).

