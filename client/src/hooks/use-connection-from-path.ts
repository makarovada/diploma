import { useLocation } from "wouter";
import { connections } from "@/lib/mock-data";
import { getConnectionIdFromPath } from "@/lib/route-utils";

export function useConnectionFromPath() {
  const [location] = useLocation();
  const id = getConnectionIdFromPath(location);
  const connection = id ? (connections.find((c) => c.id === id) ?? null) : null;
  return { id: id ?? "", connection };
}
