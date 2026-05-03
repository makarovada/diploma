import type { IngestCatalogDto } from "@/lib/api-types";

export type SelectedStreamCfg = {
  sync_mode: "full_refresh" | "incremental";
  cursor_field: string | null;
};

export type WizardMappingRow = {
  id: string;
  streamName: string;
  sourceField: string;
  targetField: string;
  transformation: string;
  required: boolean;
};

export type CheckState = { ok: boolean; message: string } | null;

export type WizardPersistMetaV1 = {
  v: 1;
  normalization_enabled: boolean;
  mapping: Array<{
    stream: string;
    source_field: string;
    target_field: string;
    transformation: string;
  }>;
};

export type WizardFormState = {
  workspaceCode: string;
  connectionName: string;
  connectionDescription: string;
  sourceId: number | null;
  credentialsConfigText: string;
  /** Совпадает с credentialsConfigText после успешного PATCH; иначе нужно снова «Сохранить». */
  credentialsSavedText: string | null;
  sourceCheck: CheckState;
  destinationCheck: CheckState;
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  enabledStreamNames: string[];
  streamOptions: Record<string, SelectedStreamCfg>;
  destinationId: number | null;
  mappingRows: WizardMappingRow[];
  normalizationEnabled: boolean;
  scheduleCron: string;
  timezone: string;
  preflightOk: boolean | null;
  preflightMessage: string | null;
};
