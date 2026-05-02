import { useRoute } from "wouter";
import {
  connectionStreamRows,
  connectorHealth,
  connections,
  issues,
  runs,
} from "@/lib/mock-data";
import { ConnectionPipeline } from "@/components/connection-pipeline";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ConnectionDetailPage() {
  const [, params] = useRoute("/connections/:id");
  const connection = connections.find((c) => c.id === params?.id);

  if (!connection) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        <p>Подключение не найдено.</p>
        <LinkAsButton href="/connections" variant="outline" className="mt-2" data-testid="button-back-connections">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  const id = connection.id;
  const lastRun = runs.find((r) => r.connectionId === id);
  const openIssues = issues.filter((i) => i.connection === connection.name && i.status === "open");

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={connection.name}
        description={`${connection.source} → ${connection.destination}`}
        breadcrumbs="Интеграции / Подключения / Обзор"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" data-testid="button-run-sync">
              Запустить
            </Button>
            <LinkAsButton href={`/connections/${id}/edit`} variant="outline" data-testid="button-edit-connection">
              Редактировать
            </LinkAsButton>
            <Button type="button" variant="outline" data-testid="button-pause-connection">
              Пауза
            </Button>
          </div>
        }
      />
      <ConnectionSubNav connectionId={id} />
      <ConnectionPipeline sourceLabel={connection.source} destLabel={connection.destination} />
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4" data-testid="connection-overview-kpis">
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Статус</p>
          <StatusBadge status={connection.status} />
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Расписание</p>
          <p className="text-sm font-medium">{connection.schedule}</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Маппинг (покрытие)</p>
          <p className="text-sm font-medium">{connection.mappingCoverage}%</p>
        </Card>
        <Card className="p-3">
          <p className="text-xs text-muted-foreground">Нормализация</p>
          <p className="text-sm font-medium">{connection.normalizationEnabled ? "Включена" : "Выключена"}</p>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4" data-testid="connection-health-card">
          <h2 className="mb-2 text-lg font-semibold">Состояние</h2>
          <p className="mb-2 text-sm text-muted-foreground">Последний запуск: {connection.lastRunAt}</p>
          {lastRun ? (
            <p className="text-sm">
              Run {lastRun.id} · <StatusBadge status={lastRun.status} /> · {lastRun.records} записей
            </p>
          ) : null}
          <p className="mt-2 text-sm">Открытых проблем: {openIssues.length}</p>
        </Card>
        <Card className="p-4" data-testid="connector-health-mini">
          <h2 className="mb-2 text-lg font-semibold">Health коннекторов</h2>
          <ul className="space-y-1 text-sm">
            {connectorHealth.slice(0, 3).map((h) => (
              <li key={h.id} data-testid={`connector-health-${h.id}`}>
                {h.name}: {h.detail}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <Card className="overflow-auto p-0" data-testid="table-connection-streams-overview">
        <table className="w-full min-w-[720px] text-left text-sm" aria-label="Потоки подключения">
          <thead className="bg-muted">
            <tr>
              <th>Поток</th>
              <th>Вкл.</th>
              <th>Режим</th>
              <th>Cursor</th>
              <th>Последний sync</th>
              <th>Записей</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {connectionStreamRows.map((s) => (
              <tr key={s.stream} className="border-t">
                <td>{s.stream}</td>
                <td>{s.enabled ? "Да" : "Нет"}</td>
                <td>{s.syncMode}</td>
                <td className="font-mono text-xs">{s.cursor}</td>
                <td>{s.lastSync}</td>
                <td>{s.records}</td>
                <td>{s.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
