import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { EntityListActions } from "@/components/entity-list-actions";
import { fetchDestinationsCatalog, fetchWorkspaces, mapDestinationCatalogItem } from "@/lib/api-datanorma";
import { deleteEltDestination } from "@/lib/api-elt";
import { queryKeys } from "@/lib/query-keys";
import { isNumericEltId } from "@/lib/elt-entity-id";

const statusRu: Record<string, string> = {
  ok: "Доступен",
  warning: "Внимание",
  error: "Ошибка",
};

export function DestinationsPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: queryKeys.destinations.list(),
    queryFn: async () => {
      const { items } = await fetchDestinationsCatalog(undefined, workspaceCode);
      return items.map(mapDestinationCatalogItem);
    },
  });

  if (query.isPending || wsQuery.isPending) {
    return <div data-testid="state-loading-destinations" className="p-4">Загрузка приёмников…</div>;
  }
  if (query.isError) {
    return <div data-testid="state-error-destinations" className="p-4">Ошибка загрузки приёмников.</div>;
  }

  const list = query.data ?? [];

  if (list.length === 0) {
    return (
      <div className="p-4">
        <PageHeader title="Приёмники" description="Системы и хранилища для нормализованных данных" breadcrumbs="Интеграции / Приёмники" actions={<LinkAsButton href="/destinations/new" data-testid="button-add-destination">Добавить приёмник</LinkAsButton>} />
        <div data-testid="state-empty-destinations" className="rounded-lg border bg-card p-8 text-center text-sm text-muted-foreground">
          Нет записей в каталоге приёмников.
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <PageHeader title="Приёмники" description="Системы и хранилища для нормализованных данных" breadcrumbs="Интеграции / Приёмники" actions={<LinkAsButton href="/destinations/new" data-testid="button-add-destination">Добавить приёмник</LinkAsButton>} />
      <div className="overflow-auto rounded-lg border" data-testid="table-destinations">
        <table className="w-full min-w-[880px] text-left text-sm" aria-label="Таблица приёмников">
          <thead className="bg-muted">
            <tr>
              <th>Название</th>
              <th>Тип</th>
              <th>Коннектор</th>
              <th>Статус</th>
              <th>Схема / база</th>
              <th>Последнее использование</th>
              <th>Подключений</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {list.map((d) => {
              const canManage = isNumericEltId(d.id);
              return (
                <tr key={d.id} className="border-t" data-testid={`row-destination-${d.id}`}>
                  <td>{d.name}</td>
                  <td>{d.type}</td>
                  <td data-testid={`cell-destination-connector-${d.id}`}>{d.connectorCode ?? "—"}</td>
                  <td>{statusRu[d.status]}</td>
                  <td>{d.schemaOrDb}</td>
                  <td>{d.lastUsed}</td>
                  <td>{d.connectionCount}</td>
                  <td>
                    <div className="flex flex-wrap items-center gap-1">
                      <LinkAsButton
                        href={`/destinations/${encodeURIComponent(d.id)}`}
                        variant="outline"
                        className="px-2 py-1 text-xs"
                        data-testid={`button-open-destination-${d.id}`}
                      >
                        Открыть
                      </LinkAsButton>
                      {canManage ? (
                        <EntityListActions
                          editHref={`/destinations/${d.id}/edit`}
                          editTestId={`button-edit-destination-${d.id}`}
                          deleteTestId={`button-delete-destination-${d.id}`}
                          entityLabel={d.name}
                          onDelete={() => deleteEltDestination(Number(d.id), workspaceCode)}
                          onDeleteSuccess={() => {
                            void queryClient.invalidateQueries({ queryKey: queryKeys.destinations.list() });
                            setLocation("/destinations");
                          }}
                          deleteDisabled={d.connectionCount > 0}
                          deleteDisabledTitle={
                            d.connectionCount > 0 ? "Сначала удалите подключения, использующие этот приёмник" : undefined
                          }
                        />
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
