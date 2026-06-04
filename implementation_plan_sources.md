# План реализации источников данных — DataNorma (ВКР)

> Ветка: `base_1` · Пакет: `datanorma` · Google Sheets — **полностью готов** (эталон)
>
> Рассматриваются только источники, для которых доступен **бесплатный тестовый аккаунт без привязки к юр. лицу**.
> **Исключены**: Ozon (sandbox только по заявке с ИНН), Wildberries (требует юр. лицо/ИП).

---

## Статус реализации на старте

| Источник | Файл коннектора | Статус | Примечание |
|---|---|---|---|
| Google Sheets | `sources/sheets.py` | ✅ Готов | OAuth2 + Service Account, полный CRUD |
| Яндекс Метрика | `sources/yandex_metrika.py` | ⚡ Частично | Есть полная логика read/discover/check, нужны тесты и UI-схема |
| AmoCRM | `sources/amocrm.py` | ⚡ Частично | Скелет есть, нужна полная реализация потоков |
| Bitrix24 | `sources/bitrix24.py` | ⚡ Частично | Скелет есть, нужна полная реализация потоков |
| МойСклад | `sources/moysklad.py` | ⚡ Частично | Скелет есть, нужна полная реализация потоков |
| 1С (файловый) | `sources/onec.py` | ⚡ Частично | Скелет есть, нужна полная реализация |

---

## Общая архитектура коннектора (паттерн GoogleSheets)

Каждый коннектор следует единой схеме `BaseSource`:

```
BaseSource
├── check()     → SourceCheckResult(ok, message, details)
├── discover()  → IngestCatalog(streams=[IngestStream(...)])
└── read(stream_name, sync_mode, cursor_field, last_cursor) → Iterator[dict]
```

**Обязательные файлы/изменения для каждого нового источника:**

1. `datanorma/sources/<source>.py` — основной коннектор
2. `datanorma/config.py` — новые поля Settings
3. `datanorma/sources/registry.py` — регистрация алиасов
4. `datanorma/web/connector_schema_meta.py` — UI-схема полей (JSON Schema)
5. `tests/sources/test_<source>.py` — юнит-тесты с фикстурами
6. `data/fixtures/<source>/` — JSON-фикстуры для offline-тестов

---

## 1. Яндекс Метрика

### Контекст
- Файл коннектора `yandex_metrika.py` **уже полностью реализован** (check/discover/read + нормализация строк)
- Зарегистрирован в `registry.py` с алиасами `yandex_metrika | yandexmetrika | metrika | ya_metrika`
- В `config.py` присутствуют поля `yandex_metrika_oauth_token` и `yandex_metrika_counter_id`
- **Тестовый аккаунт**: бесплатно на yandex.ru, счётчик создаётся без юр. лица

### Что осталось сделать

#### 1.1 Фикстуры и тесты
- [ ] Создать `data/fixtures/yandex_metrika/stat_v1_data_summary.json` — пример ответа `stat/v1/data` для стрима `summary`
- [ ] Создать аналогичные фикстуры для `visits`, `hits`, `goals_reaches`
- [ ] Создать `tests/sources/test_yandex_metrika.py`:
  - `test_check_ok` — мок Management API, HTTP 200
  - `test_check_fail` — HTTP 403, SourceCheckResult(ok=False)
  - `test_discover_returns_four_streams` — проверить что discover возвращает ровно 4 стрима
  - `test_read_summary_full_refresh` — read со стримом summary, sync_mode=full_refresh
  - `test_read_summary_incremental` — read с last_cursor='2025-01-15', проверка что строки с датой до курсора отфильтрованы
  - `test_read_unknown_stream_raises` — ValueError при неизвестном стриме
  - `test_parse_report_rows_empty` — пустой data в ответе API
  - `test_sanitize_key` — параметризованный тест `ym:s:date` → `ym_s_date`

