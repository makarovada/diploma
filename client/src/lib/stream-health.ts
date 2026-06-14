import type { EltConnectionDetailDto, NormIssueRowDto, V1SyncRunItem } from "@/lib/api-types";
import {
  computeStreamHealth,
  streamHealthLabel,
  streamHealthToBadgeStatus,
  type StreamHealthStatus,
} from "@/lib/issue-explanations";
import { filterIssuesByConnectionId, formatTs, syncRunMatchesEltConnection } from "@/lib/api-datanorma";
import type { Status } from "@/lib/types";

export type StreamOverviewRow = {
  stream: string;
  enabled: boolean;
  syncMode?: string;
  cursor: string;
  lastSync: string;
  records: number;
  openIssues: number;
  health: StreamHealthStatus;
  healthLabel: string;
  status: Status;
};


function parseEltSummaryStreams(run: V1SyncRunItem | undefined): Map<string, number> {
  const map = new Map<string, number>();
  if (!run) return map;
  const streams = run.meta?.elt_summary?.streams;
  if (!Array.isArray(streams)) return map;
  for (const s of streams) {
    const name = s.stream_name?.trim();
    if (name) map.set(name, Number(s.rows_written ?? 0));
  }
  return map;
}

export function countOpenIssuesByStream(
  normRows: NormIssueRowDto[],
  connectionId: number,
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const row of filterIssuesByConnectionId(normRows, connectionId)) {
    if ((row.status ?? "open") !== "open") continue;
    const sn = row.stream_name?.trim();
    if (!sn) continue;
    counts.set(sn, (counts.get(sn) ?? 0) + 1);
  }
  return counts;
}

export function findRunningRunForConnection(
  syncItems: V1SyncRunItem[],
  connectionId: string,
): V1SyncRunItem | undefined {
  return syncItems.find(
    (s) => syncRunMatchesEltConnection(s, connectionId) && s.status.toLowerCase() === "running",
  );
}

export function buildStreamOverviewRows(args: {
  detail: EltConnectionDetailDto;
  connectionId: number;
  syncItems: V1SyncRunItem[];
  normRows: NormIssueRowDto[];
  syncModeLabel?: (streamName: string) => string;
}): StreamOverviewRow[] {
  const { detail, connectionId, syncItems, normRows, syncModeLabel } = args;
  const connIdStr = String(connectionId);
  const connRuns = syncItems
    .filter((s) => syncRunMatchesEltConnection(s, connIdStr))
    .sort((a, b) => {
      const ta = a.started_at ? new Date(a.started_at).getTime() : 0;
      const tb = b.started_at ? new Date(b.started_at).getTime() : 0;
      return tb - ta;
    });
  const lastRun = connRuns[0];
  const lastSuccessRun = connRuns.find((r) => r.status.toLowerCase() === "success");
  const summaryFromRun = parseEltSummaryStreams(lastSuccessRun ?? lastRun);
  const issueCounts = countOpenIssuesByStream(normRows, connectionId);
  const runningRun = findRunningRunForConnection(syncItems, connIdStr);
  const runningStream =
    runningRun?.stream_name && runningRun.stream_name !== "*" ? runningRun.stream_name : null;

  return (detail.streams ?? []).map((s) => {
    const sn = s.stream_name;
    const openIssues = issueCounts.get(sn) ?? 0;
    const records = summaryFromRun.get(sn) ?? 0;
    const health = computeStreamHealth({
      streamName: sn,
      enabled: Boolean(s.is_enabled),
      openIssueCount: openIssues,
      isRunning: runningStream === sn || (Boolean(runningRun) && runningRun?.stream_name === "*"),
      lastStreamFailed: lastRun?.status.toLowerCase() === "failed" && lastRun.stream_name === sn,
    });
    return {
      stream: sn,
      enabled: Boolean(s.is_enabled),
      syncMode: syncModeLabel?.(sn),
      cursor: s.cursor_value != null ? String(s.cursor_value) : "—",
      lastSync: lastSuccessRun?.finished_at ? formatTs(lastSuccessRun.finished_at) : "—",
      records,
      openIssues,
      health,
      healthLabel: streamHealthLabel(health),
      status: streamHealthToBadgeStatus(health),
    };
  });
}
