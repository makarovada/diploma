import type {
  ActivityEvent,
  AppUser,
  AuditEntry,
  CanonicalEntity,
  Connection,
  ConnectorCatalogItem,
  Destination,
  Issue,
  MappingRow,
  NormalizationRule,
  QueueJob,
  Run,
  ScheduleRow,
  Source,
} from "./types";

export const dashboardKpis = [
  { label: "Активные подключения", value: "12" },
  { label: "Успешные запуски за 24ч", value: "38" },
  { label: "Запуски с ошибками", value: "4" },
  { label: "Проблемные записи", value: "73" },
  { label: "Среднее время sync", value: "07:42" },
  { label: "Нормализовано", value: "96.2%" },
];

export const connections: Connection[] = [
  { id: "conn-1", name: "Ozon -> PostgreSQL: заказы", source: "Ozon", destination: "PostgreSQL", status: "partial", syncMode: "incremental", schedule: "Ежедневно 03:00", lastRunAt: "2 минуты назад", records: 12340, issues: 37, mappingCoverage: 92, normalizationEnabled: true },
  { id: "conn-2", name: "1С -> ClickHouse: продажи", source: "1С", destination: "ClickHouse", status: "success", syncMode: "upsert", schedule: "Каждый час", lastRunAt: "14 минут назад", records: 8103, issues: 0, mappingCoverage: 100, normalizationEnabled: true },
  { id: "conn-3", name: "Wildberries -> CSV: остатки", source: "Wildberries", destination: "CSV", status: "failed", syncMode: "full_refresh", schedule: "Вручную", lastRunAt: "1 час назад", records: 0, issues: 12, mappingCoverage: 74, normalizationEnabled: false },
];

export const runs: Run[] = [
  { id: "run-901", connectionId: "conn-1", connectionName: "Ozon -> PostgreSQL: заказы", status: "running", stage: "normalize", startedAt: "19:41", duration: "00:02:14", records: 9342, issues: 22, triggeredBy: "Мария Иванова" },
  { id: "run-900", connectionId: "conn-2", connectionName: "1С -> ClickHouse: продажи", status: "success", stage: "complete", startedAt: "18:58", duration: "00:06:39", records: 8103, issues: 0, triggeredBy: "Расписание" },
  { id: "run-899", connectionId: "conn-3", connectionName: "Wildberries -> CSV: остатки", status: "failed", stage: "load", startedAt: "18:11", duration: "00:03:01", records: 2201, issues: 12, triggeredBy: "Иван Петров" },
];

export const issues: Issue[] = [
  { id: "iss-111", severity: "high", type: "invalid phone", connection: "Ozon -> PostgreSQL: заказы", stream: "customers", field: "customer_phone", original: "8(999)12", suggested: "+79990000000", status: "open" },
  { id: "iss-112", severity: "medium", type: "unknown currency", connection: "1С -> ClickHouse: продажи", stream: "orders", field: "currency", original: "RURR", suggested: "RUB", status: "open" },
  { id: "iss-113", severity: "low", type: "invalid date", connection: "Wildberries -> CSV: остатки", stream: "stocks", field: "updated_at", original: "32.13.2026", suggested: "2026-12-13T00:00:00Z", status: "resolved" },
];

export const mappingRows: MappingRow[] = [
  { sourceField: "order_id", type: "string", targetField: "order.external_id", transformation: "trim", required: true, sample: "WB-9981", preview: "WB-9981", state: "mapped" },
  { sourceField: "phone", type: "string", targetField: "customer.phone", transformation: "normalize_phone", required: true, sample: "8(912)555-77-88", preview: "+79125557788", state: "mapped" },
  { sourceField: "status_text", type: "string", targetField: "", transformation: "", required: true, sample: "доставлен", preview: "-", state: "required_missing" },
  { sourceField: "total_price", type: "text", targetField: "order.total_amount", transformation: "to_number", required: false, sample: "12 800,00", preview: "12800.00", state: "type_mismatch" },
];

export const normalizationRules: NormalizationRule[] = [
  { id: "rule-date", title: "Даты и время", enabled: true, fixedCount: 11200, issuesCount: 8, description: "Преобразование к ISO 8601 и UTC" },
  { id: "rule-currency", title: "Валюты", enabled: true, fixedCount: 4300, issuesCount: 3, description: "RUB/USD/EUR, округление до 2 знаков" },
  { id: "rule-fio", title: "ФИО", enabled: true, fixedCount: 2100, issuesCount: 11, description: "Нормализация регистра и разбор полного имени" },
  { id: "rule-dedup", title: "Дедупликация", enabled: false, fixedCount: 0, issuesCount: 29, description: "Поиск дублей по телефону и email" },
];

