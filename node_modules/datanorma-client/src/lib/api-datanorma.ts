import { apiGetJson, apiPostJson, type ApiRequestInit } from "@/lib/api-client";
import { filterVisibleConnectors } from "@/lib/connector-catalog";
import type {
  AdminUserRowDto,
  AuditLogRowDto,
  DestinationCatalogItemDto,
  DimSourceRowDto,
  EltConnectionDetailDto,
  NormIssueRowDto,
  SalesSummaryDto,
  StagingCountsDto,
  V1ConnectionItem,
  V1SyncRunLogItem,
  V1SyncRunItem,
  WorkspaceItemDto,
} from "@/lib/api-types";
import { enrichIssue } from "@/lib/issue-explanations";
import { describeCronExpression } from "@/lib/schedule-config";
import type { Connection, Destination, Issue, Run, Status } from "@/lib/types";

export type {
  AdminUserRowDto,
  AuditLogRowDto,
  DestinationCatalogItemDto,
  DimSourceRowDto,
  NormIssueRowDto,
  SalesSummaryDto,
  StagingCountsDto,
  V1ConnectionItem,
  V1SyncRunLogItem,
  V1SyncRunItem,
  WorkspaceItemDto,
} from "@/lib/api-types";

const soft: ApiRequestInit = { suppressGlobalAuthHandlers: true };

export async function fetchV1Connections(init?: ApiRequestInit) {
  return apiGetJson<{ items: V1ConnectionItem[] }>("/api/v1/sync-streams", { ...init });
}

export function fetchV1Syncs(limit = 50, init?: ApiRequestInit) {
  return apiGetJson<{ items: V1SyncRunItem[] }>(`/api/v1/syncs?limit=${limit}`, { ...init });
}

export function fetchV1Sync(runId: number, init?: ApiRequestInit) {
  return apiGetJson<{ item: V1SyncRunItem }>(`/api/v1/syncs/${runId}`, { ...init });
}

export function fetchV1SyncLogs(runId: number, init?: ApiRequestInit) {
  return apiGetJson<{ items: V1SyncRunLogItem[] }>(`/api/v1/syncs/${runId}/logs`, { ...init });
}

export function fetchV1SyncIssues(runId: number, limit = 200, init?: ApiRequestInit) {
  return apiGetJson<{ items: NormIssueRowDto[] }>(`/api/v1/syncs/${runId}/issues?limit=${limit}`, { ...init });
}

export function retryV1Sync(runId: number, init?: ApiRequestInit) {
  return apiPostJson<{ status: string; run_id: number }>(`/api/v1/syncs/${runId}/retry`, {}, { ...init });
}

export function cancelV1Sync(runId: number, init?: ApiRequestInit) {
  return apiPostJson<{ status: string; run_id: number; item?: V1SyncRunItem }>(
    `/api/v1/syncs/${runId}/cancel`,
    {},
    { ...init },
  );
}

export function resolveIssue(issueId: number, note = "", init?: ApiRequestInit) {
  return apiPostJson<{ item: { id: number; status: string } }>(`/api/v1/issues/${issueId}/resolve`, { note }, { ...init });
}

export function ignoreIssue(issueId: number, note = "", init?: ApiRequestInit) {
  return apiPostJson<{ item: { id: number; status: string } }>(`/api/v1/issues/${issueId}/ignore`, { note }, { ...init });
}

export function fetchSalesSummary(init?: ApiRequestInit) {
  return apiGetJson<SalesSummaryDto>("/api/data/sales-summary", { ...init });
}

export function fetchStagingCounts(init?: ApiRequestInit) {
  return apiGetJson<StagingCountsDto>("/api/data/staging-counts", { ...init });
}

export function fetchNormalizationIssues(limit = 20, init?: ApiRequestInit) {
  return apiGetJson<{ rows: NormIssueRowDto[] }>(`/api/data/normalization-issues?limit=${limit}`, { ...init });
}

/** Каталог коннекторов (источники/приёмники), без БД. Требует Bearer — используйте apiGetJson, не сырой fetch. */
export async function fetchV1ConnectorsCatalog(
  role: "all" | "source" | "destination" = "all",
  init?: ApiRequestInit,
) {
  const q = role === "all" ? "" : `?role=${role}`;
  const body = await apiGetJson<{ items: Array<Record<string, unknown>> }>(`/api/v1/connectors/catalog${q}`, { ...init });
  return { items: filterVisibleConnectors(body.items ?? []) };
}

export async function fetchV1ConnectorCatalogItem(code: string, init?: ApiRequestInit) {
  return apiGetJson<{ item: Record<string, unknown> }>(`/api/v1/connectors/catalog/${encodeURIComponent(code)}`, { ...init });
}

