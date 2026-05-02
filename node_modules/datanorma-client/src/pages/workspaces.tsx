import { workspaceList } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function WorkspacesPage() {
  return (
    <div className="p-4">
      <PageHeader title="Рабочие пространства" description="Изоляция данных и доступов между командами" breadcrumbs="Администрирование / Рабочие пространства" actions={<Button data-testid="button-create-workspace">Создать пространство</Button>} />
      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-workspaces">
        {workspaceList.map((w) => (
          <Card key={w.id} className="p-4" data-testid={`card-workspace-${w.id}`}>
            <p className="font-semibold">{w.name}</p>
            <p className="text-xs text-muted-foreground">Код: {w.code}</p>
            <p className="text-sm">Ваша роль: {w.role}</p>
            <Button variant="outline" className="mt-2" data-testid={`button-switch-workspace-${w.id}`}>
              Переключиться
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
