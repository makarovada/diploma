import { apiGetJson, ApiError, type ApiRequestInit } from "@/lib/api-client";
import type {
  AdminUserRowDto,
  DestinationCatalogItemDto,
  DimSourceRowDto,
  NormIssueRowDto,
  SalesSummaryDto,
  StagingCountsDto,
  V1ConnectionItem,
  V1SyncRunItem,
  WorkspaceItemDto,
} from "@/lib/api-types";
import type { Connection, Destination, Issue, Run, Source, Status } from "@/lib/types";

export type {
  AdminUserRowDto,
  DestinationCatalogItemDto,
  DimSourceRowDto,
  NormIssueRowDto,
  SalesSummaryDto,
  StagingCountsDto,
  V1ConnectionItem,
  V1SyncRunItem,
  WorkspaceItemDto,
} from "@/lib/api-types";

/** @deprecated используйте NormIssueRowDto */
export type NormIssueRow = NormIssueRowDto;

const soft: ApiRequestInit = { suppressGlobalAuthHandlers: true };

function catalogFromLegacyConnectionsEndpoint(data: { items?: unknown[] }): { items: V1ConnectionItem[] } | null {
  const items = data.items ?? [];
  if (items.length === 0) {
    return { items: [] };
  }
  const x = items[0];
  if (typeof x !== "object" || x === null) {
    return null;
  }
  const row = x as Record<string, unknown>;
  if ("source_id" in row && "stream_count" in row) {
    return null;
  }
  if (
    "integration_code" in row &&
    "stream_name" in row &&
    typeof row.integration_code === "string"
  ) {
    return { items: items as V1ConnectionItem[] };
  }
  return null;
}

/** Каталог строк sync_state (курсоры). Основной путь — /api/v1/sync-streams; при 404 — fallback на старый GET /api/v1/connections (только если ответ в формате sync_state). */
export async function fetchV1Connections(init?: ApiRequestInit) {
  try {
    return await apiGetJson<{ items: V1ConnectionItem[] }>("/api/v1/sync-streams", { ...init });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      const body = await apiGetJson<{ items: unknown[] }>("/api/v1/connections", { ...init });
      const mapped = catalogFromLegacyConnectionsEndpoint(body);
      if (mapped !== null) {
        return mapped;
      }
    }
    throw e;
  }
}

export function fetchV1Syncs(limit = 50, init?: ApiRequestInit) {
  return apiGetJson<{ items: V1SyncRunItem[] }>(`/api/v1/syncs?limit=${limit}`, { ...init });
}

export function fetchV1Sync(runId: number, init?: ApiRequestInit) {
  return apiGetJson<{ item: V1SyncRunItem }>(`/api/v1/syncs/${runId}`, { ...init });
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

export function fetchDimSources(init?: ApiRequestInit) {
  return apiGetJson<{ rows: DimSourceRowDto[] }>("/api/data/dim-sources", { ...init });
}

export function fetchDestinationsCatalog(init?: ApiRequestInit) {
  return apiGetJson<{ items: DestinationCatalogItemDto[]; warehouse_row_count?: number }>(
    "/api/data/destinations-catalog",
    { ...init },
  );
}

export function fetchWorkspaces(init?: ApiRequestInit) {
  return apiGetJson<{ items: WorkspaceItemDto[] }>("/api/v1/workspaces", { ...init });
}

export function fetchAdminUsers(init?: ApiRequestInit) {
  return apiGetJson<{ users: AdminUserRowDto[] }>("/api/admin/users", { ...init });
}

export function fetchDashboardExtras() {
  return Promise.allSettled([
    fetchStagingCounts(soft),
    fetchV1Syncs(8, soft),
    fetchNormalizationIssues(8, soft),
  ]);
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

export function mapV1SyncToRun(row: V1SyncRunItem): Run {
  const st = mapSyncRunStatus(row.status);
  let stage: Run["stage"] = "complete";
  if (st === "queued") stage = "extract";
  else if (st === "running") stage = "normalize";
  else if (st === "failed") stage = "load";
  else if (st === "partial") stage = "validate";
  return {
    id: String(row.id),
    connectionId: row.connection_id != null ? String(row.connection_id) : "",
    connectionName: `${row.integration_code} → ${row.stream_name}`,
    status: st,
    stage,
    startedAt: formatTs(row.started_at),
    duration: syncRunDuration(row.started_at, row.finished_at),
    records: 0,
    issues: 0,
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
  return {
    id: String(row.id),
    severity: mapNormSeverity(row.issue_type),
    type: row.issue_type,
    connection: row.source_system ?? "—",
    stream: row.batch_id ?? "—",
    field: row.field_name ?? "—",
    original: row.message ?? "—",
    suggested: row.source_record_id ? `record:${row.source_record_id}` : "—",
    status: "open",
  };
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

export function buildSourcesFromDimAndV1(dimRows: DimSourceRowDto[], v1Items: V1ConnectionItem[]): Source[] {
  const byCode = new Map<string, { n: number; last: string | null; anyOk: boolean }>();
  for (const it of v1Items) {
    const c = it.integration_code;
    const agg = byCode.get(c) ?? { n: 0, last: null as string | null, anyOk: false };
    agg.n += 1;
    const u = it.updated_at || it.last_success_at;
    if (u && (!agg.last || u > agg.last)) agg.last = u;
    if (it.last_success_at) agg.anyOk = true;
    byCode.set(c, agg);
  }
  const dimByCode = new Map(dimRows.map((r) => [r.code, r]));
  const codes = new Set<string>([...dimByCode.keys(), ...byCode.keys()]);
  return Array.from(codes)
    .sort()
    .map((code) => {
      const dim = dimByCode.get(code);
      const st = byCode.get(code);
      let checkStatus: Source["checkStatus"] = "never";
      if (st && st.n > 0) {
        checkStatus = st.anyOk ? "ok" : "warning";
      }
      const category = dim?.description?.trim() ? "Справочник" : "Интеграция";
      return {
        id: code,
        name: dim?.name ?? code,
        connector: code,
        category,
        checkStatus,
        streamCount: st?.n ?? 0,
        lastUsed: st?.last ? formatTs(st.last) : "—",
        owner: "—",
      };
    });
}

export function mapDestinationCatalogItem(row: DestinationCatalogItemDto): Destination {
  return {
    id: row.id,
    name: row.name,
    type: row.type,
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

export function syncRunDuration(started: string | null, finished: string | null): string {
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
