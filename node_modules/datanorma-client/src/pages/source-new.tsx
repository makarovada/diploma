import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export function SourceNewPage() {
  const query = useQuery({
    queryKey: ["connectors-catalog", "source-new"],
    queryFn: async () => {
      const resp = await fetch("/api/v1/connectors/catalog?role=source");
      const body = (await resp.json()) as { items?: Array<Record<string, unknown>> };
      return Array.isArray(body.items) ? body.items : [];
    },
  });
  const connectorsCatalog = query.data ?? [];

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
        {connectorsCatalog.map((c) => (
          <Card key={String(c.code)} className="p-4" data-testid={`card-connector-pick-${String(c.code)}`}>
            <p className="font-medium">{String(c.name ?? c.code)}</p>
            <p className="text-xs text-muted-foreground">{String(c.category ?? "source")}</p>
            <Button className="mt-2 w-full" variant="outline" data-testid={`button-select-connector-${String(c.code)}`}>Выбрать</Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
