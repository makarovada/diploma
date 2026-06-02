import { useQuery } from "@tanstack/react-query";
import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { PageHeader } from "@/components/page-header";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { fetchNormalizationIssues, mapNormRowToIssue } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

export function ConnectionIssuesPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  const issuesQuery = useQuery({
    queryKey: queryKeys.connectionIssues.bySource(connection?.source),
    queryFn: async () => {
      const { rows } = await fetchNormalizationIssues(200);
      return rows
        .filter((r) => (r.source_system ?? "") === connection!.source)
        .map(mapNormRowToIssue);
    },
    enabled: Boolean(connection?.source),
  });

  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }

  const rows = issuesQuery.data ?? [];

  return (
    <div className="space-y-4 p-4">
      <PageHeader title="Проблемные записи" description={connection.name} breadcrumbs="Интеграции / Подключения / Проблемы" />
      <ConnectionSubNav connectionId={id} />
      <div className="overflow-auto rounded-lg border" data-testid="table-connection-issues">
        <table className="w-full min-w-[720px] text-sm" aria-label="Проблемы подключения">
          <thead className="bg-muted">
            <tr>
              <th>Тип</th>
              <th>Поток</th>
              <th>Поле</th>
              <th>Исходное</th>
              <th>Предложение</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {issuesQuery.isLoading ? (
              <tr>
                <td colSpan={6} className="p-4 text-muted-foreground">
                  Загрузка проблем…
                </td>
              </tr>
            ) : (
              rows.map((issue) => (
                <tr key={issue.id} className="border-t">
                  <td>{issue.type}</td>
                  <td>{issue.stream}</td>
                  <td>{issue.field}</td>
                  <td>{issue.original}</td>
                  <td>{issue.suggested}</td>
                  <td>
                    <LinkAsButton href={`/issues/${issue.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-issue-${issue.id}`}>
                      Открыть
                    </LinkAsButton>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!issuesQuery.isLoading && rows.length === 0 ? <p className="text-sm text-muted-foreground">Нет проблем для этого подключения.</p> : null}
    </div>
  );
}
