/** Типы колонок для правил нормализации (совпадают с backend ColumnType). */
export const COLUMN_RULE_TYPES = [
  "string",
  "integer",
  "number",
  "boolean",
  "date",
  "datetime",
  "currency_amount",
  "currency_code",
  "phone",
  "email",
  "inn",
  "kpp",
  "ogrn",
  "enum",
  "json",
] as const;

export type ColumnRuleType = (typeof COLUMN_RULE_TYPES)[number];
