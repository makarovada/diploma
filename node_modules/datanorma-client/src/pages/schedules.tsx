import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { fetchV1Schedules } from "@/lib/api-datanorma";
import type { ScheduleRow } from "@/lib/types";

function mapScheduleRow(row: Record<string, unknown>, idx: number): ScheduleRow {
  return {
    id: String(row.id ?? `schedule-${idx}`),
    connectionName: String(row.connection_name ?? row.connection ?? "—"),
    schedule: String(row.cron_expr ?? row.schedule ?? "—"),
    timezone: String(row.timezone ?? "UTC"),
    nextRun: String(row.next_run_at ?? "—"),
    lastRun: String(row.last_run_at ?? "—"),
    status: String(row.status ?? "draft") as ScheduleRow["status"],
    owner: String(row.owner ?? "—"),
  };
}

export function SchedulesPage() {
  const query = useQuery({
    queryKey: ["schedules", "v1"],
    queryFn: async () => {
      const { items } = await fetchV1Schedules();
      return items.map(mapScheduleRow);
    },
  });
  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка расписаний…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить расписания.</div>;
  const schedules = query.data;

  return (
    <div className="p-4">
      <PageHeader title="Расписания" description="Запланированные синхронизации по подключениям" breadcrumbs="Синхронизация / Расписания" />
      <div className="overflow-auto rounded-lg border" data-testid="table-schedules">
        <table className="w-full min-w-[920px] text-left text-sm" aria-label="Расписания">
          <thead className="bg-muted">
            <tr>
              <th>Подключение</th>
              <th>Расписание</th>
              <th>Часовой пояс</th>
              <th>Следующий запуск</th>
              <th>Последний запуск</th>
              <th>Статус</th>
              <th>Владелец</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr key={s.id} className="border-t" data-testid={`row-schedule-${s.id}`}>
                <td>{s.connectionName}</td>
                <td>{s.schedule}</td>
                <td>{s.timezone}</td>
                <td>{s.nextRun}</td>
                <td>{s.lastRun}</td>
                <td><StatusBadge status={s.status} /></td>
                <td>{s.owner}</td>
                <td>
                  <Button variant="outline" className="px-2 py-1 text-xs" data-testid={`button-schedule-pause-${s.id}`}>
                    Пауза
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
