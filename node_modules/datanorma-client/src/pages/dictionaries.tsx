import { dictionarySummary } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";

export function DictionariesPage() {
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
