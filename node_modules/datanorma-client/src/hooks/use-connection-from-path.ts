import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { fetchEltConnection } from "@/lib/api-elt";
import type { EltConnectionDetailDto } from "@/lib/api-types";
import { fetchWorkspaces, mapEltDetailToConnection } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import { getConnectionIdFromPath } from "@/lib/route-utils";

export function useConnectionFromPath() {
  const [location] = useLocation();
  const id = getConnectionIdFromPath(location) ?? "";

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: queryKeys.connections.eltDetail(id, workspaceCode),
    queryFn: async () => {
      const { item } = await fetchEltConnection(Number(id), workspaceCode);
      return item;
    },
    enabled: Boolean(id) && /^\d+$/.test(id),
  });

  const detail: EltConnectionDetailDto | null = id && query.data ? query.data : null;
  const connection = detail ? mapEltDetailToConnection(detail) : null;
  const isLoading = Boolean(id) && (wsQuery.isPending || query.isPending);
  const isError = Boolean(id) && (!/^\d+$/.test(id) || query.isError);

  return { id, connection, detail, workspaceCode, isLoading, isError };
}
