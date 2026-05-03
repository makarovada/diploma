/** Единые ключи TanStack Query (объектная форма). */

export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  dashboard: {
    root: () => ["dashboard", "live"] as const,
  },
  connections: {
    list: () => ["connections", "v1"] as const,
    forPath: (id: string) => ["connections", "v1", "for-path", id] as const,
    detail: (id: string) => ["connections", "detail", id] as const,
  },
  runs: {
    list: (limit: number) => ["runs", "v1", limit] as const,
    detail: (id: string) => ["runs", "v1", "detail", id] as const,
    logs: (id: string) => ["runs", "v1", "logs", id] as const,
  },
  issues: {
    list: (limit: number) => ["issues", "normalization", limit] as const,
    detail: (issueId: string) => ["issues", "detail", issueId] as const,
  },
  sources: {
    list: () => ["sources", "aggregated"] as const,
    detail: (sourceId: string) => ["sources", "detail", sourceId] as const,
  },
  destinations: {
    list: () => ["destinations", "catalog"] as const,
    detail: (destinationId: string) => ["destinations", "detail", destinationId] as const,
  },
  users: {
    list: () => ["admin", "users"] as const,
  },
  workspaces: {
    list: () => ["workspaces", "v1"] as const,
  },
  connectionIssues: {
    bySource: (source: string | undefined) => ["normalization-issues", "by-source", source ?? ""] as const,
  },
  connectionRuns: {
    byConnection: (id: string) => ["v1-syncs", "by-connection", id] as const,
  },
  connectionStreams: {
    bySource: (source: string | undefined) => ["v1-connections", "streams", source ?? ""] as const,
  },
  connectionLogs: {
    byConnection: (id: string) => ["connection-logs", id] as const,
  },
} as const;
