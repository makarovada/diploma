import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { fetchV1Connections, mapV1ToConnection } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import { getConnectionIdFromPath } from "@/lib/route-utils";

export function useConnectionFromPath() {
  const [location] = useLocation();
  const id = getConnectionIdFromPath(location) ?? "";

  const query = useQuery({
    queryKey: queryKeys.connections.forPath(id),
    queryFn: async () => {
      const { items } = await fetchV1Connections();
      return items.map(mapV1ToConnection);
    },
    enabled: Boolean(id),
  });

  const connection = id && query.data ? (query.data.find((c) => c.id === id) ?? null) : null;
  const isLoading = Boolean(id) && query.isPending;

  return { id, connection, isLoading, isError: query.isError };
}
