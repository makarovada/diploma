import { apiDelete, apiGetJson, apiPostJson, apiPutJson, type ApiRequestInit } from "@/lib/api-client";

export type WorkspaceDto = {
  id: number;
  code: string;
  name: string;
  is_admin: boolean;
  permissions: string[];
};

export type PermissionCatalogItem = {
  code: string;
  label_ru: string;
  category: string;
};

export type WorkspaceMemberDto = {
  user_id: number;
  username: string;
  email: string | null;
  is_admin: boolean;
  joined_at: string | null;
  permissions: string[];
};

export type ResourceGrantDto = {
  id: number;
  grantee_user_id: number;
  grantee_username: string;
  level: "view" | "edit" | "manage";
  granted_by_username: string | null;
  created_at: string | null;
};

export function fetchWorkspacesV2(init?: ApiRequestInit) {
  return apiGetJson<{ items: WorkspaceDto[] }>("/api/v1/workspaces", init);
}

export function postWorkspace(body: { code: string; name: string }, init?: ApiRequestInit) {
  return apiPostJson<{ item: WorkspaceDto }>("/api/v1/workspaces", body, init);
}

export function fetchPermissionCatalog(init?: ApiRequestInit) {
  return apiGetJson<{ items: PermissionCatalogItem[] }>("/api/v1/permissions/catalog", init);
}

export function fetchWorkspaceMembers(workspaceId: number, init?: ApiRequestInit) {
  return apiGetJson<{ items: WorkspaceMemberDto[] }>(`/api/v1/workspaces/${workspaceId}/members`, init);
}

export function postWorkspaceMember(workspaceId: number, username: string, init?: ApiRequestInit) {
  return apiPostJson<{ user_id: number; username: string }>(
    `/api/v1/workspaces/${workspaceId}/members`,
    { username },
    init,
  );
}

export function deleteWorkspaceMember(workspaceId: number, userId: number, init?: ApiRequestInit) {
  return apiDelete(`/api/v1/workspaces/${workspaceId}/members/${userId}`, init);
}

export function putMemberPermissions(
  workspaceId: number,
  userId: number,
  permissions: string[],
  init?: ApiRequestInit,
) {
  return apiPutJson<{ user_id: number; permissions: string[] }>(
    `/api/v1/workspaces/${workspaceId}/members/${userId}/permissions`,
    { permissions },
    init,
  );
}

export function fetchResourceGrants(
  resourceType: "sources" | "destinations" | "connections",
  resourceId: number,
  init?: ApiRequestInit,
) {
  return apiGetJson<{ items: ResourceGrantDto[] }>(
    `/api/v1/${resourceType}/${resourceId}/grants`,
    init,
  );
}

export function postResourceGrant(
  resourceType: "sources" | "destinations" | "connections",
  resourceId: number,
  body: { username: string; level: "view" | "edit" | "manage" },
  init?: ApiRequestInit,
) {
  return apiPostJson<{ item: ResourceGrantDto }>(
    `/api/v1/${resourceType}/${resourceId}/grants`,
    body,
    init,
  );
}

export function deleteResourceGrant(
  resourceType: "sources" | "destinations" | "connections",
  resourceId: number,
  granteeUserId: number,
  init?: ApiRequestInit,
) {
  return apiDelete(`/api/v1/${resourceType}/${resourceId}/grants/${granteeUserId}`, init);
}
