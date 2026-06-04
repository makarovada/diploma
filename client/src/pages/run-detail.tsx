import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { StageTimeline } from "@/components/stage-timeline";
import { LogViewer } from "@/components/log-viewer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  fetchV1Sync,
  fetchV1SyncIssues,
  fetchV1SyncLogs,
  mapNormRowToIssue,
  mapV1SyncToRun,
  retryV1Sync,
  syncRunLogItemsToLines,
  syncRunLogLines,
} from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

export function RunDetailPage() {
  const [, params] = useRoute("/runs/:id");
  const rawId = params?.id ?? "";
  const runId = Number.parseInt(rawId, 10);

  const query = useQuery({
    queryKey: queryKeys.runs.detail(rawId),
    queryFn: async () => {
      const { item } = await fetchV1Sync(runId);
      return item;
    },
    enabled: Number.isFinite(runId) && runId > 0,
  });
  const queryClient = useQueryClient();
  const logsQuery = useQuery({
    queryKey: queryKeys.runs.logs(rawId),
    queryFn: async () => {
      const { items } = await fetchV1SyncLogs(runId);
      return items;
    },
    enabled: Number.isFinite(runId) && runId > 0,
  });
  const issuesQuery = useQuery({
    queryKey: queryKeys.issues.byRun(runId, 200),
    queryFn: async () => {
      const { items } = await fetchV1SyncIssues(runId, 200);
      return items.map(mapNormRowToIssue);
    },
    enabled: Number.isFinite(runId) && runId > 0,
  });
  const retryMutation = useMutation({
    mutationFn: () => retryV1Sync(runId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs", "v1"] });
      await queryClient.invalidateQueries({ queryKey: queryKeys.runs.detail(rawId) });
    },
  });

  if (!rawId || !Number.isFinite(runId) || runId <= 0) {
    return (
      <div className="p-4">
        Некорректный идентификатор запуска. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка запуска…</div>;
  if (query.isError) {
    return (
      <div className="p-4">
        Запуск не найден или нет доступа. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  const item = query.data;
  if (!item) {
    return (
      <div className="p-4">
        Нет данных. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  const run = mapV1SyncToRun(item);
  const logs = logsQuery.data ? syncRunLogItemsToLines(logsQuery.data) : syncRunLogLines(item);
  const runIssues = issuesQuery.data ?? [];
  const currentStage = logsQuery.data?.[logsQuery.data.length - 1]?.stage ?? run.stage;

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={`Запуск ${run.id}`}
        description={run.connectionName}
        breadcrumbs="Синхронизация / Запуски / Детали"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" data-testid="button-rerun" onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
              {retryMutation.isPending ? "Повтор..." : "Повторить"}
            </Button>
            {run.connectionId ? (
              <LinkAsButton href={`/connections/${run.connectionId}`} variant="outline" data-testid="button-open-connection-from-run">
                Открыть подключение
              </LinkAsButton>
            ) : null}
            <LinkAsButton href={`/runs/${run.id}/logs`} variant="outline" data-testid="button-open-run-logs">
              Логи на отдельной странице
            </LinkAsButton>
          </div>
        }
      />
      <Card className="p-4" data-testid="run-detail-header">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={run.status} testId={`badge-run-status-${run.id}`} />
          <span className="text-sm text-muted-foreground">
            {run.startedAt} · {run.duration} · {run.triggeredBy}
          </span>
        </div>
      </Card>
      <StageTimeline status={run.status} currentStage={currentStage} />
      <div className="grid gap-3 md:grid-cols-3" data-testid="run-summary-cards">
        <Card className="p-3">Извлечено: {run.records}</Card>
        <Card className="p-3">Нормализовано: {Math.max(0, run.records - run.issues)}</Card>
        <Card className="p-3">Проблемы: {run.issues}</Card>
      </div>
      {item.load_destination ? (
        <Card className="p-4" data-testid="run-load-destination">
          <p className="text-sm font-medium">Загрузка в приёмник</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {item.load_destination.name} ({item.load_destination.connector_code})
          </p>
        </Card>
      ) : null}
      {run.status === "failed" ? (
        <Card className="p-4" data-testid="run-error-detail">
          <p className="font-medium">Синхронизация завершилась с ошибкой</p>
          <p className="mt-1 text-sm text-muted-foreground">{item.error_message ?? "Подробности см. в логах Dagster / сообщении выше."}</p>
        </Card>
      ) : null}
      {run.status === "partial" ? (
        <Card className="p-4" data-testid="run-partial-detail">
          <p className="text-sm">Загрузка выполнена частично.</p>
          <LinkAsButton href="/issues" variant="outline" className="mt-2" data-testid="button-run-to-issues">
            Открыть проблемные записи
          </LinkAsButton>
        </Card>
      ) : null}
      <Card className="p-4" data-testid="run-issues-summary">
        <p className="font-medium">Проблемы нормализации</p>
        <p className="mt-1 text-sm text-muted-foreground">Найдено: {runIssues.length}</p>
        {issuesQuery.isError ? (
          <p className="mt-2 text-sm text-destructive">Не удалось загрузить список проблем.</p>
        ) : null}
        {runIssues.length > 0 ? (
          <div className="mt-3 overflow-auto rounded-md border" data-testid="table-run-issues">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="p-2 text-left">Поле</th>
                  <th className="p-2 text-left">Тип</th>
                  <th className="p-2 text-left">Сообщение</th>
                  <th className="p-2 text-left">Поток</th>
                </tr>
              </thead>
              <tbody>
                {runIssues.map((issue) => (
                  <tr key={issue.id} className="border-t" data-testid={`row-run-issue-${issue.id}`}>
                    <td className="p-2 font-mono text-xs">{issue.field}</td>
                    <td className="p-2">{issue.type}</td>
                    <td className="p-2 text-muted-foreground">{issue.original}</td>
                    <td className="p-2">{issue.stream}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">Нет проблем для отображения.</p>
        )}
        <LinkAsButton href="/issues" variant="outline" className="mt-3" data-testid="button-run-to-issues">
          Все проблемные записи
        </LinkAsButton>
      </Card>
      <LogViewer logs={logs} />
    </div>
  );
}
