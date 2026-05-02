import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getRunsForConnection } from "@/lib/mock-data";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { Card } from "@/components/ui/card";

export function ConnectionRunsPage() {
  const { connection, id } = useConnectionFromPath();
  if (!connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }
  const connRuns = getRunsForConnection(id);
  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Запуски подключения" description={connection.name} breadcrumbs="Интеграции / Подключения / Запуски" />
      <ConnectionSubNav connectionId={id} />
      <Card className="overflow-auto p-0" data-testid="table-connection-runs-only">
        <table className="w-full min-w-[800px] text-sm" aria-label="История запусков">
          <thead className="bg-muted">
            <tr>
              <th>Run ID</th>
              <th>Статус</th>
              <th>Старт</th>
              <th>Длительность</th>
              <th>Записей</th>
              <th>Проблемы</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {connRuns.map((r) => (
              <tr key={r.id} className="border-t" data-testid={`row-conn-run-${r.id}`}>
                <td className="font-mono text-xs">{r.id}</td>
                <td>
                  <StatusBadge status={r.status} />
                </td>
                <td>{r.startedAt}</td>
                <td>{r.duration}</td>
                <td>{r.records}</td>
                <td>{r.issues}</td>
                <td>
                  <LinkAsButton href={`/runs/${r.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-run-${r.id}`}>
                    Открыть
                  </LinkAsButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
