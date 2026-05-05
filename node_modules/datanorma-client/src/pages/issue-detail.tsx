import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchNormalizationIssues, mapNormRowToIssue } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

export function IssueDetailPage() {
  const [, params] = useRoute("/issues/:issueId");
  const issueId = params?.issueId ?? "";

  const query = useQuery({
    queryKey: queryKeys.issues.detail(issueId),
    queryFn: async () => {
      const { rows } = await fetchNormalizationIssues(200);
      const row = rows.find((r) => String(r.id) === issueId);
      if (!row) throw new Error("not_found");
      return mapNormRowToIssue(row);
    },
    enabled: Boolean(issueId),
  });

  if (!issueId) {
    return (
      <div className="p-4" data-testid="state-not-found-issue">
        Запись не найдена. <LinkAsButton href="/issues">К списку</LinkAsButton>
      </div>
    );
  }

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError || !query.data) return <div className="p-4">Ошибка загрузки.</div>;

  const issue = query.data;
  if (!issue) {
    return (
      <div className="p-4" data-testid="state-not-found-issue">
        Запись не найдена (нет в последних 200 записях). <LinkAsButton href="/issues">К списку</LinkAsButton>
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
          <strong>Сообщение:</strong> <span className="font-mono">{issue.original}</span>
        </p>
        <p className="text-sm">
          <strong>Связанная запись:</strong> <span className="font-mono">{issue.suggested}</span>
        </p>
        <p className="text-sm text-muted-foreground">Статус: {issue.status}</p>
      </Card>
    </div>
  );
}
