import { useQuery } from "@tanstack/react-query";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LogViewer } from "@/components/log-viewer";
import { PageHeader } from "@/components/page-header";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchV1Syncs, syncRunLogLines, syncRunMatchesEltConnection } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

function buildLogsFromSyncs(items: Awaited<ReturnType<typeof fetchV1Syncs>>["items"], connectionId: string): string[] {
  const lines: string[] = [];
  const forConn = items
    .filter((s) => syncRunMatchesEltConnection(s, connectionId))
    .sort((a, b) => {
      const ta = a.started_at ? new Date(a.started_at).getTime() : 0;
      const tb = b.started_at ? new Date(b.started_at).getTime() : 0;
      return tb - ta;
    })
    .slice(0, 5);
  for (const s of forConn) {
    lines.push(`—— sync #${s.id} (${s.integration_code}/${s.stream_name}) ——`);
    lines.push(...syncRunLogLines(s));
  }
  if (lines.length === 0) {
    lines.push("Нет недавних запусков для этого подключения в API.");
  }
  return lines;
}

export function ConnectionLogsPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  const logsQuery = useQuery({
    queryKey: queryKeys.connectionLogs.byConnection(id),
    queryFn: async () => {
      const { items } = await fetchV1Syncs(100);
      return buildLogsFromSyncs(items, id);
    },
    enabled: Boolean(id),
  });

  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Логи" description={`Последние sync · ${connection.name}`} breadcrumbs="Интеграции / Подключения / Логи" />
      <ConnectionSubNav connectionId={id} />
      {logsQuery.isPending ? <p className="text-sm text-muted-foreground">Загрузка логов…</p> : <LogViewer logs={logsQuery.data ?? []} />}
    </div>
  );
}
