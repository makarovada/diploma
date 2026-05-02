import { PageHeader } from "@/components/page-header";
import { DataPreviewTable, type DataPreviewRow } from "@/components/data-preview-table";

const rows: DataPreviewRow[] = [
  { original: "8(912)555-77-88", normalized: "+79125557788", type: "phone", hasIssue: false },
  { original: "RURR", normalized: "RUB", type: "currency", hasIssue: true },
  { original: "02.05.2026 19:30", normalized: "2026-05-02T16:30:00Z", type: "datetime", hasIssue: false },
  { original: "иванов иван", normalized: "Иванов Иван", type: "fio", hasIssue: false },
];

export function DataPreviewPage() {
  return (
    <div className="p-4">
      <PageHeader title="Предпросмотр данных" description="Исходное и нормализованное значение по выборке" breadcrumbs="Данные / Предпросмотр" />
      <DataPreviewTable rows={rows} />
    </div>
  );
}
