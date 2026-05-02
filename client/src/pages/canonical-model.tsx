import { useState } from "react";
import { canonicalEntities } from "@/lib/mock-data";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function CanonicalModelPage() {
  const [entityId, setEntityId] = useState(canonicalEntities[0]?.id ?? "");
  const entity = canonicalEntities.find((e) => e.id === entityId) ?? canonicalEntities[0];

  return (
    <div className="p-4">
      <PageHeader title="Каноническая модель" description="Единое представление сущностей и полей для нормализации" breadcrumbs="Данные / Каноническая модель" />
      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <Card className="p-2" data-testid="canonical-entity-list">
          <p className="px-2 py-1 text-xs font-medium text-muted-foreground">Сущности</p>
          <ul className="space-y-1">
            {canonicalEntities.map((e) => (
              <li key={e.id}>
                <button
                  type="button"
                  onClick={() => setEntityId(e.id)}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left text-sm",
                    entityId === e.id ? "bg-secondary font-medium" : "hover:bg-muted",
                  )}
                  data-testid={`canonical-entity-${e.id}`}
                >
                  {e.nameRu}
                </button>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="overflow-auto p-0" data-testid="canonical-fields-table-wrap">
          {entity ? (
            <table className="w-full min-w-[720px] text-left text-sm" aria-label={`Поля сущности ${entity.nameRu}`}>
              <thead className="bg-muted">
                <tr>
                  <th>Поле</th>
                  <th>Тип</th>
                  <th>Обязательное</th>
                  <th>Описание</th>
                  <th>Алиасы источника</th>
                  <th>Правило</th>
                  <th>Пример</th>
                </tr>
              </thead>
              <tbody>
                {entity.fields.map((f) => (
                  <tr key={f.name} className="border-t" data-testid={`row-canonical-field-${f.name.replace(/\./g, "-")}`}>
                    <td className="font-mono text-xs">{f.name}</td>
                    <td>{f.type}</td>
                    <td>{f.required ? "Да" : "Нет"}</td>
                    <td>{f.description}</td>
                    <td className="text-xs text-muted-foreground">{f.aliases}</td>
                    <td>{f.rule}</td>
                    <td className="font-mono text-xs">{f.example}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">Выберите сущность.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
