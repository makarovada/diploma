import { useQuery } from "@tanstack/react-query";
import { connections } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";

export function ConnectionsPage() {
  const query = useQuery({ queryKey: ["connections"], queryFn: async () => connections });
  if (query.isLoading) return <div data-testid="state-loading-connections" className="p-4">Загрузка подключений...</div>;
  if (query.isError || !query.data) return <div data-testid="state-error-connections" className="p-4">Ошибка загрузки подключений.</div>;
  if (query.data.length === 0) return <div data-testid="state-empty-connections" className="p-4">Пока нет подключений.</div>;

  return (
    <div className="p-4">
      <PageHeader title="Подключения" description="Сценарии передачи и нормализации данных" breadcrumbs="Интеграции / Подключения" actions={<LinkAsButton href="/connections/new" data-testid="button-create-connection">Создать подключение</LinkAsButton>} />
      <div className="overflow-auto rounded-lg border" data-testid="table-connections">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="bg-muted"><tr><th>Название</th><th>Источник</th><th>Приемник</th><th>Статус</th><th>Режим</th><th>Расписание</th><th>Проблемы</th><th>Действия</th></tr></thead>
          <tbody>
            {query.data.map((conn) => (
              <tr key={conn.id} className="border-t" data-testid={`row-connection-${conn.id}`}>
                <td>{conn.name}</td><td>{conn.source}</td><td>{conn.destination}</td><td><StatusBadge status={conn.status} /></td><td>{conn.syncMode}</td><td>{conn.schedule}</td><td>{conn.issues}</td>
                <td><LinkAsButton href={`/connections/${conn.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-connection-${conn.id}`}>Открыть</LinkAsButton></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