#### 1.2 UI-схема (connector_schema_meta.py)
Добавить в словарь `CONNECTOR_FIELDS`:
```python
"yandex_metrika": [
    {"key": "oauth_token",   "label": "OAuth-токен",    "type": "password", "required": True,
     "hint": "Получить на https://oauth.yandex.ru/, scope: metrika:read"},
    {"key": "counter_id",    "label": "ID счётчика",    "type": "string",   "required": True,
     "hint": "Число из URL счётчика в Метрике, например: 12345678"},
    {"key": "lookback_days", "label": "Глубина, дней",  "type": "integer",  "required": False,
     "default": 30, "hint": "1–365. Используется если date_from/date_to не заданы"},
    {"key": "date_from",     "label": "Дата начала",    "type": "string",   "required": False,
     "hint": "YYYY-MM-DD. Переопределяет lookback_days"},
    {"key": "date_to",       "label": "Дата конца",     "type": "string",   "required": False,
     "hint": "YYYY-MM-DD"},
]
```

#### 1.3 Инструкция получения OAuth-токена
Документировать в README / справке UI:
1. Открыть https://oauth.yandex.ru/ → «Зарегистрировать новое приложение»
2. Выбрать Yandex ID + Яндекс Метрика → `metrika:read`
3. «Веб-сервисы» → redirect URI `https://oauth.yandex.ru/verification_code`
4. После регистрации: `https://oauth.yandex.ru/authorize?response_type=token&client_id=<CLIENT_ID>`
5. Скопировать `access_token` из URL

#### 1.4 Улучшения коннектора (опционально для ВКР)
- [ ] Поддержка пагинации: добавить параметр `offset` в `_stat_report()` с циклом while `total_rows > offset`
- [ ] Стрим `ecommerce` (ym:s:productName, ym:s:productQuantity) для проектов с e-commerce
- [ ] Добавить `date_range` в `details` ответа `check()`

---

## 2. AmoCRM

### Контекст
- **Тестовый аккаунт**: бесплатно на amocrm.ru, 14-дней триал без юр. лица (далее бесплатный план ограничен)
- API: REST, авторизация через **OAuth2 Authorization Code Flow** или **Long-lived token**
- Base URL: `https://<subdomain>.amocrm.ru/api/v4/`
- Основные эндпоинты: `/leads`, `/contacts`, `/companies`, `/tasks`, `/pipelines`

### 2.1 Конфигурация — config.py
Добавить/проверить поля в `Settings`:
```python
amocrm_base_url: str = Field(default="", validation_alias="DATANORMA_AMOCRM_BASE_URL")
# пример: https://mycompany.amocrm.ru
amocrm_token: str = Field(default="", validation_alias="DATANORMA_AMOCRM_TOKEN")
# Long-lived access token (для ВКР достаточно; для production — OAuth2 refresh flow)
```
> ⚠️ Поля уже есть в `config.py`. Проверить наличие, не дублировать.

### 2.2 Реализация коннектора — sources/amocrm.py

**Константы:**
```python
AMOCRM_PAGE_LIMIT = 250  # максимум по API
STREAM_CURSOR_FIELDS = {
    "leads":     "updated_at",
    "contacts":  "updated_at",
    "companies": "updated_at",
    "tasks":     "complete_till",
}
```

**Метод `_paginate(endpoint, params)`:**
- GET `{base_url}/api/v4/{endpoint}`
- Headers: `Authorization: Bearer {token}`
- Параметры: `page=1, limit=250`
- Разобрать `_embedded.{endpoint}` из ответа
- Цикл: пока `_links.next` присутствует в ответе → page += 1
- Возвращать плоский список dict

**Метод `check()`:**
```python
GET /api/v4/account
→ status 200: SourceCheckResult(ok=True, message=f"AmoCRM {account['name']}: подключён", details={...})
→ status 401: ok=False, "Неверный токен"
→ Exception: ok=False, str(exc)
```

**Метод `discover()`:**
- Для каждого stream в STREAM_CURSOR_FIELDS:
  - Вызвать `_paginate(stream, {"limit": 5})` для получения образца
  - `records_to_json_schema(sample[:50])`
  - Создать `IngestStream` с `sync_modes=(full_refresh, incremental)`, `default_cursor_field=[cursor]`
