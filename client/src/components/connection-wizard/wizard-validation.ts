import type { WizardFormState } from "@/components/connection-wizard/wizard-types";

export function credentialsJsonError(text: string): string | null {
  try {
    JSON.parse(text || "{}");
    return null;
  } catch {
    return "Некорректный JSON в конфигурации источника.";
  }
}

function streamIncrementalOk(s: WizardFormState): boolean {
  for (const name of s.enabledStreamNames) {
    const opt = s.streamOptions[name];
    if (opt?.sync_mode === "incremental" && !(opt.cursor_field?.trim())) {
      return false;
    }
  }
  return true;
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
      if (s.enabledStreamNames.length === 0) return true;
      if (!streamIncrementalOk(s)) return true;

      if (s.mappingRows.length === 0) return true;
      const missing = s.mappingRows.filter((r) => r.required && !r.targetField.trim());
      return missing.length > 0;
    }
    case 2:
      return s.destinationId == null || !s.destinationCheck?.ok;
    case 3:
      return false;
    default:
      return true;
  }
}
