# Сравнение DataNorma и Airbyte

Краткая таблица для ВКР и онбординга: где прототип сознательно **похож** на [Airbyte](https://airbyte.com) (open-source EL / ELT), а где **расходится** по архитектуре дипломного объёма.

| Аспект | Airbyte | DataNorma |
|--------|---------|-----------|
| **Назначение** | Универсальная платформа EL(T): сотни коннекторов, SaaS и self-hosted | Узкий прототип под МСБ РФ: Ozon, 1С, Sheets → каноническая витрина |
| **Источники (Sources)** | Каталог коннекторов, CDK, marketplace | Фиксированные интеграции + YAML-маппинг полей |
| **Назначения (Destinations)** | Много типов БД/хранилищ | PostgreSQL (staging raw + витрина) |
| **Connections** | Связь source ↔ destination, конфигурация в UI | Логические связи и экраны в духе Airbyte; фактически один warehouse |
| **Протокол обмена** | Airbyte Protocol (RECORD / STATE / CATALOG …) over stdio | Модели в `datanorma/core/airbyte_protocol.py` для будущей совместимости; сейчас Dagster assets + БД |
| **Состояние инкремента** | `StateMessage`, worker | Таблица `sync_state` + курсоры в PostgreSQL |
| **Нормализация** | Опционально dbt / typing в платформе | Python + YAML (`source_mappings.yaml`), fuzzy, ЦБ РФ, даты MSK |
| **Оркестрация** | Встроенные job / worker Airbyte | **Dagster** (граф assets, расписания, UI отдельно) |
| **UI** | Airbyte Cloud / OSS console | Jinja2-консоль в визуальном духе Airbyte + REST + legacy `/ui/` |
| **RBAC / мультитенант** | Зависит от продукта / деплоя | JWT, роли, матрица операций (демо ВКР) |
| **Зависимости разработки** | Собственный CDK | `dbt-postgres` в extra `dev`; `airbyte-cdk` в extra `dev-airbyte` (по необходимости) |

Подробности про терминологию в интерфейсе см. **`/app/about`** в запущенном веб-клиенте и `README.md` (фаза C).
