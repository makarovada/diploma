import { LinkAsButton } from "@/components/link-as-button";
import { runs } from "@/lib/mock-data";
import { StatusBadge } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";

export function RunsPage() {
  return (
    <div className="p-4">
      <PageHeader title="Запуски" description="История синхронизаций по всем подключениям" breadcrumbs="Синхронизация / Запуски" />
      <div className="overflow-auto rounded-lg border" data-testid="table-runs">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="bg-muted"><tr><th>Run ID</th><th>Подключение</th><th>Статус</th><th>Stage</th><th>Старт</th><th>Длительность</th><th>Issues</th><th /></tr></thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-t" data-testid={`row-run-${run.id}`}>
                <td>{run.id}</td><td>{run.connectionName}</td><td><StatusBadge status={run.status} testId={`badge-run-status-${run.id}`} /></td><td>{run.stage}</td><td>{run.startedAt}</td><td>{run.duration}</td><td>{run.issues}</td>
                <td><LinkAsButton href={`/runs/${run.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-run-${run.id}`}>Открыть</LinkAsButton></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
