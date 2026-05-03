import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import {
  fetchNormalizationIssues,
  fetchV1Connections,
  fetchV1Syncs,
  formatTs,
  mapNormRowToIssue,
  mapV1SyncToRun,
  mapV1ToConnection,
} from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import type { Status } from "@/lib/types";
import { ConnectionPipeline } from "@/components/connection-pipeline";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ConnectionDetailPage() {
  const [, params] = useRoute("/connections/:id");
  const id = params?.id ?? "";

  const query = useQuery({
    queryKey: queryKeys.connections.detail(id),
    queryFn: async () => {
      const [conns, syncs, norm] = await Promise.all([
        fetchV1Connections(),
        fetchV1Syncs(200),
        fetchNormalizationIssues(200),
      ]);
      const connections = conns.items.map(mapV1ToConnection);
      const connection = connections.find((c) => c.id === id) ?? null;
      const rawItems = conns.items;
      const streamRows = connection
        ? rawItems
            .filter((i) => i.integration_code === connection.source)
            .map((i) => ({
              stream: i.stream_name,
              enabled: true,
              syncMode: i.sync_mode,
              cursor: i.cursor_value != null ? String(i.cursor_value) : "—",
              lastSync: formatTs(i.last_success_at),
              records: 0,
              status: (i.last_success_at ? "success" : "ready") as Status,
            }))
        : [];
      const rawRuns = syncs.items
        .filter((s) => s.connection_id != null && String(s.connection_id) === id)
        .sort((a, b) => {
          const ta = a.started_at ? new Date(a.started_at).getTime() : 0;
          const tb = b.started_at ? new Date(b.started_at).getTime() : 0;
          return tb - ta;
        });
      const lastRun = rawRuns[0] ? mapV1SyncToRun(rawRuns[0]) : null;
      const openIssues = connection
        ? norm.rows
            .filter((r) => (r.source_system ?? "") === connection.source)
            .map(mapNormRowToIssue)
        : [];
      const healthNames = [...new Set(rawItems.map((i) => i.integration_code))].slice(0, 5);
      return { connection, streamRows, lastRun, openIssues, healthNames };
    },
    enabled: Boolean(id),
  });

  if (!id) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        <p>Подключение не найдено.</p>
        <LinkAsButton href="/connections" variant="outline" className="mt-2" data-testid="button-back-connections">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending) {
    return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  }

  if (query.isError || !query.data?.connection) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        <p>Подключение не найдено.</p>
        <LinkAsButton href="/connections" variant="outline" className="mt-2" data-testid="button-back-connections">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  const { connection, streamRows, lastRun, openIssues, healthNames } = query.data;
  const cid = connection.id;

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
            <LinkAsButton href={`/connections/${cid}/edit`} variant="outline" data-testid="button-edit-connection">
              Редактировать
            </LinkAsButton>
            <Button type="button" variant="outline" data-testid="button-pause-connection">
              Пауза
            </Button>
          </div>
        }
      />
      <ConnectionSubNav connectionId={cid} />
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
          <p className="mt-2 text-sm">Открытых проблем (по источнику): {openIssues.length}</p>
        </Card>
        <Card className="p-4" data-testid="connector-health-mini">
          <h2 className="mb-2 text-lg font-semibold">Интеграции (sync_state)</h2>
          <ul className="space-y-1 text-sm">
            {healthNames.map((name) => (
              <li key={name} data-testid={`connector-health-${name}`}>
                {name}: каталог активен
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
            {streamRows.map((s) => (
              <tr key={s.stream} className="border-t">
                <td>{s.stream}</td>
                <td>{s.enabled ? "Да" : "Нет"}</td>
                <td>{s.syncMode}</td>
                <td className="font-mono text-xs">{s.cursor}</td>
                <td>{s.lastSync}</td>
                <td>{s.records}</td>
                <td>
                  <StatusBadge status={s.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
