import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  cancelV1Sync,
  fetchNormalizationIssues,
  fetchV1Syncs,
  fetchWorkspaces,
} from "@/lib/api-datanorma";
import {
  patchEltConnectionStreamEnabled,
  triggerEltConnectionStream,
} from "@/lib/api-elt";
import { DISABLE_STREAM_CONFIRM } from "@/lib/issue-explanations";
import { describeReplicationPreset, replicationPresetFromFields } from "@/lib/destination-sync-mode";
import { queryKeys } from "@/lib/query-keys";
import { buildStreamOverviewRows, findRunningRunForConnection } from "@/lib/stream-health";
import { ApiError } from "@/lib/api-client";

export function ConnectionStreamsPage() {
  const { connection, detail, id, isLoading, isError } = useConnectionFromPath();
  const queryClient = useQueryClient();

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const streamsQuery = useQuery({
    queryKey: [...queryKeys.connections.eltDetail(id, workspaceCode), "streams-health"],
    queryFn: async () => {
      const [{ items: syncItems }, { rows: normRows }] = await Promise.all([
        fetchV1Syncs(200),
        fetchNormalizationIssues(200),
      ]);
      const syncModeLabel = (streamName: string) => {
        const s = detail?.streams?.find((x) => x.stream_name === streamName);
        if (!s) return "—";
        return describeReplicationPreset(replicationPresetFromFields(s.sync_mode, s.destination_sync_mode ?? undefined));
      };
      const rows = buildStreamOverviewRows({
        detail: detail!,
        connectionId: Number(id),
        syncItems,
        normRows,
        syncModeLabel,
      });
      const runningRun = findRunningRunForConnection(syncItems, id);
      return { rows, runningRun };
    },
    enabled: Boolean(detail) && /^\d+$/.test(id),
    refetchInterval: (q) => (q.state.data?.runningRun ? 3000 : false),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(id, workspaceCode) });
    await queryClient.invalidateQueries({ queryKey: queryKeys.runs.list(200) });
    await queryClient.invalidateQueries({ queryKey: queryKeys.issues.list(200) });
  };

  const toggleMut = useMutation({
    mutationFn: ({ streamName, enabled }: { streamName: string; enabled: boolean }) =>
      patchEltConnectionStreamEnabled(Number(id), streamName, enabled, workspaceCode),
    onSuccess: invalidate,
  });

  const syncMut = useMutation({
    mutationFn: (streamName: string) => triggerEltConnectionStream(Number(id), streamName, workspaceCode),
    onSuccess: invalidate,
  });

  const enableAndSyncMut = useMutation({
    mutationFn: async (streamName: string) => {
      await patchEltConnectionStreamEnabled(Number(id), streamName, true, workspaceCode);
      return triggerEltConnectionStream(Number(id), streamName, workspaceCode);
    },
    onSuccess: invalidate,
  });

  const cancelMut = useMutation({
    mutationFn: (runId: number) => cancelV1Sync(runId),
    onSuccess: invalidate,
  });

  if (isLoading || wsQuery.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection || !detail) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  const streamRows = streamsQuery.data?.rows ?? [];
  const runningRun = streamsQuery.data?.runningRun;
  const busy =
    toggleMut.isPending || syncMut.isPending || enableAndSyncMut.isPending || cancelMut.isPending;

  let actionErr: string | null = null;
  const err = toggleMut.error ?? syncMut.error ?? enableAndSyncMut.error ?? cancelMut.error;
  if (err instanceof ApiError) actionErr = err.message;

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Потоки данных"
        description={connection.name}
        breadcrumbs="Интеграции / Подключения / Потоки"
        actions={
          <LinkAsButton href={`/connections/${id}/streams/edit`} data-testid="link-edit-connection-streams">
            Редактировать потоки
          </LinkAsButton>
        }
      />
      <ConnectionSubNav connectionId={id} />
      {actionErr ? <p className="text-sm text-destructive">{actionErr}</p> : null}
      <Card className="overflow-auto p-0" data-testid="table-connection-streams">
        <table className="w-full min-w-[1100px] text-left text-sm" aria-label="Потоки">
          <thead className="bg-muted">
            <tr>
              <th>Поток</th>
              <th>Включён</th>
              <th>Режим передачи</th>
              <th>Курсор</th>
              <th>Последний sync</th>
              <th>Записей</th>
              <th>Проблемы</th>
              <th>Статус</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {streamRows.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-4 text-muted-foreground">
                  Нет потоков
                </td>
              </tr>
            ) : (
              streamRows.map((s) => (
                <tr key={s.stream} className="border-t" data-testid={`row-stream-${s.stream}`}>
                  <td>{s.stream}</td>
                  <td>{s.enabled ? "Да" : "Нет"}</td>
                  <td>{s.syncMode ?? "—"}</td>
                  <td className="font-mono text-xs">{s.cursor}</td>
                  <td>{s.lastSync}</td>
                  <td>{s.records}</td>
                  <td>{s.openIssues > 0 ? s.openIssues : "—"}</td>
                  <td>
                    <StatusBadge status={s.status} />
                    <span className="ml-1 text-xs text-muted-foreground">{s.healthLabel}</span>
                  </td>
                  <td className="space-x-1 whitespace-nowrap p-2">
                    {s.enabled ? (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          disabled={busy || Boolean(runningRun)}
                          data-testid={`button-sync-stream-${s.stream}`}
                          onClick={() => syncMut.mutate(s.stream)}
                        >
                          Синхронизировать
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          disabled={busy}
                          data-testid={`button-disable-stream-${s.stream}`}
                          onClick={() => {
                            if (window.confirm(`${DISABLE_STREAM_CONFIRM}\n\nПоток: ${s.stream}`)) {
                              toggleMut.mutate({ streamName: s.stream, enabled: false });
                            }
                          }}
                        >
                          Отключить
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          disabled={busy}
                          data-testid={`button-enable-stream-${s.stream}`}
                          onClick={() => toggleMut.mutate({ streamName: s.stream, enabled: true })}
                        >
                          Включить
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="px-2 py-1 text-xs"
                          disabled={busy || Boolean(runningRun)}
                          data-testid={`button-enable-sync-stream-${s.stream}`}
                          onClick={() => enableAndSyncMut.mutate(s.stream)}
                        >
                          Включить и синхронизировать
                        </Button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
      {runningRun ? (
        <Card className="flex flex-wrap items-center gap-2 p-3" data-testid="connection-running-banner">
          <span className="text-sm">Выполняется синхронизация (запуск #{runningRun.id})…</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={cancelMut.isPending}
            data-testid="button-cancel-running-sync"
            onClick={() => cancelMut.mutate(runningRun.id)}
          >
            Отменить запуск
          </Button>
        </Card>
      ) : null}
    </div>
  );
}
