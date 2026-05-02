import { useRoute } from "wouter";
import { sources } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function SourceDetailPage() {
  const [, params] = useRoute("/sources/:sourceId");
  const source = sources.find((s) => s.id === params?.sourceId);

  if (!source) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Источник не найден.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">К списку источников</LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={source.name} description={`Коннектор: ${source.connector} · ${source.category}`} breadcrumbs={`Интеграции / Источники / ${source.name}`} actions={<Button data-testid="button-test-source">Проверить подключение</Button>} />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/sources" variant="outline" data-testid="button-back-sources">Назад</LinkAsButton>
        <LinkAsButton href={`/connections/new?source=${source.id}`} data-testid="button-create-connection-from-source">Создать подключение</LinkAsButton>
      </div>
      <Card className="p-4" data-testid="source-detail-overview">
        <p className="text-sm">Потоков данных: {source.streamCount}</p>
        <p className="text-sm text-muted-foreground">Владелец: {source.owner}</p>
      </Card>
    </div>
  );
}
