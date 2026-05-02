import { useRoute } from "wouter";
import { runs, runLogsExtended } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { StageTimeline } from "@/components/stage-timeline";
import { LogViewer } from "@/components/log-viewer";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function RunDetailPage() {
  const [, params] = useRoute("/runs/:id");
  const run = runs.find((x) => x.id === params?.id) ?? runs[0];

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={`Запуск ${run.id}`}
        description={run.connectionName}
        breadcrumbs="Синхронизация / Запуски / Детали"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button type="button" data-testid="button-rerun">
              Повторить
            </Button>
            <LinkAsButton href={`/connections/${run.connectionId}`} variant="outline" data-testid="button-open-connection-from-run">
              Открыть подключение
            </LinkAsButton>
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
      <StageTimeline status={run.status} />
      <div className="grid gap-3 md:grid-cols-3" data-testid="run-summary-cards">
        <Card className="p-3">Извлечено: {run.records}</Card>
        <Card className="p-3">Нормализовано: {Math.max(0, run.records - run.issues)}</Card>
        <Card className="p-3">Проблемы: {run.issues}</Card>
      </div>
      {run.status === "failed" ? (
        <Card className="p-4" data-testid="run-error-detail">
          <p className="font-medium">Синхронизация завершилась с ошибкой</p>
          <p className="mt-1 text-sm text-muted-foreground">Не удалось загрузить данные в PostgreSQL. Проверьте маппинг и структуру целевой таблицы.</p>
        </Card>
      ) : null}
      {run.status === "partial" ? (
        <Card className="p-4" data-testid="run-partial-detail">
          <p className="text-sm">Загрузка выполнена частично: {run.records - run.issues} записей загружено, {run.issues} требуют проверки.</p>
          <LinkAsButton href="/issues" variant="outline" className="mt-2" data-testid="button-run-to-issues">
            Открыть проблемные записи
          </LinkAsButton>
        </Card>
      ) : null}
      <LogViewer logs={runLogsExtended} />
    </div>
  );
}
