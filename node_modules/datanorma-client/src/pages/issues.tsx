import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { issues as demoIssues } from "@/lib/mock-data";
import { DemoFallbackBanner } from "@/components/demo-fallback-banner";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { fetchNormalizationIssues, ignoreIssue, mapNormRowToIssue, resolveIssue } from "@/lib/api-datanorma";
import { withApiOrDemo } from "@/lib/demo-fallback";
import { queryKeys } from "@/lib/query-keys";

export function IssuesPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.issues.list(200),
    queryFn: () =>
      withApiOrDemo(async () => {
        const { rows } = await fetchNormalizationIssues(200);
        return rows.map(mapNormRowToIssue);
      }, demoIssues),
  });

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить проблемы.</div>;

  const issues = query.data.value;
  const isDemo = query.data.isDemoFallback;
  const resolveMutation = useMutation({
    mutationFn: (issueId: number) => resolveIssue(issueId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.list(200) });
    },
  });
  const ignoreMutation = useMutation({
    mutationFn: (issueId: number) => ignoreIssue(issueId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.issues.list(200) });
    },
  });

  return (
    <div className="p-4">
      <PageHeader title="Проблемные записи" description="Центр качества данных" breadcrumbs="Данные / Проблемные записи" />
      {isDemo ? <DemoFallbackBanner /> : null}
      <div className="overflow-auto rounded-lg border" data-testid="table-issues">
        <table className="w-full min-w-[980px] text-sm">
          <thead className="bg-muted"><tr><th>Severity</th><th>Type</th><th>Connection</th><th>Stream</th><th>Field</th><th>Original</th><th>Suggested</th><th>Status</th><th>Действия</th></tr></thead>
          <tbody>
            {issues.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-4 text-muted-foreground">
                  Нет записей в normalization_issue.
                </td>
              </tr>
            ) : (
              issues.map((issue) => (
                <tr key={issue.id} className="border-t" data-testid={`row-issue-${issue.id}`}>
                  <td>{issue.severity}</td><td>{issue.type}</td><td>{issue.connection}</td><td>{issue.stream}</td><td>{issue.field}</td><td>{issue.original}</td><td>{issue.suggested}</td><td>{issue.status}</td>
                  <td className="flex flex-wrap gap-1">
                    <LinkAsButton href={`/issues/${issue.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-issue-${issue.id}`}>
                      Открыть
                    </LinkAsButton>
                    <Button
                      type="button"
                      variant="outline"
                      className="px-2 py-1 text-xs"
                      data-testid={`button-resolve-issue-${issue.id}`}
                      disabled={isDemo || resolveMutation.isPending}
                      onClick={() => resolveMutation.mutate(Number(issue.id))}
                    >
                      Принять исправление
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="px-2 py-1 text-xs"
                      data-testid={`button-ignore-issue-${issue.id}`}
                      disabled={isDemo || ignoreMutation.isPending}
                      onClick={() => ignoreMutation.mutate(Number(issue.id))}
                    >
                      Игнорировать
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
