import type { EltConnectionColumnRuleDto } from "@/lib/api-types";
import { COLUMN_RULE_TYPES } from "@/components/connection-wizard/column-rule-types";

type Props = {
  rows: EltConnectionColumnRuleDto[];
  entityLabels?: Record<string, string>;
  showEntity?: boolean;
  readOnly?: boolean;
  onChangeRow?: (sourceField: string, entity: string | null, patch: Partial<EltConnectionColumnRuleDto>) => void;
};

export function MappingTable({
  rows,
  entityLabels = {},
  showEntity = false,
  readOnly = true,
  onChangeRow,
}: Props) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground" data-testid="table-mapping-empty">
        Правила колонок не заданы. Создайте подключение через мастер или задайте маппинг.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-3" data-testid="table-mapping">
      <div className="overflow-auto">
        <table className="w-full min-w-[720px] text-left text-sm" aria-label="Таблица правил колонок">
          <thead>
            <tr className="border-b bg-muted">
              {showEntity ? <th className="p-2">Сущность</th> : null}
              <th className="p-2">Поле источника</th>
              <th className="p-2">Тип</th>
              <th className="p-2">Поле в normalized</th>
              <th className="p-2">Обязательное</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const key = `${r.entity ?? ""}:${r.source_field}`;
              const entityLabel = r.entity ? (entityLabels[r.entity] ?? r.entity) : "—";
              return (
                <tr key={key} className="border-b" data-testid={`row-mapping-${key}`}>
                  {showEntity ? <td className="p-2 text-xs">{entityLabel}</td> : null}
                  <td className="p-2 font-mono text-xs">{r.source_field}</td>
                  <td className="p-2">
                    {readOnly ? (
                      <span className="font-mono text-xs">{r.type}</span>
                    ) : (
                      <select
                        className="h-8 max-w-[160px] rounded-md border bg-background px-1 text-xs"
                        value={r.type}
                        onChange={(e) =>
                          onChangeRow?.(r.source_field, r.entity, { type: e.target.value })
                        }
                        data-testid={`select-mapping-type-${key}`}
                      >
                        {COLUMN_RULE_TYPES.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="p-2 font-mono text-xs">{r.target_field}</td>
                  <td className="p-2">{r.required ? "да" : "нет"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
