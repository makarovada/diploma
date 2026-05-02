import { useMemo, useState } from "react";
import type { MappingRow } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const canonicalTargets = ["", "order.external_id", "customer.phone", "order.status", "order.total_amount"];
const transforms = ["", "trim", "to_number", "normalize_phone", "lowercase", "status_map"];

export function MappingTable({ rows: initialRows }: { rows: MappingRow[] }) {
  const [rows, setRows] = useState(initialRows);
  const [search, setSearch] = useState("");
  const [filterUnmapped, setFilterUnmapped] = useState(false);

  const visible = useMemo(() => {
    return rows.filter((r) => {
      if (search && !r.sourceField.toLowerCase().includes(search.toLowerCase())) return false;
      if (filterUnmapped && r.targetField) return false;
      return true;
    });
  }, [rows, search, filterUnmapped]);

  const updateRow = (sourceField: string, patch: Partial<MappingRow>) => {
    setRows((prev) => prev.map((r) => (r.sourceField === sourceField ? { ...r, ...patch } : r)));
  };

  return (
    <div className="rounded-lg border bg-card p-3" data-testid="table-mapping-stream-orders">
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          data-testid="input-mapping-search"
          placeholder="Поиск поля..."
        />
        <Button
          type="button"
          variant={filterUnmapped ? "default" : "outline"}
          onClick={() => setFilterUnmapped((f) => !f)}
          data-testid="button-mapping-filter-unmapped"
        >
          Только несопоставленные
        </Button>
      </div>
      <div className="overflow-auto">
        <table className="w-full min-w-[900px] text-left text-sm" aria-label="Таблица сопоставления">
          <thead>
            <tr className="border-b">
              <th>Source field</th>
              <th>Тип</th>
              <th>Целевое поле</th>
              <th>Преобразование</th>
              <th>Обязательное</th>
              <th>Пример</th>
              <th>Preview</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.sourceField} className="border-b" data-testid={`row-mapping-${r.sourceField}`}>
                <td>{r.sourceField}</td>
                <td>{r.type}</td>
                <td>
                  <select
                    className="h-8 max-w-[200px] rounded-md border bg-background px-1 text-xs"
                    value={r.targetField}
                    onChange={(e) => updateRow(r.sourceField, { targetField: e.target.value, state: e.target.value ? "mapped" : "unmapped" })}
                    data-testid={`select-mapping-target-${r.sourceField}`}
                    aria-label={`Целевое поле для ${r.sourceField}`}
                  >
                    {canonicalTargets.map((t) => (
                      <option key={t || "empty"} value={t}>
                        {t || "— не выбрано —"}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select
                    className="h-8 max-w-[160px] rounded-md border bg-background px-1 text-xs"
                    value={r.transformation}
                    onChange={(e) => updateRow(r.sourceField, { transformation: e.target.value })}
                    data-testid={`select-mapping-transform-${r.sourceField}`}
                    aria-label={`Преобразование для ${r.sourceField}`}
                  >
                    {transforms.map((t) => (
                      <option key={t || "empty"} value={t}>
                        {t || "—"}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{r.required ? "Да" : "Нет"}</td>
                <td className="font-mono text-xs">{r.sample}</td>
                <td className="font-mono text-xs">{r.preview}</td>
                <td>
                  <span
                    className={cn(
                      "text-xs",
                      r.state === "required_missing" && "text-destructive",
                      r.state === "type_mismatch" && "text-warning",
                    )}
                  >
                    {r.state}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
