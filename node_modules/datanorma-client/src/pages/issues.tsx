import { issues } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";

export function IssuesPage() {
  return (
    <div className="p-4">
      <PageHeader title="Проблемные записи" description="Центр качества данных" breadcrumbs="Данные / Проблемные записи" />
      <div className="overflow-auto rounded-lg border" data-testid="table-issues">
        <table className="w-full min-w-[980px] text-sm">
          <thead className="bg-muted"><tr><th>Severity</th><th>Type</th><th>Connection</th><th>Field</th><th>Original</th><th>Suggested</th><th>Status</th><th>Действия</th></tr></thead>
          <tbody>
            {issues.map((issue) => (
              <tr key={issue.id} className="border-t" data-testid={`row-issue-${issue.id}`}>
                <td>{issue.severity}</td><td>{issue.type}</td><td>{issue.connection}</td><td>{issue.field}</td><td>{issue.original}</td><td>{issue.suggested}</td><td>{issue.status}</td>
                <td className="flex flex-wrap gap-1">
                  <LinkAsButton href={`/issues/${issue.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-issue-${issue.id}`}>
                    Открыть
                  </LinkAsButton>
                  <Button type="button" variant="outline" className="px-2 py-1 text-xs" data-testid={`button-resolve-issue-${issue.id}`}>
                    Принять исправление
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
