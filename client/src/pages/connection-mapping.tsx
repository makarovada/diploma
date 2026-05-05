import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { MappingTable } from "@/components/mapping-table";
import { PageHeader } from "@/components/page-header";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";
import type { MappingRow } from "@/lib/types";

const mappingRows: MappingRow[] = [
  { sourceField: "order_id", type: "string", targetField: "order.external_id", transformation: "", required: true, sample: "123", preview: "123", state: "mapped" },
];

export function ConnectionMappingPage() {
  const { connection, id, isLoading, isError } = useConnectionFromPath();
  if (isLoading) return <div className="p-4 text-muted-foreground">Загрузка…</div>;
  if (isError || !connection) {
    return (
      <div className="p-4">
        Не найдено. <LinkAsButton href="/connections">К списку</LinkAsButton>
      </div>
    );
  }
  return (
    <div className="space-y-4 p-4">
      <PageHeader
        title="Маппинг"
        description="Сопоставление полей источника с normalized-моделью"
        breadcrumbs="Интеграции / Подключения / Маппинг"
        actions={
          <Button type="button" variant="outline" data-testid="button-automap">
            Авто-сопоставление
          </Button>
        }
      />
      <ConnectionSubNav connectionId={id} />
      <MappingTable rows={mappingRows} />
    </div>
  );
}