- Дополнительный стрим `pipelines` (только full_refresh, без курсора)

**Метод `read(stream_name, sync_mode, cursor_field, last_cursor)`:**
```python
params = {"limit": AMOCRM_PAGE_LIMIT}
if sync_mode == "incremental" and last_cursor:
    # AmoCRM принимает updated_at фильтр через query params
    params["filter[updated_at][from]"] = int(last_cursor_as_timestamp)
rows = list(_paginate(stream_name, params))
# Нормализация: преобразовать unix timestamp updated_at → ISO 8601
for row in rows:
    if "updated_at" in row:
        row["updated_at"] = datetime.utcfromtimestamp(row["updated_at"]).isoformat()
yield from filter_incremental_dict_rows(rows, cursor_field, last_cursor)
```

**Нормализация специфичных полей:**
- `leads`: `_embedded.tags` → `tags` (список имён через запятую), `_embedded.contacts` → `contact_ids`
- `contacts`: `custom_fields_values` → flatten в `cf_{field_code}`
- Удалить все `_links` ключи из каждой записи

### 2.3 Фикстуры — data/fixtures/amocrm/
- `leads_page1.json` — 3 сделки с `_embedded`, `_links.next`
- `leads_page2.json` — 2 сделки без `_links.next`
- `contacts_page1.json`
- `account.json` — ответ `/api/v4/account`

### 2.4 Тесты — tests/sources/test_amocrm.py
- `test_check_ok` — мок `/api/v4/account` HTTP 200
- `test_check_unauthorized` — HTTP 401
- `test_discover_streams` — проверить 5 стримов (leads/contacts/companies/tasks/pipelines)
- `test_read_leads_full_refresh` — чтение всех страниц (2 страницы через мок)
- `test_read_leads_incremental` — фильтр по updated_at > last_cursor
- `test_pagination_follows_next_link` — проверить что при наличии `_links.next` делается второй запрос
- `test_normalize_timestamps` — unix timestamp → ISO 8601

### 2.5 UI-схема (connector_schema_meta.py)
```python
"amocrm": [
    {"key": "base_url", "label": "URL аккаунта", "type": "string", "required": True,
     "hint": "https://yourcompany.amocrm.ru"},
    {"key": "token",    "label": "Access token", "type": "password", "required": True,
     "hint": "Настройки → Интеграции → Показать ключи API → Access token"},
]
```

### 2.6 Инструкция получения токена
1. Войти в AmoCRM → Настройки → Интеграции
2. Создать интеграцию, тип «Внешняя»
3. В разделе «Ключи и доступы» скопировать **Access token** (действует 24ч) или настроить OAuth2 refresh

---

## 3. Bitrix24

### Контекст
- **Тестовый аккаунт**: бесплатный тариф на bitrix24.ru без юр. лица (до 5 пользователей)
- API: REST через **входящий вебхук** (Webhook URL) или OAuth2
- Для ВКР используем Webhook (проще): `https://<portal>.bitrix24.ru/rest/<user_id>/<token>/`
- Основные методы: `crm.lead.list`, `crm.deal.list`, `crm.contact.list`, `crm.company.list`, `task.item.list`
- Ответ: `{ "result": [...], "next": 50, "total": 123 }`

### 3.1 Конфигурация — config.py
```python
bitrix24_webhook_url: str = Field(default="", validation_alias="DATANORMA_BITRIX24_WEBHOOK_URL")
# пример: https://myportal.bitrix24.ru/rest/1/abcdef123456/
```
> ⚠️ Поле уже есть в `config.py`. Проверить.

### 3.2 Реализация коннектора — sources/bitrix24.py

**Константы:**
```python
BITRIX_PAGE_SIZE = 50  # API возвращает максимум 50 записей за запрос
STREAM_METHOD_MAP = {
    "leads":     "crm.lead.list",
    "deals":     "crm.deal.list",
    "contacts":  "crm.contact.list",
    "companies": "crm.company.list",
    "tasks":     "task.item.list",
    "activities":"crm.activity.list",
}
STREAM_CURSOR_FIELDS = {
    "leads":      "DATE_MODIFY",
    "deals":      "DATE_MODIFY",
    "contacts":   "DATE_MODIFY",
    "companies":  "DATE_MODIFY",
    "tasks":      "CHANGED_DATE",
    "activities": "LAST_UPDATED",
}
```

