import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchEltConnections } from "@/lib/api-elt";
import { fetchV1Schedules, fetchWorkspaces } from "@/lib/api-datanorma";
import { describeCronExpression } from "@/lib/schedule-config";
import type { ScheduleRow } from "@/lib/types";

function formatTimestamp(value: unknown): string {
  if (value == null || value === "") return "—";
  const s = String(value);
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString("ru-RU");
}

function mapScheduleRow(row: Record<string, unknown>, idx: number): ScheduleRow {
  const tz = String(row.timezone ?? "UTC");
  const cron = String(row.cron_expr ?? row.schedule_cron ?? row.schedule ?? "").trim();
  return {
    id: String(row.id ?? row.connection_id ?? `schedule-${idx}`),
    connectionName: String(row.connection_name ?? row.connection ?? "—"),
    schedule: cron ? describeCronExpression(cron, tz) : "ручной",
    timezone: tz,
    nextRun: formatTimestamp(row.next_run_at),
    lastRun: formatTimestamp(row.last_run_at),
    status: String(row.status ?? "draft") as ScheduleRow["status"],
    owner: String(row.owner ?? "—"),
  };
}

export function SchedulesPage() {
  const query = useQuery({
    queryKey: ["schedules", "v1"],
    queryFn: async () => {
      const { items } = await fetchV1Schedules();
      const fromSchedulesApi = items.map(mapScheduleRow);
      if (fromSchedulesApi.length > 0) return fromSchedulesApi;
      const ws = await fetchWorkspaces();
      const workspaceCode = ws.items[0]?.workspace_code ?? "main";
      const { items: connections } = await fetchEltConnections(workspaceCode);
      return connections
        .filter((c) => c.schedule_cron?.trim())
        .map((c, idx) =>
          mapScheduleRow(
            {
              id: c.id,
              connection_id: c.id,
              connection_name: c.name,
              schedule_cron: c.schedule_cron,
              timezone: c.timezone,
              status: c.is_active ? "ready" : "paused",
              owner: c.created_by,
            },
            idx,
          ),
        );
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
            {schedules.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-6 text-center text-muted-foreground" data-testid="schedules-empty">
                  Нет подключений с расписанием. Задайте расписание в мастере создания подключения или в{" "}
                  <LinkAsButton href="/connections" className="inline h-auto bg-transparent p-0 text-xs text-primary underline hover:opacity-90">
                    настройках подключения
                  </LinkAsButton>
                  .
                </td>
              </tr>
            ) : (
              schedules.map((s) => (
                <tr key={s.id} className="border-t" data-testid={`row-schedule-${s.id}`}>
                  <td>
                    <LinkAsButton
                      href={`/connections/${s.id}/settings`}
                      className="h-auto bg-transparent p-0 font-normal text-primary underline hover:opacity-90"
                    >
                      {s.connectionName}
                    </LinkAsButton>
                  </td>
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
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