export async function probeRestBuilder(
  config: Record<string, unknown>,
  streamIndex = 0,
  init?: ApiRequestInit,
) {
  return apiPostJson<{
    ok: boolean;
    status_code: number | null;
    message: string;
    sample_records: Record<string, unknown>[];
    record_count: number;
    schema_hint?: Record<string, unknown>;
    stream?: string;
    url?: string;
  }>("/api/v1/connectors/rest-builder/probe", { config, stream_index: streamIndex }, { ...init });
}

export function fetchDimSources(init?: ApiRequestInit) {
  return apiGetJson<{ rows: DimSourceRowDto[] }>("/api/data/dim-sources", { ...init });
}

export function fetchDestinationsCatalog(init?: ApiRequestInit, workspaceCode?: string) {
  const q =
    workspaceCode != null && workspaceCode !== ""
      ? `?workspace_code=${encodeURIComponent(workspaceCode)}`
      : "";
  return apiGetJson<{ items: DestinationCatalogItemDto[]; warehouse_row_count?: number }>(
    `/api/data/destinations-catalog${q}`,
    { ...init },
  );
}

export function fetchWorkspaces(init?: ApiRequestInit) {
  return apiGetJson<{ items: WorkspaceItemDto[] }>("/api/v1/workspaces", { ...init }).then((r) => ({
    items: r.items.map((w) => ({
      ...w,
      workspace_code: w.code ?? w.workspace_code ?? "main",
      workspace_name: w.name ?? w.workspace_name ?? w.code,
    })),
  }));
}