**Метод `_call(method, params)`:**
- POST `{webhook_url}{method}.json`
- Body: `{"start": offset, ...filter_params}`
- Разобрать `result` из JSON
- Цикл пагинации: пока `next` присутствует в ответе → `start = response["next"]`

**Метод `check()`:**
```python
POST {webhook_url}app.info.json
→ {"result": {...}}: ok=True
→ HTTP 401/403: ok=False
```

**Метод `discover()`** — аналогично другим коннекторам, образец 10 записей per stream

**Метод `read()`:**
```python
filter_params = {}
if sync_mode == "incremental" and last_cursor:
    # Bitrix24 поддерживает фильтрацию через FILTER
    filter_params = {"FILTER[>" + cursor_field + "]": last_cursor}
rows = _call(STREAM_METHOD_MAP[stream_name], filter_params)
yield from filter_incremental_dict_rows(rows, cursor_field, last_cursor)
```

**Нормализация:**
- `DATE_MODIFY`, `DATE_CREATE` оставить как строки ISO (Bitrix возвращает в формате `2024-05-01T12:00:00+03:00`)
- `ASSIGNED_BY_ID` → `assigned_by_id` (snake_case)
- Функция `_normalize_row(row)`: ключи в нижний регистр + snake_case

### 3.3 Фикстуры — data/fixtures/bitrix24/
- `leads_page1.json` — `{"result": [...50 items], "next": 50, "total": 75}`
- `leads_page2.json` — `{"result": [...25 items], "total": 75}`
- `app_info.json` — ответ `app.info`

### 3.4 Тесты — tests/sources/test_bitrix24.py
- `test_check_ok`
- `test_check_bad_webhook` — невалидный URL → ok=False
- `test_discover_six_streams`
- `test_read_deals_full_refresh_paginated` — 2 страницы
- `test_read_incremental_filter_applied` — проверить что в запросе есть `FILTER[>DATE_MODIFY]`
- `test_normalize_row_keys_snake_case`

### 3.5 UI-схема
```python
"bitrix24": [
    {"key": "webhook_url", "label": "Webhook URL", "type": "string", "required": True,
     "hint": "Bitrix24 → Разработчикам → Входящие вебхуки → URL вебхука"},
]
```

### 3.6 Инструкция получения Webhook URL
1. Войти в Bitrix24 → меню слева → «Разработчикам»
2. «Входящие вебхуки» → «Добавить вебхук»
3. Выбрать права: CRM (чтение), Задачи (чтение)
4. Скопировать URL (формат: `https://<портал>.bitrix24.ru/rest/<id>/<токен>/`)

---

## 4. МойСклад

### Контекст
- **Тестовый аккаунт**: бесплатный тариф на moysklad.ru без юр. лица (индивидуальный предприниматель)
- API: REST JSON API v1.2, авторизация Bearer token
- Base URL: `https://api.moysklad.ru/api/remap/1.2/`
- Пагинация: `limit` (до 1000) + `offset`; в ответе `meta.size` (total), `rows` (страница)
- Основные эндпоинты: `/entity/product`, `/entity/customerorder`, `/entity/demand` (отгрузки), `/entity/invoiceout`, `/entity/counterparty`, `/entity/stock/all`

### 4.1 Конфигурация — config.py
```python
moysklad_token: str = Field(default="", validation_alias="DATANORMA_MOYSKLAD_TOKEN")
```
> ⚠️ Поле уже есть. Дополнительно рассмотреть:
```python
moysklad_page_limit: int = Field(default=1000)
moysklad_lookback_days: int = Field(default=30)
```

### 4.2 Реализация коннектора — sources/moysklad.py

