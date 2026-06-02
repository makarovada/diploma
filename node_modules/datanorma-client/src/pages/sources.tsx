import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Input } from "@/components/ui/input";
import { EntityListActions } from "@/components/entity-list-actions";
import { queryKeys } from "@/lib/query-keys";
import { fetchEltSources, deleteEltSource } from "@/lib/api-elt";
import { fetchWorkspaces, formatTs } from "@/lib/api-datanorma";

const checkLabel: Record<string, string> = {
  ok: "Проверено",
  warning: "Предупреждение",
  error: "Ошибка",
  never: "Не проверялось",
};

function checkFromSourceRow(lastChecked: string | null | undefined, status: string): keyof typeof checkLabel {
  if (lastChecked) return "ok";
  if (status === "error") return "error";
  return "never";
}

export function SourcesPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const wsQuery = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: () => fetchWorkspaces(),
  });
  const workspaceCode = wsQuery.data?.items?.[0]?.workspace_code ?? "main";

  const query = useQuery({
    queryKey: queryKeys.sources.eltList(workspaceCode),
    queryFn: async () => {
      const { items } = await fetchEltSources(workspaceCode);
      return items;
    },
  });

  if (query.isPending || wsQuery.isPending) {
    return <div data-testid="state-loading-sources" className="p-4">Загрузка источников…</div>;
  }
  if (query.isError) {
    return <div data-testid="state-error-sources" className="p-4">Ошибка загрузки источников.</div>;
  }

  const list = query.data ?? [];

  if (list.length === 0) {
    return (
      <div className="p-4">
        <PageHeader
          title="Источники"
          description="Доменные источники (ELT) в текущем workspace"
          breadcrumbs="Интеграции / Источники"
          actions={<LinkAsButton href="/sources/new" data-testid="button-add-source">Добавить источник</LinkAsButton>}
        />
        <div data-testid="state-empty-sources" className="rounded-lg border bg-card p-8 text-center">
          <p className="font-medium">Источников пока нет</p>
          <p className="mt-1 text-sm text-muted-foreground">Создайте источник и подключение через мастер.</p>
          <LinkAsButton href="/sources/new" className="mt-4" data-testid="button-empty-create-source">
            Создать источник
          </LinkAsButton>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <PageHeader
        title="Источники"
        description="Доменные источники (ELT)"
        breadcrumbs="Интеграции / Источники"
        actions={<LinkAsButton href="/sources/new" data-testid="button-add-source">Добавить источник</LinkAsButton>}
      />
      <div className="mb-3 flex flex-wrap gap-2">
        <Input className="max-w-sm" placeholder="Поиск по названию или коннектору…" data-testid="input-sources-search" />
      </div>
      <div className="overflow-auto rounded-lg border" data-testid="table-sources">
        <table className="w-full min-w-[720px] text-left text-sm" aria-label="Таблица источников">
          <thead className="bg-muted">
            <tr>
              <th>ID</th>
              <th>Название</th>
              <th>Коннектор</th>
              <th>Статус</th>
              <th>Проверка</th>
              <th>Обновлён</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => {
              const ck = checkFromSourceRow(s.last_checked_at, s.status);
              return (
                <tr key={s.id} className="border-t" data-testid={`row-source-${s.id}`}>
                  <td className="font-mono text-xs">{s.id}</td>
                  <td>{s.name}</td>
                  <td>{s.connector_code}</td>
                  <td>{s.status}</td>
                  <td>{checkLabel[ck]}</td>
                  <td>{formatTs(s.updated_at)}</td>
                  <td>
                    <div className="flex flex-wrap items-center gap-1">
                      <LinkAsButton
                        href={`/sources/${encodeURIComponent(String(s.id))}`}
                        variant="outline"
                        className="px-2 py-1 text-xs"
                        data-testid={`button-open-source-${s.id}`}
                      >
                        Открыть
                      </LinkAsButton>
                      <EntityListActions
                        editHref={`/sources/${s.id}/edit`}
                        editTestId={`button-edit-source-${s.id}`}
                        deleteTestId={`button-delete-source-${s.id}`}
                        entityLabel={s.name}
                        onDelete={() => deleteEltSource(s.id, workspaceCode)}
                        onDeleteSuccess={() => {
                          void queryClient.invalidateQueries({ queryKey: queryKeys.sources.eltList(workspaceCode) });
                          setLocation("/sources");
                        }}
                      />
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
