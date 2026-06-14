/**
 * REST API v1: доменные source / destination / connection (Фаза 4).
 */
import { apiDelete, apiGetJson, apiPatchJson, apiPostJson, type ApiRequestInit } from "@/lib/api-client";
import type {
  EltCheckResponseDto,
  EltConnectionCreatePayload,
  EltConnectionDetailDto,
  EltConnectionPatchPayload,
  EltConnectionTriggerResponseDto,
  EltDestinationCreatePayload,
  EltDestinationItemDto,
  EltDiscoverResponseDto,
  EltSourceCreatePayload,
  EltSourceItemDto,
} from "@/lib/api-types";

function ws(workspaceCode: string): string {
  return `workspace_code=${encodeURIComponent(workspaceCode)}`;
}

export function createEltSource(body: EltSourceCreatePayload, init?: ApiRequestInit) {
  return apiPostJson<{ item: EltSourceItemDto }, EltSourceCreatePayload>("/api/v1/sources", body, init);
}

export function fetchEltSources(workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ items: EltSourceItemDto[] }>(`/api/v1/sources?${ws(workspaceCode)}`, init);
}

export function fetchEltSource(sourceId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ item: EltSourceItemDto }>(`/api/v1/sources/${sourceId}?${ws(workspaceCode)}`, init);
}

export function patchEltSource(
  sourceId: number,
  body: { workspace_code?: string; name?: string | null; connector_code?: string | null; config?: Record<string, unknown> | null; status?: string | null },
  init?: ApiRequestInit,
) {
  return apiPatchJson<{ item: EltSourceItemDto }, typeof body>(`/api/v1/sources/${sourceId}`, body, init);
}

export function deleteEltSource(sourceId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiDelete(`/api/v1/sources/${sourceId}?${ws(workspaceCode)}`, init);
}

export function postEltSourceCheck(sourceId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiPostJson<EltCheckResponseDto, Record<string, never>>(
    `/api/v1/sources/${sourceId}/check?${ws(workspaceCode)}`,
    {},
    init,
  );
}

export function postEltSourceDiscover(sourceId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiPostJson<EltDiscoverResponseDto, Record<string, never>>(
    `/api/v1/sources/${sourceId}/discover?${ws(workspaceCode)}`,
    {},
    init,
  );
}

export function fetchEltDestinations(workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ items: EltDestinationItemDto[] }>(`/api/v1/destinations?${ws(workspaceCode)}`, init);
}

export function fetchEltDestination(destinationId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ item: EltDestinationItemDto }>(`/api/v1/destinations/${destinationId}?${ws(workspaceCode)}`, init);
}

export function postEltDestinationCheck(destinationId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiPostJson<EltCheckResponseDto, Record<string, never>>(
    `/api/v1/destinations/${destinationId}/check?${ws(workspaceCode)}`,
    {},
    init,
  );
}

export function createEltDestination(body: EltDestinationCreatePayload, init?: ApiRequestInit) {
  return apiPostJson<{ item: EltDestinationItemDto }, EltDestinationCreatePayload>(
    "/api/v1/destinations",
    body,
    init,
  );
}

export function patchEltDestination(
  destinationId: number,
  body: {
    workspace_code?: string;
    name?: string | null;
    connector_code?: string | null;
    config?: Record<string, unknown> | null;
    status?: string | null;
  },
  init?: ApiRequestInit,
) {
  return apiPatchJson<{ item: EltDestinationItemDto }, typeof body>(`/api/v1/destinations/${destinationId}`, body, init);
}

export function deleteEltDestination(destinationId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiDelete(`/api/v1/destinations/${destinationId}?${ws(workspaceCode)}`, init);
}

export function postEltDestinationWrite(
  destinationId: number,
  body: {
    workspace_code: string;
    stream_name: string;
    records: Record<string, unknown>[];
    schema?: Record<string, unknown>;
    mode: "append" | "full_refresh" | "upsert" | "replace_table";
  },
  init?: ApiRequestInit,
) {
  return apiPostJson<
    { ok: boolean; message: string; rows_written: number; details?: Record<string, unknown> },
    typeof body
  >(`/api/v1/destinations/${destinationId}/write`, body, init);
}

export function createEltConnection(body: EltConnectionCreatePayload, init?: ApiRequestInit) {
  return apiPostJson<{ item: EltConnectionDetailDto }, EltConnectionCreatePayload>("/api/v1/connections", body, init);
}

export function fetchEltConnections(workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ items: EltConnectionDetailDto[] }>(`/api/v1/connections?${ws(workspaceCode)}`, init);
}

export function fetchEltConnection(connectionId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiGetJson<{ item: EltConnectionDetailDto }>(`/api/v1/connections/${connectionId}?${ws(workspaceCode)}`, init);
}

export function patchEltConnection(
  connectionId: number,
  body: EltConnectionPatchPayload,
  init?: ApiRequestInit,
) {
  return apiPatchJson<{ item: EltConnectionDetailDto }, EltConnectionPatchPayload>(
    `/api/v1/connections/${connectionId}`,
    body,
    init,
  );
}

export function triggerEltConnection(
  connectionId: number,
  workspaceCode = "main",
  options?: { streamName?: string },
  init?: ApiRequestInit,
) {
  const body = options?.streamName ? { stream_name: options.streamName } : {};
  return apiPostJson<EltConnectionTriggerResponseDto, { stream_name?: string }>(
    `/api/v1/connections/${connectionId}/trigger?${ws(workspaceCode)}`,
    body,
    init,
  );
}

export async function patchEltConnectionStreamEnabled(
  connectionId: number,
  streamName: string,
  enabled: boolean,
  workspaceCode = "main",
  init?: ApiRequestInit,
) {
  const { item } = await fetchEltConnection(connectionId, workspaceCode, init);
  const streams = (item.streams ?? []).map((s) => ({
    stream_name: s.stream_name,
    sync_mode: (s.sync_mode || "full_refresh") as "full_refresh" | "incremental",
    destination_sync_mode: s.destination_sync_mode ?? "refresh_overwrite",
    cursor_field: s.cursor_field,
    primary_key: s.primary_key,
    is_enabled: s.stream_name === streamName ? enabled : s.is_enabled,
  }));
  return patchEltConnection(connectionId, { streams, workspace_code: workspaceCode }, init);
}

export function triggerEltConnectionStream(
  connectionId: number,
  streamName: string,
  workspaceCode = "main",
  init?: ApiRequestInit,
) {
  return triggerEltConnection(connectionId, workspaceCode, { streamName }, init);
}

export function deleteEltConnection(connectionId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiDelete(`/api/v1/connections/${connectionId}?${ws(workspaceCode)}`, init);
}
