import { cn } from "@/lib/utils";

export type DataPreviewRow = {
  original: string;
  normalized: string;
  type: string;
  hasIssue: boolean;
};

export function DataPreviewTable({ rows }: { rows: DataPreviewRow[] }) {
  return (
    <div className="overflow-auto rounded-lg border bg-card" data-testid="data-preview-table">
      <table className="w-full min-w-[640px] text-left text-sm" aria-label="Предпросмотр: исходное и нормализованное">
        <thead className="bg-muted">
          <tr>
            <th>Исходное</th>
            <th>Нормализованное</th>
            <th>Тип</th>
            <th>Проблема</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t" data-testid={`row-data-preview-${i}`}>
              <td className="font-mono text-xs">{row.original}</td>
              <td className="font-mono text-xs">{row.normalized}</td>
              <td>
                <span className={cn("rounded-full bg-secondary px-2 py-0.5 text-xs")} data-testid={`badge-preview-type-${i}`}>
                  {row.type}
                </span>
              </td>
              <td>{row.hasIssue ? "Да" : "Нет"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
