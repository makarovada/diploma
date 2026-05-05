/**
 * DTO / контракты ответов REST API (как приходит с сервера).
 * UI-модели — в types.ts; маппинг — в api-datanorma.ts.
 */

export type WorkspaceRefDto = {
  id: number;
  code: string;
  name: string;
};

export type MeDto = {
  username: string;
  roles: string[];
  user_id?: number | null;
  workspaces: WorkspaceRefDto[];
  active_workspace_id: number | null;
};

export type LoginResponseDto = {
  access_token: string;
  token_type: string;
};

export type AuditLogRowDto = {
  id: number;
  workspace_id: number | null;
  actor_user_id: number | null;
  actor_username: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  result: string;
  payload_json: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string | null;
};

export type V1ConnectionItem = {
  id: number;
  integration_code: string;
  stream_name: string;
  sync_mode: string;
  cursor_field: string | null;
  cursor_value: unknown;
  last_success_at: string | null;
  updated_at: string | null;
};

export type V1SyncRunItem = {
  id: number;
  workspace_id?: number | null;
  connection_id: number | null;
  integration_code: string;
  stream_name: string;
  status: string;
  dagster_run_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  triggered_by: string | null;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
  load_destination?: { connector_code: string; name: string };
};

export type V1SyncRunLogItem = {
  id: number;
  sync_run_id: number;
  stage: "extract" | "staging_raw" | "normalize" | "dbt_run" | "validate" | "complete";
  level: "debug" | "info" | "warning" | "error";
  message: string;
  technical_details?: Record<string, unknown> | null;
  record_ref?: string | null;
  created_at?: string | null;
};

export type SalesSummaryDto = {
  table: string;
  row_count: number;
  max_loaded_at: string | null;
};

export type StagingCountsDto = {
  raw_ozon_postings_staging: number;
  raw_1c_orders_staging: number;
  raw_google_sheet_orders_staging: number;
};

export type NormIssueRowDto = {
  id: number;
  batch_id: string | null;
  source_system: string | null;
  source_record_id: string | null;
  field_name: string | null;
  issue_type: string;
  message: string | null;
  status?: "open" | "resolved" | "ignored";
  resolved_at?: string | null;
  resolution_note?: string | null;
  resolved_by?: string | null;
  created_at: string | null;
};

export type WorkspaceItemDto = {
  org_code: string;
  org_name: string;
  workspace_code: string;
  workspace_name: string;
};

export type AdminUserRowDto = {
  id: number;
  username: string;
  email: string | null;
  roles: string[];
};

export type DimSourceRowDto = {
  code: string;
  name: string;
  description: string | null;
};

export type DbtModelColumnDto = {
  name: string;
  dataType: string;
  description?: string;
  isPrimaryKey?: boolean;
};

/** GET /api/v1/dbt/models */
export type DbtModelItemDto = {
  name: string;
  schema: string;
  materialized_as: string;
  sources: string[];
  domain: string;
  path: string;
  description?: string;
  columns: DbtModelColumnDto[];
};

export type DbtModelsResponseDto = {
  items: DbtModelItemDto[];
  source?: "manifest" | "sql";
};

export type DbtModelPreviewResponseDto = {
  model_name: string;
  schema: string;
  rows: Record<string, unknown>[];
};

export type DestinationCatalogItemDto = {
  id: string;
  name: string;
  type: string;
  connector_code?: string;
  status: "ok" | "warning" | "error";
  schema_or_db: string;
  last_used_label: string;
  connection_count: number;
};

/** Доменная модель Фазы 4: GET /api/v1/sources, destinations, connections */
export type EltSourceItemDto = {
  id: number;
  workspace_id: number;
  name: string;
  connector_code: string;
  config: Record<string, unknown>;
  status: string;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_checked_at?: string | null;
};

export type EltDestinationItemDto = {
  id: number;
  workspace_id: number;
  name: string;
  connector_code: string;
  config: Record<string, unknown>;
  status: string;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_checked_at?: string | null;
};

export type EltDestinationCreatePayload = {
  workspace_code: string;
  name: string;
  connector_code: string;
  config: Record<string, unknown>;
};

export type EltCheckResponseDto = {
  ok: boolean;
  message: string;
  details: unknown;
};

export type IngestStreamDto = {
  name: string;
  json_schema?: Record<string, unknown>;
  supported_sync_modes?: string[];
  default_cursor_field?: string[] | null;
  source_defined_cursor?: boolean | null;
};

export type IngestCatalogDto = {
  streams: IngestStreamDto[];
};

export type EltDiscoverResponseDto = {
  catalog: IngestCatalogDto;
};

export type EltConnectionStreamRowDto = {
  id: number;
  connection_id: number;
  stream_name: string;
  sync_mode: string;
  cursor_field: string | null;
  primary_key: string | null;
  is_enabled: boolean;
  cursor_value: string | null;
  mapping_profile_id: number | null;
};

export type EltConnectionDetailDto = {
  id: number;
  workspace_id: number;
  name: string;
  description: string | null;
  source_id: number;
  destination_id: number;
  status: string;
  schedule_cron: string | null;
  timezone: string;
  is_active: boolean;
  created_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  stream_count?: number;
  streams?: EltConnectionStreamRowDto[];
};

export type EltConnectionCreatePayload = {
  workspace_code: string;
  name: string;
  description?: string | null;
  source_id: number;
  destination_id: number;
  schedule_cron?: string | null;
  timezone: string;
  streams: Array<{
    stream_name: string;
    sync_mode: string;
    cursor_field?: string | null;
    primary_key?: string | null;
    is_enabled?: boolean;
    mapping_profile_id?: number | null;
  }>;
};

export type EltConnectionTriggerResponseDto = {
  status: string;
  message?: string;
  run_id: number;
  sync_run: Record<string, unknown>;
};
