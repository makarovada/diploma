# Документация DataNorma

Единая точка входа в документацию проекта.

## Основные документы

| Документ | Содержание |
|----------|------------|
| [architecture.md](architecture.md) | Архитектура, ELT-поток, схема метаданных |
| [data_layers.md](data_layers.md) | Слои `raw` / `normalized` / `semantic` |
| [connectors.md](connectors.md) | Каталог коннекторов и контракт |
| [normalization_rules.md](normalization_rules.md) | `ColumnRule` / `StreamRules`, `cast_row` |
| [dbt_models.md](dbt_models.md) | Бизнес-витрины в `semantic.*` |
| [yandex_metrika_connector.md](yandex_metrika_connector.md) | Источник Яндекс Метрика |
| [backend.md](backend.md) | Модули Python-пакета |
| [frontend.md](frontend.md) | React SPA, маршруты, мастер подключения |
| [api.md](api.md) | Карта REST API |
| [security.md](security.md) | Auth, workspace ACL, CORS |
| [deploy.md](deploy.md) | Локальный и production запуск |
| [testing.md](testing.md) | pytest, Vitest, Playwright, Allure, Locust |
| [user_guide.md](user_guide.md) | Роли и сценарии |
| [acceptance_plan.md](acceptance_plan.md) | ПМИ и критерии приёмки |
| [comparison_ingest.md](comparison_ingest.md) | Позиционирование vs Ingest |
| [adding_russian_connector.md](adding_russian_connector.md) | Добавление нового source |
| [vkr_rbac_text.md](vkr_rbac_text.md) | Материал по RBAC для ВКР |

Корневой [README.md](../README.md) — быстрый старт.

## Стандарт документации

- русский язык;
- терминология: `source`, `destination`, `connection`, `sync`, `stream`, `StreamRules`, `ColumnRule`, workspace, RBAC;
- продуктовый контур: connection sync (`source.read → cast_row → destination.write`);
- бизнес-витрины — dbt `semantic.*`, не жёсткие ORM-модели в backend.
