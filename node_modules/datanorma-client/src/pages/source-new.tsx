import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { connectorsCatalog } from "@/lib/mock-data";
import { Card } from "@/components/ui/card";

export function SourceNewPage() {
  return (
    <div className="p-4">
      <PageHeader title="Новый источник" description="Выберите коннектор и задайте параметры доступа" breadcrumbs="Интеграции / Источники / Новый" />
      <div className="mb-4 max-w-md space-y-2">
        <Input placeholder="Название источника" data-testid="input-source-name" />
        <Input placeholder="API token (пример)" type="password" data-testid="input-source-secret" />
        <Button data-testid="button-save-source">Сохранить</Button>
        <LinkAsButton href="/sources" variant="outline" data-testid="button-cancel-source">Отмена</LinkAsButton>
      </div>
      <p className="mb-2 text-sm font-medium">Популярные коннекторы</p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="grid-source-connectors">
        {connectorsCatalog.filter((c) => c.role === "source" || c.role === "both").map((c) => (
          <Card key={c.id} className="p-4" data-testid={`card-connector-pick-${c.id}`}>
            <p className="font-medium">{c.name}</p>
            <p className="text-xs text-muted-foreground">{c.description}</p>
            <Button className="mt-2 w-full" variant="outline" data-testid={`button-select-connector-${c.id}`}>Выбрать</Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
