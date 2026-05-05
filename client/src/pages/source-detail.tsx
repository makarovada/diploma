import { useQuery } from "@tanstack/react-query";
import { useRoute } from "wouter";
import { buildSourcesFromDimAndV1, fetchDimSources, fetchV1Connections } from "@/lib/api-datanorma";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { queryKeys } from "@/lib/query-keys";
import type { Source } from "@/lib/types";

async function loadSourceById(sourceId: string): Promise<Source> {
  const [dim, v1] = await Promise.all([fetchDimSources(), fetchV1Connections()]);
  const list = buildSourcesFromDimAndV1(dim.rows, v1.items);
  const s = list.find((x) => x.id === sourceId);
  if (s) return s;
  throw new Error("not_found");
}

export function SourceDetailPage() {
  const [, params] = useRoute("/sources/:sourceId");
  const sourceId = params?.sourceId ? decodeURIComponent(params.sourceId) : "";

  const query = useQuery({
    queryKey: queryKeys.sources.detail(sourceId),
    queryFn: () => loadSourceById(sourceId),
    enabled: Boolean(sourceId),
  });

  if (!sourceId) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Источник не найден.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">
          К списку источников
        </LinkAsButton>
      </div>
    );
  }

  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (query.isError) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Источник не найден или ошибка API.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">
          К списку источников
        </LinkAsButton>
      </div>
    );
  }

  const source = query.data;
  if (!source) {
    return (
      <div className="p-4" data-testid="state-not-found-source">
        <p>Источник не найден.</p>
        <LinkAsButton href="/sources" variant="outline" className="mt-2" data-testid="button-back-sources">
          К списку источников
        </LinkAsButton>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <PageHeader title={source.name} description={`Коннектор: ${source.connector} · ${source.category}`} breadcrumbs={`Интеграции / Источники / ${source.name}`} actions={<Button data-testid="button-test-source">Проверить подключение</Button>} />
      <div className="flex flex-wrap gap-2">
        <LinkAsButton href="/sources" variant="outline" data-testid="button-back-sources">
          Назад
        </LinkAsButton>
        <LinkAsButton href={`/connections/new?source=${encodeURIComponent(source.id)}`} data-testid="button-create-connection-from-source">
          Создать подключение
        </LinkAsButton>
      </div>
      <Card className="p-4" data-testid="source-detail-overview">
        <p className="text-sm">Потоков данных: {source.streamCount}</p>
        <p className="text-sm text-muted-foreground">Владелец: {source.owner}</p>
        <p className="text-sm text-muted-foreground">Статус проверки: {source.checkStatus}</p>
      </Card>
    </div>
  );
}
