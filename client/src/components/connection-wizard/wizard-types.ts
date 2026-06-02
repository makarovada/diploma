import type { IngestCatalogDto } from "@/lib/api-types";
import type { ColumnRuleType } from "@/components/connection-wizard/column-rule-types";

export type SchemaLayout = "flat" | "entities";

export type StreamDefaultDto = {
  stream_name: string;
  sync_mode: string;
  destination_sync_mode: string;
  cursor_field: string[] | null;
  primary_key: string[] | null;
};

export type WizardColumnRuleRow = {
  id: string;
  /** Internal stream name; null for flat layout display only */
  entity: string | null;
  sourceField: string;
  targetField: string;
  ruleType: ColumnRuleType;
  required: boolean;
};

export type CheckState = { ok: boolean; message: string } | null;

export type WizardPersistMetaV2 = {
  v: 2;
  layout: SchemaLayout;
  selected_entities: string[];
  normalization_enabled: boolean;
  column_rules: Array<{
    entity: string | null;
    source_field: string;
    target_field: string;
    type: string;
    required: boolean;
  }>;
};

export type WizardFormState = {
  workspaceCode: string;
  connectionName: string;
  connectionDescription: string;
  sourceId: number | null;
  credentialsConfigText: string;
  credentialsSavedText: string | null;
  sourceCheck: CheckState;
  destinationCheck: CheckState;
  schemaLayout: SchemaLayout;
  entityLabels: Record<string, string>;
  streamDefaults: StreamDefaultDto[];
  discovery: IngestCatalogDto | null;
  discoveryError: string | null;
  selectedEntities: string[];
  destinationId: number | null;
  columnRuleRows: WizardColumnRuleRow[];
  normalizationEnabled: boolean;
  scheduleCron: string;
  timezone: string;
  preflightOk: boolean | null;
  preflightMessage: string | null;
};
