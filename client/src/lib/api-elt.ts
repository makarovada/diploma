/**
 * REST API v1: доменные source / destination / connection (Фаза 4).
 */
import { apiGetJson, apiPatchJson, apiPostJson, type ApiRequestInit } from "@/lib/api-client";
import type {
  EltCheckResponseDto,
  EltConnectionCreatePayload,
  EltConnectionDetailDto,
  EltConnectionTriggerResponseDto,
  EltDestinationCreatePayload,
  EltDestinationItemDto,
  EltDiscoverResponseDto,
  EltSourceItemDto,
} from "@/lib/api-types";

function ws(workspaceCode: string): string {
  return `workspace_code=${encodeURIComponent(workspaceCode)}`;
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

export function triggerEltConnection(connectionId: number, workspaceCode = "main", init?: ApiRequestInit) {
  return apiPostJson<EltConnectionTriggerResponseDto, Record<string, never>>(
    `/api/v1/connections/${connectionId}/trigger?${ws(workspaceCode)}`,
    {},
    init,
  );
}
