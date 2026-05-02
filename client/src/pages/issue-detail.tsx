import { useRoute } from "wouter";
import { issues } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";

export function IssueDetailPage() {
  const [, params] = useRoute("/issues/:issueId");
  const issue = issues.find((i) => i.id === params?.issueId);

  if (!issue) {
    return (
      <div className="p-4" data-testid="state-not-found-issue">
        Запись не найдена. <LinkAsButton href="/issues">К списку</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={`Проблема ${issue.id}`} description={`${issue.type} · ${issue.connection}`} breadcrumbs="Данные / Проблемные записи / Детали" />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/issues" variant="outline" data-testid="button-back-issues">
          Назад
        </LinkAsButton>
        <Button type="button" data-testid="button-accept-suggested">
          Принять предложенное значение
        </Button>
        <Button type="button" variant="outline" data-testid="button-create-rule-from-issue">
          Создать правило
        </Button>
      </div>
      <Card className="space-y-2 p-4" data-testid="issue-detail-body">
        <p className="text-sm">
          <strong>Серьёзность:</strong> {issue.severity}
        </p>
        <p className="text-sm">
          <strong>Поток:</strong> {issue.stream} · <strong>Поле:</strong> {issue.field}
        </p>
        <p className="text-sm">
          <strong>Исходное значение:</strong> <span className="font-mono">{issue.original}</span>
        </p>
        <p className="text-sm">
          <strong>Предложение:</strong> <span className="font-mono">{issue.suggested}</span>
        </p>
        <p className="text-sm text-muted-foreground">Статус: {issue.status}</p>
      </Card>
    </div>
  );
}
