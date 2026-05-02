import { useRoute } from "wouter";
import { LogViewer } from "@/components/log-viewer";
import { PageHeader } from "@/components/page-header";
import { runLogsExtended, runs } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";

export function RunLogsPage() {
  const [, params] = useRoute("/runs/:runId/logs");
  const run = runs.find((r) => r.id === params?.runId);

  if (!run) {
    return (
      <div className="p-4" data-testid="state-not-found-run-logs">
        Запуск не найден. <LinkAsButton href="/runs">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={`Логи запуска ${run.id}`} description={run.connectionName} breadcrumbs="Синхронизация / Запуски / Логи" />
      <LinkAsButton href={`/runs/${run.id}`} variant="outline" data-testid="button-back-run-detail">
        К карточке запуска
      </LinkAsButton>
      <LogViewer logs={runLogsExtended} />
    </div>
  );
}
