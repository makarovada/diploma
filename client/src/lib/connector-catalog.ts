export function isHiddenConnectorCode(_code: string | null | undefined): boolean {
  return false;
}

export function filterVisibleConnectors<T extends Record<string, unknown>>(items: T[]): T[] {
  return items;
}
