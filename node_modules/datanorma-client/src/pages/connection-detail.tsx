import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRoute, useLocation } from "wouter";
import {
  fetchNormalizationIssues,
  fetchV1Syncs,
  fetchWorkspaces,
  mapEltDetailToConnection,
  mapNormRowToIssue,
  mapV1SyncToRun,
  syncRunMatchesEltConnection,
} from "@/lib/api-datanorma";
import { deleteEltConnection, fetchEltConnection, triggerEltConnection } from "@/lib/api-elt";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";
import { queryKeys } from "@/lib/query-keys";
import type { Status } from "@/lib/types";
import { ConnectionPipeline } from "@/components/connection-pipeline";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ApiError } from "@/lib/api-client";
import { describeReplicationPreset, replicationPresetFromFields } from "@/lib/destination-sync-mode";
import { ResourceAccessPanel } from "@/components/resource-access-panel";
import { useAuth } from "@/app/auth-context";
import { usePermission } from "@/hooks/use-permission";

export function ConnectionDetailPage() {
  const [, params] = useRoute("/connections/:id");
  const [, setLocation] = useLocation();
  const id = params?.id ?? "";
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canManageAccess = Boolean(user?.is_workspace_admin) || usePermission("connection.delete");

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: [...queryKeys.connections.detail(id), "elt", workspaceCode],
    queryFn: async () => {
      const [{ item }, { items: syncItems }, { rows: normRows }] = await Promise.all([
        fetchEltConnection(Number(id), workspaceCode),
        fetchV1Syncs(200),
        fetchNormalizationIssues(200),
      ]);
      const connection = mapEltDetailToConnection(item);
      const streamRows =
        item.streams?.map((s) => ({
          stream: s.stream_name,
          enabled: s.is_enabled,
          syncMode: describeReplicationPreset(
            replicationPresetFromFields(s.sync_mode, s.destination_sync_mode ?? undefined),
          ),
          cursor: s.cursor_value != null ? String(s.cursor_value) : "—",
          lastSync: "—",
          records: 0,
          status: "ready" as Status,
        })) ?? [];
      const rawRuns = syncItems
        .filter((s) => syncRunMatchesEltConnection(s, id))
        .sort((a, b) => {
          const ta = a.started_at ? new Date(a.started_at).getTime() : 0;
          const tb = b.started_at ? new Date(b.started_at).getTime() : 0;
          return tb - ta;
        });
      const lastRun = rawRuns[0] ? mapV1SyncToRun(rawRuns[0]) : null;
      const srcCode = item.source_connector_code ?? "";
      const openIssues = normRows
        .filter((r) => srcCode && (r.source_system ?? "") === srcCode)
        .map(mapNormRowToIssue);
      const healthNames = item.source_connector_code ? [item.source_connector_code] : [];
      return { connection, item, streamRows, lastRun, openIssues, healthNames };
    },
    enabled: Boolean(id) && /^\d+$/.test(id),
  });

  const triggerMut = useMutation({
    mutationFn: () => triggerEltConnection(Number(id), workspaceCode),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.runs.list(200) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.connections.detail(id) });
    },
  });

  if (!id || !/^\d+$/.test(id)) {
    return (
      <div className="p-4" data-testid="state-not-found-connection">
        <p>Подключение не найдено.</p>
        <LinkAsButton href="/connections" variant="outline" className="mt-2" data-testid="button-back-connections">
          К списку
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending || wsQuery.isPending) {
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
  let triggerErr: string | null = null;
  if (triggerMut.isError) {
    triggerErr = triggerMut.error instanceof ApiError ? triggerMut.error.message : "Ошибка запуска";
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={connection.name}
        description={`${connection.source} → ${connection.destination}`}
        breadcrumbs="Интеграции / Подключения / Обзор"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              data-testid="button-run-sync"
              disabled={triggerMut.isPending}
              onClick={() => triggerMut.mutate()}
            >
              {triggerMut.isPending ? "Запуск…" : "Запустить"}
            </Button>
            <LinkAsButton href={`/connections/${cid}/edit`} variant="outline" data-testid="button-edit-connection">
              Изменить
            </LinkAsButton>
            <LinkAsButton href={`/connections/${cid}/settings`} variant="outline" data-testid="button-connection-settings">
              Расписание
            </LinkAsButton>
            <ConfirmDeleteButton
              entityLabel={connection.name}
              testId="button-delete-connection-detail"
              onDelete={() => deleteEltConnection(Number(cid), workspaceCode)}
              onSuccess={() => {
                void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
                setLocation("/connections");
              }}
            />
          </div>
        }
      />
      {triggerErr ? <p className="text-sm text-destructive">{triggerErr}</p> : null}
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
          <p className="mb-2 text-sm text-muted-foreground">Последний запуск: {lastRun ? lastRun.startedAt : connection.lastRunAt}</p>
          {lastRun ? (
            <p className="text-sm">
              Run {lastRun.id} · <StatusBadge status={lastRun.status} /> · {lastRun.records} записей
            </p>
          ) : null}
          <p className="mt-2 text-sm">Открытых проблем (по источнику): {openIssues.length}</p>
        </Card>
        <Card className="p-4" data-testid="connector-health-mini">
          <h2 className="mb-2 text-lg font-semibold">Интеграции</h2>
          <ul className="space-y-1 text-sm">
            {healthNames.map((name) => (
              <li key={name} data-testid={`connector-health-${name}`}>
                {name}: активен
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
      {/^\d+$/.test(id) ? (
        <ResourceAccessPanel resourceType="connections" resourceId={Number(id)} canManage={canManageAccess} />
      ) : null}
    </div>
  );
}
