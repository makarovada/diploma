import type { WizardMappingRow } from "@/components/connection-wizard/wizard-types";

const canonicalTargets = ["", "order.external_id", "customer.phone", "order.status", "order.total_amount"];

type Props = {
  rows: WizardMappingRow[];
  onChangeRow: (id: string, patch: Partial<WizardMappingRow>) => void;
};

export function StepMapping({ rows, onChangeRow }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-mapping">
      <p className="mb-3 text-sm text-muted-foreground">
        Сопоставьте поля источника с каноническими полями. Обязательные поля должны быть заполнены перед переходом
        дальше.
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="hint-mapping-empty">
          Нет полей для маппинга — выберите потоки на предыдущем шаге.
        </p>
      ) : (
        <div className="overflow-auto rounded-md border" data-testid="table-wizard-mapping">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="p-2">Поток</th>
                <th className="p-2">Поле источника</th>
                <th className="p-2">Целевое поле</th>
                <th className="p-2">Обязательное</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t" data-testid={`row-wizard-mapping-${r.id}`}>
                  <td className="p-2 font-mono text-xs">{r.streamName}</td>
                  <td className="p-2 font-mono text-xs">{r.sourceField}</td>
                  <td className="p-2">
                    <select
                      className="h-8 max-w-[240px] rounded-md border bg-background px-2 text-xs"
                      value={r.targetField}
                      onChange={(e) =>
                        onChangeRow(r.id, {
                          targetField: e.target.value,
                        })
                      }
                      data-testid={`select-mapping-target-${r.id}`}
                      aria-label={`Целевое поле для ${r.streamName}.${r.sourceField}`}
                    >
                      {canonicalTargets.map((t) => (
                        <option key={t || "empty"} value={t}>
                          {t || "— не выбрано —"}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="p-2">{r.required ? "да" : "нет"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
