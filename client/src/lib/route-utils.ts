/** Извлекает id подключения из путей вида /connections/:id, /connections/:id/edit, … */
export function getConnectionIdFromPath(location: string): string | null {
  const pathOnly = location.split("?")[0] ?? location;
  const m = pathOnly.match(/^\/connections\/([^/]+)/);
  return m?.[1] && m[1] !== "new" ? m[1] : null;
}

/** Защита от open redirect: только относительные пути внутри приложения. */
export function safeReturnPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("://")) {
    return "/";
  }
  return next;
}

/** Параметр next из пути wouter (например `/login?next=/runs`). */
export function readNextFromRoutePath(loc: string): string | null {
  const q = loc.includes("?") ? loc.slice(loc.indexOf("?") + 1) : "";
  if (!q) return null;
  return new URLSearchParams(q).get("next");
}

/** Текущий маршрут внутри hash (#/path?query) для return URL после 401. */
export function currentHashRoutePath(): string {
  if (typeof window === "undefined") {
    return "/";
  }
  return window.location.hash.replace(/^#/, "") || "/";
}

/** Подписи верхнего уровня для хлебных крошек и заголовков (минимальный набор по ТЗ). */
export const routeSegmentLabels: Record<string, string> = {
  "/": "Дашборд",
  "/activity": "Активность",
  "/connections": "Подключения",
  "/sources": "Источники",
  "/destinations": "Приёмники",
  "/connectors": "Каталог коннекторов",
  "/runs": "Запуски",
  "/schedules": "Расписания",
  "/queue": "Очередь",
  "/normalization": "Нормализация",
  "/semantic-layer": "Семантический слой",
  "/issues": "Проблемные записи",
  "/data-preview": "Предпросмотр данных",
  "/users": "Пользователи и роли",
  "/workspaces": "Рабочие пространства",
  "/dictionaries": "Справочники",
  "/settings": "Настройки",
  "/audit": "Аудит",
  "/help": "Помощь",
  "/api-docs": "API docs",
  "/login": "Вход",
};

/** Человекочитаемый заголовок для пути без query (первый сегмент или точное совпадение). */
export function routeLabel(path: string): string {
  const pathOnly = (path.split("?")[0] ?? path).replace(/\/$/, "") || "/";
  if (routeSegmentLabels[pathOnly]) {
    return routeSegmentLabels[pathOnly];
  }
  const first = `/${pathOnly.split("/").filter(Boolean)[0] ?? ""}`;
  return routeSegmentLabels[first] ?? pathOnly;
}
