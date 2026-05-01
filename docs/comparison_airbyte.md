# Сравнение DataNorma и Airbyte

Документ фиксирует текущее позиционирование DataNorma как MVP-платформы интеграции данных для малого и среднего бизнеса в РФ.
По смыслу DataNorma следует продуктовой модели [Airbyte](https://airbyte.com): `sources -> connections -> sync -> destination`, но реализована на собственном стеке (Dagster + FastAPI + PostgreSQL + Python/YAML-нормализация).

## Краткое сравнение

| Аспект | Airbyte | DataNorma (текущее состояние) |
|--------|---------|-------------------------------|
| **Назначение** | Универсальная EL(T)-платформа, большой ecosystem | Вертикально сфокусированный MVP под SMB РФ |
| **Sources** | Большой каталог коннекторов + marketplace | Встроенные коннекторы (`Ozon`, `1C`, `Google Sheets`) + `rest_builder` |
| **Destinations** | Много хранилищ и БД | Сейчас один основной destination: PostgreSQL |
| **Connections** | Богатая модель связей source/destination в UI | Логика connections присутствует в API/UI, практический контур заточен под единый warehouse |
| **Incremental state** | Нативный state-протокол и workers | `sync_state` в PostgreSQL + cursor filtering в pipeline |
| **Нормализация** | Typing/Dedup + dbt-пайплайны | Кастомная бизнес-нормализация (MSK datetime, ЦБ РФ, fuzzy, units) |
| **Оркестрация** | Собственный runtime | Dagster assets/schedules/checks/sensors |
| **UI/API** | Зрелая product-консоль | FastAPI + Jinja2 UI (`/app/*`) + REST (`/api/*`, `/api/v1/*`) |
| **RBAC/мультитенантность** | Развитые enterprise-сценарии | Роли и матрица операций есть; мультитенантность реализована базовым контуром |
| **Расширяемость** | Высокая, через CDK/коннекторы | Есть source framework и YAML builder, но ecosystem пока ограничен |

## Что уже близко к Airbyte

- Единая терминология `sources/destinations/connections/syncs`.
- Инкрементальный контур со state в БД.
- Raw staging слой и последующая нормализация/загрузка в warehouse.
- Наличие API/UI-слоя для операционной работы команды.

## Что остаётся развить до уровня полноценной платформы

- Расширить библиотеку готовых российских коннекторов.
- Добавить больше destination-адаптеров.
- Укрепить жизненный цикл sync jobs (ретраи, более полная оркестрация через API).
- Расширить no-code UX для конфигурирования связей и маппингов.
- Усилить production-ready контур (CI/CD, деплой-практики, эксплуатационная наблюдаемость).

## Связанные документы

- Карта проекта и runbook: `README.md`
- Полный чеклист ручного тестирования: `docs/manual_testing_guide.md`
- Список UI-маршрутов: `docs/phase_c_routes.md`
