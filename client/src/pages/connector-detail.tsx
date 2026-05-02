import { useRoute } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { connectorsCatalog } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function ConnectorDetailPage() {
  const [, params] = useRoute("/connectors/:connectorId");
  const c = connectorsCatalog.find((x) => x.id === params?.connectorId);

  if (!c) {
    return (
      <div className="p-4" data-testid="state-not-found-connector">
        <p>Коннектор не найден.</p>
        <LinkAsButton href="/connectors" variant="outline" className="mt-2" data-testid="button-back-connectors">К каталогу</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={c.name} description={c.description} breadcrumbs={`Интеграции / Каталог / ${c.name}`} />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/connectors" variant="outline" data-testid="button-back-connectors">Назад</LinkAsButton>
        {(c.role === "source" || c.role === "both") ? <Button data-testid="button-create-source-from-connector">Создать источник</Button> : null}
        {(c.role === "destination" || c.role === "both") ? <Button variant="outline" data-testid="button-create-destination-from-connector">Создать приёмник</Button> : null}
      </div>
      <Card className="p-4" data-testid="connector-detail-overview">
        <p className="text-sm"><strong>Категория:</strong> {c.category}</p>
        <p className="text-sm"><strong>Регион:</strong> {c.region === "ru" ? "Российские" : "Международные"}</p>
        <p className="text-sm"><strong>Поддерживаемые потоки:</strong> {c.streams.join(", ")}</p>
        <p className="text-sm"><strong>Авторизация:</strong> {c.auth}</p>
      </Card>
    </div>
  );
}