**Константы:**
```python
MOYSKLAD_BASE = "https://api.moysklad.ru/api/remap/1.2"
MOYSKLAD_PAGE_LIMIT = 1000

STREAM_ENTITY_MAP = {
    "products":        "entity/product",
    "customer_orders": "entity/customerorder",
    "demands":         "entity/demand",
    "invoices_out":    "entity/invoiceout",
    "counterparties":  "entity/counterparty",
    "stock":           "report/stock/all",
}
STREAM_CURSOR_FIELDS = {
    "products":        "updated",
    "customer_orders": "updated",
    "demands":         "updated",
    "invoices_out":    "updated",
    "counterparties":  "updated",
    # stock — только full_refresh (нет поля updated)
}
```

**Метод `_paginate(entity_path, filter_str=None)`:**
```python
offset = 0
while True:
    params = {"limit": MOYSKLAD_PAGE_LIMIT, "offset": offset}
    if filter_str:
        params["filter"] = filter_str
    status, body = request_json("GET", f"{MOYSKLAD_BASE}/{entity_path}",
                                headers={"Authorization": f"Bearer {token}"}, params=params)
    rows = body.get("rows", [])
    yield from rows
    meta = body.get("meta", {})
    if offset + MOYSKLAD_PAGE_LIMIT >= meta.get("size", 0):
        break
    offset += MOYSKLAD_PAGE_LIMIT
```

**Метод `check()`:**
```python
GET /entity/employee?limit=1
→ 200: ok=True
→ 401: ok=False, "Неверный токен"
```

**Метод `read()`:**
```python
filter_str = None
if sync_mode == "incremental" and last_cursor:
    # МойСклад поддерживает: filter=updated>2024-01-01 12:00:00
    filter_str = f"updated>{last_cursor.replace('T', ' ')[:19]}"
rows = list(_paginate(STREAM_ENTITY_MAP[stream_name], filter_str))
rows_normalized = [_flatten_moysklad_row(r) for r in rows]
yield from filter_incremental_dict_rows(rows_normalized, cursor_field, last_cursor)
```

**Функция `_flatten_moysklad_row(row)`:**
- `meta.href` → `href` (ссылка на объект)
- Вложенные `agent`, `organization`, `store` → `agent_name` / `agent_href`
- `positions.meta.href` → `positions_href` (не раскрывать позиции, слишком вложены)
- Все `meta` ключи удалить из верхнего уровня

**Специфика стрима `stock`:**
- Эндпоинт `report/stock/all` — нет `updated`, только full_refresh
- Параметры: `stockMode=all`, `groupBy=product`

### 4.3 Фикстуры — data/fixtures/moysklad/
- `customer_orders_page1.json` — `{"meta": {"size": 1100, "limit": 1000, "offset": 0}, "rows": [...]}`
- `customer_orders_page2.json` — `{"meta": {"size": 1100, "limit": 1000, "offset": 1000}, "rows": [...]}`
- `products_page1.json`
- `stock_all.json`

### 4.4 Тесты — tests/sources/test_moysklad.py
- `test_check_ok`
- `test_check_invalid_token` — HTTP 401
- `test_discover_streams` — проверить 6 стримов
- `test_read_customer_orders_paginated` — 2 страницы (1100 записей)
- `test_read_incremental_filter` — проверить `filter=updated>...` в запросе
- `test_stock_is_full_refresh_only` — стрим stock не имеет cursor_field в IngestStream
- `test_flatten_row_removes_meta`

### 4.5 UI-схема
```python
"moysklad": [
    {"key": "token",          "label": "Токен API",     "type": "password", "required": True,
     "hint": "МойСклад → Настройки → Доступ к API → Создать токен"},
    {"key": "lookback_days",  "label": "Глубина, дней", "type": "integer",  "required": False,
     "default": 30},
]
```

### 4.6 Инструкция получения токена
1. МойСклад → Настройки (шестерёнка) → «Доступ к API»
2. «Создать новый токен» → задать имя → «Создать»
3. Скопировать токен (показывается один раз)

---

## 5. 1С (файловый экспорт)

### Контекст
- **Тестовый аккаунт**: 1С:Предприятие имеет **бесплатную учебную версию** (1С:Предприятие 8 — учебная)
  - Скачать: https://edu.1c.ru/ или http://1cv8edu.ru/
  - Ограничения: максимум 10 пользователей, нет 1С:Фреш подписки