export const runLogs = [
  "[19:41:12] [info] [extract] Извлечено 9342 записи из потока orders",
  "[19:41:26] [info] [staging] Данные загружены в staging.orders_raw",
  "[19:41:59] [warning] [normalize] Найдено 22 записи с некорректным телефоном",
  "[19:42:07] [error] [load] Колонка customer_phone отсутствует в public.orders_normalized",
];

export const activityEvents: ActivityEvent[] = [
  { id: "act-1", at: "2026-05-02 19:41", type: "run", title: "Запуск завершён частично", detail: "Ozon -> PostgreSQL: заказы · run-901" },
  { id: "act-2", at: "2026-05-02 18:58", type: "run", title: "Синхронизация успешна", detail: "1С -> ClickHouse: продажи · run-900" },
  { id: "act-3", at: "2026-05-02 17:20", type: "issue", title: "Новая проблемная запись", detail: "invalid phone · customers.customer_phone" },
  { id: "act-4", at: "2026-05-02 16:05", type: "config", title: "Обновлён маппинг", detail: "Профиль default для потока orders" },
  { id: "act-5", at: "2026-05-02 12:30", type: "user", title: "Приглашён пользователь", detail: "analyst@company.ru · роль Аналитик" },
];

export const sources: Source[] = [
  { id: "src-1", name: "Ozon — продажи", connector: "Ozon", category: "Маркетплейсы", checkStatus: "ok", streamCount: 6, lastUsed: "2 минуты назад", owner: "Мария Иванова" },
  { id: "src-2", name: "1С УТ — выгрузка", connector: "1С", category: "Учёт", checkStatus: "warning", streamCount: 4, lastUsed: "14 минут назад", owner: "Иван Петров" },
  { id: "src-3", name: "Google Sheets — лиды", connector: "Google Sheets", category: "Таблицы", checkStatus: "ok", streamCount: 1, lastUsed: "вчера", owner: "Мария Иванова" },
  { id: "src-4", name: "Яндекс Метрика — сайт", connector: "Яндекс Метрика", category: "Веб-аналитика", checkStatus: "ok", streamCount: 4, lastUsed: "3 часа назад", owner: "Пётр Аналитиков" },
];

export const destinations: Destination[] = [
  { id: "dst-1", name: "PostgreSQL — витрина", type: "PostgreSQL", status: "ok", schemaOrDb: "warehouse / public", lastUsed: "2 минуты назад", connectionCount: 5 },
  { id: "dst-2", name: "ClickHouse — аналитика", type: "ClickHouse", status: "ok", schemaOrDb: "analytics / default", lastUsed: "14 минут назад", connectionCount: 2 },
  { id: "dst-3", name: "Экспорт CSV — отчёты", type: "CSV", status: "warning", schemaOrDb: "—", lastUsed: "1 час назад", connectionCount: 1 },
];

export const connectorsCatalog: ConnectorCatalogItem[] = [
  { id: "ozon", name: "Ozon", category: "Маркетплейсы", region: "ru", role: "source", preview: false, description: "Заказы, остатки, товары для продавцов Ozon.", streams: ["orders", "products", "stocks"], auth: "API key" },
  {
    id: "yandex_metrika",
    name: "Яндекс Метрика",
    category: "Веб-аналитика",
    region: "ru",
    role: "source",
    preview: false,
    description: "Сводки, визиты, хиты и достижения целей счётчика через API Метрики.",
    streams: ["summary", "visits", "hits", "goals_reaches"],
    auth: "OAuth / токен",
  },
  { id: "1c", name: "1С", category: "Учёт", region: "ru", role: "source", preview: false, description: "Выгрузки из типовых и отраслевых конфигураций 1С.", streams: ["documents", "catalogs", "registers"], auth: "COM / HTTP-сервис / файлы" },
  { id: "google_sheets", name: "Google Sheets", category: "Таблицы", region: "intl", role: "source", preview: false, description: "Листы как табличный источник для прототипов и отчётов.", streams: ["sheet_range"], auth: "OAuth" },
  { id: "wb", name: "Wildberries", category: "Маркетплейсы", region: "ru", role: "source", preview: false, description: "Продажи и остатки по API Wildberries.", streams: ["orders", "stocks"], auth: "API key" },
  { id: "bitrix24", name: "Битрикс24", category: "CRM", region: "ru", role: "source", preview: false, description: "Сделки, контакты, лиды из облака или коробки.", streams: ["deals", "leads", "contacts"], auth: "OAuth / вебхук" },
  { id: "amocrm", name: "amoCRM", category: "CRM", region: "ru", role: "source", preview: false, description: "Воронки, сделки и контакты amoCRM.", streams: ["leads", "contacts", "companies"], auth: "OAuth / long-lived token" },
  { id: "moysklad", name: "МойСклад", category: "Учёт", region: "ru", role: "source", preview: false, description: "Склад, контрагенты, документы.", streams: ["demands", "stock"], auth: "login / token" },
  { id: "postgres", name: "PostgreSQL", category: "Базы данных", region: "intl", role: "destination", preview: false, description: "Загрузка в реляционную витрину.", streams: ["настраиваемые таблицы"], auth: "login / password" },
  { id: "clickhouse", name: "ClickHouse", category: "Базы данных", region: "intl", role: "destination", preview: false, description: "Колоночное хранилище для аналитики и витрин.", streams: ["tables"], auth: "login / password" },
  { id: "csv", name: "CSV", category: "Файлы", region: "intl", role: "destination", preview: false, description: "Выгрузка в файлы CSV для обмена и отчётности.", streams: ["file"], auth: "путь / S3" },
  { id: "xlsx", name: "XLSX", category: "Файлы", region: "intl", role: "destination", preview: false, description: "Выгрузка в Excel для бизнес-пользователей.", streams: ["workbook"], auth: "путь / S3" },
  { id: "rest-builder", name: "REST API Builder", category: "API", region: "intl", role: "source", preview: true, description: "Универсальный источник по OpenAPI/REST.", streams: ["custom"], auth: "token / OAuth" },
];

