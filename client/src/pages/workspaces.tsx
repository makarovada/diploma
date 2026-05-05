import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchWorkspaces } from "@/lib/api-datanorma";
import { queryKeys } from "@/lib/query-keys";

export function WorkspacesPage() {
  const query = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: async () => {
      const { items } = await fetchWorkspaces();
      return items.map((w) => ({
        id: `${w.org_code}/${w.workspace_code}`,
        name: w.workspace_name,
        code: w.workspace_code,
        org: w.org_name,
        role: "—",
      }));
    },
  });

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить рабочие пространства.</div>;

  const workspaceList = query.data;

  return (
    <div className="p-4">
      <PageHeader title="Рабочие пространства" description="Изоляция данных и доступов между командами" breadcrumbs="Администрирование / Рабочие пространства" actions={<Button data-testid="button-create-workspace">Создать пространство</Button>} />
      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-workspaces">
        {workspaceList.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="state-empty-workspaces">
            Нет записей.
          </p>
        ) : (
          workspaceList.map((w) => (
            <Card key={w.id} className="p-4" data-testid={`card-workspace-${w.id.replace(/[^\w-]/g, "_")}`}>
              <p className="font-semibold">{w.name}</p>
              <p className="text-xs text-muted-foreground">
                Код: {w.code} · {w.org}
              </p>
              <p className="text-sm">Ваша роль: {w.role}</p>
              <Button variant="outline" className="mt-2" data-testid={`button-switch-workspace-${w.id.replace(/[^\w-]/g, "_")}`}>
                Переключиться
              </Button>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
