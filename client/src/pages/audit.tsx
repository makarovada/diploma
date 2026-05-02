import { useQuery } from "@tanstack/react-query";
import { auditEntries } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { PageFooter } from "@/components/page-footer";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function AuditPage() {
  const query = useQuery({
    queryKey: ["audit"],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 200));
      return auditEntries;
    },
  });

  if (query.isLoading) return <div data-testid="state-loading-audit" className="p-4">Загрузка журнала аудита…</div>;
  if (query.isError || !query.data) return <div data-testid="state-error-audit" className="p-4">Не удалось загрузить аудит.</div>;

  return (
    <div className="p-4">
      <PageHeader title="Аудит" description="Действия пользователей и системные изменения" breadcrumbs="Администрирование / Аудит" />
      <div className="mb-3 flex flex-wrap gap-2">
        <Input className="max-w-xs" placeholder="Актор, действие, сущность…" data-testid="input-audit-search" />
        <Button variant="outline" data-testid="button-audit-filter">Фильтры</Button>
      </div>
      <div className="overflow-auto rounded-lg border" data-testid="table-audit">
        <table className="w-full min-w-[1000px] text-left text-sm" aria-label="Журнал аудита">
          <thead className="bg-muted">
            <tr>
              <th>Время</th>
              <th>Кто</th>
              <th>Действие</th>
              <th>Тип сущности</th>
              <th>Имя</th>
              <th>Результат</th>
              <th>Детали</th>
            </tr>
          </thead>
          <tbody>
            {query.data.map((a) => (
              <tr key={a.id} className="border-t" data-testid={`row-audit-${a.id}`}>
                <td className="whitespace-nowrap text-xs">{a.at}</td>
                <td>{a.actor}</td>
                <td className="font-mono text-xs">{a.action}</td>
                <td>{a.entityType}</td>
                <td>{a.entityName}</td>
                <td>{a.result === "success" ? "Успех" : "Ошибка"}</td>
                <td className="max-w-[240px] truncate text-xs text-muted-foreground">{a.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PageFooter />
    </div>
  );
}
