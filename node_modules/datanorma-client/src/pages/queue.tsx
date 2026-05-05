import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { fetchV1Queue, formatTs } from "@/lib/api-datanorma";
import type { QueueJob } from "@/lib/types";

function mapQueueJob(row: Record<string, unknown>): QueueJob {
  return {
    id: String(row.id ?? ""),
    connectionName: String(row.connection_name ?? row.connection ?? "—"),
    stage: String(row.stage ?? "queued"),
    priority: Number(row.priority ?? 0),
    queuedAt: formatTs((row.queued_at as string | null | undefined) ?? null),
    startedAt: formatTs((row.started_at as string | null | undefined) ?? null),
    worker: String(row.worker ?? "—"),
    status: (String(row.status ?? "queued") as QueueJob["status"]),
  };
}

export function QueuePage() {
  const query = useQuery({
    queryKey: ["queue", "v1"],
    queryFn: async () => {
      const { items } = await fetchV1Queue();
      return items.map(mapQueueJob);
    },
  });

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка очереди…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить очередь.</div>;

  const queueJobs = query.data;

  return (
    <div className="p-4">
      <PageHeader title="Очередь" description="Текущие задания в очереди и на исполнении (только просмотр)" breadcrumbs="Синхронизация / Очередь" />
      <div className="overflow-auto rounded-lg border" data-testid="table-queue">
        <table className="w-full min-w-[960px] text-left text-sm" aria-label="Очередь заданий">
          <thead className="bg-muted">
            <tr>
              <th>Job ID</th>
              <th>Подключение</th>
              <th>Этап</th>
              <th>Приоритет</th>
              <th>В очереди</th>
              <th>Старт</th>
              <th>Worker</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {queueJobs.map((j) => (
              <tr key={j.id} className="border-t" data-testid={`row-queue-${j.id}`}>
                <td className="font-mono text-xs">{j.id}</td>
                <td>{j.connectionName}</td>
                <td>{j.stage}</td>
                <td>{j.priority}</td>
                <td>{j.queuedAt}</td>
                <td>{j.startedAt}</td>
                <td>{j.worker}</td>
                <td><StatusBadge status={j.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
