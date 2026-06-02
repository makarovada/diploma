# Документация DataNorma

Единая точка входа в документацию проекта.

## Основные документы

- `README.md` - короткий старт и ссылки на ключевые разделы.
- `docs/architecture.md` - целевая архитектура и поток `raw -> normalized -> semantic`.
- `docs/data_layers.md` - описание слоев данных и границ ответственности.
- `docs/dbt_models.md` - правила добавления бизнес-витрин в dbt.
- `docs/connectors.md` - контракт и каталог коннекторов.
- `docs/yandex_metrika_connector.md` - специфика источника Яндекс Метрика.
- `docs/normalization_rules.md` - структурная нормализация.
- `docs/frontend.md` - стратегия React UI.
- `docs/backend.md` - backend-компоненты.
- `docs/api.md` - API-карта.
- `docs/security.md` - auth/RBAC/CORS/секреты.
- `docs/deploy.md` - запуск и deployment.
- `docs/testing.md` - проверки и smoke.
- `docs/user_guide.md` - инструкции по ролям.
- `docs/acceptance_plan.md` - ПМИ и критерии приемки.
- `docs/manual_testing_guide.md` - подробные ручные сценарии.
- `docs/comparison_ingest.md` - позиционирование относительно Ingest.
- `docs/adding_russian_connector.md` - инструкция по добавлению нового коннектора.
- `docs/vkr_rbac_text.md` - материал по RBAC для ВКР.

## Стандарт документации

Для всех документов в проекте используется:
- русский язык как основной;
- единая терминология: `sources`, `destinations`, `connections`, `sync`, `raw`, `normalized`, `semantic`, `RBAC`, `MVP`;
- согласованное описание границ текущей версии;
- ссылки на связанные документы между разделами.
