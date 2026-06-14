import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchNormalizationIssues, fetchWorkspaces, ignoreIssue, mapNormRowToIssue, resolveIssue } from "@/lib/api-datanorma";
import { patchEltConnectionStreamEnabled } from "@/lib/api-elt";
import { DISABLE_STREAM_CONFIRM } from "@/lib/issue-explanations";
import { queryKeys } from "@/lib/query-keys";

export function IssueDetailPage() {
  const [, params] = useRoute("/issues/:issueId");
  const issueId = params?.issueId ?? "";
  const queryClient = useQueryClient();

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

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

  const resolveMutation = useMutation({
    mutationFn: () => resolveIssue(Number(issueId)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.detail(issueId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.list(200) });
    },
  });

  const ignoreMutation = useMutation({
    mutationFn: () => ignoreIssue(Number(issueId)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.detail(issueId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.list(200) });
    },
  });

  const disableStreamMutation = useMutation({
    mutationFn: () =>
      patchEltConnectionStreamEnabled(Number(issue!.connectionId), issue!.stream, false, workspaceCode),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltDetail(issue!.connectionId!, workspaceCode) });
    },
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
  const editRulesHref =
    issue.connectionId != null
      ? `/connections/${issue.connectionId}/streams/edit${issue.field ? `?field=${encodeURIComponent(issue.field)}` : ""}`
      : null;

  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title={issue.title ?? `Проблема ${issue.id}`}
        description={`${issue.connection} · ${issue.stream}`}
        breadcrumbs="Данные / Проблемные записи / Детали"
      />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/issues" variant="outline" data-testid="button-back-issues">
          Назад
        </LinkAsButton>
        {editRulesHref ? (
          <LinkAsButton href={editRulesHref} data-testid="button-create-rule-from-issue">
            Исправить правило
          </LinkAsButton>
        ) : null}
        <Button
          type="button"
          variant="outline"
          data-testid="button-accept-suggested"
          disabled={resolveMutation.isPending || issue.status !== "open"}
          onClick={() => resolveMutation.mutate()}
        >
          Отметить решённым
        </Button>
        <Button
          type="button"
          variant="outline"
          data-testid="button-ignore-issue-detail"
          disabled={ignoreMutation.isPending || issue.status !== "open"}
          onClick={() => ignoreMutation.mutate()}
        >
          Игнорировать
        </Button>
        {issue.connectionId && issue.status === "open" ? (
          <Button
            type="button"
            variant="outline"
            data-testid="button-disable-stream-from-issue"
            disabled={disableStreamMutation.isPending}
            onClick={() => {
              if (window.confirm(`${DISABLE_STREAM_CONFIRM}\n\nПоток: ${issue.stream}`)) {
                disableStreamMutation.mutate();
              }
            }}
          >
            Отключить поток
          </Button>
        ) : null}
      </div>
      <Card className="space-y-3 p-4" data-testid="issue-detail-body">
        <div>
          <p className="text-sm font-medium">Что случилось</p>
          <p className="text-sm text-muted-foreground">{issue.explanation ?? issue.original}</p>
        </div>
        <div>
          <p className="text-sm font-medium">Что сделать</p>
          <p className="text-sm text-muted-foreground">{issue.recommendedAction ?? "—"}</p>
        </div>
        <p className="text-sm">
          <strong>Серьёзность:</strong> {issue.severity}
        </p>
        <p className="text-sm">
          <strong>Поток:</strong> {issue.stream} · <strong>Поле:</strong> {issue.field}
        </p>
        <p className="text-sm">
          <strong>Сообщение:</strong> <span className="font-mono">{issue.original}</span>
        </p>
        {issue.rawValue ? (
          <p className="text-sm">
            <strong>Исходное значение:</strong> <span className="font-mono">{issue.rawValue}</span>
          </p>
        ) : null}
        <p className="text-sm">
          <strong>Запись в источнике:</strong> <span className="font-mono">{issue.suggested}</span>
        </p>
        <p className="text-sm text-muted-foreground">Статус: {issue.status}</p>
        {issue.syncRunId ? (
          <LinkAsButton href={`/runs/${issue.syncRunId}`} variant="outline" className="text-xs" data-testid="link-issue-sync-run">
            Открыть запуск #{issue.syncRunId}
          </LinkAsButton>
        ) : null}
      </Card>
      {ignoreMutation.isSuccess ? (
        <p className="text-sm text-muted-foreground">Запись помечена как игнорируемая и не учитывается в отчётах.</p>
      ) : null}
    </div>
  );
}
