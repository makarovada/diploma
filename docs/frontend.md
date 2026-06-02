# Веб-интерфейс DataNorma

- **Продуктовый UI** — React/Vite SPA, собирается в `client/`, раздаётся с FastAPI под **`/ui/`** (корень **`/`** перенаправляет на **`/ui/`**). Маршрутизация в приложении — hash (`/#/...`), API — **`/api/...`** с Bearer JWT.
- **Новые пользовательские экраны** добавлять в React (`client/src/pages/...`), с **`data-testid`** на ключевых элементах.

Подробности запуска и переменные окружения — в корневом [README.md](../README.md).

## Цвета и дальтонизм

Семантические токены в `client/src/index.css` подобраны по палитре [Paul Tol](https://sronpersonalpages.nl/~pault/): **успех — синий**, **ошибка — вермилион (оранжево-красный)**, **предупреждение — жёлто-оранжевый**, **выполняется — сине-фиолетовый**. Пара «зелёный / красный» для статусов не используется. Бейджи (`StatusBadge`) дополнительно различаются **иконкой и рамкой**, не только цветом.

### Как проверить у себя

1. **Chrome / Edge:** DevTools → ⋮ → More tools → **Rendering** → **Emulate vision deficiencies** (Deuteranopia, Protanopia, Tritanopia).
2. **Firefox:** about:config → `ui.useAccessibility.colors` или расширения-симуляторы.
3. Онлайн: [Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/) — загрузите скриншот страницы «Запуски» или дашборда.

После правок в `client/`: `docker compose build fastapi --pull=false` (UI в образе на `:8080`) или dev-сервер на `:5173`.

## Мастер подключения

Шаг **«Колонки и типы»** (`connection-wizard`): обнаружение схемы (`POST /api/v1/sources/{id}/discover` → `layout`, `entity_labels`), маппинг полей с типами нормализации (`phone`, `email`, `inn`, …). Создание подключения: `POST /api/v1/connections` с `column_rules` и `wizard_meta`. Страница **Правила колонок** читает `column_rules` из `GET /api/v1/connections/{id}`.