- **Стратегия интеграции для ВКР**: файловый экспорт (CSV/XML/JSON) как наиболее универсальный метод
  - Не требует HTTP-сервера 1С (нужна лицензия КОРП)
  - Поддерживается во всех версиях платформы
- **Путь**: `datanorma_1c_export_path` (уже в `config.py`)

### 5.1 Поддерживаемые форматы файлов

| Формат | Описание | Приоритет |
|---|---|---|
| CSV | Выгрузка через обработку | ✅ Основной |
| XML (CommerceML 2.x) | Обмен с сайтом / 1С-Битрикс | ✅ Поддержать |
| JSON | Кастомные обработки | ⚡ Опционально |

### 5.2 Реализация коннектора — sources/onec.py

**Структура каталога экспорта:**
```
{datanorma_1c_export_path}/
├── НоменклатураСписок.csv       → stream: nomenclature
├── ОстаткиТоваров.csv           → stream: stock_balance
├── ЗаказыПокупателей.csv        → stream: customer_orders
├── РеализацияТоваров.csv        → stream: sales
├── import.xml                   → XML CommerceML (если есть)
└── export.json                  → JSON (если есть)
```

**Константы:**
```python
# Маппинг: имя файла (паттерн) → имя стрима
FILE_STREAM_MAP: dict[str, str] = {
    "номенклатура":     "nomenclature",
    "nomenclature":     "nomenclature",
    "остатки":          "stock_balance",
    "stock":            "stock_balance",
    "заказы":           "customer_orders",
    "orders":           "customer_orders",
    "реализация":       "sales",
    "sales":            "sales",
}
# Поля-курсоры по стриму
STREAM_CURSOR_FIELDS = {
    "customer_orders": "Дата",
    "sales":           "Дата",
}
```

**Метод `_detect_streams(export_dir)`:**
```python
streams = {}
for path in Path(export_dir).iterdir():
    stem_lower = path.stem.lower()
    for pattern, stream_name in FILE_STREAM_MAP.items():
        if pattern in stem_lower:
            streams[stream_name] = path
            break
# Проверить наличие XML
for xml_path in Path(export_dir).glob("*.xml"):
    streams["xml_" + xml_path.stem.lower()[:20]] = xml_path
return streams
```

**Метод `_read_csv(file_path)`:**
```python
# Попробовать кодировки: utf-8-sig → cp1251 → utf-8
for encoding in ("utf-8-sig", "cp1251", "utf-8"):
    try:
        with open(file_path, encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=";")
            return list(reader)
    except (UnicodeDecodeError, StopIteration):
        continue
raise RuntimeError(f"Не удалось прочитать {file_path}: неизвестная кодировка")
```

**Метод `_read_xml_commerceml(file_path)`:**
- Разобрать `<КоммерческаяИнформация>` → `<Каталог>` → `<Товары>` → `<Товар>`
- Каждый `<Товар>` → flat dict: `id`, `name`, `description`, `price_*` (для каждого `<ЦенаТипЦены>`)

**Метод `check()`:**
```python
export_dir = self._export_path()
if not export_dir:
    return SourceCheckResult(ok=False, message="Не задан путь datanorma_1c_export_path")
p = Path(export_dir)
if not p.exists():
    return SourceCheckResult(ok=False, message=f"Путь не существует: {export_dir}")
files = list(p.iterdir())
return SourceCheckResult(ok=True, message=f"Каталог доступен, файлов: {len(files)}", details={...})
```

**Метод `discover()`:** — обнаружить файлы → прочитать 200 строк → `records_to_json_schema`

**Метод `read()`:**
```python
file_path = self._detect_streams(export_dir).get(stream_name)
if file_path is None:
    raise ValueError(f"1С: файл для стрима {stream_name!r} не найден в {export_dir}")
if file_path.suffix.lower() == ".csv":
    rows = self._read_csv(file_path)
elif file_path.suffix.lower() == ".xml":
    rows = self._read_xml_commerceml(file_path)
else:
    raise ValueError(f"Неподдерживаемый формат: {file_path.suffix}")
cursor = STREAM_CURSOR_FIELDS.get(stream_name)
yield from filter_incremental_dict_rows(rows, cursor, last_cursor)
```

