import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { fetchEltConnections, deleteEltConnection } from "@/lib/api-elt";
import { fetchWorkspaces, mapEltDetailToConnection } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { EntityListActions } from "@/components/entity-list-actions";

export function ConnectionsPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: queryKeys.connections.eltList(workspaceCode),
    queryFn: async () => {
      const { items } = await fetchEltConnections(workspaceCode);
      return items.map(mapEltDetailToConnection);
    },
  });

  if (query.isPending || wsQuery.isPending) {
    return <div data-testid="state-loading-connections" className="p-4">Загрузка подключений...</div>;
  }
  if (query.isError || !query.data) {
    return <div data-testid="state-error-connections" className="p-4">Ошибка загрузки подключений.</div>;
  }
  if (query.data.length === 0) {
    return <div data-testid="state-empty-connections" className="p-4">Пока нет подключений.</div>;
  }

  return (
    <div className="p-4">
      <PageHeader
        title="Подключения"
        description="Доменные подключения ELT (источник → приёмник)"
        breadcrumbs="Интеграции / Подключения"
        actions={<LinkAsButton href="/connections/new" data-testid="button-create-connection">Создать подключение</LinkAsButton>}
      />
      <div className="overflow-auto rounded-lg border" data-testid="table-connections">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="bg-muted">
            <tr>
              <th>Название</th>
              <th>Источник</th>
              <th>Приемник</th>
              <th>Статус</th>
              <th>Режим</th>
              <th>Расписание</th>
              <th>Проблемы</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {query.data.map((conn) => (
              <tr key={conn.id} className="border-t" data-testid={`row-connection-${conn.id}`}>
                <td>{conn.name}</td>
                <td>{conn.source}</td>
                <td>{conn.destination}</td>
                <td>
                  <StatusBadge status={conn.status} />
                </td>
                <td>{conn.syncMode}</td>
                <td className="max-w-[200px] truncate font-mono text-xs">{conn.schedule}</td>
                <td>{conn.issues}</td>
                <td>
                  <div className="flex flex-wrap items-center gap-1">
                    <LinkAsButton
                      href={`/connections/${conn.id}`}
                      variant="outline"
                      className="px-2 py-1 text-xs"
                      data-testid={`button-open-connection-${conn.id}`}
                    >
                      Открыть
                    </LinkAsButton>
                    <EntityListActions
                      editHref={`/connections/${conn.id}/edit`}
                      editTestId={`button-edit-connection-${conn.id}`}
                      deleteTestId={`button-delete-connection-${conn.id}`}
                      entityLabel={conn.name}
                      onDelete={() => deleteEltConnection(Number(conn.id), workspaceCode)}
                      onDeleteSuccess={() => {
                        void queryClient.invalidateQueries({ queryKey: queryKeys.connections.eltList(workspaceCode) });
                        setLocation("/connections");
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
