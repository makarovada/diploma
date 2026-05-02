import { schedules } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

export function SchedulesPage() {
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