### 5.3 Обработка 1С для автоматического экспорта
Предоставить пользователям готовую внешнюю обработку `.epf`:
- Параметр: путь для выгрузки
- Выгружать: НоменклатураСписок.csv, ОстаткиТоваров.csv, ЗаказыПокупателей.csv
- Кодировка UTF-8-BOM, разделитель `;`
- Запускать по расписанию через регламентное задание

> Для ВКР: предоставить **описание обработки** + тестовые фикстуры CSV вместо реальной `.epf`

### 5.4 Фикстуры — data/fixtures/onec/
- `НоменклатураСписок.csv` — 20 строк с заголовком (UTF-8-BOM, разделитель `;`)
- `ОстаткиТоваров.csv`
- `ЗаказыПокупателей.csv` — с полем `Дата`
- `import.xml` — минимальный CommerceML 2.0 с 5 товарами

### 5.5 Тесты — tests/sources/test_onec.py
- `test_check_ok` — tmp_path с файлами фикстур
- `test_check_path_not_exists` — несуществующий путь → ok=False
- `test_check_no_path_configured` — пустая настройка → ok=False
- `test_detect_streams_finds_csv` — файл `НоменклатураСписок.csv` → stream `nomenclature`
- `test_read_csv_cp1251_encoding` — файл в CP1251 читается корректно
- `test_read_csv_utf8bom_encoding` — UTF-8-BOM
- `test_read_xml_commerceml` — товары из XML
- `test_discover_returns_streams` — 4 стрима из каталога с фикстурами
- `test_read_incremental_filter` — строки до last_cursor отфильтрованы
- `test_read_missing_stream_raises` — ValueError

### 5.6 UI-схема
```python
"1c": [
    {"key": "export_path", "label": "Путь к каталогу экспорта", "type": "string", "required": True,
     "hint": "Абсолютный путь к папке, куда 1С выгружает файлы CSV/XML. Пример: /opt/1c_exports/"},
]
```

---

## Сводный чеклист реализации

### По файлам:

| Файл | 1С | AmoCRM | Bitrix24 | МойСклад | Яндекс Метрика |
|---|:---:|:---:|:---:|:---:|:---:|
| `sources/<name>.py` — check/discover/read | 🔲 | 🔲 | 🔲 | 🔲 | ✅ |
| `config.py` — новые поля Settings | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| `sources/registry.py` — алиасы | ✅ | ✅ | ✅ | ✅ | ✅ |
| `connector_schema_meta.py` — UI JSON Schema | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| `tests/sources/test_<name>.py` | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |
| `data/fixtures/<name>/` — JSON/CSV | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 |

✅ — готово · ⚠️ — требует проверки · 🔲 — нужно создать

### По приоритету реализации:

1. **Яндекс Метрика** — коннектор готов, только тесты + UI-схема (минимум работы)
2. **МойСклад** — чистый REST, хорошая документация, пагинация простая
3. **Bitrix24** — webhook-авторизация проще OAuth, хорошо задокументирован
4. **AmoCRM** — OAuth flow чуть сложнее, нужен токен-обмен
5. **1С** — файловый подход, максимально независимый, нет внешних зависимостей

---

## Архитектурные требования ко всем коннекторам

1. **Без secrets в коде** — все токены только через `source_config` dict или `Settings`
2. **Timeout на HTTP-запросы** — не более 30 секунд (httpx `timeout=30.0`)
3. **Логирование** — `_log.warning(...)` при пропуске строки, `_log.debug(...)` при пагинации
4. **Идемпотентность discover()** — повторные вызовы возвращают одинаковую схему
5. **Типизация** — все публичные методы с аннотациями типов
6. **Graceful degradation** — `check()` никогда не бросает исключение, возвращает `SourceCheckResult(ok=False, ...)`

