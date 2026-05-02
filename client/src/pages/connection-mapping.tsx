import { ConnectionSubNav } from "@/components/connection-sub-nav";
import { MappingTable } from "@/components/mapping-table";
import { PageHeader } from "@/components/page-header";
import { mappingRows } from "@/lib/mock-data";
import { useConnectionFromPath } from "@/hooks/use-connection-from-path";
import { LinkAsButton } from "@/components/link-as-button";
import { Button } from "@/components/ui/button";

export function ConnectionMappingPage() {
  const { connection, id } = useConnectionFromPath();
  if (!connection) {
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
        description="Сопоставление полей источника с канонической моделью"
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
