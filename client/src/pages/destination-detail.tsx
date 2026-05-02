import { useRoute } from "wouter";
import { destinations } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";

export function DestinationDetailPage() {
  const [, params] = useRoute("/destinations/:destinationId");
  const dest = destinations.find((d) => d.id === params?.destinationId);

  if (!dest) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">К списку приёмников</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={dest.name} description={`${dest.type} · ${dest.schemaOrDb}`} breadcrumbs={`Интеграции / Приёмники / ${dest.name}`} />
      <div className="flex gap-2">
        <LinkAsButton href="/destinations" variant="outline" data-testid="button-back-destinations">Назад</LinkAsButton>
      </div>
      <Card className="p-4" data-testid="destination-detail-overview">
        <p className="text-sm">Используется в подключениях: {dest.connectionCount}</p>
        <p className="text-sm text-muted-foreground">Последнее использование: {dest.lastUsed}</p>
      </Card>
    </div>
  );
}
