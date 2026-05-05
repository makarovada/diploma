import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";

export function DictionariesPage() {
  const query = useQuery({
    queryKey: ["dictionaries", "summary"],
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
    <div className="p-4">
      <PageHeader title="Справочники" description="Соответствия для нормализации статусов, валют и кодов" breadcrumbs="Администрирование / Справочники" actions={<Button data-testid="button-add-dictionary">Добавить справочник</Button>} />
      <div className="overflow-auto rounded-lg border" data-testid="table-dictionaries">
        <table className="w-full text-left text-sm" aria-label="Справочники">
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
              <tr key={d.id} className="border-t" data-testid={`row-dictionary-${d.id}`}>
                <td>{d.name}</td>
                <td>{d.rows}</td>
                <td>{d.updatedAt}</td>
                <td>
                  <Button variant="outline" className="px-2 py-1 text-xs" data-testid={`button-open-dictionary-${d.id}`}>
                    Открыть
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
