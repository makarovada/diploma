import { useQuery } from "@tanstack/react-query";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Card } from "@/components/ui/card";
import { fetchV1Connections, formatTs } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import type { Status } from "@/lib/types";

export function ConnectionStreamsPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  const streamsQuery = useQuery({
    queryKey: queryKeys.connectionStreams.bySource(connection?.source),
    queryFn: async () => {
      const { items } = await fetchV1Connections();
      return items
        .filter((i) => i.integration_code === connection!.source)
        .map((i) => ({
          stream: i.stream_name,
          enabled: true,
          syncMode: i.sync_mode,
          cursor: i.cursor_value != null ? String(i.cursor_value) : "—",
          primaryKey: "—",
          lastSync: formatTs(i.last_success_at),
          records: 0,
          status: (i.last_success_at ? "success" : "ready") as Status,
        }));
    },
    enabled: Boolean(connection?.source),
  });

  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  const streamRows = streamsQuery.data ?? [];

  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Потоки данных" description={connection.name} breadcrumbs="Интеграции / Подключения / Потоки" />
      <ConnectionSubNav connectionId={id} />
      <Card className="overflow-auto p-0" data-testid="table-connection-streams">
        <table className="w-full min-w-[800px] text-left text-sm" aria-label="Потоки">
          <thead className="bg-muted">
            <tr>
              <th>Поток</th>
              <th>Включён</th>
              <th>Режим sync</th>
              <th>Cursor</th>
              <th>Primary key</th>
              <th>Последний sync</th>
              <th>Записей</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {streamsQuery.isPending ? (
              <tr>
                <td colSpan={8} className="p-4 text-muted-foreground">
                  Загрузка потоков…
                </td>
              </tr>
            ) : (
              streamRows.map((s) => (
                <tr key={s.stream} className="border-t" data-testid={`row-stream-${s.stream}`}>
                  <td>{s.stream}</td>
                  <td>{s.enabled ? "Да" : "Нет"}</td>
                  <td>{s.syncMode}</td>
                  <td className="font-mono text-xs">{s.cursor}</td>
                  <td className="font-mono text-xs">{s.primaryKey}</td>
                  <td>{s.lastSync}</td>
                  <td>{s.records}</td>
                  <td>
                    <StatusBadge status={s.status} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
