/** Режимы репликации (парные, как в Airbyte / CDK). */

export type DestinationSyncMode =
  | "refresh_overwrite"
  | "refresh_append"
  | "append"
  | "append_dedup";

export type ReplicationPresetId =
  | "full_overwrite"
  | "full_append"
  | "incremental_append"
  | "incremental_dedup";

export type ReplicationPreset = {
  id: ReplicationPresetId;
  label: string;
  hint: string;
  sync_mode: "full_refresh" | "incremental";
  destination_sync_mode: DestinationSyncMode;
  needsCursor: boolean;
  needsPrimaryKey: boolean;
};

export const REPLICATION_PRESETS: ReplicationPreset[] = [
  {
    id: "full_overwrite",
    label: "Полная выгрузка — перезапись",
    hint: "Каждый запуск очищает таблицу приёмника и загружает все данные заново. Дубликатов нет.",
    sync_mode: "full_refresh",
    destination_sync_mode: "refresh_overwrite",
    needsCursor: false,
    needsPrimaryKey: false,
  },
  {
    id: "full_append",
    label: "Полная выгрузка — добавление",
    hint: "Каждый запуск читает весь источник и дописывает строки в приёмник (дубликаты возможны).",
    sync_mode: "full_refresh",
    destination_sync_mode: "refresh_append",
    needsCursor: false,
    needsPrimaryKey: false,
  },
  {
    id: "incremental_append",
    label: "Инкремент — добавление",
    hint: "Только новые/изменённые записи по курсору; строки дописываются без слияния.",
    sync_mode: "incremental",
    destination_sync_mode: "append",
    needsCursor: true,
    needsPrimaryKey: false,
  },
  {
    id: "incremental_dedup",
    label: "Инкремент — дедупликация",
    hint: "Инкремент по курсору + upsert по первичному ключу (как Deduped History в Airbyte).",
    sync_mode: "incremental",
    destination_sync_mode: "append_dedup",
    needsCursor: true,
    needsPrimaryKey: true,
  },
];

export function replicationPresetFromFields(
  sync_mode: string,
  destination_sync_mode: string | null | undefined,
): ReplicationPresetId {
  const sm = (sync_mode || "full_refresh").trim();
  const dsm = (destination_sync_mode || "").trim();
  if (dsm === "refresh_append" || (sm === "full_refresh" && dsm === "refresh_append")) {
    return "full_append";
  }
  if (dsm === "append_dedup") return "incremental_dedup";
  if (dsm === "append" || sm === "incremental") return "incremental_append";
  if (dsm === "refresh_overwrite" || sm === "full_refresh") return "full_overwrite";
  return sm === "incremental" ? "incremental_append" : "full_overwrite";
}

export function fieldsFromReplicationPreset(id: ReplicationPresetId): {
  sync_mode: "full_refresh" | "incremental";
  destination_sync_mode: DestinationSyncMode;
} {
  const p = REPLICATION_PRESETS.find((x) => x.id === id)!;
  return { sync_mode: p.sync_mode, destination_sync_mode: p.destination_sync_mode };
}

export function describeReplicationPreset(id: ReplicationPresetId): string {
  return REPLICATION_PRESETS.find((x) => x.id === id)?.label ?? id;
}

export function suggestPrimaryKeyField(fieldNames: string[]): string | null {
  const lower = fieldNames.map((f) => ({ f, l: f.toLowerCase() }));
  const idExact = lower.find((x) => x.l === "id");
  if (idExact) return idExact.f;
  const idSuffix = lower.find((x) => x.l.endsWith("_id") || x.l.endsWith("id"));
  if (idSuffix) return idSuffix.f;
  return fieldNames[0] ?? null;
}

export function parsePrimaryKeyFields(raw: string | string[] | null | undefined): string[] {
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x).trim()).filter(Boolean);
  }
  const text = (raw ?? "").trim();
  if (!text) return [];
  if (text.startsWith("[")) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((x) => String(x).trim()).filter(Boolean);
      }
    } catch {
      /* ignore */
    }
  }
  if (text.includes(",")) {
    return text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  }
  return [text];
}

export function encodePrimaryKeyFields(fields: string[] | null | undefined): string | null {
  const cleaned = (fields ?? []).map((x) => x.trim()).filter(Boolean);
  if (cleaned.length === 0) return null;
  if (cleaned.length === 1) return cleaned[0];
  return JSON.stringify(cleaned);
}

export function parseCursorFields(raw: string | string[] | null | undefined): string[] {
  if (Array.isArray(raw)) {
    return raw.map((x) => String(x).trim()).filter(Boolean);
  }
  const text = (raw ?? "").trim();
  if (!text) return [];
  if (text.startsWith("[")) {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((x) => String(x).trim()).filter(Boolean);
      }
    } catch {
      /* ignore */
    }
  }
  if (text.includes(",")) {
    return text
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);
  }
  return [text];
}

export function encodeCursorFields(fields: string[] | null | undefined): string | null {
  const cleaned = (fields ?? []).map((x) => x.trim()).filter(Boolean);
  if (cleaned.length === 0) return null;
  if (cleaned.length === 1) return cleaned[0];
  return JSON.stringify(cleaned);
}
