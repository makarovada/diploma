/** Коннекторы, скрытые из UI-каталога (бэкенд по-прежнему поддерживает их для существующих интеграций). */
const HIDDEN_CONNECTOR_CODES = new Set(["1c", "onec", "ozon", "wildberries", "wb"]);

export function isHiddenConnectorCode(code: string | null | undefined): boolean {
  if (!code) return false;
  const k = code.trim().toLowerCase().replace(/-/g, "_");
  return HIDDEN_CONNECTOR_CODES.has(k);
}

export function filterVisibleConnectors<T extends Record<string, unknown>>(items: T[]): T[] {
  return items.filter((item) => !isHiddenConnectorCode(String(item.code ?? "")));
}
