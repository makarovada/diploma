import type { SchemaLayout } from "@/components/connection-wizard/wizard-types";
import type { WizardColumnRuleRow } from "@/components/connection-wizard/wizard-types";
import { COLUMN_RULE_TYPES } from "@/components/connection-wizard/column-rule-types";

type Props = {
  layout: SchemaLayout;
  entityLabels: Record<string, string>;
  rows: WizardColumnRuleRow[];
  onChangeRow: (id: string, patch: Partial<WizardColumnRuleRow>) => void;
};

export function ColumnRulesEditor({ layout, entityLabels, rows, onChangeRow }: Props) {
  const showEntity = layout === "entities";

  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-column-rules">
      <p className="mb-3 text-sm text-muted-foreground">
        Для каждого поля задайте имя в normalized-слое и тип нормализации (телефон, почта, ИНН и т.д.). По умолчанию
        поле сохраняется под тем же именем, что в источнике.
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="hint-column-rules-empty">
          Нет полей — сначала обнаружьте колонки
          {showEntity ? " и включите хотя бы одну сущность" : ""}.
        </p>
      ) : (
        <div className="overflow-auto rounded-md border" data-testid="table-wizard-column-rules">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                {showEntity ? <th className="p-2">Сущность</th> : null}
                <th className="p-2">Поле источника</th>
                <th className="p-2">Поле в normalized</th>
                <th className="p-2">Тип</th>
                <th className="p-2">Обязательное</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const entityLabel = r.entity ? (entityLabels[r.entity] ?? r.entity) : "—";
                return (
                  <tr key={r.id} className="border-t" data-testid={`row-wizard-column-rule-${r.id}`}>
                    {showEntity ? (
                      <td className="p-2 text-xs">
                        <span className="font-medium">{entityLabel}</span>
                        {r.entity ? (
                          <span className="ml-1 font-mono text-muted-foreground">({r.entity})</span>
                        ) : null}
                      </td>
                    ) : null}
                    <td className="p-2 font-mono text-xs">{r.sourceField}</td>
                    <td className="p-2">
                      <input
                        className="h-8 w-full max-w-[220px] rounded-md border bg-background px-2 font-mono text-xs"
                        value={r.targetField}
                        onChange={(e) => onChangeRow(r.id, { targetField: e.target.value })}
                        data-testid={`input-column-target-${r.id}`}
                        aria-label={`Поле normalized для ${r.sourceField}`}
                      />
                    </td>
                    <td className="p-2">
                      <select
                        className="h-8 max-w-[180px] rounded-md border bg-background px-2 text-xs"
                        value={r.ruleType}
                        onChange={(e) =>
                          onChangeRow(r.id, {
                            ruleType: e.target.value as WizardColumnRuleRow["ruleType"],
                          })
                        }
                        data-testid={`select-column-type-${r.id}`}
                        aria-label={`Тип нормализации для ${r.sourceField}`}
                      >
                        {COLUMN_RULE_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="p-2">
                      <input
                        type="checkbox"
                        checked={r.required}
                        onChange={(e) => onChangeRow(r.id, { required: e.target.checked })}
                        data-testid={`checkbox-column-required-${r.id}`}
                        aria-label={`Обязательное поле ${r.sourceField}`}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
