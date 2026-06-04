import type { Bitrix24Config } from "@/components/bitrix24-source-form";
import { bitrix24ConfigToRecord, parseBitrix24Config } from "@/components/bitrix24-source-form";

/** Нормализует config источника перед сохранением / отображением в мастере. */
export function normalizeSourceConfigForConnector(
  connectorCode: string | null | undefined,
  config: Record<string, unknown>,
): Record<string, unknown> {
  if (connectorCode === "bitrix24") {
    return bitrix24ConfigToRecord(parseBitrix24Config(config));
  }
  return config;
}

export function normalizeSourceConfigTextForConnector(
  connectorCode: string | null | undefined,
  configText: string,
): string {
  try {
    const parsed = JSON.parse(configText || "{}") as Record<string, unknown>;
    return JSON.stringify(normalizeSourceConfigForConnector(connectorCode, parsed), null, 2);
  } catch {
    return configText;
  }
}

export function parseBitrix24ConfigFromText(configText: string): Bitrix24Config {
  try {
    const parsed = JSON.parse(configText || "{}") as Record<string, unknown>;
    return parseBitrix24Config(parsed);
  } catch {
    return parseBitrix24Config({});
  }
}
