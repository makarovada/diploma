import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { destinations as demoDestinations } from "@/lib/mock-data";
import { DemoFallbackBanner } from "@/components/demo-fallback-banner";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { fetchDestinationsCatalog, mapDestinationCatalogItem } from "@/lib/api-datanorma";
import { withApiOrDemo } from "@/lib/demo-fallback";
import { queryKeys } from "@/lib/query-keys";
import type { Destination } from "@/lib/types";

async function loadDestinationById(id: string): Promise<Destination> {
  const { items } = await fetchDestinationsCatalog(undefined, "main");
  const row = items.find((x) => x.id === id);
  if (row) return mapDestinationCatalogItem(row);
  const d = demoDestinations.find((x) => x.id === id);
  if (d) return d;
  throw new Error("not_found");
}

export function DestinationDetailPage() {
  const [, params] = useRoute("/destinations/:destinationId");
  const destinationId = params?.destinationId ? decodeURIComponent(params.destinationId) : "";

  const query = useQuery({
    queryKey: queryKeys.destinations.detail(destinationId),
    queryFn: () =>
      withApiOrDemo(
        async () => loadDestinationById(destinationId),
        demoDestinations.find((d) => d.id === destinationId) ?? demoDestinations[0],
      ),
    enabled: Boolean(destinationId),
  });

  if (!destinationId) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">
          К списку приёмников
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден или ошибка API.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">
          К списку приёмников
        </LinkAsButton>
      </div>
    );
  }

  const dest = query.data?.value;
  const isDemo = query.data?.isDemoFallback ?? false;
  if (!dest) {
    return (
      <div className="p-4" data-testid="state-not-found-destination">
        <p>Приёмник не найден.</p>
        <LinkAsButton href="/destinations" variant="outline" className="mt-2" data-testid="button-back-destinations">
          К списку приёмников
        </LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {isDemo ? <DemoFallbackBanner /> : null}
      <PageHeader
        title={dest.name}
        description={`${dest.type}${dest.connectorCode ? ` · ${dest.connectorCode}` : ""} · ${dest.schemaOrDb}`}
        breadcrumbs={`Интеграции / Приёмники / ${dest.name}`}
      />
      <div className="flex gap-2">
        <LinkAsButton href="/destinations" variant="outline" data-testid="button-back-destinations">
          Назад
        </LinkAsButton>
      </div>
      <Card className="p-4" data-testid="destination-detail-overview">
        {dest.connectorCode ? (
          <p className="text-sm" data-testid="destination-detail-connector">
            Коннектор: <span className="font-medium">{dest.connectorCode}</span>
          </p>
        ) : null}
        <p className="text-sm">Используется в подключениях: {dest.connectionCount}</p>
        <p className="text-sm text-muted-foreground">Последнее использование: {dest.lastUsed}</p>
      </Card>
    </div>
  );
}