export type AuditLogQuery = {
  workspace_id?: number;
  actor?: string;
  action?: string;
  resource_type?: string;
  result?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

export function fetchV1AuditLog(query: AuditLogQuery = {}, init?: ApiRequestInit) {
  const sp = new URLSearchParams();
  if (query.workspace_id != null) sp.set("workspace_id", String(query.workspace_id));
  if (query.actor?.trim()) sp.set("actor", query.actor.trim());
  if (query.action?.trim()) sp.set("action", query.action.trim());
  if (query.resource_type?.trim()) sp.set("resource_type", query.resource_type.trim());
  if (query.result?.trim()) sp.set("result", query.result.trim());
  if (query.date_from?.trim()) sp.set("date_from", query.date_from.trim());
  if (query.date_to?.trim()) sp.set("date_to", query.date_to.trim());
  if (query.limit != null) sp.set("limit", String(query.limit));
  if (query.offset != null) sp.set("offset", String(query.offset));
  const q = sp.toString();
  return apiGetJson<{ items: AuditLogRowDto[] }>(`/api/v1/audit-log${q ? `?${q}` : ""}`, { ...init });
}

export function fetchV1Queue(init?: ApiRequestInit) {
  return apiGetJson<{ items: Record<string, unknown>[] }>("/api/v1/queue", { ...init });
}

export function fetchV1Activity(init?: ApiRequestInit) {
  return apiGetJson<{ items: Record<string, unknown>[] }>("/api/v1/activity", { ...init });
}

export function fetchV1Schedules(init?: ApiRequestInit) {
  return apiGetJson<{ items: Record<string, unknown>[] }>("/api/v1/schedules", { ...init });
}

export function fetchAdminUsers(init?: ApiRequestInit) {
  return apiGetJson<{ users: AdminUserRowDto[] }>("/api/admin/users", { ...init });
}

export function mapSyncRunStatus(apiStatus: string): Status {
  const v = apiStatus.toLowerCase();
  if (v === "queued") return "queued";
  if (v === "running") return "running";
  if (v === "success") return "success";
  if (v === "failed") return "failed";
  if (v === "cancelled") return "cancelled";
  if (v === "partial") return "partial";
  return "draft";
}

/** Запуск sync_run относится к доменному ELT-подключению (id из /connections/:id). */
export function syncRunMatchesEltConnection(row: V1SyncRunItem, eltConnectionId: string): boolean {
  const d = row.domain_connection_id ?? row.connection_id;
  return d != null && String(d) === eltConnectionId;
}

export function mapV1SyncToRun(row: V1SyncRunItem): Run {
  const st = mapSyncRunStatus(row.status);
  let stage: Run["stage"] = "complete";
  if (st === "queued") stage = "extract";
  else if (st === "running") stage = "dbt_run";
  else if (st === "failed") stage = "validate";
  else if (st === "partial") stage = "validate";
  const connRef =
    row.domain_connection_id != null ? String(row.domain_connection_id) : row.connection_id != null ? String(row.connection_id) : "";
  return {
    id: String(row.id),
    connectionId: connRef,
    connectionName: `${row.integration_code} → ${row.stream_name}`,
    status: st,
    stage,
    startedAt: formatTs(row.started_at),
    duration: syncRunDuration(row.started_at, row.finished_at, row.duration_ms),
    records: row.records_written ?? 0,
    issues: row.issues_count ?? 0,
    triggeredBy: row.triggered_by ?? "—",
  };
}

function mapNormSeverity(issueType: string): Issue["severity"] {
  const t = issueType.toLowerCase();
  if (t.includes("error") || t.includes("invalid") || t.includes("reject")) return "high";
  if (t.includes("warn")) return "medium";
  return "low";
}

export function mapNormRowToIssue(row: NormIssueRowDto): Issue {
  const issueType = row.issue_type || row.error_code || "cast_error";
  const msg = row.message ?? row.error_text ?? "—";
  const base: Issue = {
    id: String(row.id),
    severity: mapNormSeverity(issueType),
    type: issueType,
    connection: row.connection_name ?? (row.connection_id != null ? `#${row.connection_id}` : row.source_system ?? "—"),
    stream: row.stream_name ?? row.batch_id ?? "—",
    field: row.field_name ?? row.target_field ?? "—",
    original: msg,
    suggested: row.source_record_id ? `record:${row.source_record_id}` : "—",
    status: row.status ?? "open",
  };
  return enrichIssue(base, row);
}

export function filterIssuesByConnectionId(rows: NormIssueRowDto[], connectionId: number): NormIssueRowDto[] {
  return rows.filter((r) => r.connection_id === connectionId);
}

export function formatTs(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export function mapV1ToConnection(row: V1ConnectionItem): Connection {
  const sm = row.sync_mode as Connection["syncMode"];
  const mode = sm === "incremental" || sm === "full_refresh" || sm === "append" || sm === "upsert" ? sm : "incremental";
  return {
    id: String(row.id),
    name: `${row.integration_code} → ${row.stream_name}`,
    source: row.integration_code,
    destination: "PostgreSQL (warehouse)",
    status: row.last_success_at ? "success" : "ready",
    syncMode: mode,
    schedule: "—",
    lastRunAt: formatTs(row.last_success_at),
    records: 0,
    issues: 0,
    mappingCoverage: 0,
    normalizationEnabled: true,
  };
}

/** Карточка подключения из ELT GET /api/v1/connections */
export function mapEltDetailToConnection(row: EltConnectionDetailDto): Connection {
  const firstStream = row.streams?.[0];
  const sm = (firstStream?.sync_mode as Connection["syncMode"]) || "incremental";
  const mode = sm === "incremental" || sm === "full_refresh" || sm === "append" || sm === "upsert" ? sm : "incremental";
  let st: Connection["status"] = "ready";
  if (!row.is_active) st = "disabled";
  else if (row.status === "paused") st = "paused";
  const src =
    row.source_connector_code && row.source_name
      ? `${row.source_connector_code} · ${row.source_name}`
      : row.source_connector_code || `source #${row.source_id}`;
  const dst =
    row.destination_name && row.destination_connector_code
      ? `${row.destination_connector_code} · ${row.destination_name}`
      : row.destination_name || row.destination_connector_code || `destination #${row.destination_id}`;
  return {
    id: String(row.id),
    name: row.name,
    source: src,
    destination: dst,
    status: st,
    syncMode: mode,
    schedule: row.schedule_cron?.trim()
      ? describeCronExpression(row.schedule_cron.trim(), row.timezone || "UTC")
      : "ручной",
    lastRunAt: "—",
    records: 0,
    issues: 0,
    mappingCoverage: 0,
    normalizationEnabled: true,
  };
}

export function mapDestinationCatalogItem(row: DestinationCatalogItemDto): Destination {
  return {
    id: row.id,
    name: row.name,
    type: row.type,
    connectorCode: row.connector_code,
    status: row.status,
    schemaOrDb: row.schema_or_db,
    lastUsed: row.last_used_label,
    connectionCount: row.connection_count,
  };
}

export function syncRunLogLines(row: V1SyncRunItem): string[] {
  const lines: string[] = [];
  if (row.started_at) lines.push(`[info] Старт: ${formatTs(row.started_at)}`);
  if (row.finished_at) lines.push(`[info] Окончание: ${formatTs(row.finished_at)}`);
  if (row.dagster_run_id) lines.push(`[info] Dagster run: ${row.dagster_run_id}`);
  if (row.error_message) lines.push(`[error] ${row.error_message}`);
  if (lines.length === 0) lines.push("Нет текстовых логов в API для этого запуска.");
  return lines;
}

export function syncRunLogItemsToLines(rows: V1SyncRunLogItem[]): string[] {
  if (rows.length === 0) return ["Нет текстовых логов в API для этого запуска."];
  return rows.map((r) => `[${r.level}] [${r.stage}] ${r.message}`);
}

export function syncRunDuration(
  started: string | null,
  finished: string | null,
  durationMs?: number | null,
): string {
  if (durationMs != null && durationMs >= 0) {
    const sec = Math.max(0, Math.floor(durationMs / 1000));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  if (!started) return "—";
  try {
    const a = new Date(started).getTime();
    const b = finished ? new Date(finished).getTime() : Date.now();
    const sec = Math.max(0, Math.floor((b - a) / 1000));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  } catch {
    return "—";
  }
}
