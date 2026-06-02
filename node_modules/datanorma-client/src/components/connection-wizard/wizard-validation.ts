import type { StreamDefaultDto, WizardFormState } from "@/components/connection-wizard/wizard-types";
import { REPLICATION_PRESETS, replicationPresetFromFields } from "@/lib/destination-sync-mode";

export function credentialsJsonError(text: string): string | null {
  try {
    JSON.parse(text || "{}");
    return null;
  } catch {
    return "Некорректный JSON в конфигурации источника.";
  }
}

function streamReplicationValid(st: StreamDefaultDto): boolean {
  const preset = REPLICATION_PRESETS.find(
    (p) => p.id === replicationPresetFromFields(st.sync_mode, st.destination_sync_mode),
  );
  if (!preset) return false;
  if (preset.needsCursor && (st.cursor_field ?? []).length === 0) return false;
  if (preset.needsPrimaryKey && (st.primary_key ?? []).length === 0) return false;
  return true;
}

function selectedSchemaKeys(s: WizardFormState): string[] {
  if (s.schemaLayout === "flat") {
    const first = s.discovery?.streams?.[0]?.name;
    return first ? [first] : [];
  }
  return s.selectedEntities;
}

/** true = Next должен быть отключён */
export function stepBlocksNext(step: number, s: WizardFormState): boolean {
  switch (step) {
    case 0:
      return (
        !s.connectionName.trim() ||
        s.sourceId == null ||
        Boolean(credentialsJsonError(s.credentialsConfigText)) ||
        s.credentialsSavedText !== s.credentialsConfigText ||
        !s.sourceCheck?.ok
      );
    case 1: {
      if (!s.discovery?.streams?.length) return true;
      const keys = selectedSchemaKeys(s);
      if (keys.length === 0) return true;
      if (s.columnRuleRows.length === 0) return true;
      const active = s.streamDefaults.filter((d) => keys.includes(d.stream_name));
      if (active.length !== keys.length) return true;
      return !active.every(streamReplicationValid);
    }
    case 2:
      return s.destinationId == null || !s.destinationCheck?.ok;
    case 3:
      return false;
    default:
      return true;
  }
}
