import type { ColumnRuleType } from "@/components/connection-wizard/column-rule-types";

/** Простая эвристика типа колонки по имени поля (как в backend default_stream_rules). */
export function inferColumnRuleType(sourceField: string): ColumnRuleType {
  const name = sourceField.toLowerCase();
  if (name.includes("phone") || name.includes("телефон")) return "phone";
  if (name.includes("inn") || name.includes("инн")) return "inn";
  if (name.includes("kpp") || name.includes("кпп")) return "kpp";
  if (name.includes("ogrn") || name.includes("огрн")) return "ogrn";
  if (name.includes("email") || name.includes("e_mail") || name.includes("почта") || name.endsWith("mail")) {
    return "email";
  }
  if (name.includes("amount") || name.includes("сумма") || name.includes("price") || name.includes("цена")) {
    return "currency_amount";
  }
  if (name.includes("currency") || name.includes("валют")) return "currency_code";
  if (name.includes("date") || name.includes("дата") || name.endsWith("_at")) return "datetime";
  if (name === "id" || name.endsWith("_id")) return "integer";
  if (name.includes("count") || name.includes("qty") || name.includes("quantity")) return "integer";
  return "string";
}
