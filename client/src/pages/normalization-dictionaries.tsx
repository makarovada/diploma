import { PageHeader } from "@/components/page-header";
import { useQuery } from "@tanstack/react-query";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";

export function NormalizationDictionariesPage() {
  const query = useQuery({
    queryKey: ["normalization", "dictionaries"],
    queryFn: async () => {
      const [currency, unit, status] = await Promise.all([
        fetch(`/api/v1/dictionaries/currency`).then((r) => r.json()),
        fetch(`/api/v1/dictionaries/unit`).then((r) => r.json()),
        fetch(`/api/v1/dictionaries/status`).then((r) => r.json()),
      ]);
      return [
        { id: "dict-currency", name: "Валюты", rows: Array.isArray(currency.items) ? currency.items.length : 0, updatedAt: "—" },
        { id: "dict-unit", name: "Единицы измерения", rows: Array.isArray(unit.items) ? unit.items.length : 0, updatedAt: "—" },
        { id: "dict-status", name: "Статусы", rows: Array.isArray(status.items) ? status.items.length : 0, updatedAt: "—" },
      ];
    },
  });
  if (query.isPending) return <div className="p-4 text-muted-foreground">Загрузка справочников…</div>;
  if (query.isError || !query.data) return <div className="p-4">Не удалось загрузить справочники.</div>;
  const dictionarySummary = query.data;
  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Справочники для нормализации"
        description="Соответствия статусов, валют и кодов"
        breadcrumbs="Данные / Нормализация / Справочники"
        actions={<LinkAsButton href="/dictionaries" variant="outline" data-testid="link-to-admin-dictionaries">Все справочники</LinkAsButton>}
      />
      <div className="overflow-auto rounded-lg border" data-testid="table-norm-dictionaries">
        <table className="w-full text-sm" aria-label="Справочники нормализации">
          <thead className="bg-muted">
            <tr>
              <th>Название</th>
              <th>Строк</th>
              <th>Обновлено</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {dictionarySummary.map((d) => (
              <tr key={d.id} className="border-t">
                <td>{d.name}</td>
                <td>{d.rows}</td>
                <td>{d.updatedAt}</td>
                <td>
                  <Button type="button" variant="outline" className="px-2 py-1 text-xs" data-testid={`button-norm-dict-${d.id}`}>
                    Редактировать
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