export const canonicalEntities: CanonicalEntity[] = [
  {
    id: "customer",
    nameRu: "Клиент",
    fields: [
      { name: "customer.id", type: "uuid", required: true, description: "Внутренний идентификатор", aliases: "client_id, buyer_id", rule: "trim, lower", example: "a1b2c3d4-…" },
      { name: "customer.phone", type: "phone_e164", required: false, description: "Телефон E.164", aliases: "tel, mobile", rule: "normalize_phone", example: "+79125557788" },
      { name: "customer.email", type: "email", required: false, description: "Email", aliases: "mail", rule: "lowercase", example: "user@company.ru" },
    ],
  },
  {
    id: "order",
    nameRu: "Заказ",
    fields: [
      { name: "order.external_id", type: "string", required: true, description: "ID заказа во внешней системе", aliases: "order_id, Номер", rule: "trim", example: "OZ-100992" },
      { name: "order.total_amount", type: "decimal", required: true, description: "Сумма в базовой валюте", aliases: "sum, total", rule: "currency + scale 2", example: "12800.00" },
      { name: "order.status", type: "enum", required: true, description: "Статус в канонической модели", aliases: "state", rule: "status_map", example: "delivered" },
    ],
  },
  {
    id: "product",
    nameRu: "Товар",
    fields: [
      { name: "product.sku", type: "string", required: true, description: "Артикул", aliases: "offer_id", rule: "trim", example: "SKU-7781" },
      { name: "product.name", type: "string", required: true, description: "Наименование", aliases: "title", rule: "title_case", example: "Кроссовки" },
    ],
  },
];

export const appUsers: AppUser[] = [
  { id: "u1", name: "Админ Системный", email: "admin@company.ru", role: "platform_admin", workspace: "ООО Ромашка", status: "active", lastActive: "сейчас" },
  { id: "u2", name: "Мария Иванова", email: "integrator@company.ru", role: "data_integrator", workspace: "ООО Ромашка", status: "active", lastActive: "5 минут назад" },
  { id: "u3", name: "Пётр Аналитиков", email: "analyst@company.ru", role: "analyst", workspace: "ООО Ромашка", status: "active", lastActive: "вчера" },
  { id: "u4", name: "Новый пользователь", email: "viewer@company.ru", role: "viewer", workspace: "ООО Ромашка", status: "invited", lastActive: "—" },
];

export const auditEntries: AuditEntry[] = [
  { id: "aud-1", at: "2026-05-02 19:40", actor: "Мария Иванова", action: "sync.start", entityType: "connection", entityName: "Ozon -> PostgreSQL: заказы", result: "success", details: "run-901" },
  { id: "aud-2", at: "2026-05-02 16:00", actor: "Админ Системный", action: "user.invite", entityType: "user", entityName: "viewer@company.ru", result: "success", details: "роль viewer" },
  { id: "aud-3", at: "2026-05-01 09:15", actor: "Мария Иванова", action: "mapping.update", entityType: "mapping_profile", entityName: "default / orders", result: "success", details: "изменено 3 поля" },
  { id: "aud-4", at: "2026-04-30 22:01", actor: "system", action: "sync.failed", entityType: "run", entityName: "run-899", result: "failure", details: "ошибка загрузки в PostgreSQL" },
];

