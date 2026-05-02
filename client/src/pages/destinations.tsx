import { useQuery } from "@tanstack/react-query";
import { destinations } from "@/lib/mock-data";
import { LinkAsButton } from "@/components/link-as-button";
import { PageHeader } from "@/components/page-header";

const statusRu: Record<string, string> = {
  ok: "Доступен",
  warning: "Внимание",
  error: "Ошибка",
};

export function DestinationsPage() {
  const query = useQuery({
    queryKey: ["destinations"],
    queryFn: async () => {
      await new Promise((r) => setTimeout(r, 150));
      return destinations;
    },
  });

  if (query.isLoading) return <div data-testid="state-loading-destinations" className="p-4">Загрузка приёмников…</div>;
  if (query.isError) return <div data-testid="state-error-destinations" className="p-4">Ошибка загрузки приёмников.</div>;
  const list = query.data ?? [];

  return (
    <div className="p-4">
      <PageHeader title="Приёмники" description="Системы и хранилища для нормализованных данных" breadcrumbs="Интеграции / Приёмники" actions={<LinkAsButton href="/destinations/new" data-testid="button-add-destination">Добавить приёмник</LinkAsButton>} />
      <div className="overflow-auto rounded-lg border" data-testid="table-destinations">
        <table className="w-full min-w-[880px] text-left text-sm" aria-label="Таблица приёмников">
          <thead className="bg-muted">
            <tr>
              <th>Название</th>
              <th>Тип</th>
              <th>Статус</th>
              <th>Схема / база</th>
              <th>Последнее использование</th>
              <th>Подключений</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.map((d) => (
              <tr key={d.id} className="border-t" data-testid={`row-destination-${d.id}`}>
                <td>{d.name}</td>
                <td>{d.type}</td>
                <td>{statusRu[d.status]}</td>
                <td>{d.schemaOrDb}</td>
                <td>{d.lastUsed}</td>
                <td>{d.connectionCount}</td>
                <td>
                  <LinkAsButton href={`/destinations/${d.id}`} variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-destination-${d.id}`}>
                    Открыть
                  </LinkAsButton>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
