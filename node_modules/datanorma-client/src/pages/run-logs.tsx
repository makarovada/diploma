import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { LogViewer } from "@/components/log-viewer";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchV1Sync, mapV1SyncToRun, syncRunLogLines } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

export function RunLogsPage() {
  const [, params] = useRoute("/runs/:runId/logs");
  const rawId = params?.runId ?? "";
  const runId = Number.parseInt(rawId, 10);

  const query = useQuery({
    queryKey: queryKeys.runs.logs(rawId),
    queryFn: async () => {
      const { item } = await fetchV1Sync(runId);
      return item;
    },
    enabled: Number.isFinite(runId) && runId > 0,
  });

  if (!rawId || !Number.isFinite(runId) || runId <= 0) {
    return (
      <div className="p-4" data-testid="state-not-found-run-logs">
        Запуск не найден. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError || !query.data) {
    return (
      <div className="p-4" data-testid="state-not-found-run-logs">
        Запуск не найден. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  const item = query.data;
  const run = mapV1SyncToRun(item);

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={`Логи запуска ${run.id}`} description={run.connectionName} breadcrumbs="Синхронизация / Запуски / Логи" />
      <LinkAsButton href={`/runs/${run.id}`} variant="outline" data-testid="button-back-run-detail">
        К карточке запуска
      </LinkAsButton>
      <LogViewer logs={syncRunLogLines(item)} />
    </div>
  );
}
