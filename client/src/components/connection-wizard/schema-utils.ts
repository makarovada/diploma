export function schemaPropertyKeys(schema: Record<string, unknown> | undefined): string[] {
  if (!schema || typeof schema !== "object") return [];
  const props = schema.properties;
  if (!props || typeof props !== "object") return [];
  return Object.keys(props as Record<string, unknown>);
}

export function jsonSchemaRequiredList(schema: Record<string, unknown> | undefined): string[] {
  if (!schema) return [];
  const r = schema.required;
  if (!Array.isArray(r)) return [];
  return r.filter((x): x is string => typeof x === "string");
}