export const schedules: ScheduleRow[] = [
  { id: "sch-1", connectionName: "Ozon -> PostgreSQL: заказы", schedule: "Ежедневно 03:00", timezone: "Europe/Moscow", nextRun: "2026-05-03 03:00", lastRun: "2026-05-02 03:00", status: "success", owner: "Мария Иванова" },
  { id: "sch-2", connectionName: "1С -> ClickHouse: продажи", schedule: "Каждый час", timezone: "Europe/Moscow", nextRun: "2026-05-02 20:00", lastRun: "2026-05-02 19:00", status: "running", owner: "Расписание" },
];

export const queueJobs: QueueJob[] = [
  { id: "job-101", connectionName: "Ozon -> PostgreSQL: заказы", stage: "normalize", priority: 10, queuedAt: "19:40:01", startedAt: "19:40:05", worker: "worker-2", status: "running" },
  { id: "job-100", connectionName: "Битрикс24 -> PostgreSQL: сделки", stage: "queued", priority: 5, queuedAt: "19:39:50", startedAt: "—", worker: "—", status: "queued" },
];

export const workspaceList = [
  { id: "ws-main", name: "ООО Ромашка", code: "main", role: "владелец" },
  { id: "ws-demo", name: "Демо-песочница", code: "demo", role: "участник" },
];

export const dictionarySummary = [
  { id: "dict-currency", name: "Валюты (ISO 4217)", rows: 12, updatedAt: "2026-04-01" },
  { id: "dict-status-order", name: "Статусы заказа (канон)", rows: 18, updatedAt: "2026-03-15" },
  { id: "dict-phone-region", name: "Коды регионов телефонов РФ", rows: 90, updatedAt: "2026-01-10" },
];

/** Для демонстрации empty state на дашборде установите `true`. */
export const dashboardForceEmptyState = false;

/** Запуски за 7 дней (stacked bar — мок). */
export const dashboardRunsByDay = [
  { day: "26.04", success: 14, partial: 1, failed: 0, running: 0 },
  { day: "27.04", success: 11, partial: 2, failed: 1, running: 0 },
  { day: "28.04", success: 16, partial: 0, failed: 0, running: 0 },
  { day: "29.04", success: 9, partial: 3, failed: 2, running: 0 },
  { day: "30.04", success: 12, partial: 1, failed: 0, running: 0 },
  { day: "01.05", success: 15, partial: 2, failed: 0, running: 0 },
  { day: "02.05", success: 10, partial: 2, failed: 1, running: 1 },
];

export const connectorHealth = [
  { id: "h-ozon", name: "Ozon", status: "ok" as const, detail: "API отвечает в норме" },
  { id: "h-metrika", name: "Яндекс Метрика", status: "ok" as const, detail: "Отчёты и логи доступны" },
  { id: "h-1c", name: "1С", status: "warning" as const, detail: "Повышенная задержка выгрузки" },
  { id: "h-pg", name: "PostgreSQL", status: "ok" as const, detail: "Витрина доступна" },
  { id: "h-ch", name: "ClickHouse", status: "ok" as const, detail: "Кластер в норме" },
];

export const connectionStreamRows = [
  { stream: "orders", enabled: true, syncMode: "incremental", cursor: "updated_at", primaryKey: "id", lastSync: "2 минуты назад", records: 12340, status: "success" },
  { stream: "products", enabled: true, syncMode: "full_refresh", cursor: "—", primaryKey: "sku", lastSync: "1 час назад", records: 5600, status: "partial" },
  { stream: "customers", enabled: true, syncMode: "incremental", cursor: "modified_at", primaryKey: "id", lastSync: "2 минуты назад", records: 8900, status: "success" },
  { stream: "stocks", enabled: false, syncMode: "incremental", cursor: "ts", primaryKey: "offer_id", lastSync: "—", records: 0, status: "draft" },
];

export const runLogsExtended = [
  "[19:41:12] [info] [extract] Извлечено 9342 записи из потока orders",
  "[19:41:26] [info] [staging] Данные загружены в staging.orders_raw",
  "[19:41:45] [info] [normalize] Применены правила дат и телефонов",
  "[19:41:59] [warning] [normalize] Найдено 22 записи с некорректным телефоном",
  "[19:42:01] [info] [validate] Проверка обязательных полей пройдена частично",
  "[19:42:07] [error] [load] Колонка customer_phone отсутствует в public.orders_normalized",
  "[19:42:08] [info] [complete] Синхронизация завершена с предупреждениями",
];

export function getRunsForConnection(connectionId: string) {
  return runs.filter((r) => r.connectionId === connectionId);
}

export function getIssuesForConnection(connectionName: string) {
  return issues.filter((i) => i.connection === connectionName);
}
