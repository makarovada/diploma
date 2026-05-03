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
      return !s.connectionName.trim();
    case 1:
      return s.sourceId == null;
    case 2:
      return (
        Boolean(credentialsJsonError(s.credentialsConfigText)) ||
        s.credentialsSavedText !== s.credentialsConfigText
      );
    case 3:
      return !s.sourceCheck?.ok;
    case 4:
      return (
        !s.discovery?.streams?.length ||
        s.enabledStreamNames.length === 0 ||
        !streamIncrementalOk(s)
      );
    case 5:
      return s.destinationId == null;
    case 6:
      return !s.destinationCheck?.ok;
    case 7: {
      const missing = s.mappingRows.filter((r) => r.required && !r.targetField.trim());
      return missing.length > 0;
    }
    case 8:
      return false;
    case 9:
      return false;
    case 10:
      return s.preflightOk !== true;
    case 11:
      return false;
    default:
      return true;
  }
}
