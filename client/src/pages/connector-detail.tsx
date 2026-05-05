import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ConnectorCatalogItem } from "@/lib/types";

function mapRole(v: string): ConnectorCatalogItem["role"] {
  if (v === "source" || v === "destination" || v === "both") return v;
  return "source";
}

export function ConnectorDetailPage() {
  const [, params] = useRoute("/connectors/:connectorId");
  const connectorId = params?.connectorId ?? "";
  const query = useQuery({
    queryKey: ["connector-detail", connectorId],
    queryFn: async () => {
      const resp = await fetch(`/api/v1/connectors/catalog/${encodeURIComponent(connectorId)}`);
      const body = (await resp.json()) as { item?: Record<string, unknown> };
      const item = body.item ?? {};
      return {
        id: String(item.code ?? ""),
        name: String(item.name ?? ""),
        category: String(item.category ?? "source"),
        region: "ru" as const,
        role: mapRole(String(item.category ?? "source")),
        preview: false,
        description: String(item.name ?? ""),
        streams: Array.isArray(item.streams) ? item.streams.map((s) => String((s as Record<string, unknown>).stream_name ?? "")) : [],
        auth: "—",
      } satisfies ConnectorCatalogItem;
    },
    enabled: Boolean(connectorId),
  });
  const c = query.data;

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
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
