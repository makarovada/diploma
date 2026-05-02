import { queueJobs } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";

export function QueuePage() {
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
